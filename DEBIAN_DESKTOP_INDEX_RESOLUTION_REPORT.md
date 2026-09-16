# Antigravity Desktop Index Resolution Report

**Date:** 2026-09-16  
**Environment:** Debian 13 (Trixie), Linux 6.12.43+bpo-amd64  
**Antigravity Desktop Version:** 2.10.0  
**Language Server Version:** 2.10.0  
**CLI Version (`agy`):** 1.2.4  
**Workspace Under Investigation:** `/home/ferb27/projects/cleanAI` (`file:///home/ferb27/projects/cleanAI`)  
**Shared Migration Package:** `/media/ferb27/Store data/anti-conversation-migration/sandbox/dish_cleaner/`  

---

## A. Result

```text
READY_FOR_NATIVE_PROJECT_REGISTRATION
```

The authoritative Desktop conversation index store has been conclusively resolved to **`~/.gemini/antigravity/agyhub_summaries_proto.pb`** (Model A). The migration tooling has been updated to `--target desktop` with zero dependence on the CLI SQLite database. Live Desktop state was untouched during this audit.

---

## B. Desktop Storage Model

Desktop and CLI run with distinct storage roots and distinct summary architectures:

| Subsystem | Storage Root | Conversation Database | Brain Logs & Artifacts | Sidebar Index Store |
| :--- | :--- | :--- | :--- | :--- |
| **Desktop (2.10.0)** | `~/.gemini/antigravity/` | `conversations/<id>.db` | `brain/<id>/` | **`agyhub_summaries_proto.pb`** |
| **CLI (`agy` 1.2.4)** | `~/.gemini/antigravity-cli/` | `conversations/<id>.db` | `brain/<id>/` | `conversation_summaries.db` (SQLite) |

Process inspection of active PID 3614 (`language_server`) confirms:
```text
/home/ferb27/.local/opt/antigravity/resources/bin/language_server \
  --subclient_type hub \
  --override_ide_version 2.10.0 \
  --app_data_dir antigravity
```
`--app_data_dir antigravity` binds `language_server` directly to `~/.gemini/antigravity/`. It manages `agyhub_summaries_proto.pb` as the active index for `ConversationService` and sidebar browsing.

---

## C. Known Visible Conversation Trace

Four native Desktop conversations were audited across all candidate index and storage locations:

| Conversation UUID | Title / Preview | `agyhub_summaries_proto.pb` | Desktop `state.vscdb` | CLI `conversation_summaries.db` | Desktop `conversations/<id>.db` | Desktop `brain/<id>/` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `8c18b20e-c2e6-4760-a8b0-2be7e31cb00e` | Han_Nom_OCR (NomNaOCR audit) | **YES** | **NO** | **NO** | **YES** | **YES** |
| `b49c7afa-473e-47eb-ab54-51dd55e755b0` | Debian Pre-Deployment System Audit | **YES** | **NO** | **NO** | **YES** | **YES** |
| `208e3c71-1480-4e39-bc19-d48bd17152a4` | GNOME macOS Tahoe Installation | **YES** | **NO** | **NO** | **YES** | **YES** |
| `f9e8963c-7254-4acd-9c27-770f267bfca5` | Debian Handoff Folder Inspection | **YES** | **NO** | **NO** | **YES** | **YES** |

**Primary Trace Subject:** `8c18b20e-c2e6-4760-a8b0-2be7e31cb00e`
- Visible in Desktop sidebar: **YES**
- Present in `agyhub_summaries_proto.pb`: **YES** (inner blob length: 668 bytes)
- Present in Desktop `state.vscdb`: **NO**
- Present in CLI `conversation_summaries.db`: **NO**

---

## D. CLI vs Desktop Separation

- **Relationship:** **`INDEPENDENT`**
- The CLI database `~/.gemini/antigravity-cli/conversation_summaries.db` contains exactly one row (`60bdca5b-97ae-46b6-903c-615d21a8985b`), which does not appear in `agyhub_summaries_proto.pb` and is not rendered in Desktop Antigravity.
- Conversely, none of the 4 Desktop conversations exist in `conversation_summaries.db`.
- Inserting records into the CLI database has **zero effect** on Antigravity Desktop's sidebar.

---

## E. agyhub_summaries_proto Findings

Binary dissection of `~/.gemini/antigravity/agyhub_summaries_proto.pb` revealed its exact protobuf message schema:

```protobuf
message TrajectorySummariesProto {
    repeated TrajectorySummaryEntry entries = 1;
}

message TrajectorySummaryEntry {
    string key = 1;             // conversation_id UUID
    bytes value = 2;            // TrajectorySummaryInfo inner message
}
```

The inner message (`TrajectorySummaryInfo`) contains 12 active fields:
1. `field 1` (string): Title / preview text
2. `field 2` (varint): Step count
3. `field 3` (message): Timestamp (created/modified)
4. `field 4` (string): `trajectory_id` UUID
5. `field 5` (varint): Status flag (`1` = idle)
6. `field 7` (message): Timestamp (last user input)
7. `field 9` (message): Workspace info (subfield 1 & 2 = workspace URI, subfield 3 = git remote info, subfield 4 = branch)
8. `field 10` (message): Timestamp
9. `field 15` (message): Secondary preview / timestamp
10. `field 16` (varint): `not_fully_idle` flag
11. `field 17` (message): Detailed project/workspace binding (17.1 = workspace info, 17.6 = conversation ID, 17.7 = workspace URI, 17.18 = project GUID)
12. `field 22` (varint): Trajectory type (`4` = interactive chat)

---

## F. state.vscdb Findings

Audited `/home/ferb27/.config/Antigravity/User/globalStorage/state.vscdb`:
- **Last Modified Timestamp:** 2026-08-26 10:43 (untouched during active sessions).
- **Process Lock:** Not opened by `antigravity` or `language_server` (verified via `lsof`).
- **Key Inspection:**
  - `antigravityUnifiedStateSync.trajectorySummaries` = `""` (empty string)
  - `antigravityUnifiedStateSync.sidebarWorkspaces` = `""` (empty string)
  - `chat.ChatSessionStore.index` = `{"version":1,"entries":{}}`
- **Conclusion:** Antigravity Desktop 2.10.0 on Debian has decoupled conversation index storage from VSCode's `state.vscdb`.

---

## G. Project Registration Model

Inspection of `~/.gemini/config/projects/`:
- Existing configurations:
  - `3699d26c-1beb-48a9-87b4-7f0e0734b680.json` (`anti-crossos-system`)
  - `f13530cd-5147-4717-a4c0-24478aa885a8.json` (`Han_Nom_OCR`)
  - `default-cli-project.json`
  - `outside-of-project.json`
- `cleanAI` (`file:///home/ferb27/projects/cleanAI`): **NOT YET REGISTERED**.
- **Status:** `PROJECT_GUID_STATUS: UNRESOLVED`.
- Policy: Never fabricate a project GUID using arbitrary generation flags. Antigravity Desktop must register the project natively upon first folder open.

---

## H. Desktop 2.10 Compatibility

- **Windows Source Version:** 2.14.0
- **Debian Target Version:** 2.10.0
- **Comparison:**
  - In Windows 2.14.0, each `TrajectorySummaryInfo` protobuf was exported in `conversation_summaries.db` under column `raw_summary`.
  - In Debian 2.10.0, the inner protobuf structure in `agyhub_summaries_proto.pb` has the **identical 12 fields** with identical tags, wire types, and subfield definitions.
  - **Result:** 100% binary compatibility for `TrajectorySummaryInfo`.

---

## I. Reference Tool Findings

Inspected `FutureisinPast/antigravity-conversation-fix` (`rebuild_conversations.py`):
- Originally targeted legacy Antigravity IDE where `trajectorySummaries` was stored base64-encoded in `state.vscdb`.
- **Reusable logic:** Varint encoding/decoding, field stripping, workspace submessage construction (subfields 1, 2, 3, 4).
- **Debian 2.10 adaptation:** The protobuf payload is saved directly to `agyhub_summaries_proto.pb` (binary protobuf format) rather than injected into `state.vscdb`.

---

## J. Authoritative Registration Set

### Model A (Proven Authoritative)
```text
~/.gemini/antigravity/conversations/<id>.db
+
~/.gemini/antigravity/brain/<id>/
+
~/.gemini/antigravity/agyhub_summaries_proto.pb
+
~/.gemini/config/projects/<guid>.json
```

---

## K. Helper Changes

Patched files in `/home/ferb27/anti-crossos-system/conversation-migration/`:

1. **`MIGRATION_PLAN.json` (v2.0.0):**
   - Configured `migration_target: "desktop"`.
   - Explicitly points to `agyhub_summaries_proto.pb`.
   - Removed `--force-guid` from standard workflow; requires native GUID discovery.

2. **`apply_dish_cleaner_sandbox.py`:**
   - Adds `--target desktop` enforcement.
   - Refuses to run while `antigravity` or `language_server` is running (never kills processes).
   - Verifies package SHA256 hashes against `hashes.json`.
   - Auto-discovers native Debian project GUID from `~/.gemini/config/projects/`. Halts if unresolved.
   - Backs up `agyhub_summaries_proto.pb` with SHA-256 manifest before mutation.
   - Performs field-aware re-encoding of inner summary fields 9 and 17, completely stripping Windows URIs (`file:///e:` / `file:///c:`) and Windows GUIDs (`088c8445-...`).
   - Appends rewritten entries to `agyhub_summaries_proto.pb` via atomic write + `fsync`.
   - Verifies SQLite integrity of copied conversation databases.
   - Supports offline rollback via `--rollback <backup_dir>`.

3. **`verify_dish_cleaner_sandbox.py`:**
   - Verifies presence and SQLite integrity of `conversations/<id>.db`.
   - Verifies brain folder and `transcript.jsonl`.
   - Parses `agyhub_summaries_proto.pb`, checking that conversation UUIDs exist, target workspace URI is active, and zero residual Windows metadata remains.

---

## L. Backup / Rollback Protocol

- **Backup Target:** `~/anti-crossos-system/backups/conversation-migration/<timestamp>/`
- **Files Included:** `agyhub_summaries_proto.pb`
- **Manifest:** `backup_manifest.json` with original paths, sizes, and SHA-256 hashes.
- **Rollback Command:**
  ```bash
  python3 /home/ferb27/anti-crossos-system/conversation-migration/apply_dish_cleaner_sandbox.py --rollback <backup_dir>
  ```
  *(Requires Antigravity Desktop closed)*.

---

## M. Exact Next User Action

1. **Mở Antigravity Desktop trên Debian.**
2. **Chọn menu `File -> Open Folder...` và mở thư mục:**
   ```text
   /home/ferb27/projects/cleanAI
   ```
   *(Thao tác này khiến Antigravity Desktop tự động tạo file cấu hình dự án chuẩn tại `~/.gemini/config/projects/<new-guid>.json`)*.
3. **Đóng hoàn toàn Antigravity Desktop** (xác nhận không còn tiến trình `antigravity` hay `language_server`).
4. **Chạy lệnh kiểm tra dry-run trong terminal ngoài:**
   ```bash
   python3 /home/ferb27/anti-crossos-system/conversation-migration/apply_dish_cleaner_sandbox.py --dry-run
   ```
5. **Tiến hành import offline thật sự khi đã sẵn sàng.**
