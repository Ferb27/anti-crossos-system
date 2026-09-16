import json
import os
import shutil
import sys
import unittest
from pathlib import Path

package_dir = Path(__file__).resolve().parent.parent
if str(package_dir) not in sys.path:
    sys.path.insert(0, str(package_dir))

import crossos_core as core


class TestNTFSIntegrationHardened(unittest.TestCase):
    def setUp(self):
        self.shared_root = core.find_shared_root()
        if not self.shared_root or not self.shared_root.exists():
            self.skipTest("Shared NTFS partition not available for integration testing.")
        
        self.test_state_dir = self.shared_root / "anti-crossos-state-test"
        self.prod_state_dir = self.shared_root / core.DEFAULT_STATE_DIRNAME
        if self.test_state_dir.exists():
            shutil.rmtree(self.test_state_dir, ignore_errors=True)

    def tearDown(self):
        if hasattr(self, "test_state_dir") and self.test_state_dir.exists():
            shutil.rmtree(self.test_state_dir, ignore_errors=True)

    def test_real_ntfs_hardened_lifecycle_and_recovery(self):
        mock_repo = Path("/home/ferb27/anti-crossos-system")
        explicit_id = "aabbccdd00112233"

        # 1. Begin
        t1 = core.begin_task(
            repo_path=mock_repo,
            title="NTFS Integration Hardened Test",
            intent="Verify atomic replace, fsync, and recovery on ntfs3",
            state_dir=self.test_state_dir,
            project_id=explicit_id,
        )
        task_id = t1["task_id"]
        self.assertTrue((self.test_state_dir / "VERSION").exists())
        self.assertTrue((self.test_state_dir / "projects" / explicit_id / "current.json").exists())
        self.assertTrue((self.test_state_dir / "projects" / explicit_id / "events.jsonl").exists())

        # 2. Prepare handoff (atomic save + previous snapshot rotation + event append with fsync)
        h1 = core.prepare_handoff(
            repo_path=mock_repo,
            next_action="Verify NTFS resilience on Windows",
            summary="Hardened phase completed cleanly",
            state_dir=self.test_state_dir,
            project_id=explicit_id,
        )
        self.assertEqual(h1["handoff_sequence"], 2)
        curr_f = self.test_state_dir / "projects" / explicit_id / "current.json"
        prev_f = self.test_state_dir / "projects" / explicit_id / "current.json.previous"
        self.assertTrue(curr_f.exists())
        self.assertTrue(prev_f.exists())

        # 3. Resume task (hardened: no --force)
        r1 = core.resume_task(
            repo_path=mock_repo,
            state_dir=self.test_state_dir,
            project_id=explicit_id,
        )
        self.assertEqual(r1["task"]["status"], "RESUMED")

        # 4. Readback and verify recovery from .previous when current is corrupted
        curr_f.write_text("CORRUPTED_CURRENT_SNAPSHOT", encoding="utf-8")
        recovered, note = core.read_snapshot(self.test_state_dir / "projects" / explicit_id)
        self.assertIsNotNone(recovered)
        self.assertEqual(note, "RECOVERED_FROM_PREVIOUS_SNAPSHOT")
        self.assertEqual(recovered["task"]["status"], "READY_FOR_HANDOFF")

        # 5. Restore previous for completion
        shutil.copy2(prev_f, curr_f)

        # 6. Complete task
        c1 = core.complete_task(
            repo_path=mock_repo,
            result="PASS",
            evidence_summary="Hardened NTFS integration test passed with 0 errors",
            state_dir=self.test_state_dir,
            project_id=explicit_id,
        )
        self.assertEqual(c1["task"]["status"], "PASS")
        archive_f = self.test_state_dir / "projects" / explicit_id / "tasks" / f"{task_id}.json"
        self.assertTrue(archive_f.exists())

        # 7. State integrity validation
        val = core.validate_state_integrity(state_dir=self.test_state_dir)
        self.assertTrue(val["valid"])
        self.assertEqual(val["projects_count"], 1)

        # 8. Verify production directory was never touched
        self.assertFalse(self.prod_state_dir.exists())


if __name__ == "__main__":
    unittest.main()
