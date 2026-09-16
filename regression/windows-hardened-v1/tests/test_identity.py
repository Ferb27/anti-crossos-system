import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add crossos package directory to sys.path
package_dir = Path(__file__).resolve().parent.parent
if str(package_dir) not in sys.path:
    sys.path.insert(0, str(package_dir))

import crossos_core as core

# Import debian_memory_bridge for parity check
bridge_path = Path("/home/ferb27/.gemini/antigravity/tencentdb-sync-bridge")
if str(bridge_path) not in sys.path:
    sys.path.insert(0, str(bridge_path))
import debian_memory_bridge


class TestIdentity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="crossos-test-identity-")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_git_repo_with_remote(self, url: str) -> Path:
        repo_dir = Path(self.temp_dir) / f"repo-{abs(hash(url))}"
        repo_dir.mkdir(parents=True, exist_ok=True)
        git_config = repo_dir / ".git" / "config"
        git_config.parent.mkdir(parents=True, exist_ok=True)
        git_config.write_text(
            f'[core]\n\trepositoryformatversion = 0\n[remote "origin"]\n\turl = {url}\n',
            encoding="utf-8",
        )
        return repo_dir

    def test_tencentdb_parity_on_standard_remotes(self):
        """Verify 100% parity with debian_memory_bridge compute_scope_id on git remotes."""
        test_urls = [
            "https://github.com/example/anti-crossos-system.git",
            "https://github.com/example/repo",
            "git@github.com:example/repo.git",
            "ssh://git@github.com/example/repo.git",
            "https://github.com/vinceliuice/WhiteSur-cursors.git",
        ]

        for url in test_urls:
            repo = self._create_git_repo_with_remote(url)
            proj_id, proj_name = core.compute_project_id(repo)
            scope_id, scope_name = debian_memory_bridge.compute_scope_id(repo)

            self.assertEqual(
                proj_id,
                scope_id,
                f"Parity mismatch for url {url}: crossos={proj_id}, tencentdb={scope_id}",
            )
            self.assertEqual(proj_name, scope_name)

    def test_different_repos_produce_different_ids(self):
        repo1 = self._create_git_repo_with_remote("https://github.com/org/repo-a.git")
        repo2 = self._create_git_repo_with_remote("https://github.com/org/repo-b.git")

        id1, _ = core.compute_project_id(repo1)
        id2, _ = core.compute_project_id(repo2)
        self.assertNotEqual(id1, id2)

    def test_non_git_project_requires_explicit_id(self):
        non_git = Path(self.temp_dir) / "empty-dir"
        non_git.mkdir()

        with self.assertRaises(core.ProjectIDRequiredError):
            core.compute_project_id(non_git)

    def test_explicit_project_id_override(self):
        non_git = Path(self.temp_dir) / "custom-app"
        non_git.mkdir()

        custom_id = "0123456789abcdef"
        proj_id, name = core.compute_project_id(non_git, explicit_id=custom_id)
        self.assertEqual(proj_id, custom_id)
        self.assertEqual(name, "custom-app")

    def test_invalid_explicit_project_id_rejected(self):
        non_git = Path(self.temp_dir) / "custom-app"
        non_git.mkdir()

        with self.assertRaises(core.CrossOSError):
            core.compute_project_id(non_git, explicit_id="not-valid-hex!@#$")


if __name__ == "__main__":
    unittest.main()
