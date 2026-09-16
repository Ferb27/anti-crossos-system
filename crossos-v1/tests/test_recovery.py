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


class TestRecoveryHardened(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="crossos-test-recovery-")
        self.state_dir = Path(self.temp_dir) / "state"
        self.repo_dir = Path(self.temp_dir) / "repo"
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        git_config = self.repo_dir / ".git" / "config"
        git_config.parent.mkdir(parents=True, exist_ok=True)
        git_config.write_text(
            '[core]\n\trepositoryformatversion = 0\n[remote "origin"]\n\turl = https://github.com/org/recovery-test.git\n',
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_corrupt_current_json_recovers_from_previous(self):
        """Simulate corrupt current.json and verify automatic recovery from current.json.previous."""
        t1 = core.begin_task(repo_path=self.repo_dir, title="Recovery Task", state_dir=self.state_dir)
        proj_id = t1["project_id"]
        project_dir = self.state_dir / "projects" / proj_id

        core.prepare_handoff(repo_path=self.repo_dir, next_action="Step 2", state_dir=self.state_dir)

        current_file = project_dir / "current.json"
        prev_file = project_dir / "current.json.previous"
        self.assertTrue(prev_file.exists())

        # Corrupt current.json
        current_file.write_text('{"schema_version": 1, "task": {"title": "BROKEN', encoding="utf-8")

        recovered, note = core.read_snapshot(project_dir)
        self.assertIsNotNone(recovered)
        self.assertEqual(note, "RECOVERED_FROM_PREVIOUS_SNAPSHOT")
        self.assertEqual(recovered["task"]["title"], "Recovery Task")

    def test_corrupt_both_snapshots_hard_stops_no_event_fabrication(self):
        """Verify that if both current.json and previous are corrupt, it hard-stops with CORRUPTED_HANDOFF_STATE

        and DOES NOT fabricate state from events.jsonl (events.jsonl is non-authoritative).
        """
        t1 = core.begin_task(repo_path=self.repo_dir, title="Hard stop task", state_dir=self.state_dir)
        proj_id = t1["project_id"]
        project_dir = self.state_dir / "projects" / proj_id

        core.prepare_handoff(repo_path=self.repo_dir, next_action="Step 2", state_dir=self.state_dir)

        current_file = project_dir / "current.json"
        prev_file = project_dir / "current.json.previous"
        self.assertTrue(current_file.exists())
        self.assertTrue(prev_file.exists())

        # Corrupt BOTH snapshot files
        current_file.write_text("CORRUPTED", encoding="utf-8")
        prev_file.write_text("CORRUPTED_PREV", encoding="utf-8")

        # Must return None and CORRUPTED_HANDOFF_STATE
        recovered, note = core.read_snapshot(project_dir)
        self.assertIsNone(recovered)
        self.assertEqual(note, "CORRUPTED_HANDOFF_STATE")

        # Operations must raise CorruptedStateError
        with self.assertRaises(core.CorruptedStateError):
            core.prepare_handoff(repo_path=self.repo_dir, next_action="Should fail", state_dir=self.state_dir)

        with self.assertRaises(core.CorruptedStateError):
            core.resume_task(repo_path=self.repo_dir, state_dir=self.state_dir)

        with self.assertRaises(core.CorruptedStateError):
            core.complete_task(repo_path=self.repo_dir, result="PASS", state_dir=self.state_dir)

    def test_malformed_event_tail_tolerated(self):
        t1 = core.begin_task(repo_path=self.repo_dir, title="Event tail test", state_dir=self.state_dir)
        proj_id = t1["project_id"]
        project_dir = self.state_dir / "projects" / proj_id

        events_file = project_dir / "events.jsonl"
        with events_file.open("a", encoding="utf-8") as f:
            f.write("MALFORMED NON-JSON LINE AT TAIL\n")

        events = core.get_events(repo_path=self.repo_dir, state_dir=self.state_dir)
        self.assertGreaterEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()
