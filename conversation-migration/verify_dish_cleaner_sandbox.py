#!/usr/bin/env python3
"""verify_dish_cleaner_sandbox.py — Verification tool for dish_cleaner Desktop conversation migration

Inspects target Debian Antigravity Desktop storage to verify that migrated conversations match
the Windows source sandbox package in schema, integrity, step counts, brain logs, and that
agyhub_summaries_proto.pb contains remapped Debian workspace URIs and project GUIDs.
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path


def decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    val, shift = 0, 0
    while True:
        if pos >= len(data):
            raise IndexError("Unexpected end of varint stream")
        b = data[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return val, pos


def parse_agyhub_proto_entries(data: bytes) -> dict[str, bytes]:
    pos = 0
    entries = {}
    while pos < len(data):
        tag, pos = decode_varint(data, pos)
        fn, wt = tag >> 3, tag & 7
        length, pos = decode_varint(data, pos)
        entry_bytes = data[pos:pos + length]
        pos += length

        ep = 0
        uid, inner = None, None
        while ep < len(entry_bytes):
            t, ep = decode_varint(entry_bytes, ep)
            efn, ewt = t >> 3, t & 7
            if ewt == 2:
                el, ep = decode_varint(entry_bytes, ep)
                c = entry_bytes[ep:ep + el]
                ep += el
                if efn == 1:
                    uid = c.decode("utf-8", errors="replace")
                elif efn == 2:
                    inner = c
            elif ewt == 0:
                _, ep = decode_varint(entry_bytes, ep)
            elif ewt == 1:
                ep += 8
            elif ewt == 5:
                ep += 4
        if uid and inner:
            entries[uid] = inner
    return entries


def check_sqlite_integrity(db_path: Path) -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        c = conn.cursor()
        c.execute("PRAGMA integrity_check")
        row = c.fetchone()
        conn.close()
        res = row[0] if row else "unknown"
        return res == "ok", res
    except Exception as e:
        return False, str(e)


def get_table_counts(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    counts = {}
    for t in tables:
        c.execute(f"SELECT count(*) FROM {t}")
        counts[t] = c.fetchone()[0]
    conn.close()
    return counts


def verify_desktop_migration(plan_path: Path) -> int:
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    pkg_dir = Path(plan["source_package"]["path"])
    meta_path = pkg_dir / "migration_metadata.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        expected_schemas = meta.get("schema_info", {}).get("schema_fingerprints", {})
    else:
        expected_schemas = {}

    gemini_dir = Path.home() / ".gemini"
    conv_dir = gemini_dir / "antigravity" / "conversations"
    brain_dir = gemini_dir / "antigravity" / "brain"
    proto_file = gemini_dir / "antigravity" / "agyhub_summaries_proto.pb"

    target_uri = plan["target_environment"]["target_workspace_uri"]

    print("==================================================================")
    print("  Antigravity Desktop Migration Verification — dish_cleaner")
    print("==================================================================")
    print(f"Plan:                      {plan_path}")
    print(f"Target Conversations Dir:  {conv_dir}")
    print(f"Target Brain Dir:          {brain_dir}")
    print(f"Desktop Index Proto:       {proto_file}")

    active_conversations = [c for c in plan["conversations"] if c.get("action") == "IMPORT_TO_CLEANAI"]
    deferred_conversations = [c for c in plan["conversations"] if c.get("action") != "IMPORT_TO_CLEANAI"]

    print(f"\nEvaluating {len(active_conversations)} expected active conversations...")

    # Parse agyhub proto
    proto_entries = {}
    if proto_file.exists():
        with open(proto_file, "rb") as f:
            proto_entries = parse_agyhub_proto_entries(f.read())
        print(f"[+] agyhub_summaries_proto.pb parsed ({len(proto_entries)} total conversations in index)")
    else:
        print("[!] Warning: agyhub_summaries_proto.pb does not exist!")

    all_pass = True

    for c in active_conversations:
        cid = c["conversation_id"]
        print(f"\n--- Checking conversation: {cid} ({c['preview']}) ---")

        # 1. DB file existence
        db_file = conv_dir / f"{cid}.db"
        if not db_file.exists():
            print(f"  [!] Missing DB file: {db_file}")
            all_pass = False
            continue
        print(f"  [+] DB file present: {db_file.name} ({db_file.stat().st_size} bytes)")

        # 2. SQLite integrity
        ok, res = check_sqlite_integrity(db_file)
        if not ok:
            print(f"  [!] SQLite integrity failure: {res}")
            all_pass = False
        else:
            print(f"  [+] SQLite integrity: ok")

        # 3. Row counts comparison
        actual_counts = get_table_counts(db_file)
        if cid in expected_schemas:
            exp_counts = expected_schemas[cid].get("row_counts", {})
            counts_match = True
            for t, exp_c in exp_counts.items():
                act_c = actual_counts.get(t, -1)
                if act_c != exp_c:
                    print(f"  [!] Count mismatch in {t}: expected {exp_c}, got {act_c}")
                    counts_match = False
                    all_pass = False
            if counts_match:
                print(f"  [+] Table row counts match package metadata: {actual_counts}")

        # 4. Brain directory
        b_dir = brain_dir / cid
        if not b_dir.exists():
            print(f"  [!] Missing brain dir: {b_dir}")
            all_pass = False
        else:
            transcript = b_dir / ".system_generated" / "logs" / "transcript.jsonl"
            has_transcript = transcript.exists()
            print(f"  [+] Brain directory present (transcript.jsonl exists: {has_transcript})")

        # 5. Desktop Proto Index verification
        if cid not in proto_entries:
            print(f"  [!] Missing from agyhub_summaries_proto.pb index: {cid}")
            all_pass = False
        else:
            inner = proto_entries[cid]
            # Check for Debian target URI
            has_target_uri = target_uri.encode() in inner
            has_windows_uri = b"file:///e" in inner or b"file:///c" in inner
            has_windows_guid = b"088c8445" in inner

            if not has_target_uri:
                print(f"  [!] Target workspace URI not found in protobuf metadata for {cid}")
                all_pass = False
            elif has_windows_uri or has_windows_guid:
                print(f"  [!] Residual Windows metadata detected in protobuf for {cid}")
                all_pass = False
            else:
                print(f"  [+] agyhub_summaries_proto.pb index entry verified (Debian URI active, 0 Windows residual)")

    print(f"\n--- Deferred conversations ({len(deferred_conversations)}) ---")
    for c in deferred_conversations:
        cid = c["conversation_id"]
        db_file = conv_dir / f"{cid}.db"
        present = db_file.exists()
        print(f"  - {cid} ({c['preview']}): Action={c['action']} (Present in target: {present})")

    print("\n==================================================================")
    if all_pass:
        print("  VERIFICATION RESULT: PASS")
        return 0
    else:
        print("  VERIFICATION RESULT: FAIL (One or more checks failed or files not yet imported)")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Verify dish_cleaner Desktop conversation migration")
    parser.add_argument("--plan", type=Path, default=Path(__file__).parent / "MIGRATION_PLAN.json", help="Path to MIGRATION_PLAN.json")
    args = parser.parse_args()
    sys.exit(verify_desktop_migration(args.plan))


if __name__ == "__main__":
    main()
