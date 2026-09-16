import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

package_dir = Path(__file__).resolve().parent.parent
ctl_script = package_dir / "crossos_ctl.py"


class TestCLIJsonHardened(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="crossos-test-cli-")
        self.state_dir = Path(self.temp_dir) / "state"
        self.repo_dir = Path(self.temp_dir) / "repo"
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        git_config = self.repo_dir / ".git" / "config"
        git_config.parent.mkdir(parents=True, exist_ok=True)
        git_config.write_text(
            '[core]\n\trepositoryformatversion = 0\n[remote "origin"]\n\turl = https://github.com/org/cli-test.git\n',
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _run_cli(self, *args) -> tuple[int, dict, str]:
        cmd = [sys.executable, str(ctl_script), "--repo", str(self.repo_dir), "--state-dir", str(self.state_dir), "--json", *args]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        stdout = proc.stdout.strip()
        data = {}
        if stdout:
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as err:
                self.fail(f"CLI stdout was not valid JSON: '{stdout}', err: {err}")
        return proc.returncode, data, proc.stderr

    def test_cli_json_lifecycle(self):
        # 1. status before any task
        rc, data, _ = self._run_cli("status")
        self.assertEqual(rc, 0)
        self.assertTrue(data.get("ok"))
        self.assertIsNone(data.get("active_task"))

        # 2. begin
        rc, data, _ = self._run_cli("begin", "--title", "CLI Test Task")
        self.assertEqual(rc, 0)
        self.assertTrue(data.get("ok"))
        self.assertEqual(data["task"]["task"]["title"], "CLI Test Task")

        # 3. inspect
        rc, data, _ = self._run_cli("inspect")
        self.assertEqual(rc, 0)
        self.assertTrue(data.get("ok"))
        self.assertIn("current_snapshot", data)

        # 4. handoff
        rc, data, _ = self._run_cli("handoff", "--next", "Resume on Windows")
        self.assertEqual(rc, 0)
        self.assertTrue(data.get("ok"))
        self.assertEqual(data["handoff"]["task"]["status"], "READY_FOR_HANDOFF")

        # 5. resume (hardened: no --force)
        rc, data, _ = self._run_cli("resume")
        self.assertEqual(rc, 0)
        self.assertTrue(data.get("ok"))
        self.assertEqual(data["resumed"]["task"]["status"], "RESUMED")

        # 6. complete
        rc, data, _ = self._run_cli("complete", "--result", "PASS")
        self.assertEqual(rc, 0)
        self.assertTrue(data.get("ok"))
        self.assertEqual(data["task"]["task"]["status"], "PASS")

        # 7. validate
        rc, data, _ = self._run_cli("validate")
        self.assertEqual(rc, 0)
        self.assertTrue(data.get("valid"))

        # 8. events
        rc, data, _ = self._run_cli("events")
        self.assertEqual(rc, 0)
        self.assertTrue(data.get("ok"))
        self.assertGreaterEqual(len(data.get("events", [])), 3)


if __name__ == "__main__":
    unittest.main()
