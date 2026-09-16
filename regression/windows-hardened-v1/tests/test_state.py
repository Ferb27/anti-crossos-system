import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

package_dir = Path(__file__).resolve().parent.parent
if str(package_dir) not in sys.path:
    sys.path.insert(0, str(package_dir))

import crossos_core as core


class TestStateHardened(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="crossos-test-state-")
        self.state_dir = Path(self.temp_dir) / "state"
        self.repo_dir = Path(self.temp_dir) / "repo"
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        git_config = self.repo_dir / ".git" / "config"
        git_config.parent.mkdir(parents=True, exist_ok=True)
        git_config.write_text(
            '[core]\n\trepositoryformatversion = 0\n[remote "origin"]\n\turl = https://github.com/org/test-project.git\n',
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_lifecycle(self):
        """Test complete lifecycle: begin -> handoff -> resume -> complete(PASS)."""
        # 1. Begin
        t1 = core.begin_task(
            repo_path=self.repo_dir,
            title="Implement state tests",
            intent="Ensure state machine integrity",
            state_dir=self.state_dir,
        )
        self.assertEqual(t1["task"]["status"], "IN_PROGRESS")
        self.assertEqual(t1["handoff_sequence"], 1)

        # 2. Handoff
        h1 = core.prepare_handoff(
            repo_path=self.repo_dir,
            next_action="Run test suite on Windows",
            summary="Implemented state tests on Debian",
            instructions_for_peer="Check Python version >= 3.10",
            verification_result="PASS",
            state_dir=self.state_dir,
        )
        self.assertEqual(h1["task"]["status"], "READY_FOR_HANDOFF")
        self.assertEqual(h1["handoff_sequence"], 2)

        # 3. Resume (hardened: no --force parameter)
        r1 = core.resume_task(repo_path=self.repo_dir, state_dir=self.state_dir)
        self.assertEqual(r1["task"]["status"], "RESUMED")

        # 4. Complete
        c1 = core.complete_task(
            repo_path=self.repo_dir,
            result="PASS",
            evidence_summary="All unit tests passed",
            state_dir=self.state_dir,
        )
        self.assertEqual(c1["task"]["status"], "PASS")

        # Check archive exists in tasks/
        proj_id = t1["project_id"]
        archive_file = self.state_dir / "projects" / proj_id / "tasks" / f"{t1['task_id']}.json"
        self.assertTrue(archive_file.exists())
        archived_data = json.loads(archive_file.read_text(encoding="utf-8"))
        self.assertEqual(archived_data["task"]["status"], "PASS")

    def test_fix_required_is_non_terminal(self):
        """Verify FIX_REQUIRED updates status, does not archive, and allows continuation."""
        t1 = core.begin_task(
            repo_path=self.repo_dir,
            title="Fix bug task",
            state_dir=self.state_dir,
        )
        # Complete with FIX_REQUIRED
        c1 = core.complete_task(
            repo_path=self.repo_dir,
            result="FIX_REQUIRED",
            evidence_summary="Test failed on edge case 4",
            state_dir=self.state_dir,
        )
        self.assertEqual(c1["task"]["status"], "FIX_REQUIRED")

        # Verify not archived to tasks/
        proj_id = t1["project_id"]
        archive_file = self.state_dir / "projects" / proj_id / "tasks" / f"{t1['task_id']}.json"
        self.assertFalse(archive_file.exists())

        # Verify task can still be handed off from FIX_REQUIRED
        h1 = core.prepare_handoff(
            repo_path=self.repo_dir,
            next_action="Investigate edge case 4",
            state_dir=self.state_dir,
        )
        self.assertEqual(h1["task"]["status"], "READY_FOR_HANDOFF")

    def test_invalid_transitions(self):
        t1 = core.begin_task(
            repo_path=self.repo_dir,
            title="Task 1",
            state_dir=self.state_dir,
        )
        with self.assertRaises(core.InvalidStateTransitionError):
            core.resume_task(repo_path=self.repo_dir, state_dir=self.state_dir)

        with self.assertRaises(core.InvalidStateTransitionError):
            core.begin_task(
                repo_path=self.repo_dir,
                title="Task 2",
                state_dir=self.state_dir,
            )

    def test_events_logged(self):
        t1 = core.begin_task(
            repo_path=self.repo_dir,
            title="Event test task",
            state_dir=self.state_dir,
        )
        events = core.get_events(repo_path=self.repo_dir, state_dir=self.state_dir)
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "TASK_CREATED")


if __name__ == "__main__":
    unittest.main()
