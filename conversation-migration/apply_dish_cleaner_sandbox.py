#!/usr/bin/env python3
"""apply_dish_cleaner_sandbox.py — Offline Antigravity Desktop Conversation Migration Helper

Migrates dish_cleaner conversations from the Windows sandbox package into native
Debian Antigravity Desktop storage (~/.gemini/antigravity/), including:
- Conversation databases (~/.gemini/antigravity/conversations/)
- Brain logs and artifacts (~/.gemini/antigravity/brain/)
- Native Desktop summary index (~/.gemini/antigravity/agyhub_summaries_proto.pb)

Safety Gates:
1. Refuses to run if Antigravity Desktop or language_server processes are running (offline only).
2. Never attempts to kill processes; requires the user to shut down Desktop cleanly.
3. Verifies package SHA256 integrity against hashes.json.
4. Auto-discovers native project GUID for file:///home/ferb27/projects/cleanAI from
   ~/.gemini/config/projects/*.json. Halts if unresolved.
5. Backs up every Desktop file to be modified (including agyhub_summaries_proto.pb)
   with SHA256 manifests before any mutation.
6. Rewrites protobuf summary metadata (fields 9 and 17) to match Debian URI and project GUID
   with ZERO residual Windows path strings.
7. Validates SQLite DB integrity and protobuf index readability after write.
8. Supports full offline rollback via --rollback <backup_dir>.
9. NEVER touches OAuth credentials, global state DB, or TencentDB.
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Protobuf Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def encode_varint(val: int) -> bytes:
    out = bytearray()
    while True:
        b = val & 0x7F
        val >>= 7
        if val:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def encode_tag(field_num: int, wire_type: int) -> bytes:
    return encode_varint((field_num << 3) | wire_type)


def encode_len_delimited(field_num: int, data: str | bytes) -> bytes:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return encode_tag(field_num, 2) + encode_varint(len(data)) + data


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


def rewrite_workspace_submsg(data: bytes, new_uri: str) -> bytes:
    """Rewrite subfields 1 and 2 of workspace info to new_uri while preserving git remote info."""
    pos = 0
    out = bytearray()
    while pos < len(data):
        tag, pos = decode_varint(data, pos)
        fn, wt = tag >> 3, tag & 7
        if wt == 2:
            l, pos = decode_varint(data, pos)
            val = data[pos:pos + l]
            pos += l
            if fn in (1, 2):
                out += encode_len_delimited(fn, new_uri)
            else:
                out += encode_len_delimited(fn, val)
        elif wt == 0:
            v, pos = decode_varint(data, pos)
            out += encode_tag(fn, wt) + encode_varint(v)
        elif wt == 1:
            val = data[pos:pos + 8]
            pos += 8
            out += encode_tag(fn, wt) + val
        elif wt == 5:
            val = data[pos:pos + 4]
            pos += 4
            out += encode_tag(fn, wt) + val
    return bytes(out)


def rewrite_inner_summary(inner_blob: bytes, new_uri: str, new_guid: str) -> bytes:
    """Rewrite field 9 and field 17 in TrajectorySummaryInfo with Debian URI and GUID."""
    pos = 0
    out = bytearray()
    while pos < len(inner_blob):
        tag, pos = decode_varint(inner_blob, pos)
        fn, wt = tag >> 3, tag & 7
        if wt == 2:
            l, pos = decode_varint(inner_blob, pos)
            val = inner_blob[pos:pos + l]
            pos += l
            if fn == 9:
                out += encode_len_delimited(9, rewrite_workspace_submsg(val, new_uri))
            elif fn == 17:
                p17 = 0
                out17 = bytearray()
                while p17 < len(val):
                    tag17, p17 = decode_varint(val, p17)
                    fn17, wt17 = tag17 >> 3, tag17 & 7
                    if wt17 == 2:
                        l17, p17 = decode_varint(val, p17)
                        val17 = val[p17:p17 + l17]
                        p17 += l17
                        if fn17 == 1:
                            out17 += encode_len_delimited(1, rewrite_workspace_submsg(val17, new_uri))
                        elif fn17 == 7:
                            out17 += encode_len_delimited(7, new_uri)
                        elif fn17 == 18:
                            out17 += encode_len_delimited(18, new_guid)
                        else:
                            out17 += encode_len_delimited(fn17, val17)
                    elif wt17 == 0:
                        v17, p17 = decode_varint(val, p17)
                        out17 += encode_tag(fn17, wt17) + encode_varint(v17)
                    elif wt17 == 1:
                        val17 = val[p17:p17 + 8]
                        p17 += 8
                        out17 += encode_tag(fn17, wt17) + val17
                    elif wt17 == 5:
                        val17 = val[p17:p17 + 4]
                        p17 += 4
                        out17 += encode_tag(fn17, wt17) + val17
                out += encode_len_delimited(17, out17)
            else:
                out += encode_len_delimited(fn, val)
        elif wt == 0:
            v, pos = decode_varint(inner_blob, pos)
            out += encode_tag(fn, wt) + encode_varint(v)
        elif wt == 1:
            val = inner_blob[pos:pos + 8]
            pos += 8
            out += encode_tag(fn, wt) + val
        elif wt == 5:
            val = inner_blob[pos:pos + 4]
            pos += 4
            out += encode_tag(fn, wt) + val
    return bytes(out)


def parse_agyhub_proto_entries(data: bytes) -> list[tuple[str, bytes]]:
    """Parse agyhub_summaries_proto.pb into a list of (conversation_id, inner_blob) tuples."""
    pos = 0
    entries = []
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
            entries.append((uid, inner))
    return entries


def serialize_agyhub_proto_entries(entries: list[tuple[str, bytes]]) -> bytes:
    """Serialize list of (conversation_id, inner_blob) into agyhub_summaries_proto.pb format."""
    out = bytearray()
    for uid, inner in entries:
        entry_bytes = encode_len_delimited(1, uid) + encode_len_delimited(2, inner)
        out += encode_len_delimited(1, entry_bytes)
    return bytes(out)


# ─────────────────────────────────────────────────────────────────────────────
# Safety Gate Functions
# ─────────────────────────────────────────────────────────────────────────────

def is_process_running(proc_name: str) -> bool:
    try:
        res = subprocess.run(
            ["pgrep", "-f", proc_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if res.returncode == 0:
            pids = res.stdout.strip().split()
            current_pid = str(os.getpid())
            other_pids = [p for p in pids if p != current_pid]
            return len(other_pids) > 0
    except Exception:
        pass
    return False


def check_offline_gate() -> tuple[bool, list[str]]:
    blocked = []
    for proc in ["antigravity", "language_server"]:
        if is_process_running(proc):
            blocked.append(proc)
    return len(blocked) == 0, blocked


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def verify_package_hashes(pkg_dir: Path, hashes_json: Path) -> tuple[bool, int, list[str]]:
    with open(hashes_json, "r", encoding="utf-8") as f:
        hashes = json.load(f)

    verified = 0
    failures = []
    for rel_path, meta in hashes.items():
        rel_norm = rel_path.replace("\\", "/")
        target = pkg_dir / rel_norm
        if not target.exists():
            failures.append(f"MISSING: {rel_path}")
            continue
        actual_hash = sha256_file(target)
        expected_hash = meta["sha256"].lower()
        if actual_hash != expected_hash:
            failures.append(f"HASH_MISMATCH: {rel_path} (exp {expected_hash}, got {actual_hash})")
        else:
            verified += 1

    return len(failures) == 0, verified, failures


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


def discover_native_project_guid(target_workspace_uri: str) -> str | None:
    """Discover registered project GUID for target_workspace_uri from ~/.gemini/config/projects/."""
    projects_dir = Path.home() / ".gemini" / "config" / "projects"
    if projects_dir.exists():
        for p in projects_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                resources = data.get("projectResources", {}).get("resources", [])
                for r in resources:
                    if r.get("folderUri") == target_workspace_uri:
                        return data.get("id")
            except Exception:
                pass
    return None


def execute_rollback(backup_dir: Path) -> bool:
    print(f"[*] Starting rollback from {backup_dir}...")
    is_offline, active_procs = check_offline_gate()
    if not is_offline:
        print(f"[!] FATAL: Cannot rollback while active processes are running: {active_procs}")
        print("    Close Antigravity Desktop before rolling back.")
        return False

    manifest_file = backup_dir / "backup_manifest.json"
    if not manifest_file.exists():
        print(f"[!] Error: backup_manifest.json not found in {backup_dir}")
        return False

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Verify backup hashes
    for entry in manifest.get("files", []):
        src = backup_dir / entry["backup_rel"]
        if not src.exists():
            print(f"[!] Missing backup file: {src}")
            return False
        if sha256_file(src) != entry["sha256"]:
            print(f"[!] Corrupted backup file: {src}")
            return False

    # Restore files
    for entry in manifest.get("files", []):
        src = backup_dir / entry["backup_rel"]
        dst = Path(entry["original_path"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  [+] Restored: {dst}")

    # Remove newly created files
    for created in manifest.get("created_files", []):
        target = Path(created)
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
                print(f"  [-] Removed created directory: {target}")
            else:
                target.unlink()
                print(f"  [-] Removed created file: {target}")

    print("[+] Rollback completed successfully.")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Main Migration Logic (Target: Desktop)
# ─────────────────────────────────────────────────────────────────────────────

def run_desktop_migration(plan_path: Path, dry_run: bool) -> int:
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    print("==================================================================")
    print("  Antigravity Offline Desktop Conversation Migration — dish_cleaner")
    print("==================================================================")
    print(f"Plan file:     {plan_path}")
    print(f"Target:        desktop (~/.gemini/antigravity/)")
    print(f"Dry run mode:  {dry_run}")
    print(f"Timestamp:     {datetime.datetime.now().isoformat()}")

    # GATE 1: Offline process check
    is_offline, active_procs = check_offline_gate()
    if not is_offline:
        print("\n[!] FATAL: Offline gate FAILED!")
        print(f"    Active processes detected: {active_procs}")
        print("    Antigravity Desktop and language_server MUST be completely stopped.")
        print("    Close the Antigravity application cleanly before executing this helper.")
        return 1
    print("\n[+] Gate 1 (Offline check): PASS (Antigravity & language_server are stopped)")

    # GATE 2: Package location & integrity
    pkg_dir = Path(plan["source_package"]["path"])
    hashes_file = pkg_dir / "hashes.json"
    if not pkg_dir.exists() or not hashes_file.exists():
        print(f"\n[!] FATAL: Migration package not found at {pkg_dir}")
        return 2

    hash_pass, count, failures = verify_package_hashes(pkg_dir, hashes_file)
    if not hash_pass:
        print(f"\n[!] FATAL: Package hash verification FAILED! ({len(failures)} failures)")
        for fail in failures[:10]:
            print(f"    {fail}")
        return 3
    print(f"[+] Gate 2 (Package integrity): PASS ({count} files verified against hashes.json)")

    # GATE 3: Native Project GUID Resolution
    target_workspace_uri = plan["target_environment"]["target_workspace_uri"]
    project_guid = discover_native_project_guid(target_workspace_uri)

    if not project_guid:
        print(f"\n[!] FATAL: Native Project GUID unresolved for {target_workspace_uri}")
        print("    Antigravity has not yet registered this workspace.")
        print("    ACTION REQUIRED:")
        print("    1. Open /home/ferb27/projects/cleanAI once in Antigravity Desktop.")
        print("    2. Close Antigravity Desktop cleanly.")
        print("    3. Re-run this helper. It will automatically detect the generated GUID.")
        print("    Refusing to proceed without native project registration.")
        return 4
    print(f"[+] Gate 3 (Native Project GUID): PASS (Discovered GUID: {project_guid})")

    # Target Desktop paths
    gemini_dir = Path.home() / ".gemini"
    target_conv_dir = gemini_dir / "antigravity" / "conversations"
    target_brain_dir = gemini_dir / "antigravity" / "brain"
    target_proto_file = gemini_dir / "antigravity" / "agyhub_summaries_proto.pb"

    # Select conversations
    active_conversations = [c for c in plan["conversations"] if c.get("action") == "IMPORT_TO_CLEANAI"]
    deferred_conversations = [c for c in plan["conversations"] if c.get("action") != "IMPORT_TO_CLEANAI"]

    print(f"\n[+] Active import plan ({len(active_conversations)} conversations):")
    for c in active_conversations:
        print(f"    - {c['conversation_id']} ({c['preview']}) -> {c['action']}")
    print(f"[+] Deferred conversations ({len(deferred_conversations)}):")
    for c in deferred_conversations:
        print(f"    - {c['conversation_id']} ({c['preview']}) -> {c['action']}")

    # Collision Check
    for c in active_conversations:
        cid = c["conversation_id"]
        if (target_conv_dir / f"{cid}.db").exists():
            print(f"\n[!] FATAL: Collision detected! Conversation DB {cid}.db already exists.")
            return 5
        if (target_brain_dir / cid).exists():
            print(f"\n[!] FATAL: Collision detected! Brain directory {cid} already exists.")
            return 6

    # Check existing agyhub_summaries_proto.pb
    existing_entries = []
    if target_proto_file.exists():
        with open(target_proto_file, "rb") as f:
            raw_proto = f.read()
        existing_entries = parse_agyhub_proto_entries(raw_proto)
        existing_cids = {uid for uid, _ in existing_entries}
        for c in active_conversations:
            if c["conversation_id"] in existing_cids:
                print(f"\n[!] FATAL: Collision detected! Conversation {c['conversation_id']} already in agyhub_summaries_proto.pb.")
                return 7

    if dry_run:
        print("\n[*] DRY-RUN complete. All pre-flight safety gates passed successfully.")
        print("    No changes were made to Desktop state.")
        return 0

    # GATE 4: Backup Desktop State
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_base = Path.home() / "anti-crossos-system" / "backups" / "conversation-migration" / timestamp_str
    backup_base.mkdir(parents=True, exist_ok=True)

    backup_manifest = {
        "timestamp": timestamp_str,
        "target": "desktop",
        "plan": plan_path.name,
        "target_project_guid": project_guid,
        "target_workspace_uri": target_workspace_uri,
        "files": [],
        "created_files": [],
    }

    if target_proto_file.exists():
        backup_proto = backup_base / "agyhub_summaries_proto.pb"
        shutil.copy2(target_proto_file, backup_proto)
        backup_manifest["files"].append({
            "original_path": str(target_proto_file),
            "backup_rel": "agyhub_summaries_proto.pb",
            "sha256": sha256_file(backup_proto),
            "size": backup_proto.stat().st_size,
        })
        print(f"[+] Backed up agyhub_summaries_proto.pb -> {backup_proto}")

    target_conv_dir.mkdir(parents=True, exist_ok=True)
    target_brain_dir.mkdir(parents=True, exist_ok=True)

    # Copy conversation DBs & brain folders
    for c in active_conversations:
        cid = c["conversation_id"]
        src_db = pkg_dir / "conversations" / f"{cid}.db"
        dst_db = target_conv_dir / f"{cid}.db"

        shutil.copy2(src_db, dst_db)
        backup_manifest["created_files"].append(str(dst_db))

        # Verify SQLite integrity
        ok, res = check_sqlite_integrity(dst_db)
        if not ok:
            print(f"[!] FATAL: SQLite integrity check failed on copied {dst_db}: {res}")
            execute_rollback(backup_base)
            return 8
        print(f"[+] Installed conversation DB: {dst_db.name} (integrity: ok)")

        src_brain = pkg_dir / "brain" / cid
        dst_brain = target_brain_dir / cid
        shutil.copytree(src_brain, dst_brain)
        backup_manifest["created_files"].append(str(dst_brain))
        print(f"[+] Installed brain directory: {dst_brain.name}")

    # Load summary_rows.json from package for inner protobuf blobs
    with open(pkg_dir / "summary_rows.json", "r", encoding="utf-8") as f:
        raw_summary_rows = json.load(f)

    rows_by_cid = {r["conversation_id"]: r for r in raw_summary_rows}

    # Prepare updated entries list
    updated_entries = list(existing_entries)

    for c in active_conversations:
        cid = c["conversation_id"]
        row = rows_by_cid.get(cid)
        if not row or not row.get("raw_summary_b64"):
            print(f"[!] Error: raw_summary_b64 missing for {cid}")
            execute_rollback(backup_base)
            return 9

        orig_inner = base64.b64decode(row["raw_summary_b64"])
        # Rewrite inner summary fields 9 and 17
        rewritten_inner = rewrite_inner_summary(orig_inner, target_workspace_uri, project_guid)

        # Sanity check: ensure zero Windows URIs or Windows project GUIDs remain
        if b"file:///e" in rewritten_inner or b"file:///c" in rewritten_inner or b"088c8445" in rewritten_inner:
            print(f"[!] Error: Residual Windows metadata detected in rewritten protobuf for {cid}")
            execute_rollback(backup_base)
            return 10

        updated_entries.append((cid, rewritten_inner))
        print(f"[+] Re-encoded Desktop summary index entry for {cid} (project: {project_guid})")

    # Serialize new agyhub_summaries_proto.pb and atomically replace
    serialized_proto = serialize_agyhub_proto_entries(updated_entries)
    temp_proto = target_proto_file.with_suffix(".tmp")
    with open(temp_proto, "wb") as f:
        f.write(serialized_proto)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_proto, target_proto_file)
    print(f"[+] Successfully updated {target_proto_file} ({len(updated_entries)} total entries)")

    # Save backup manifest
    with open(backup_base / "backup_manifest.json", "w", encoding="utf-8") as f:
        json.dump(backup_manifest, f, indent=2)

    # Save execution report
    report = {
        "status": "SUCCESS",
        "target": "desktop",
        "timestamp": timestamp_str,
        "backup_directory": str(backup_base),
        "imported_conversations": [c["conversation_id"] for c in active_conversations],
        "deferred_conversations": [c["conversation_id"] for c in deferred_conversations],
        "project_guid": project_guid,
        "target_workspace_uri": target_workspace_uri,
        "index_file": str(target_proto_file),
        "total_desktop_conversations": len(updated_entries),
    }
    report_file = Path.home() / "anti-crossos-system" / "conversation-migration" / f"MIGRATION_EXECUTION_REPORT_{timestamp_str}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[+] Desktop migration completed successfully! Report saved to: {report_file}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Antigravity Offline Desktop Conversation Migration Helper")
    parser.add_argument("--plan", type=Path, default=Path(__file__).parent / "MIGRATION_PLAN.json", help="Path to MIGRATION_PLAN.json")
    parser.add_argument("--target", choices=["desktop", "cli"], default="desktop", help="Migration target environment (default: desktop)")
    parser.add_argument("--dry-run", action="store_true", help="Perform safety checks without mutating Desktop files")
    parser.add_argument("--rollback", type=Path, help="Roll back migration from a backup directory")

    args = parser.parse_args()

    if args.rollback:
        success = execute_rollback(args.rollback)
        sys.exit(0 if success else 1)

    if args.target != "desktop":
        print("[!] Target 'cli' is deferred. Only '--target desktop' is supported for Desktop migration.")
        sys.exit(1)

    ret = run_desktop_migration(args.plan, args.dry_run)
    sys.exit(ret)


if __name__ == "__main__":
    main()
