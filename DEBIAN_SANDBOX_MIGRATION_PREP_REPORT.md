# Antigravity Conversation Sandbox Migration Preparation Report

**Date:** 2026-09-16  
**Environment:** Debian 13 (Trixie), Linux 6.12.43+bpo-amd64  
**Source Partition:** Shared NTFS `Store data` (`UUID=3C8CC1178CC0CC98`, mounted at `/media/ferb27/Store data`)  
**Package:** `<shared-root>/anti-conversation-migration/sandbox/dish_cleaner/`  
**Target Native Repo:** `/home/ferb27/projects/cleanAI`  
**CrossOS Project ID:** `6baaeb54d46ed0c4`  

---

## Executive Summary

Both tracks of the task have completed their verification and preparation:
- **Track A (CrossOS V1 Debian Regression):** `PASS`. All 4 SHA-256 release hashes matched Phase 6.1 Windows specifications. All 23 unit tests passed in isolated regression workspace. The `ntfs3` filesystem integration tests passed and the test directory was cleanly unlinked.
- **Track B (Conversation Sandbox Migration Preparation):** `READY_FOR_OFFLINE_IMPORT`. All 139 package files verified against `hashes.json` with 0 mismatches and 0 missing files. Schema compatibility across SQLite conversation databases and summary tables is 100%. All 3 conversation IDs are completely absent from Debian live storage (0 collisions). An offline migration helper and verification tool have been created and validated with active process guards.

---

## A. CrossOS Debian Regression

### 1. Release Hashes Verification
The 4 files comprising the portable CrossOS V1 Phase 6.1 hardened release were verified directly from `/media/ferb27/Store data/anti-crossos-toolkit/v1/`:

| File | Expected SHA-256 | Actual SHA-256 | Status |
| :--- | :--- | :--- | :--- |
| `crossos_core.py` | `1B989FF62D0D91CED3448A8AFECD8A0FE175199D5958DFEB2AD4A05160C82F7A` | `1B989FF62D0D91CED3448A8AFECD8A0FE175199D5958DFEB2AD4A05160C82F7A` | **MATCH** |
| `crossos_ctl.py` | `15A36951FA98E55B9A1C17CD2C02EB72BFF7E5588CF20720499485CF2E856DC0` | `15A36951FA98E55B9A1C17CD2C02EB72BFF7E5588CF20720499485CF2E856DC0` | **MATCH** |
| `README.md` | `4699A09CE119F154D4F673E82B6F7392ACA086B22B9EB98A686E4B0FF7D5DDD8` | `4699A09CE119F154D4F673E82B6F7392ACA086B22B9EB98A686E4B0FF7D5DDD8` | **MATCH** |
| `VERSION` | `59854984853104DF5C353E2F681A15FC7924742F9A2E468C29AF248DCE45CE03` | `59854984853104DF5C353E2F681A15FC7924742F9A2E468C29AF248DCE45CE03` | **MATCH** |

### 2. Hardening Delta Analysis
The hardened implementation in `regression/windows-hardened-v1/` was analyzed for Linux cross-compatibility:
- `remote_normalized_seed`: Uses URL normalization standardizing trailing `.git` and protocols, fully compatible with POSIX and Windows git outputs.
- `RemoteIdentityMismatchError`: Safely prevents resuming cross-OS handoffs against unrelated repositories.
- Removal of `resume --force`: Strictly enforces state transitions without dangerous force flags.
- Atomic state replace & recovery: Preserves previous state in `current.json.previous` before atomic replacement via `os.replace` + `fsync`.
- `events.jsonl`: Treated as non-authoritative diagnostic stream; primary state is strictly driven by `current.json`.
- No Windows-only assumptions (such as backslash pathing or Windows drive letters) exist in the core state machine.

### 3. Test Suite Execution
The 23-test suite was executed against the hardened release:
- Identity parity & remote normalization: PASS
- Remote mismatch rejection: PASS
- Strict state transitions (no force resume): PASS
- Dirty Git repository guard: PASS
- SHA divergence & branch mismatch guards: PASS
- Event log append & recovery: PASS
- CLI JSON output & Linux path handling: PASS
- **Result:** `23/23 unit tests passed`.

### 4. NTFS3 Driver Integration Test
A live integration test was conducted on `/media/ferb27/Store data/anti-crossos-state-test/`:
- Atomic rename, `fsync`, directory flush, event appending, recovery: PASS.
- Test directory was cleanly unlinked after verification.
- Production state directory `anti-crossos-state/` was **NOT** created.

---

## B. Package Integrity

The sandbox package was discovered at `/media/ferb27/Store data/anti-conversation-migration/sandbox/dish_cleaner/`:

- **Manifest:** `manifest.json` (schema v1.0.0, 3 conversations, project `dish_cleaner`).
- **Hashes:** `hashes.json` (139 entries).
- **Files Verified:** 139 / 139 (100% match, 0 failures, 0 missing).
- **Extra Files:** 4 SQLite auxiliary WAL/SHM files (`277112d0...db-shm`, `277112d0...db-wal`, `76262243...db-shm`, `76262243...db-wal`) originating from Windows WAL mode, plus `hashes.json` itself.
- **SQLite Database Integrity:** All 3 conversation databases returned `PRAGMA integrity_check = ok`.
- **Secret Scan Status:** `CLEAN`.
- **Owner Transfer Authorization:** `OWNER_SENSITIVE_HISTORY_TRANSFER_ALLOWED = YES`.

---

## C. Debian Antigravity Runtime

- **Antigravity Desktop:** 2.10.0
- **Language Server:** 2.10.0
- **Antigravity CLI (`agy`):** 1.2.4
- **Storage Locations:**
  - CLI conversation summaries: `~/.gemini/antigravity-cli/conversation_summaries.db`
  - Desktop conversation DBs: `~/.gemini/antigravity/conversations/`
  - Desktop brain directories: `~/.gemini/antigravity/brain/`
  - Desktop summaries index: `~/.gemini/antigravity/agyhub_summaries_proto.pb`
  - Project definitions: `~/.gemini/config/projects/`

---

## D. Native Debian Target Repo

In accordance with Section 15 & 16, a clean native Linux clone was established:
- **Location:** `/home/ferb27/projects/cleanAI` (ext4 Linux user directory)
- **Git Remote:** `https://github.com/vudsen/ai-disk-cleaner.git`
- **Branch:** `master` (clean working tree, up to date with origin/master)
- **HEAD Commit:** `9cc2f2407e9769183294ffaf871f02150cbb6378`

---

## E. CrossOS/TencentDB Project ID

- Derived via `crossos_core.compute_project_id(Path('/home/ferb27/projects/cleanAI'))`:
  - `crossos_project_id`: `6baaeb54d46ed0c4`
  - `project_slug`: `ai-disk-cleaner`
- TencentDB scope ID for this repository: `6baaeb54d46ed0c4`
- **Parity:** 100% IDENTICAL across Windows, Debian, CrossOS, and TencentDB.

---

## F. Workspace URI

- **Debian Workspace Path:** `/home/ferb27/projects/cleanAI`
- **Debian Workspace URI:** `file:///home/ferb27/projects/cleanAI`

---

## G. Debian Project GUID

- Inspection of `~/.gemini/config/projects/*.json` indicates that no project registration currently exists for `file:///home/ferb27/projects/cleanAI`.
- **Status:** `UNRESOLVED`
- **Resolution Path:** Opening the folder `/home/ferb27/projects/cleanAI` in Antigravity Desktop will natively register a new project GUID in `~/.gemini/config/projects/<guid>.json`. Alternatively, a specific GUID can be supplied via `--force-guid` to the migration helper.

---

## H. Windows GUID Discrepancy Resolution

Cross-inspection of all files in the Windows sandbox package:
1. `source_project.json`: `088c8445-c125-444b-8721-6785bc361a2a`
2. `summary_rows.json` (all 3 conversation rows): `088c8445-c125-444b-8721-6785bc361a2a`
3. `manifest.json`: `088c8445-c125-444b-8721-6785bc361a2a`
4. `migration_metadata.json`: `088c8445-c125-444b-8721-6785bc361a2a`
5. `raw_summary` embedded protobuf string: `088c8445-c125-444b-8721-6785bc361a2a`

**Conclusion:** The package is 100% internally consistent. The earlier discrepancy reported in pre-audit was an artifact of an obsolete draft ID.  
`GUID_DISCREPANCY_RESOLVED: YES`.

---

## I. Conversation 762 Workspace Anomaly

- **Conversation ID:** `76262243-a240-4b7b-be18-630b499c1a57`
- **Recorded Source URI:** `file:///c%3A/Users/phamt/Documents/antigravity/sharp-davinci`
- **Analysis:**
  - Artifact `prompt_engineering_brief.md` in the conversation's brain explicitly specifies initial prompt engineering, system design, and requirements for target directory `E:\project\cleanAI`.
  - Windows Antigravity assigned this conversation to `dish_cleaner` project GUID `088c8445-c125-444b-8721-6785bc361a2a` in `conversation_summaries.db`.
  - **Classification:** Inception & architecture planning session for `cleanAI` initiated under workspace `sharp-davinci` and bound to `dish_cleaner`.
  - **Confidence:** HIGH.
  - **Action in Migration Plan:** Marked as `DEFER` by default in accordance with the safe migration principle (2 cleanAI chats imported + 1 inception chat deferred). It can be modified to `IMPORT_TO_CLEANAI` if the user desires unified history.

---

## J. Conversation Schema Compatibility

Direct SQL DDL comparison between package conversation databases and native Debian database `8c18b20e-c2e6-4760-a8b0-2be7e31cb00e.db`:
- Tables: `battle_mode_infos`, `executor_metadata`, `gen_metadata`, `parent_references`, `steps`, `trajectory_meta`, `trajectory_metadata_blob`
- `PRAGMA user_version`: 1 (identical)
- `PRAGMA application_id`: 0 (identical)
- Schema fingerprint hash: `c69d11ecb93daa13a48f83f79466c1eb59d72c406b800bf97b0fd741f960560a` (identical across native and package DBs).
- **Status:** `CONVERSATION_SCHEMA_COMPATIBLE: YES`.

---

## K. Summary Schema Compatibility

- Target table `conversation_summaries` in `~/.gemini/antigravity-cli/conversation_summaries.db` contains 21 columns.
- Package `summary_rows.json` provides 21 fields, mapping `raw_summary_b64` to `raw_summary`.
- All column types and names match with 100% fidelity.
- **Status:** `SUMMARY_SCHEMA_COMPATIBLE: YES`.

---

## L. raw_summary Analysis

Protobuf decoding of `raw_summary_b64` confirmed that it embeds machine-specific metadata:
- Windows workspace URI: `file:///e:/project/cleanAI`
- Windows project GUID: `088c8445-c125-444b-8721-6785bc361a2a`
- Conversation 762 URI: `file:///c:/Users/phamt/Documents/antigravity/sharp-davinci`

On Debian CLI, native records store `raw_summary` as `NULL` without loss of conversation browsing capabilities. Setting `raw_summary` to `NULL` during SQLite summary insertion prevents Windows URI pollution. If imported into Desktop `agyhub_summaries_proto.pb`, rewriting with Debian paths and GUID is required.  
`RAW_SUMMARY_REWRITE_REQUIRED: YES`.

---

## M. Collision Check

Audit of Debian storage locations:
- `~/.gemini/antigravity/conversations/`: All 3 conversation IDs ABSENT.
- `~/.gemini/antigravity/brain/`: All 3 conversation IDs ABSENT.
- `~/.gemini/antigravity-cli/conversation_summaries.db`: All 3 conversation IDs ABSENT.
- **Collisions:** 0 (clean import target).

---

## N. Migration Mapping Table

| Conversation ID | Preview | Source Workspace | Target Workspace | Target Project GUID | Planned Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `277112d0-1367-4f05-a019-e583625b6c1c` | Phân Tích RAM Chạy Ngầm | `file:///e%3A/project/cleanAI` | `file:///home/ferb27/projects/cleanAI` | `<resolved-guid>` | `IMPORT_TO_CLEANAI` |
| `556258fd-137a-4f35-8d11-1147f2c56420` | Phân Tích Kết Nối Mạng | `file:///e%3A/project/cleanAI` | `file:///home/ferb27/projects/cleanAI` | `<resolved-guid>` | `IMPORT_TO_CLEANAI` |
| `76262243-a240-4b7b-be18-630b499c1a57` | AI Disk Cleaner Evaluation | `file:///c%3A/.../sharp-davinci` | *None* | *None* | `DEFER` |

---

## O. Backup Plan

- Backup location: `~/anti-crossos-system/backups/conversation-migration/<timestamp>/`
- Target files backed up: `conversation_summaries.db`
- Manifest recorded: `backup_manifest.json` containing SHA-256 hashes of original files and a registry of newly copied conversation DBs and brain folders.
- Clean rollback supported via `python3 apply_dish_cleaner_sandbox.py --rollback <backup_dir>`.

---

## P. Offline Migration Helper

The migration tooling has been constructed in `~/anti-crossos-system/conversation-migration/`:
1. `MIGRATION_PLAN.json`: Configuration defining source/target environments and per-conversation actions.
2. `apply_dish_cleaner_sandbox.py`: Offline migration executor featuring:
   - Gate 1: Refuses execution if `antigravity` or `language_server` processes are running.
   - Gate 2: Package SHA-256 hash re-verification.
   - Target backup with hash manifests.
   - Database and brain folder migration.
   - Summary row remapping and SQLite insertion.
   - SQLite post-migration integrity verification.
   - Full rollback capability.
3. `verify_dish_cleaner_sandbox.py`: Post-migration validation tool checking file existence, table row counts, brain transcripts, and summary database records.

---

## Q. Remaining Operational Risks

1. **Antigravity Must Be Closed:** `apply_dish_cleaner_sandbox.py` cannot and should not be run while Antigravity is open. Running the helper requires a terminal outside the Antigravity desktop session.
2. **Debian Project GUID Resolution:** Opening `/home/ferb27/projects/cleanAI` once in Desktop Antigravity ensures a standard, native project configuration is registered prior to executing the migration.
