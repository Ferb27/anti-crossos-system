import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

package_dir = Path(__file__).resolve().parent.parent
if str(package_dir) not in sys.path:
    sys.path.insert(0, str(package_dir))

import crossos_core as core


class TestGitGuardHardened(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="crossos-test-git-")
        self.state_dir = Path(self.temp_dir) / "state"
        self.repo_dir = Path(self.temp_dir) / "repo"
        self.repo_dir.mkdir(parents=True, exist_ok=True)

        # Initialize real git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/example/git-guard-test.git"], cwd=self.repo_dir, check=True)

        # Initial commit
        readme = self.repo_dir / "README.md"
        readme.write_text("# Initial", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.repo_dir, check=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dirty_worktree_blocks_handoff(self):
        """Verify dirty git status --porcelain blocks prepare_handoff with DirtyWorktreeError."""
        core.begin_task(repo_path=self.repo_dir, title="Task with dirty git", state_dir=self.state_dir)

        # Make worktree dirty
        readme = self.repo_dir / "README.md"
        readme.write_text("# Modified without commit", encoding="utf-8")

        with self.assertRaises(core.DirtyWorktreeError):
            core.prepare_handoff(
                repo_path=self.repo_dir,
                next_action="Continue on Windows",
                state_dir=self.state_dir,
            )

        # Verify state is still IN_PROGRESS
        status = core.get_status(repo_path=self.repo_dir, state_dir=self.state_dir)
        self.assertEqual(status["active_task"]["status"], "IN_PROGRESS")

        # Commit changes to clean worktree
        subprocess.run(["git", "commit", "-am", "commit changes"], cwd=self.repo_dir, check=True)

        # Handoff should now succeed
        res = core.prepare_handoff(
            repo_path=self.repo_dir,
            next_action="Continue on Windows",
            state_dir=self.state_dir,
        )
        self.assertEqual(res["task"]["status"], "READY_FOR_HANDOFF")

    def test_branch_divergence_blocks_resume(self):
        """Verify resume fails if peer repository has different branch (no --force bypass)."""
        core.begin_task(repo_path=self.repo_dir, title="Sync task", state_dir=self.state_dir)
        core.prepare_handoff(repo_path=self.repo_dir, next_action="Resume test", state_dir=self.state_dir)

        # Switch branch to simulate divergence
        subprocess.run(["git", "checkout", "-b", "feature-diverged"], cwd=self.repo_dir, check=True, capture_output=True)

        # Resume should raise GitDivergenceError (hardened: no --force)
        with self.assertRaises(core.GitDivergenceError):
            core.resume_task(repo_path=self.repo_dir, state_dir=self.state_dir)

        # Status must remain READY_FOR_HANDOFF
        status = core.get_status(repo_path=self.repo_dir, state_dir=self.state_dir)
        self.assertEqual(status["active_task"]["status"], "READY_FOR_HANDOFF")

    def test_remote_identity_mismatch_blocks_resume(self):
        """Verify resume fails if peer repository remote seed differs from writer remote seed."""
        t1 = core.begin_task(repo_path=self.repo_dir, title="Remote check task", state_dir=self.state_dir)
        orig_proj_id = t1["project_id"]
        core.prepare_handoff(repo_path=self.repo_dir, next_action="Resume test", state_dir=self.state_dir)

        # Change remote URL to simulate remote mismatch on receiving clone
        subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/another-org/git-guard-test.git"], cwd=self.repo_dir, check=True)

        # Resume with explicit original project_id should raise RemoteIdentityMismatchError
        with self.assertRaises(core.RemoteIdentityMismatchError):
            core.resume_task(repo_path=self.repo_dir, state_dir=self.state_dir, project_id=orig_proj_id)


if __name__ == "__main__":
    unittest.main()
