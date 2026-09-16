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


class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="crossos-test-sec-")
        self.state_dir = Path(self.temp_dir) / "state"
        self.repo_dir = Path(self.temp_dir) / "repo"
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        git_config = self.repo_dir / ".git" / "config"
        git_config.parent.mkdir(parents=True, exist_ok=True)
        git_config.write_text(
            '[core]\n\trepositoryformatversion = 0\n[remote "origin"]\n\turl = https://github.com/org/sec-test.git\n',
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_redact_bearer_tokens(self):
        text = "Authorization: Bearer secret_bearer_token_value_here"
        redacted = core.redact(text)
        self.assertNotIn("secret_bearer_token_value_here", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_redact_github_and_openai_tokens(self):
        text = "tokens: ghp_1234567890abcdef1234567890abcdef and sk-1234567890abcdef1234567890"
        redacted = core.redact(text)
        self.assertNotIn("ghp_1234567890abcdef1234567890abcdef", redacted)
        self.assertNotIn("sk-1234567890abcdef1234567890", redacted)

    def test_redact_private_key(self):
        pk = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----"
        redacted = core.redact(pk)
        self.assertNotIn("MIIEowIBAAKCAQEA0", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_redact_env_assignments(self):
        env_line = "AWS_SECRET_ACCESS_KEY=SuperSecretAwsKey123"
        redacted = core.redact(env_line)
        self.assertNotIn("SuperSecretAwsKey123", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_safe_git_sha_not_redacted(self):
        sha = "a1b2c3d4e5f678901234567890abcdef12345678"
        redacted = core.redact(sha)
        self.assertEqual(sha, redacted)

    def test_serialization_sanitization(self):
        """Verify secrets passed to handoff arguments are sanitized in current.json on disk."""
        core.begin_task(repo_path=self.repo_dir, title="Secure task", state_dir=self.state_dir)
        core.prepare_handoff(
            repo_path=self.repo_dir,
            next_action="Deploy with API_KEY: secret_key_12345",
            summary="Tested with Bearer my_super_secret_token",
            evidence_summary="Database password=SuperPassword999",
            state_dir=self.state_dir,
        )

        proj_id, _ = core.compute_project_id(self.repo_path if hasattr(self, 'repo_path') else self.repo_dir)
        current_file = self.state_dir / "projects" / proj_id / "current.json"
        content = current_file.read_text(encoding="utf-8")

        self.assertNotIn("secret_key_12345", content)
        self.assertNotIn("my_super_secret_token", content)
        self.assertNotIn("SuperPassword999", content)


if __name__ == "__main__":
    unittest.main()
