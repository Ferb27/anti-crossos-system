# CROSS-OS HANDOFF CONTROL PLANE SPECIFICATION (V1)
**Document Version:** 1.0.0-draft  
**Author:** Antigravity Agent (Debian Local Worker)  
**Target Environment:** Lenovo Legion Slim 7 16IRH8 — Dual Boot Windows 11 / Debian 13.6 (trixie)  
**Target File:** `/home/ferb27/anti-crossos-system/CROSS_OS_HANDOFF_DESIGN.md`  
**Execution Stage:** Phase 4 — Design & Specification Only (Zero Implementation / Zero Daemons)  

---

## A. Goals

1. **Asynchronous Cross-OS Task Continuity:**
   Provide a reliable, non-realtime state handover mechanism between `Anti Windows` and `Anti Debian` so an in-flight development task can resume seamlessly across OS reboots.
2. **Strict Three-Tier Data Separation:**
   - **Tier 1 (Source of Truth):** Local native repository clones, active filesystem, fresh commands output, and Git metadata.
   - **Tier 2 (Current Task Continuity):** Structured cross-OS handoff plane stored on the shared partition under `anti-crossos-state/`.
   - **Tier 3 (Long-Term Knowledge):** Shared TencentDB/RAG memory hub storing durable architectural decisions and past verified solutions.
3. **Dual-Boot Optimization & Zero Daemon Overhead:**
   Since Windows and Debian execute exclusively (never concurrently on this machine), design around static, file-based synchronization requiring zero always-on daemons, background listeners, or network RPCs.
4. **Filesystem Resilience on NTFS:**
   Guarantee corruption-free state updates across both the Windows native NTFS driver and Linux kernel `ntfs3` driver via atomic write-replace workflows.
5. **Single Writer Discipline:**
   Only the primary active Local Worker (Antigravity on the booted OS) is authorized to write handoff state. Scouts and Specialist Subagents remain read-only advisors.
6. **Strict Git Safety Contract:**
   Never blindly assume native clones on Windows and Linux are in identical state. Enforce a verification gate before resuming any task.

---

## B. Non-Goals

1. **No Realtime Remote Procedure Calls (RPC):**
   No socket servers, WebSockets, or HTTP servers running across the network during standard handoff, because dual-boot hardware prevents concurrent execution.
2. **No Shared Working Trees or Build Artifacts:**
   No symlinking or sharing of `.git`, `.venv`, `node_modules`, binary targets, or build caches across the NTFS partition. Each OS maintains its own native clone and toolchain.
3. **No Automated Reboot or Bootloader Manipulation:**
   The control plane does not touch GRUB, EFI NVRAM, or invoke system restarts. Reboots remain 100% user-directed.
4. **No Replacement for Git or TencentDB:**
   The handoff plane does not version code diffs (Git does) and does not index permanent project history (TencentDB does).
5. **No Secret or Credential Storage:**
   Tokens, private keys, session cookies, and `.env` credentials are strictly barred from the handoff storage.

---

## C. Current Verified Environment

| Property | Windows 11 Native | Debian 13.6 Native | Cross-OS Standard |
| :--- | :--- | :--- | :--- |
| **Physical Machine** | Lenovo Legion Slim 7 16IRH8 | Lenovo Legion Slim 7 16IRH8 | Shared Hardware Chassis |
| **Shared Drive D:** | `D:\` (NTFS, UUID `3C8CC1178CC0CC98`) | `/media/ferb27/Store data` (`ntfs3`) | UUID `3C8CC1178CC0CC98` |
| **Shared Base Path** | `D:\` | Auto-discovered mountpoint | `find_shared_root()` |
| **Python Runtime** | Python 3.12 (User AppData) | Python 3.13.5 (`/usr/bin/python3`) | Python >= 3.10 stdlib |
| **Antigravity IDE** | Desktop Application | Desktop 2.10.0 / CLI 1.2.4 | Agent Harness V3 |
| **Active RAG Hub** | `D:\codex_base` | `.../codex_base` via bridge | TencentDB file bridge |
| **Handoff Location** | `D:\anti-crossos-state\` | `<shared-root>/anti-crossos-state/` | Common Root Directory |

---

## D. Architecture

The architecture maintains a clean unidirectional flow during active development, with an asynchronous state bridge across system reboots:

```text
               ┌───────────────────────────────┐
               │            USER               │
               └───────────────┬───────────────┘
                               │ Prompts / Requirements
                               ▼
               ┌───────────────────────────────┐
               │           GPT Web             │
               │    (Primary Orchestrator)     │
               └───────────────┬───────────────┘
                               │ Directs active Local Worker
                               ▼
 ═══════════════════════════════════════════════════════════════════════
  ACTIVE BOOTED OS (Debian 13 or Windows 11)
 ═══════════════════════════════════════════════════════════════════════
   ┌─────────────────────────────────────────────────────────────────┐
   │            Antigravity Main Local Worker (Anti)                 │
   │                                                                 │
   │   ┌───────────────┐   ┌────────────────┐   ┌────────────────┐   │
   │   │   Scout V3    │   │  Subagents     │   │   Executor     │   │
   │   │  (Read-Only)  │   │  (Specialists) │   │ (Controlled)   │   │
   │   └───────────────┘   └────────────────┘   └────────────────┘   │
   └───────────────┬───────────────────────────────┬─────────────────┘
                   │ Fresh Checks & Execution      │ Single Writer
                   ▼                               ▼
       ┌────────────────────────┐      ┌─────────────────────────┐
       │   Native Local Clone   │      │ Cross-OS Control Plane  │
       │   (Source of Truth)    │      │ (anti-crossos-state/)   │
       └────────────────────────┘      └────────────┬────────────┘
                                                    │
 ═══════════════════════════════════════════════════╪═══════════════════
  SYSTEM REBOOT (Cold transition)                   │ Stored on NTFS
 ═══════════════════════════════════════════════════╪═══════════════════
                                                    │
 ═══════════════════════════════════════════════════╪═══════════════════
  PEER BOOTED OS (Windows 11 or Debian 13)          │
 ═══════════════════════════════════════════════════╪═══════════════════
                   ┌────────────────────────────────┘
                   │ Bootstrap Discovery & Resume
                   ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │            Antigravity Peer Local Worker (Anti)                 │
   │   1. Inspect native clone vs handoff snapshot                   │
   │   2. Validate Git branch / HEAD SHA                             │
   │   3. Resume execution from Next Action                          │
   └─────────────────────────────────────────────────────────────────┘
```

---

## E. Storage Layout

The shared root directory is created under `<shared-root>/anti-crossos-state/`:

```text
<shared-root>/anti-crossos-state/
│
├── VERSION                                  # Protocol version: "1"
│
├── machine/
│   ├── windows.json                         # Windows non-sensitive hardware/toolchain capabilities
│   └── debian.json                          # Debian non-sensitive hardware/toolchain capabilities
│
└── projects/
    └── <project_id>/                        # Deterministic 16-hex project identifier
        ├── projectspec.json                 # Project identity, remote mapping, and display name
        ├── current.json                     # Active task handoff snapshot (atomic write-replace)
        ├── current.json.previous            # Immediate rollback snapshot
        ├── events.jsonl                     # Append-only chronological audit log
        │
        ├── tasks/
        │   └── <task_id>.json               # Archival record of completed/closed tasks
        │
        └── artifacts/
            ├── manifest.jsonl               # Register of non-git file attachments (logs, diffs)
            └── files/
                └── <artifact_id>            # Raw artifact payloads
```

### Storage Engine Trade-Off: JSON + JSONL vs SQLite
* **Decision:** **JSON + JSONL** is selected as the default storage engine.
* **Rationale:**
  1. **Cross-Driver Locking Risks:** SQLite WAL mode relies on shared memory (`-shm`) and POSIX file locks (`fcntl`/`flock`). Dual-boot transitions between kernel `ntfs3` and Windows native NTFS drivers can leave uncommitted WAL locks, causing `database is locked` or requiring recovery passes upon OS boot.
  2. **Inspectability & Human Audit:** JSON and JSONL files are plain text, human-readable, easily diffed, and can be inspected or repaired directly with standard CLI tools (`jq`, `cat`, Python).
  3. **Simplicity (Ponytail Principle):** Managing a snapshot (`current.json`) plus append log (`events.jsonl`) satisfies 100% of requirements without binary database dependencies.

---

## F. Project Identity Strategy

To guarantee that Windows and Debian resolve identical project workspaces without relying on local directory paths:

### 1. Primary Strategy: Normalized Git Remote URL
If the repository has a Git remote (e.g. `origin`):
1. Extract URL: `git config --get remote.origin.url`
2. Normalize URL string:
   - Strip authentication: `https://token@...` -> `https://...`
   - Convert SSH syntax: `git@github.com:org/repo.git` -> `github.com/org/repo`
   - Strip protocol: `https://github.com/org/repo.git` -> `github.com/org/repo`
   - Strip trailing `.git` and trailing slashes `/`.
   - Convert to lowercase.
3. Compute Hash:
   ```python
   project_id = hashlib.sha256(norm_url.encode("utf-8")).hexdigest()[:16]
   ```
*Verification:* Both Windows (`D:\Projects\my-app`) and Debian (`/home/ferb27/my-app`) pointing to the same remote will compute the exact same 16-character hexadecimal `project_id`.

### 2. Secondary Fallback: Git Root Commit SHA
If no remote is configured (e.g., local repo):
1. Query initial commit: `git rev-list --max-parents=0 HEAD`
2. Compute Hash: `hashlib.sha256(root_sha.encode("utf-8")).hexdigest()[:16]`
*Verification:* Distributed Git clones of the same repository share the exact same root commit.

### 3. Tertiary Fallback: Project Anchor Marker
If the directory is not a Git repository:
1. Probe `.anti_project_id` file in the workspace root.
2. If missing, generate UUID4 hex and write `.anti_project_id`.

---

## G. Task Schema (`current.json`)

The `current.json` file contains the definitive state of the active task:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "schema_version": 1,
  "project_id": "bbc0daf62487403d",
  "project_name": "anti-crossos-system",
  "task_id": "task-20260916-181500-7f2a",
  "handoff_sequence": 3,
  "writer": {
    "os": "debian",
    "hostname": "gtr",
    "anti_version": "2.10.0",
    "written_at": "2026-09-16T11:15:00Z"
  },
  "task": {
    "title": "Implement cross-OS state discovery",
    "intent": "Enable Debian Anti to read Windows handoff files automatically",
    "status": "READY_FOR_HANDOFF"
  },
  "git": {
    "remote_url": "https://github.com/org/anti-crossos-system",
    "branch": "feat/crossos-plane",
    "head_sha": "a1b2c3d4e5f678901234567890abcdef12345678",
    "dirty": false,
    "uncommitted_files_count": 0,
    "recommended_action": "FETCH_AND_VERIFY"
  },
  "execution": {
    "summary": "Completed Phase 3 runtime audit. Verified all 69 skills and MCP processes.",
    "next_action": "Review CROSS_OS_HANDOFF_DESIGN.md on Windows and validate toolchain availability.",
    "instructions_for_peer_os": "Inspect git status on Windows. Confirm branch feat/crossos-plane is synced."
  },
  "verification": {
    "last_result": "PASS",
    "test_commands": [
      "python3 /home/ferb27/.gemini/antigravity/ai-scout-v3/scout_run.py --status",
      "python3 /home/ferb27/.gemini/antigravity/tencentdb-sync-bridge/debian_memory_bridge.py status"
    ],
    "evidence_summary": "Scout V3 READY, Memory Bridge CONNECTED, zero Python errors."
  },
  "artifacts": [
    {
      "artifact_id": "art-001",
      "name": "DEBIAN_POST_RESTART_VERIFICATION.md",
      "rel_path": "artifacts/files/art-001_DEBIAN_POST_RESTART_VERIFICATION.md",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "rag": {
    "relevant_scope_id": "bbc0daf62487403d",
    "durable_learning_captured": false
  },
  "timestamps": {
    "created_at": "2026-09-16T10:45:00Z",
    "updated_at": "2026-09-16T11:15:00Z"
  }
}
```

---

## H. Event Schema (`events.jsonl`)

Each line in `events.jsonl` represents an immutable state transition:

```json
{
  "event_id": "evt-20260916-181501-8b3c",
  "sequence": 3,
  "timestamp": "2026-09-16T11:15:01Z",
  "os": "debian",
  "project_id": "bbc0daf62487403d",
  "task_id": "task-20260916-181500-7f2a",
  "type": "HANDOFF_WRITTEN",
  "summary": "Handoff sequence 3 prepared on Debian for Windows reboot.",
  "actor": "anti_local_worker",
  "payload": {
    "head_sha": "a1b2c3d4e5f678901234567890abcdef12345678",
    "status": "READY_FOR_HANDOFF"
  }
}
```

### Event Types:
* `TASK_CREATED`: Task initiated by Orchestrator / User prompt.
* `TASK_STARTED`: Local Worker commenced active code / investigation.
* `VERIFICATION_RUN`: Automated test / check executed with verifiable result.
* `HANDOFF_WRITTEN`: Active OS finalized snapshot and serialized to shared disk.
* `TASK_RESUMED`: Peer OS validated repository state and adopted task.
* `TASK_COMPLETED`: Task successfully concluded (`PASS`).
* `TASK_BLOCKED`: Task cannot proceed due to divergence or missing dependency.

---

## I. State Machine

```text
                 ┌───────────────┐
                 │      NEW      │
                 └───────┬───────┘
                         │ begin_task()
                         ▼
               ┌───────────────────┐
               │    IN_PROGRESS    │◄────────────────┐
               └─────────┬─────────┘                 │
                         │ prepare_handoff()         │
                         ▼                           │
             ┌───────────────────────┐               │
             │   READY_FOR_HANDOFF   │               │
             └───────────┬───────────┘               │
                         │ [System Reboot]           │
                         │ resume_task()             │
                         ▼                           │
               ┌───────────────────┐                 │
               │      RESUMED      ├─────────────────┘
               └─────────┬─────────┘ (continue execution)
                         │
        ┌────────────────┼────────────────┐
        │ complete()     │ fail()         │ block()
        ▼                ▼                ▼
   ┌─────────┐   ┌──────────────┐   ┌───────────┐
   │  PASS   │   │ FIX_REQUIRED │   │  BLOCKED  │
   └─────────┘   └──────────────┘   └───────────┘
```

### Transition Validation Rules:
1. Only `IN_PROGRESS` or `RESUMED` states can transition to `READY_FOR_HANDOFF`.
2. A task in `READY_FOR_HANDOFF` can only transition to `RESUMED` when executed on the peer OS (or re-adopted after aborted reboot).
3. Terminal states (`PASS`, `FIX_REQUIRED`, `BLOCKED`) cause the task to be archived into `tasks/<task_id>.json`.

---

## J. Atomicity & Recovery Protocol

### 1. The Write-Replace Pattern
To avoid partial writes or file corruption across NTFS implementations:
```python
def atomic_save_json(target_path: Path, data: dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_name(f"{target_path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    
    # 1. Write to temporary file in the same directory (same filesystem volume)
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())  # Flush OS buffers to physical disk
        
    # 2. Rotate previous snapshot if target exists
    prev_path = target_path.with_name(f"{target_path.name}.previous")
    if target_path.exists():
        try:
            shutil.copy2(target_path, prev_path)
        except Exception:
            pass
            
    # 3. Atomic rename (maps to MoveFileExW on Windows, rename(2) on Linux)
    os.replace(temp_path, target_path)
```

### 2. Recovery from Incomplete Writes
If `current.json` is missing, empty, or fails JSON parsing upon boot:
1. **Fallback 1:** Automatically load `current.json.previous`.
2. **Fallback 2:** If `previous` is unreadable, read the tail of `events.jsonl` to reconstruct the last known task ID and sequence number.
3. **Safety Stop:** If neither snapshot nor event log yields valid state, flag `CORRUPTED_HANDOFF_STATE` and ask user confirmation before touching files.

---

## K. Git Safety Contract

The control plane enforces **zero destructive Git actions**:

```text
Handoff Git Expectations
 ├─ expected_remote
 ├─ expected_branch
 └─ expected_sha
       │
       ▼ Peer OS Boots
 [Resume Inspection Gate]
 ├─ 1. Check current git remote URL (must match project_id)
 ├─ 2. Check current active branch (git rev-parse --abbrev-ref HEAD)
 ├─ 3. Check current commit SHA (git rev-parse HEAD)
 ├─ 4. Check status cleanliness (git status --porcelain)
       │
       ├─ If clean && HEAD == expected_sha:
       │    ──► PASS: Auto-resume approved
       │
       ├─ If clean && HEAD != expected_sha:
       │    ──► Fetch allowed (git fetch origin <branch> --dry-run)
       │    ──► Prompt user to fast-forward
       │
       └─ If dirty == true (Uncommitted changes exist):
            ──► STOP: Flag HANDOFF_DIVERGENCE
            ──► Refuse automatic overwrite or stash
```

### Handling Uncommitted Work (`dirty = true`):
* Uncommitted files in a native Linux clone **will not exist** in the native Windows clone.
* If a handoff is requested while the working tree is dirty:
  - **Preferred Path:** Prompt user / orchestrator to commit changes: `git commit -m "wip: handoff checkpoint"`.
  - **Fallback Path:** Generate a clean patch artifact (`git diff HEAD > patch.diff`), store it under `artifacts/files/`, register in manifest, and alert the peer OS to inspect and apply the patch.

---

## L. Artifact Handling

1. **Non-Git Artifact Storage:**
   Artifacts too large or inappropriate for Git (profiler traces, benchmark JSONs, audio renders, debug dumps) are stored directly under `<shared-root>/anti-crossos-state/projects/<project_id>/artifacts/files/<artifact_id>`.
2. **Relative Referencing:**
   Artifact paths inside `current.json` must be stored as **relative paths** from the project directory (e.g. `artifacts/files/art-001.dump`), never as absolute paths (`D:\...` or `/media/...`).
3. **Integrity Validation:**
   Each artifact record contains a SHA-256 hash. The receiving OS verifies file integrity before reading.

---

## M. Relation with TencentDB / RAG Hub

```text
┌──────────────────────────────────────┐       ┌──────────────────────────────────────┐
│  Tier 2: Handoff State (Episodic)    │       │  Tier 3: TencentDB Memory (Semantic) │
├──────────────────────────────────────┤       ├──────────────────────────────────────┤
│ "What task is being executed now?"   │       │ "What architectural rules apply?"    │
│ "What commit SHA was verified?"      │       │ "How did we resolve this bug before?"│
│ "What is the exact next test?"       │       │ "What is the global project policy?" │
│ Lifespan: Hours / Days (per task)    │       │ Lifespan: Permanent / Cumulative     │
└──────────────────────────────────────┘       └──────────────────────────────────────┘
```

* **Boundary Discipline:**
  - Handoff NEVER overrides current repository code or Git state.
  - At task completion (`PASS`), the Local Worker determines if the task yielded durable procedural knowledge (e.g. tool configuration, bug root cause). If verified, it captures an entry into TencentDB via `debian_memory_bridge.py` or Windows bridge.

---

## N. Windows Flow

1. **Boot & Session Initialization:**
   - Anti starts in project workspace (e.g. `D:\projects\my-app`).
   - Anti runs `crossos status`:
     - Discovers `D:\anti-crossos-state`.
     - Identifies `project_id`.
     - Checks `current.json`.
2. **Resume Check:**
   - If `current.json` status is `READY_FOR_HANDOFF` from Debian:
     - Verify local git branch and SHA.
     - Present handoff summary to user/orchestrator: *"Resuming task `<task_id>` from Debian..."*
     - Transition state to `RESUMED`.
3. **Execution:**
   - Anti executes requested Windows tasks (e.g. Office PowerPoint generation, Windows-specific tooling).
4. **Handoff Preparation:**
   - User requests switch to Debian:
     - Anti commits work or generates patch.
     - Runs verification tests.
     - Writes `current.json` with status `READY_FOR_HANDOFF`.
     - Appends event to `events.jsonl`.

---

## O. Debian Flow

1. **Boot & Session Initialization:**
   - Anti starts in project workspace (e.g. `/home/ferb27/my-app`).
   - Anti runs `crossos status`:
     - Discovers mountpoint via UUID `3C8CC1178CC0CC98` (`/media/ferb27/Store data`).
     - Identifies `project_id`.
     - Checks `current.json`.
2. **Resume Check:**
   - If `current.json` status is `READY_FOR_HANDOFF` from Windows:
     - Verify local git branch and SHA.
     - Present handoff summary to user/orchestrator: *"Resuming task `<task_id>` from Windows..."*
     - Transition state to `RESUMED`.
3. **Execution:**
   - Anti executes requested Linux tasks (e.g. Linux build, test runs, Docker execution).
4. **Handoff Preparation:**
   - User requests switch to Windows:
     - Anti commits work or generates patch.
     - Runs verification tests.
     - Writes `current.json` with status `READY_FOR_HANDOFF`.
     - Appends event to `events.jsonl`.

---

## P. Bootstrap Protocol (Session Start Reflex)

When an agent session begins:
```text
Step 1: Discover shared root directory:
        - Check env CROSSOS_STATE_DIR
        - Windows: Check D:\anti-crossos-state
        - Linux: Probe findmnt by UUID 3C8CC1178CC0CC98 -> <mount>/anti-crossos-state
Step 2: If shared state directory not found:
        - Gracefully degrade (Cross-OS sync disabled, standard local mode).
Step 3: Resolve current project_id from Git remote or root commit.
Step 4: Check if projects/<project_id>/current.json exists.
Step 5: If exists and status == 'READY_FOR_HANDOFF' from peer OS:
        - Print 1-line notification:
          "⚡ Cross-OS Handoff Pending from <peer_os>: [<task_title>]. Run 'crossos resume' to adopt."
        - DO NOT auto-execute actions without user confirmation.
```

---

## Q. Handoff Protocol (Before Reboot)

Triggered when user states intent to reboot or task requires peer OS capabilities:
```text
Step 1: Check Git working tree:
        - If dirty, prompt user to commit or stage a patch.
Step 2: Run verification commands to capture latest test result.
Step 3: Summarize:
        - Completed milestones
        - Pending items / next action
        - Contextual instructions for peer OS
Step 4: Increment handoff_sequence counter.
Step 5: Write atomic current.json with status = 'READY_FOR_HANDOFF'.
Step 6: Append event HANDOFF_WRITTEN to events.jsonl.
Step 7: Confirm to user:
        "✓ Cross-OS handoff saved (Seq <N>). Safe to reboot to <peer_os>."
```

---

## R. Resume Protocol (After Reboot)

Triggered on peer OS upon user prompt or session start:
```text
Step 1: Read current.json and parse metadata.
Step 2: Validate Git state:
        - Compare active branch with git.branch
        - Compare HEAD SHA with git.head_sha
        - Check if working tree is clean
Step 3: If Git divergence detected:
        - Output divergence report.
        - Require explicit user approval before proceeding.
Step 4: Transition status in current.json to 'RESUMED'.
Step 5: Append event TASK_RESUMED to events.jsonl.
Step 6: Present execution plan based on execution.next_action.
```

---

## S. Security & Privacy

1. **Zero Credentials Policy:**
   Handoff schema strictly prohibits API keys, OAuth tokens, SSH keys, passwords, and `.env` files.
2. **Data Sanitization:**
   All summary strings, command arguments, and logs are processed through regex redaction (`SECRET_VALUE_PATTERNS` from `debian_memory_bridge.py`) before writing to disk.
3. **No Cross-OS Code Execution Without Review:**
   The `execution.next_action` field contains textual instructions, never raw arbitrary shell scripts that execute blindly without agent/user review.

---

## T. CLI vs MCP Architecture Decision

Three integration models were analyzed:

| Criteria | Option A: CLI Only | Option B: MCP Server Only | Option C: Python Core + CLI + MCP Adapter |
| :--- | :--- | :--- | :--- |
| **Complexity** | Very Low (single Python script) | Medium (FastMCP process, protocol) | Low-Medium (Separated module + thin wrappers)|
| **Dual-Boot Reliability** | High (Zero daemon, runs anywhere) | Medium (Requires active Antigravity session)| **High** (CLI works in terminal, MCP in GUI) |
| **Debuggability** | Instant (`python script.py status`) | Requires MCP inspector / logs | **Instant** (direct CLI commands) |
| **Agent Ergonomics** | Needs `run_command` | Native IDE tool call (`call_tool`) | **Both** (Native tool or CLI execution) |
| **Cross-Platform Parity** | 100% Python stdlib | Requires venv & MCP libraries | **100% Core stdlib**, MCP optional |

### Decision: **Option C (Core Library + CLI + Optional MCP Adapter)**
* **Phase 1 Implementation:** Deliver `crossos_core.py` (stdlib only) and `crossos_ctl.py` (CLI interface).
* **Future Layer:** Add a lightweight MCP wrapper (`crossos_mcp.py`) that delegates directly to `crossos_core.py`.

---

## U. Recommended V1 Specification

* **Module Package:** Single portable utility folder `scripts/ai-crossos/`:
  - `crossos_core.py`: Standalone Python standard library module (file IO, hashing, atomic writes, discovery).
  - `crossos_ctl.py`: Human & agent CLI (`status`, `begin`, `handoff`, `resume`, `complete`, `validate`).
* **Runtime Dependencies:** `0` external PyPI packages (uses `json`, `hashlib`, `pathlib`, `os`, `shutil`, `argparse`).
* **Shared Store Location:** `<UUID:3C8CC1178CC0CC98>/anti-crossos-state/`.

---

## V. Acceptance Criteria

1. **Zero State Mutation During Design Phase:** No state directories or code created until design approved.
2. **Deterministic Project Matching:** Windows and Debian test cases compute identical 16-hex `project_id` for given repository URL.
3. **Atomic Write Resilience:** Simulated write interruption leaves `current.json` intact or recoverable via `current.json.previous`.
4. **Git Divergence Detection:** Protocol successfully flags and blocks execution when simulated branch or commit SHA does not match.
5. **Zero Secret Leakage:** Redaction tests prove tokens and keys are scrubbed before serialization.

---

## W. Future V2 Roadmap

1. **Remote Cloud Bridge (Optional):**
   Add S3 / WebDAV / Git-backed remote storage adapter if Windows and Debian ever run simultaneously on separate physical machines.
2. **Automatic Patch Staging:**
   Automate `git diff` patch bundling and checksum validation for seamless transfer of uncommitted micro-slices.
3. **IDE Notification Integration:**
   Native Antigravity status bar indicator showing pending cross-OS handoffs upon opening a workspace.
