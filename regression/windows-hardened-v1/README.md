# Cross-OS Handoff Control Plane (V1)

Portable, zero-dependency Python standard-library utility facilitating seamless development task handovers between **Antigravity Debian** and **Antigravity Windows** across cold system reboots via a shared NTFS partition.

---

## 1. Architectural Model

```text
  Active Booted OS (Debian / Windows)
  ┌──────────────────────────────────────────────┐
  │ Local Worker (Anti)                          │
  │  - Source of Truth: Native local clone + Git │
  └──────────────────────┬───────────────────────┘
                         │ crossos handoff
                         ▼
  ┌──────────────────────────────────────────────┐
  │ Shared NTFS Partition                        │
  │ UUID: 3C8CC1178CC0CC98 (D:\ on Windows)      │
  │ Path: <shared-root>/anti-crossos-state/      │
  │  - Task Continuity snapshot (current.json)   │
  │  - Chronological audit log (events.jsonl)    │
  └──────────────────────┬───────────────────────┘
                         │ Cold Reboot
                         ▼
  Peer Booted OS (Windows / Debian)
  ┌──────────────────────────────────────────────┐
  │ Local Worker (Anti)                          │
  │  - crossos status (detects pending handoff)  │
  │  - crossos resume (verifies Git & adopts)    │
  └──────────────────────────────────────────────┘
```

### Separation of Concerns
1. **Tier 1 (Source of Truth):** Local native repository clones, local active filesystem, and Git metadata.
2. **Tier 2 (Current Task Continuity):** Ephemeral task handoff plane stored under `<shared-root>/anti-crossos-state/`.
3. **Tier 3 (Permanent Semantic Memory):** Shared TencentDB/RAG memory hub storing durable architectural decisions.

---

## 2. CLI Usage & Commands

```bash
# General syntax
python3 crossos_ctl.py [GLOBAL_OPTIONS] <SUBCOMMAND> [SUBCOMMAND_OPTIONS]

# Global Options
--repo <path>         Target repository directory (default: current directory)
--state-dir <path>    Override shared state directory
--project-id <id>     Explicit 8-64 character hexadecimal project identifier
--json                Emit clean machine-readable JSON to stdout
```

### Subcommands

| Command | Purpose | Key Arguments |
| :--- | :--- | :--- |
| `status` | Query active task, pending handoff, and Git alignment (read-only) | None |
| `inspect` | Detailed dump of snapshot JSON, fresh Git status, and event tail | None |
| `begin` | Initiate a new task session | `--title <str>`, `[--intent <str>]` |
| `handoff` | Freeze active state and write handoff snapshot for peer OS | `--next <str>`, `[--summary <str>]`, `[--instructions <str>]`, `[--verification-result PASS\|FAIL]` |
| `resume` | Adopt and activate a pending handoff task on current OS | None |
| `complete`| Finalize active task (archives if terminal) | `[--result PASS\|FIX_REQUIRED\|BLOCKED]`, `[--evidence <str>]` |
| `validate`| Inspect state directory structure and JSON integrity | None |
| `events`  | Display recent audit events from append-only log | `[--tail <int>]` |

---

## 3. Exit Codes

| Code | Meaning | Remediation |
| :--- | :--- | :--- |
| `0` | Success | Operation completed cleanly. |
| `1` | General Operational Error | Invalid state transition, missing state, corrupted state, or unreadable JSON. |
| `2` | Dirty Worktree Gate (`DIRTY_WORKTREE`) | Commit uncommitted changes in Git before initiating handoff. |
| `3` | Git Divergence / Remote Identity (`HANDOFF_DIVERGENCE` / `PROJECT_REMOTE_IDENTITY_MISMATCH`) | Synchronize working tree, branch, commit SHA, or remote URL with writer OS. |
| `4` | Project ID Required (`PROJECT_ID_REQUIRED`) | Repository lacks a Git remote. Provide `--project-id <hex_id>`. |

---

## 4. State Machine & Lifecycle

```text
                 ┌───────────────┐
                 │      NEW      │
                 └───────┬───────┘
                         │ crossos begin
                         ▼
               ┌───────────────────┐
               │    IN_PROGRESS    │◄────────────────┐
               └─────────┬─────────┘                 │
                         │ crossos handoff           │
                         ▼                           │
             ┌───────────────────────┐               │
             │   READY_FOR_HANDOFF   │               │
             └───────────┬───────────┘               │
                         │ [Cold Reboot]             │
                         │ crossos resume            │
                         ▼                           │
               ┌───────────────────┐                 │
               │      RESUMED      ├─────────────────┘
               └─────────┬─────────┘ (continue work)
                         │
        ┌────────────────┼────────────────┐
        │ complete PASS  │ FIX_REQUIRED   │ complete BLOCKED / ESCALATE
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────────┐   ┌───────────┐
   │  PASS*  │    │ FIX_REQUIRED │   │ BLOCKED*  │
   └─────────┘    └──────────────┘   └───────────┘
   (* = Terminal state archived to tasks/<task_id>.json)
```

- **Non-Terminal Fixes:** Setting status to `FIX_REQUIRED` does not archive the task; it allows in-place remediation or further handoff cycles.
- **Terminal Archival:** Completing with `PASS`, `BLOCKED`, or `ESCALATE` automatically archives a frozen copy to `tasks/<task_id>.json`.

---

## 5. Git Safety, Remote Identity & Divergence Rules

- **Zero Destructive Actions:** `crossos` never executes `git stash`, `git reset`, `git checkout`, or `git apply` automatically.
- **Dirty Worktree Gate:** Handoff is strictly refused (`DIRTY_WORKTREE`, exit code 2) if `git status --porcelain` detects uncommitted or untracked changes. Uncommitted work cannot cross OS boundaries.
- **Remote URL Identity Requirement:** CrossOS V1 intentionally preserves TencentDB scope parity. Therefore, native clones on Debian and Windows MUST use matching remote URL identity forms (e.g. `https://github.com/org/repo.git`) to automatically resolve to the same project ID. If peer remote seeds differ, resume is refused with `PROJECT_REMOTE_IDENTITY_MISMATCH`.
- **Resume Gate (Zero Bypass):** When adopting a task, `resume` verifies that local branch, commit HEAD SHA, and normalized remote URL seed match the writer OS. No `--force` or safety bypass exists. If diverged, execution halts with `HANDOFF_DIVERGENCE` (exit code 3).

---

## 6. Storage Layout & Crash-Resilient Write Protocol

```text
<shared-root>/anti-crossos-state/
├── VERSION
└── projects/
    └── <project_id>/
        ├── projectspec.json
        ├── current.json                  # Active snapshot
        ├── current.json.previous         # Immediate rollback snapshot
        ├── events.jsonl                  # Append-only chronological audit log
        └── tasks/
            └── <task_id>.json            # Historical archives
```

### Atomic Write-Replace Pattern & Atomicity Model
1. Writes formatted JSON to a unique temporary file (`current.json.tmp.<pid>.<uuid>`) in the target directory.
2. Flushes buffers and calls `os.fsync(fd)` to force disk writes.
3. Rotates existing `current.json` to `current.json.previous`.
4. Replaces target file via atomic filesystem rename (`os.replace`).
5. Appends transition event to `events.jsonl` with `os.fsync`.

> **Classification:** Best-effort crash resilience (`BEST_EFFORT_CRASH_RESILIENCE_VERIFIED`) via atomic rename and fsync. Not an absolute guarantee against sudden power loss or storage hardware faults.

### Authoritative State Recovery Protocol
`current.json` and `current.json.previous` are the sole authoritative state records:
1. `crossos` reads `current.json`.
2. If `current.json` is missing or corrupted, `crossos` automatically falls back to `current.json.previous`.
3. If both primary and backup snapshots are unreadable or corrupt, execution halts with `CORRUPTED_HANDOFF_STATE`.
4. The append-only event log (`events.jsonl`) is strictly preserved as an audit trail and diagnostic log; it is not used for partial state fabrication.

---

## 7. Security & Redaction Model

- **Zero Credentials Stored:** API tokens (`Bearer`, `sk-`, `ghp_`, `AIza...`), private keys, passwords, and `.env` assignments are automatically redacted via regex prior to serializing any snapshot, summary, instruction, or event log entry.
- **Safe Hash Preservation:** Full 40-character Git commit hashes and 16-character project IDs are preserved without over-redaction.

---

## 8. Cross-OS Validation

This implementation has undergone Phase 5 validation on Debian 13.6 native Linux and Phase 6/6.1 production hardening on native Windows 11.

