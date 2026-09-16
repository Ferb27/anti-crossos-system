#!/usr/bin/env python3
"""Cross-OS Handoff Control Plane CLI (crossos_ctl).

Provides human and agent CLI commands to inspect, manage, and execute
cross-OS task handoffs across dual-boot reboots.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add package directory to path for local execution
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

import crossos_core as core


def print_json_out(data: Any) -> None:
    """Print clean JSON output to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_status(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    state_dir = Path(args.state_dir).resolve() if args.state_dir else None

    try:
        res = core.get_status(repo_path, state_dir=state_dir, project_id=args.project_id)
        if args.json:
            print_json_out(res)
            return 0

        print(f"=== Cross-OS Task Status ===")
        print(f"Repository:   {res['repo_path']}")
        print(f"Project ID:   {res['project_id'] or '[UNKNOWN]'}")
        print(f"Shared Root:  {res['shared_root'] or '[NOT_FOUND]'}")
        print(f"State Dir:    {res['state_dir'] or '[NONE]'}")

        task = res.get("active_task")
        if task:
            print(f"\nActive Task:  {task['task_id']}")
            print(f"Title:        {task['title']}")
            print(f"Status:       {task['status']}")
            print(f"Writer OS:    {task['writer_os']} (Seq: {task['handoff_sequence']})")
            if task.get("next_action"):
                print(f"Next Action:  {task['next_action']}")
            if task.get("instructions_for_peer_os"):
                print(f"Instructions: {task['instructions_for_peer_os']}")
        else:
            print("\nActive Task:  [NO ACTIVE TASK]")

        if res.get("pending_handoff"):
            print("\n⚡ PENDING HANDOFF DETECTED! Run 'crossos resume' to adopt this task.")

        if res.get("remote_identity_match") is False:
            print("\n⚠️  WARNING: REMOTE IDENTITY MISMATCH DETECTED (PROJECT_ID_EXPLICIT / REMOTE_IDENTITY_DIFFERENT).")

        if res.get("warnings"):
            print("\nWarnings / Notes:")
            for w in res["warnings"]:
                print(f"  - {w}")

        return 0

    except core.ProjectIDRequiredError as err:
        if args.json:
            print_json_out({"ok": False, "error": "PROJECT_ID_REQUIRED", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 4
    except Exception as err:
        if args.json:
            print_json_out({"ok": False, "error": err.__class__.__name__, "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1


def cmd_inspect(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    state_dir = Path(args.state_dir).resolve() if args.state_dir else None

    try:
        shared_root = core.find_shared_root()
        resolved_state_dir = state_dir or (shared_root / core.DEFAULT_STATE_DIRNAME if shared_root else None)
        if not resolved_state_dir or not resolved_state_dir.exists():
            raise core.CrossOSError("State directory does not exist or shared partition is not mounted.")

        proj_id, proj_name = core.compute_project_id(repo_path, explicit_id=args.project_id)
        project_dir = resolved_state_dir / "projects" / proj_id
        if not project_dir.exists():
            raise core.CrossOSError(f"No handoff state exists for project '{proj_id}'.")

        snapshot, recovery_note = core.read_snapshot(project_dir)
        git_info = core.inspect_git(repo_path)
        events = core.get_events(repo_path, state_dir=state_dir, project_id=args.project_id, tail=5)

        inspect_data = {
            "ok": True,
            "project_id": proj_id,
            "project_name": proj_name,
            "recovery_note": recovery_note,
            "current_snapshot": snapshot,
            "fresh_git": git_info,
            "recent_events": events,
        }

        if args.json:
            print_json_out(inspect_data)
            return 0

        print(f"=== Cross-OS State Inspection [{proj_id}] ===")
        if recovery_note:
            print(f"Notice: {recovery_note}\n")
        print(f"Snapshot JSON:\n{json.dumps(snapshot, indent=2, ensure_ascii=False)}")
        print(f"\nFresh Git State:\n{json.dumps(git_info, indent=2, ensure_ascii=False)}")
        return 0

    except core.CorruptedStateError as err:
        if args.json:
            print_json_out({"ok": False, "error": "CORRUPTED_HANDOFF_STATE", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1
    except core.ProjectIDRequiredError as err:
        if args.json:
            print_json_out({"ok": False, "error": "PROJECT_ID_REQUIRED", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 4
    except Exception as err:
        if args.json:
            print_json_out({"ok": False, "error": err.__class__.__name__, "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1


def cmd_begin(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    state_dir = Path(args.state_dir).resolve() if args.state_dir else None

    try:
        res = core.begin_task(
            repo_path=repo_path,
            title=args.title,
            intent=args.intent or "",
            state_dir=state_dir,
            project_id=args.project_id,
        )
        if args.json:
            print_json_out({"ok": True, "task": res})
            return 0

        print(f"✓ Task initiated successfully.")
        print(f"  Task ID:    {res['task_id']}")
        print(f"  Title:      {res['task']['title']}")
        print(f"  Status:     {res['task']['status']}")
        print(f"  Project ID: {res['project_id']}")
        return 0

    except core.ProjectIDRequiredError as err:
        if args.json:
            print_json_out({"ok": False, "error": "PROJECT_ID_REQUIRED", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 4
    except core.InvalidStateTransitionError as err:
        if args.json:
            print_json_out({"ok": False, "error": "INVALID_STATE_TRANSITION", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        if args.json:
            print_json_out({"ok": False, "error": err.__class__.__name__, "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1


def cmd_handoff(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    state_dir = Path(args.state_dir).resolve() if args.state_dir else None

    test_commands = [c.strip() for c in args.test_command.split(";")] if getattr(args, "test_command", None) else []

    try:
        res = core.prepare_handoff(
            repo_path=repo_path,
            next_action=args.next,
            summary=args.summary or "",
            instructions_for_peer=args.instructions or "",
            verification_result=args.verification_result or "PASS",
            evidence_summary=args.evidence or "",
            test_commands=test_commands,
            state_dir=state_dir,
            project_id=args.project_id,
        )
        if args.json:
            print_json_out({"ok": True, "handoff": res})
            return 0

        print(f"✓ Handoff snapshot saved (Sequence {res['handoff_sequence']}).")
        print(f"  Task ID:     {res['task_id']}")
        print(f"  Status:      {res['task']['status']}")
        print(f"  Next Action: {res['execution']['next_action']}")
        print(f"  Safe to reboot to peer OS.")
        return 0

    except core.DirtyWorktreeError as err:
        if args.json:
            print_json_out({"ok": False, "error": "DIRTY_WORKTREE", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 2
    except core.ProjectIDRequiredError as err:
        if args.json:
            print_json_out({"ok": False, "error": "PROJECT_ID_REQUIRED", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 4
    except core.InvalidStateTransitionError as err:
        if args.json:
            print_json_out({"ok": False, "error": "INVALID_STATE_TRANSITION", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        if args.json:
            print_json_out({"ok": False, "error": err.__class__.__name__, "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1


def cmd_resume(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    state_dir = Path(args.state_dir).resolve() if args.state_dir else None

    try:
        res = core.resume_task(
            repo_path=repo_path,
            state_dir=state_dir,
            project_id=args.project_id,
        )
        if args.json:
            print_json_out({"ok": True, "resumed": res})
            return 0

        print(f"✓ Task adopted and resumed on {core.get_current_os()}.")
        print(f"  Task ID:     {res['task_id']}")
        print(f"  Title:       {res['task']['title']}")
        print(f"  Status:      {res['task']['status']}")
        print(f"  Next Action: {res['execution']['next_action']}")
        if res['execution'].get('instructions_for_peer_os'):
            print(f"  Notes:       {res['execution']['instructions_for_peer_os']}")
        return 0

    except core.RemoteIdentityMismatchError as err:
        if args.json:
            print_json_out({"ok": False, "error": "PROJECT_REMOTE_IDENTITY_MISMATCH", "message": str(err), "details": err.details})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 3
    except core.GitDivergenceError as err:
        if args.json:
            print_json_out({"ok": False, "error": "HANDOFF_DIVERGENCE", "message": str(err), "details": err.details})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 3
    except core.CorruptedStateError as err:
        if args.json:
            print_json_out({"ok": False, "error": "CORRUPTED_HANDOFF_STATE", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1
    except core.ProjectIDRequiredError as err:
        if args.json:
            print_json_out({"ok": False, "error": "PROJECT_ID_REQUIRED", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 4
    except core.InvalidStateTransitionError as err:
        if args.json:
            print_json_out({"ok": False, "error": "INVALID_STATE_TRANSITION", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1
    except Exception as err:
        if args.json:
            print_json_out({"ok": False, "error": err.__class__.__name__, "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1


def cmd_complete(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    state_dir = Path(args.state_dir).resolve() if args.state_dir else None

    try:
        res = core.complete_task(
            repo_path=repo_path,
            result=args.result or "PASS",
            evidence_summary=args.evidence or "",
            state_dir=state_dir,
            project_id=args.project_id,
        )
        if args.json:
            print_json_out({"ok": True, "task": res})
            return 0

        print(f"✓ Task status updated to '{res['task']['status']}'.")
        print(f"  Task ID: {res['task_id']}")
        if res['task']['status'] in core.TERMINAL_STATUSES:
            print(f"  Archived to tasks/{res['task_id']}.json.")
        else:
            print(f"  Non-terminal status: task remains active for remediation.")
        return 0

    except core.ProjectIDRequiredError as err:
        if args.json:
            print_json_out({"ok": False, "error": "PROJECT_ID_REQUIRED", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 4
    except Exception as err:
        if args.json:
            print_json_out({"ok": False, "error": err.__class__.__name__, "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).resolve() if args.state_dir else None
    res = core.validate_state_integrity(state_dir=state_dir)
    if args.json:
        print_json_out(res)
        return 0 if res.get("valid") else 1

    if res.get("valid"):
        print(f"✓ State repository is valid. ({res.get('projects_count', 0)} projects)")
        return 0
    else:
        print(f"✗ Validation failed for state repository:")
        for err in res.get("errors", []):
            print(f"  - {err}")
        return 1


def cmd_events(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    state_dir = Path(args.state_dir).resolve() if args.state_dir else None

    try:
        events = core.get_events(repo_path, state_dir=state_dir, project_id=args.project_id, tail=args.tail)
        if args.json:
            print_json_out({"ok": True, "events": events})
            return 0

        print(f"=== Recent Events (Tail {args.tail}) ===")
        for ev in events:
            print(f"[{ev.get('timestamp')}] ({ev.get('os')}) {ev.get('type')}: {ev.get('summary')}")
        return 0

    except core.ProjectIDRequiredError as err:
        if args.json:
            print_json_out({"ok": False, "error": "PROJECT_ID_REQUIRED", "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 4
    except Exception as err:
        if args.json:
            print_json_out({"ok": False, "error": err.__class__.__name__, "message": str(err)})
        else:
            print(f"Error: {err}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crossos",
        description=f"Cross-OS Handoff Control Plane V{core.VERSION}",
    )
    parser.add_argument("--repo", default=".", help="Target repository directory (default: current directory)")
    parser.add_argument("--state-dir", default=None, help="Shared state directory override")
    parser.add_argument("--project-id", default=None, help="Explicit project identifier override")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON to stdout")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Show active task handoff status")
    p_status.set_defaults(func=cmd_status)

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Detailed JSON inspection of handoff state")
    p_inspect.set_defaults(func=cmd_inspect)

    # begin
    p_begin = subparsers.add_parser("begin", help="Initiate a new development task")
    p_begin.add_argument("--title", required=True, help="Task title / summary")
    p_begin.add_argument("--intent", default="", help="Detailed intent / prompt")
    p_begin.set_defaults(func=cmd_begin)

    # handoff
    p_handoff = subparsers.add_parser("handoff", help="Freeze and prepare handoff to peer OS")
    p_handoff.add_argument("--next", required=True, help="Next action description for peer OS")
    p_handoff.add_argument("--summary", default="", help="Summary of work completed so far")
    p_handoff.add_argument("--instructions", default="", help="Contextual notes / instructions for peer OS")
    p_handoff.add_argument("--verification-result", default="PASS", choices=["PASS", "FAIL", "NONE"], help="Last verification outcome")
    p_handoff.add_argument("--evidence", default="", help="Verification evidence summary")
    p_handoff.add_argument("--test-command", default="", help="Semicolon-separated test commands executed")
    p_handoff.set_defaults(func=cmd_handoff)

    # resume
    p_resume = subparsers.add_parser("resume", help="Adopt and resume pending handoff task")
    p_resume.set_defaults(func=cmd_resume)

    # complete
    p_complete = subparsers.add_parser("complete", help="Complete or update task status")
    p_complete.add_argument("--result", default="PASS", choices=["PASS", "FIX_REQUIRED", "BLOCKED", "ESCALATE"], help="Completion result")
    p_complete.add_argument("--evidence", default="", help="Completion / verification evidence")
    p_complete.set_defaults(func=cmd_complete)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate state repository integrity")
    p_val.set_defaults(func=cmd_validate)

    # events
    p_events = subparsers.add_parser("events", help="Show recent state events")
    p_events.add_argument("--tail", type=int, default=10, help="Number of events to display")
    p_events.set_defaults(func=cmd_events)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    code = args.func(args)
    sys.exit(code)


if __name__ == "__main__":
    main()
