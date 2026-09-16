#!/usr/bin/env python3
"""Cross-OS Handoff Control Plane V1 Core Library.

Enables asynchronous task handover between Antigravity Debian and Antigravity
Windows across cold reboots via a shared NTFS partition.
Uses strictly the Python >= 3.10 standard library (zero external PyPI dependencies).
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "1.0.0"
SCHEMA_VERSION = 1
DEFAULT_SHARED_UUID = "3C8CC1178CC0CC98"
DEFAULT_STATE_DIRNAME = "anti-crossos-state"
DEFAULT_TOOLKIT_DIRNAME = "anti-crossos-toolkit"

VALID_STATUSES = {
    "NEW",
    "IN_PROGRESS",
    "READY_FOR_HANDOFF",
    "RESUMED",
    "PASS",
    "FIX_REQUIRED",
    "BLOCKED",
    "ESCALATE",
}

TERMINAL_STATUSES = {"PASS", "BLOCKED", "ESCALATE"}
NON_TERMINAL_STATUSES = {"NEW", "IN_PROGRESS", "READY_FOR_HANDOFF", "RESUMED", "FIX_REQUIRED"}

# Secret redaction patterns matching debian_memory_bridge.py and Windows codex-memory bridge
SECRET_VALUE_PATTERNS = [
    re.compile(r"(?is)(-----BEGIN [^-]*PRIVATE KEY-----).*?(-----END [^-]*PRIVATE KEY-----)", re.MULTILINE),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+"),
    re.compile(r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret|cookie|credential)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)\b(?:sk|rk|pk|ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\b(?:sk|rk|pk)-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z-_]{35}\b"),
    re.compile(r"(?m)^([A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|AUTH|CREDENTIAL)[A-Z0-9_]*\s*=\s*)[^\r\n]+"),
]


class CrossOSError(Exception):
    """Base exception for Cross-OS handoff operations."""
    pass


class ProjectIDRequiredError(CrossOSError):
    """Raised when project identity cannot be resolved from Git and no explicit ID was provided."""
    pass


class DirtyWorktreeError(CrossOSError):
    """Raised when an operation requires a clean Git working tree but uncommitted changes exist."""
    pass


class GitDivergenceError(CrossOSError):
    """Raised when repository state on peer OS diverges from expected handoff state."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class InvalidStateTransitionError(CrossOSError):
    """Raised when a requested state transition is not allowed by the state machine."""
    pass


class CorruptedStateError(CrossOSError):
    """Raised when state files are unreadable or corrupt."""
    pass


class RemoteIdentityMismatchError(CrossOSError):
    """Raised when repository remote seed does not match expected handoff state."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


def utc_now() -> str:
    """Return ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_current_os() -> str:
    """Return normalized current operating system string: 'debian' or 'windows'."""
    if sys.platform == "win32":
        return "windows"
    return "debian"


def redact(value: Any, limit: Optional[int] = None) -> str:
    """Sanitize secrets, tokens, passwords, and private keys from strings."""
    if value is None:
        return ""
    text = str(value).encode("utf-8", errors="replace").decode("utf-8")
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.pattern.startswith("(?is)(-----"):
            text = pattern.sub(r"\1[REDACTED]\2", text)
        elif "bearer" in pattern.pattern.lower():
            text = pattern.sub(r"\1[REDACTED]", text)
        elif "ghp|gho" in pattern.pattern or "sk|rk|pk" in pattern.pattern or "AIza" in pattern.pattern:
            text = pattern.sub("[REDACTED]", text)
        elif pattern.pattern.startswith("(?m)^([A-Z0-9_]*"):
            text = pattern.sub(r"\1[REDACTED]", text)
        else:
            text = pattern.sub(r"\1[REDACTED]", text)
    if limit is not None and len(text) > limit:
        text = text[: max(0, limit - 32)] + " …[truncated]"
    return text


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact sensitive values within a dictionary."""
    sanitized: Dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, str):
            sanitized[k] = redact(v)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [redact(item) if isinstance(item, str) else (sanitize_dict(item) if isinstance(item, dict) else item) for item in v]
        else:
            sanitized[k] = v
    return sanitized


def find_shared_root() -> Optional[Path]:
    """Discover the shared NTFS partition root across Windows and Debian.
    
    Priority:
    1. CROSSOS_SHARED_ROOT environment variable
    2. CROSSOS_STATE_DIR parent environment variable
    3. Windows: D:\\ drive if existing
    4. Linux: probe findmnt by UUID 3C8CC1178CC0CC98
    5. Existing codex_base path discovery (drive root)
    6. Common fallback mount paths (/media/*/*, /mnt/d)
    """
    # 1. Direct shared root override
    env_shared = os.environ.get("CROSSOS_SHARED_ROOT")
    if env_shared:
        p = Path(env_shared).resolve()
        if p.exists() and p.is_dir():
            return p

    # 2. State dir parent override
    env_state = os.environ.get("CROSSOS_STATE_DIR")
    if env_state:
        p = Path(env_state).resolve().parent
        if p.exists() and p.is_dir():
            return p

    # 3. Windows platform
    if sys.platform == "win32":
        win_p = Path(r"D:\ ")
        win_d = Path(str(win_p).strip())
        if win_d.exists():
            return win_d

    # 4. Linux findmnt probe by UUID
    if sys.platform != "win32":
        try:
            out = subprocess.check_output(
                ["findmnt", "-rn", "-S", f"UUID={DEFAULT_SHARED_UUID}", "-o", "TARGET"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).strip()
            if out:
                unescaped = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), out)
                target_p = Path(unescaped).resolve()
                if target_p.exists() and target_p.is_dir():
                    return target_p
        except (OSError, subprocess.SubprocessError):
            pass

    # 5. Codex Base discovery mechanism
    media_candidates = glob.glob("/media/*/*/codex_base") + glob.glob("/media/*/codex_base") + ["/mnt/d/codex_base"]
    for cand in media_candidates:
        p = Path(cand)
        if p.exists():
            root_cand = p.parent
            if root_cand.exists() and root_cand.is_dir():
                return root_cand

    # 6. Username-independent dynamic mount discovery
    dynamic_candidates = glob.glob("/media/*/*") + glob.glob("/mnt/*")
    for cand in dynamic_candidates:
        cand_p = Path(cand)
        if cand_p.exists() and cand_p.is_dir():
            if (cand_p / "codex_base").exists() or (cand_p / DEFAULT_STATE_DIRNAME).exists() or (cand_p / DEFAULT_TOOLKIT_DIRNAME).exists():
                return cand_p

    return None


def get_default_state_dir() -> Path:
    """Return default state root directory."""
    env_state = os.environ.get("CROSSOS_STATE_DIR")
    if env_state:
        return Path(env_state).resolve()
    shared_root = find_shared_root()
    if not shared_root:
        raise CrossOSError(
            "Shared storage not found. Ensure Drive D: (UUID 3C8CC1178CC0CC98) is mounted or set CROSSOS_STATE_DIR."
        )
    return shared_root / DEFAULT_STATE_DIRNAME


def compute_scope_id_legacy(repo_path: Path) -> Tuple[str, str]:
    """Exact TencentDB scope_id algorithm from debian_memory_bridge.py."""
    git_config = repo_path / ".git" / "config"
    name = repo_path.name
    seed = str(repo_path.resolve())

    if git_config.exists():
        try:
            content = git_config.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                if "url =" in line:
                    seed = line.split("url =", 1)[1].strip()
                    match = re.search(r"[:/]([^/:]+?)(?:\.git)?$", seed)
                    if match:
                        name = match.group(1)
                    break
        except Exception:
            pass

    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return h, name


def compute_project_id(repo_path: Path, explicit_id: Optional[str] = None) -> Tuple[str, str]:
    """Resolve project ID with 100% parity with TencentDB scope_id when Git remote exists.
    
    If explicit_id is provided, validates format and uses it directly.
    Otherwise, extracts Git remote URL identically to debian_memory_bridge.py.
    If no Git remote exists, raises ProjectIDRequiredError (V1 requires explicit ID for non-remote repos).
    """
    repo_path = repo_path.resolve()
    name = repo_path.name

    if explicit_id:
        cleaned_id = explicit_id.strip().lower()
        if not re.match(r"^[0-9a-f]{8,64}$", cleaned_id):
            raise CrossOSError(f"Invalid explicit project_id format: '{explicit_id}'. Must be 8-64 hex characters.")
        return cleaned_id, name

    # Check git configuration
    git_config = repo_path / ".git" / "config"
    seed: Optional[str] = None

    if git_config.exists() and git_config.is_file():
        try:
            content = git_config.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                if "url =" in line:
                    seed = line.split("url =", 1)[1].strip()
                    match = re.search(r"[:/]([^/:]+?)(?:\.git)?$", seed)
                    if match:
                        name = match.group(1)
                    break
        except Exception:
            pass

    # Fallback to git command if .git is a worktree file or git config command is available
    if not seed:
        try:
            res = subprocess.run(
                ["git", "-C", str(repo_path), "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            if res.returncode == 0 and res.stdout.strip():
                seed = res.stdout.strip()
                match = re.search(r"[:/]([^/:]+?)(?:\.git)?$", seed)
                if match:
                    name = match.group(1)
        except (OSError, subprocess.SubprocessError):
            pass

    if not seed:
        raise ProjectIDRequiredError(
            f"Repository '{repo_path}' has no Git remote URL. Cross-OS identification requires a Git remote "
            f"or an explicit '--project-id <id>' argument."
        )

    # Compute sha256 [:16] identically to TencentDB
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return h, name


def inspect_git(repo_path: Path) -> Dict[str, Any]:
    """Inspect fresh Git working tree status non-destructively."""
    repo_path = repo_path.resolve()
    git_info: Dict[str, Any] = {
        "is_git_repo": False,
        "remote_url": "",
        "remote_normalized_seed": "",
        "branch": "",
        "head_sha": "",
        "dirty": False,
        "uncommitted_files_count": 0,
    }

    try:
        # Check if inside git work tree
        res_toplevel = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
        if res_toplevel.returncode != 0:
            return git_info

        git_info["is_git_repo"] = True

        # Remote URL
        res_remote = subprocess.run(
            ["git", "-C", str(repo_path), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if res_remote.returncode == 0 and res_remote.stdout.strip():
            url = res_remote.stdout.strip()
            git_info["remote_url"] = url
            git_info["remote_normalized_seed"] = url.strip().lower()
        else:
            git_config = repo_path / ".git" / "config"
            if git_config.exists() and git_config.is_file():
                try:
                    for line in git_config.read_text(encoding="utf-8", errors="replace").splitlines():
                        if "url =" in line:
                            url = line.split("url =", 1)[1].strip()
                            git_info["remote_url"] = url
                            git_info["remote_normalized_seed"] = url.strip().lower()
                            break
                except Exception:
                    pass

        # Branch
        res_branch = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if res_branch.returncode == 0:
            git_info["branch"] = res_branch.stdout.strip()

        # HEAD SHA
        res_sha = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if res_sha.returncode == 0:
            git_info["head_sha"] = res_sha.stdout.strip()

        # Dirty status
        res_status = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if res_status.returncode == 0:
            lines = [line for line in res_status.stdout.splitlines() if line.strip()]
            git_info["uncommitted_files_count"] = len(lines)
            git_info["dirty"] = len(lines) > 0

    except (OSError, subprocess.SubprocessError) as err:
        git_info["error"] = str(err)

    return git_info


def atomic_save_json(target_path: Path, data: Dict[str, Any], rotate_previous: bool = True) -> None:
    """Best-effort crash-resilient atomic write and replace.
    
    1. Writes JSON to temporary file in the same directory volume.
    2. Flushes and fsyncs file descriptor.
    3. If target_path exists and rotate_previous is True, copies target_path to .previous.
    4. Replaces target_path atomically using os.replace().
    """
    target_path = target_path.resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_name(f"{target_path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")

    try:
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        if rotate_previous and target_path.exists():
            prev_path = target_path.with_name(f"{target_path.name}.previous")
            try:
                shutil.copy2(target_path, prev_path)
            except Exception:
                # Documented: non-fatal, proceed with replacement
                pass

        os.replace(temp_path, target_path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


def append_event(events_path: Path, event: Dict[str, Any]) -> bool:
    """Append-only single event logger with fsync."""
    events_path = events_path.resolve()
    events_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        with events_path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        return True
    except Exception:
        return False


def read_snapshot(project_dir: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Read current task snapshot with authoritative fallback policy.
    
    Order:
    1. current.json
    2. current.json.previous
    3. If files exist but invalid/corrupted -> (None, "CORRUPTED_HANDOFF_STATE")
    4. If no snapshot files exist -> (None, None)
    
    events.jsonl is preserved strictly as an audit trail and diagnostic log,
    never used to fabricate authoritative state.
    """
    current_path = project_dir / "current.json"
    prev_path = project_dir / "current.json.previous"

    # 1. Try reading primary current.json
    if current_path.exists():
        try:
            content = current_path.read_text(encoding="utf-8").strip()
            if content:
                data = json.loads(content)
                if isinstance(data, dict) and "task" in data and "task_id" in data:
                    return data, None
        except Exception:
            pass

    # 2. Fallback to current.json.previous
    if prev_path.exists():
        try:
            content = prev_path.read_text(encoding="utf-8").strip()
            if content:
                data = json.loads(content)
                if isinstance(data, dict) and "task" in data and "task_id" in data:
                    return data, "RECOVERED_FROM_PREVIOUS_SNAPSHOT"
        except Exception:
            pass

    # 3. If either current or previous file exists but neither was valid
    if current_path.exists() or prev_path.exists():
        return None, "CORRUPTED_HANDOFF_STATE"

    return None, None


# ----------------------------------------------------------------------
# Core Controller Workflows
# ----------------------------------------------------------------------

def begin_task(
    repo_path: Path,
    title: str,
    intent: str = "",
    state_dir: Optional[Path] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Initiate a new in-flight task for a project."""
    repo_path = repo_path.resolve()
    state_dir = state_dir.resolve() if state_dir else get_default_state_dir()
    proj_id, proj_name = compute_project_id(repo_path, explicit_id=project_id)
    project_dir = state_dir / "projects" / proj_id

    # Check existing snapshot
    existing, recovery_note = read_snapshot(project_dir)
    if recovery_note == "CORRUPTED_HANDOFF_STATE":
        raise CorruptedStateError(
            f"CORRUPTED_HANDOFF_STATE: Primary and backup snapshots for project '{proj_id}' are corrupted. "
            f"Manual intervention required; refusing to overwrite or fabricate state."
        )
    if existing:
        curr_status = existing.get("task", {}).get("status", "")
        if curr_status not in TERMINAL_STATUSES and curr_status != "":
            raise InvalidStateTransitionError(
                f"Cannot begin new task. Existing task '{existing.get('task_id')}' is currently active in state '{curr_status}'. "
                f"Complete or archive it before starting a new task."
            )

    git_info = inspect_git(repo_path)
    now_ts = utc_now()
    task_id = f"task-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"

    task_record = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "project_id": proj_id,
        "project_name": proj_name,
        "task_id": task_id,
        "handoff_sequence": 1,
        "writer": {
            "os": get_current_os(),
            "hostname": platform.node(),
            "written_at": now_ts,
        },
        "task": {
            "title": redact(title),
            "intent": redact(intent),
            "status": "IN_PROGRESS",
        },
        "git": {
            "remote_url": git_info.get("remote_url", ""),
            "remote_normalized_seed": git_info.get("remote_normalized_seed", ""),
            "branch": git_info.get("branch", ""),
            "head_sha": git_info.get("head_sha", ""),
            "dirty": git_info.get("dirty", False),
            "uncommitted_files_count": git_info.get("uncommitted_files_count", 0),
            "recommended_action": "CONTINUE_WORK",
        },
        "execution": {
            "summary": f"Task initiated on {get_current_os()}",
            "next_action": "",
            "instructions_for_peer_os": "",
        },
        "verification": {
            "last_result": "NONE",
            "test_commands": [],
            "evidence_summary": "",
        },
        "artifacts": [],
        "rag": {
            "relevant_scope_id": proj_id,
            "durable_learning_captured": False,
        },
        "timestamps": {
            "created_at": now_ts,
            "updated_at": now_ts,
        },
    }

    # Save project specification
    projectspec = {
        "schema_version": SCHEMA_VERSION,
        "project_id": proj_id,
        "project_name": proj_name,
        "remote_url": git_info.get("remote_url", ""),
        "remote_normalized_seed": git_info.get("remote_normalized_seed", ""),
        "created_at": now_ts,
        "updated_at": now_ts,
    }

    # Initialize VERSION file in state root
    version_file = state_dir / "VERSION"
    if not version_file.exists():
        atomic_save_json(version_file, {"protocol_version": 1}, rotate_previous=False)

    atomic_save_json(project_dir / "projectspec.json", projectspec, rotate_previous=False)
    atomic_save_json(project_dir / "current.json", task_record, rotate_previous=True)

    # Append event
    event = {
        "event_id": f"evt-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}",
        "sequence": 1,
        "timestamp": now_ts,
        "os": get_current_os(),
        "project_id": proj_id,
        "task_id": task_id,
        "type": "TASK_CREATED",
        "summary": f"Task '{title}' started.",
        "actor": "anti_local_worker",
        "payload": {
            "status": "IN_PROGRESS",
            "head_sha": git_info.get("head_sha", ""),
        },
    }
    append_event(project_dir / "events.jsonl", event)

    return task_record


def prepare_handoff(
    repo_path: Path,
    next_action: str,
    summary: str = "",
    instructions_for_peer: str = "",
    verification_result: str = "PASS",
    evidence_summary: str = "",
    test_commands: Optional[List[str]] = None,
    state_dir: Optional[Path] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Freeze task state and prepare handoff snapshot for reboot to peer OS."""
    repo_path = repo_path.resolve()
    state_dir = state_dir.resolve() if state_dir else get_default_state_dir()
    proj_id, _ = compute_project_id(repo_path, explicit_id=project_id)
    project_dir = state_dir / "projects" / proj_id

    snapshot, recovery_note = read_snapshot(project_dir)
    if recovery_note == "CORRUPTED_HANDOFF_STATE":
        raise CorruptedStateError(
            f"CORRUPTED_HANDOFF_STATE: Snapshots for project '{proj_id}' are corrupted. Cannot hand off."
        )
    if not snapshot:
        raise CrossOSError(f"No active task found to hand off for project '{proj_id}'. Run 'crossos begin' first.")

    current_status = snapshot.get("task", {}).get("status")
    if current_status not in {"IN_PROGRESS", "RESUMED", "FIX_REQUIRED"}:
        raise InvalidStateTransitionError(
            f"Cannot hand off task in state '{current_status}'. Allowed states: IN_PROGRESS, RESUMED, FIX_REQUIRED."
        )

    # Fresh Git Inspection — Dirty Worktree Gate (V1 Rule)
    git_info = inspect_git(repo_path)
    if git_info.get("is_git_repo") and git_info.get("dirty"):
        raise DirtyWorktreeError(
            f"DIRTY_WORKTREE: Working tree contains {git_info.get('uncommitted_files_count')} uncommitted changes. "
            f"Cross-OS handoff cannot transfer uncommitted work. Commit changes or reset before handoff."
        )

    now_ts = utc_now()
    seq = snapshot.get("handoff_sequence", 0) + 1

    # Update snapshot fields
    snapshot["handoff_sequence"] = seq
    snapshot["writer"] = {
        "os": get_current_os(),
        "hostname": platform.node(),
        "written_at": now_ts,
    }
    snapshot["task"]["status"] = "READY_FOR_HANDOFF"

    snapshot["git"] = {
        "remote_url": git_info.get("remote_url", snapshot.get("git", {}).get("remote_url", "")),
        "remote_normalized_seed": git_info.get("remote_normalized_seed", snapshot.get("git", {}).get("remote_normalized_seed", "")),
        "branch": git_info.get("branch", snapshot.get("git", {}).get("branch", "")),
        "head_sha": git_info.get("head_sha", snapshot.get("git", {}).get("head_sha", "")),
        "dirty": False,
        "uncommitted_files_count": 0,
        "recommended_action": "VERIFY_AND_RESUME",
    }

    snapshot["execution"] = {
        "summary": redact(summary or snapshot.get("execution", {}).get("summary", "")),
        "next_action": redact(next_action),
        "instructions_for_peer_os": redact(instructions_for_peer),
    }

    snapshot["verification"] = {
        "last_result": verification_result.upper(),
        "test_commands": [redact(cmd) for cmd in (test_commands or [])],
        "evidence_summary": redact(evidence_summary),
    }

    snapshot["timestamps"]["updated_at"] = now_ts

    # Atomic write-replace with previous snapshot rotation
    atomic_save_json(project_dir / "current.json", snapshot, rotate_previous=True)

    # Append event
    event = {
        "event_id": f"evt-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}",
        "sequence": seq,
        "timestamp": now_ts,
        "os": get_current_os(),
        "project_id": proj_id,
        "task_id": snapshot.get("task_id"),
        "type": "HANDOFF_WRITTEN",
        "summary": f"Handoff sequence {seq} prepared on {get_current_os()}.",
        "actor": "anti_local_worker",
        "payload": {
            "status": "READY_FOR_HANDOFF",
            "head_sha": git_info.get("head_sha", ""),
            "next_action": redact(next_action),
        },
    }
    append_event(project_dir / "events.jsonl", event)

    return snapshot


def resume_task(
    repo_path: Path,
    state_dir: Optional[Path] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Resume an in-flight handoff task on the currently booted OS."""
    repo_path = repo_path.resolve()
    state_dir = state_dir.resolve() if state_dir else get_default_state_dir()
    proj_id, _ = compute_project_id(repo_path, explicit_id=project_id)
    project_dir = state_dir / "projects" / proj_id

    snapshot, recovery_note = read_snapshot(project_dir)
    if recovery_note == "CORRUPTED_HANDOFF_STATE":
        raise CorruptedStateError(
            f"CORRUPTED_HANDOFF_STATE: Snapshots for project '{proj_id}' are corrupt. Cannot resume."
        )
    if not snapshot:
        raise CrossOSError(f"No handoff state found for project '{proj_id}'.")

    current_status = snapshot.get("task", {}).get("status")
    if current_status != "READY_FOR_HANDOFF":
        raise InvalidStateTransitionError(
            f"Cannot resume task in state '{current_status}'. Status must be 'READY_FOR_HANDOFF'."
        )

    # Validate Git state against handoff expectations
    git_info = inspect_git(repo_path)
    divergences: List[str] = []

    if git_info.get("is_git_repo"):
        expected_branch = snapshot.get("git", {}).get("branch")
        expected_sha = snapshot.get("git", {}).get("head_sha")
        expected_seed = snapshot.get("git", {}).get("remote_normalized_seed")
        actual_seed = git_info.get("remote_normalized_seed")

        # Remote identity match check
        if expected_seed and actual_seed and expected_seed != actual_seed:
            raise RemoteIdentityMismatchError(
                f"PROJECT_REMOTE_IDENTITY_MISMATCH: Handoff remote seed '{expected_seed}' does not match "
                f"receiving repository remote seed '{actual_seed}'. Both clones must use matching remote URLs.",
                details={"expected_remote_seed": expected_seed, "actual_remote_seed": actual_seed},
            )

        if git_info.get("dirty"):
            divergences.append(f"Local working tree is dirty ({git_info.get('uncommitted_files_count')} changes)")
        if expected_branch and git_info.get("branch") != expected_branch:
            divergences.append(f"Branch mismatch: expected '{expected_branch}', found '{git_info.get('branch')}'")
        if expected_sha and git_info.get("head_sha") != expected_sha:
            divergences.append(f"HEAD SHA mismatch: expected '{expected_sha}', found '{git_info.get('head_sha')}'")

    if divergences:
        raise GitDivergenceError(
            f"HANDOFF_DIVERGENCE: Cannot resume task due to repository divergence:\n" +
            "\n".join(f"  - {d}" for d in divergences) +
            "\nSynchronize repository state before resuming.",
            details={"divergences": divergences, "git_info": git_info},
        )

    now_ts = utc_now()
    snapshot["task"]["status"] = "RESUMED"
    snapshot["writer"] = {
        "os": get_current_os(),
        "hostname": platform.node(),
        "written_at": now_ts,
    }
    snapshot["timestamps"]["updated_at"] = now_ts

    atomic_save_json(project_dir / "current.json", snapshot, rotate_previous=True)

    # Append event
    event = {
        "event_id": f"evt-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}",
        "sequence": snapshot.get("handoff_sequence", 0),
        "timestamp": now_ts,
        "os": get_current_os(),
        "project_id": proj_id,
        "task_id": snapshot.get("task_id"),
        "type": "TASK_RESUMED",
        "summary": f"Task resumed on {get_current_os()}.",
        "actor": "anti_local_worker",
        "payload": {
            "status": "RESUMED",
            "head_sha": git_info.get("head_sha", ""),
        },
    }
    append_event(project_dir / "events.jsonl", event)

    return snapshot


def complete_task(
    repo_path: Path,
    result: str = "PASS",
    evidence_summary: str = "",
    state_dir: Optional[Path] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Complete a task with terminal status (PASS, BLOCKED, ESCALATE) or update FIX_REQUIRED."""
    repo_path = repo_path.resolve()
    state_dir = state_dir.resolve() if state_dir else get_default_state_dir()
    proj_id, _ = compute_project_id(repo_path, explicit_id=project_id)
    project_dir = state_dir / "projects" / proj_id

    snapshot, recovery_note = read_snapshot(project_dir)
    if recovery_note == "CORRUPTED_HANDOFF_STATE":
        raise CorruptedStateError(
            f"CORRUPTED_HANDOFF_STATE: Snapshots for project '{proj_id}' are corrupt. Cannot complete."
        )
    if not snapshot:
        raise CrossOSError(f"No active task found for project '{proj_id}'.")

    result = result.upper()
    if result not in {"PASS", "FIX_REQUIRED", "BLOCKED", "ESCALATE"}:
        raise CrossOSError(f"Invalid completion result '{result}'. Must be PASS, FIX_REQUIRED, BLOCKED, or ESCALATE.")

    now_ts = utc_now()
    snapshot["task"]["status"] = result
    snapshot["verification"]["last_result"] = result
    if evidence_summary:
        snapshot["verification"]["evidence_summary"] = redact(evidence_summary)
    snapshot["timestamps"]["updated_at"] = now_ts

    task_id = snapshot.get("task_id", "unknown")

    # If terminal status (PASS, BLOCKED, ESCALATE), archive copy to tasks/<task_id>.json
    if result in TERMINAL_STATUSES:
        tasks_dir = project_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        archive_path = tasks_dir / f"{task_id}.json"
        atomic_save_json(archive_path, snapshot, rotate_previous=False)

    atomic_save_json(project_dir / "current.json", snapshot, rotate_previous=True)

    # Append event
    event = {
        "event_id": f"evt-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}",
        "sequence": snapshot.get("handoff_sequence", 0),
        "timestamp": now_ts,
        "os": get_current_os(),
        "project_id": proj_id,
        "task_id": task_id,
        "type": "TASK_COMPLETED" if result == "PASS" else ("TASK_BLOCKED" if result in {"BLOCKED", "ESCALATE"} else "VERIFICATION_RUN"),
        "summary": f"Task ended with status '{result}'.",
        "actor": "anti_local_worker",
        "payload": {
            "status": result,
            "evidence": redact(evidence_summary),
        },
    }
    append_event(project_dir / "events.jsonl", event)

    return snapshot


def get_status(
    repo_path: Path,
    state_dir: Optional[Path] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Read-only query of project handoff status without modifying any files."""
    repo_path = repo_path.resolve()
    shared_root = find_shared_root()
    resolved_state_dir = state_dir.resolve() if state_dir else (shared_root / DEFAULT_STATE_DIRNAME if shared_root else None)

    status_data: Dict[str, Any] = {
        "ok": True,
        "repo_path": str(repo_path),
        "shared_root": str(shared_root) if shared_root else None,
        "state_dir": str(resolved_state_dir) if resolved_state_dir else None,
        "project_id": None,
        "project_name": repo_path.name,
        "active_task": None,
        "pending_handoff": False,
        "git_match": True,
        "warnings": [],
    }

    if not resolved_state_dir or not resolved_state_dir.exists():
        status_data["warnings"].append("State directory does not exist or shared drive is not mounted.")
        return status_data

    try:
        proj_id, proj_name = compute_project_id(repo_path, explicit_id=project_id)
        status_data["project_id"] = proj_id
        status_data["project_name"] = proj_name
    except ProjectIDRequiredError as e:
        status_data["warnings"].append(str(e))
        return status_data

    project_dir = resolved_state_dir / "projects" / proj_id
    if not project_dir.exists():
        status_data["warnings"].append(f"No handoff state exists for project '{proj_id}'.")
        return status_data

    snapshot, recovery_note = read_snapshot(project_dir)
    if recovery_note == "CORRUPTED_HANDOFF_STATE":
        status_data["warnings"].append("CORRUPTED_HANDOFF_STATE: Primary and backup snapshots are unreadable or corrupt.")
        status_data["ok"] = False
        return status_data
    elif recovery_note:
        status_data["warnings"].append(f"Recovery: {recovery_note}")

    if not snapshot:
        status_data["warnings"].append("No readable task snapshot found.")
        return status_data

    task_status = snapshot.get("task", {}).get("status", "")
    writer_os = snapshot.get("writer", {}).get("os", "")
    current_os = get_current_os()

    is_pending = (task_status == "READY_FOR_HANDOFF" and writer_os != current_os)

    git_info = inspect_git(repo_path)
    git_match = True
    remote_identity_match = True

    if git_info.get("is_git_repo"):
        expected_sha = snapshot.get("git", {}).get("head_sha")
        expected_branch = snapshot.get("git", {}).get("branch")
        expected_seed = snapshot.get("git", {}).get("remote_normalized_seed")
        actual_seed = git_info.get("remote_normalized_seed")

        if expected_seed and actual_seed and expected_seed != actual_seed:
            remote_identity_match = False
            git_match = False
            if project_id:
                status_data["warnings"].append(
                    f"PROJECT_ID_EXPLICIT: REMOTE_IDENTITY_DIFFERENT (Writer seed: '{expected_seed}', Local seed: '{actual_seed}')"
                )
            else:
                status_data["warnings"].append(
                    f"REMOTE_IDENTITY_DIFFERENT: Writer seed '{expected_seed}' differs from local '{actual_seed}'."
                )

        if task_status == "READY_FOR_HANDOFF":
            if (expected_sha and git_info.get("head_sha") != expected_sha) or \
               (expected_branch and git_info.get("branch") != expected_branch) or \
               git_info.get("dirty"):
                git_match = False

    status_data["active_task"] = {
        "task_id": snapshot.get("task_id"),
        "title": snapshot.get("task", {}).get("title"),
        "status": task_status,
        "writer_os": writer_os,
        "handoff_sequence": snapshot.get("handoff_sequence"),
        "next_action": snapshot.get("execution", {}).get("next_action"),
        "instructions_for_peer_os": snapshot.get("execution", {}).get("instructions_for_peer_os"),
        "updated_at": snapshot.get("timestamps", {}).get("updated_at"),
    }
    status_data["pending_handoff"] = is_pending
    status_data["git_match"] = git_match
    status_data["remote_identity_match"] = remote_identity_match

    return status_data


def get_events(
    repo_path: Path,
    state_dir: Optional[Path] = None,
    project_id: Optional[str] = None,
    tail: int = 10,
) -> List[Dict[str, Any]]:
    """Retrieve recent events from the project audit log."""
    repo_path = repo_path.resolve()
    state_dir = state_dir.resolve() if state_dir else get_default_state_dir()
    proj_id, _ = compute_project_id(repo_path, explicit_id=project_id)
    events_path = state_dir / "projects" / proj_id / "events.jsonl"

    if not events_path.exists():
        return []

    events: List[Dict[str, Any]] = []
    try:
        lines = events_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-tail:]:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return events


def validate_state_integrity(state_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Validate directory structure and JSON integrity of state repository."""
    resolved_state_dir = state_dir.resolve() if state_dir else get_default_state_dir()
    res: Dict[str, Any] = {
        "valid": True,
        "state_dir": str(resolved_state_dir),
        "errors": [],
        "projects_count": 0,
    }

    if not resolved_state_dir.exists():
        res["valid"] = False
        res["errors"].append("State directory does not exist.")
        return res

    version_file = resolved_state_dir / "VERSION"
    if not version_file.exists():
        res["valid"] = False
        res["errors"].append("Missing VERSION file in state root.")

    projects_root = resolved_state_dir / "projects"
    if projects_root.exists() and projects_root.is_dir():
        proj_dirs = [p for p in projects_root.iterdir() if p.is_dir()]
        res["projects_count"] = len(proj_dirs)
        for p in proj_dirs:
            snap, note = read_snapshot(p)
            if note == "CORRUPTED_HANDOFF_STATE":
                res["valid"] = False
                res["errors"].append(f"Corrupted snapshot state in project '{p.name}'.")

    return res
