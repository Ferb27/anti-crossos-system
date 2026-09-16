# Security & Privacy Policy

## 1. Scope & Repository Boundaries

This repository is strictly intended for version-controlling the **tooling, architecture specifications, test suites, and documentation** of the Anti Cross-OS System.

Under no circumstances should user runtime state, secrets, or raw conversation payloads be committed to this repository.

---

## 2. Hard Security Gates

### Prohibited Artifacts
The following artifacts must never be tracked in Git:
- **Local Application State (`~/.gemini`):** OAuth tokens, live configs, user sessions, credentials.
- **Raw Conversation Payloads:** SQLite databases (`conversations/*.db`), protobuf indices (`*.pb`), brain artifacts, and raw execution transcripts (`transcript.jsonl`).
- **Secrets & Credentials:** API keys, personal access tokens, private keys (`*.pem`, `*.key`, `id_rsa`), service credentials, or environment files (`.env`).
- **External Working Trees:** Directories from shared external disks (`/media/ferb27/...`), `codex_base`, or other project repositories.
- **Local System Backups:** State snapshots under `backups/`.

### Migration Payload Policy
The conversation migration tooling contained in `conversation-migration/` is source code and schema documentation only. All binary payloads, conversation SQLite databases, and user history packages remain exclusively on local shared storage and are explicitly excluded via `.gitignore`.

---

## 3. Reporting Vulnerabilities

If any potential security issue or unintended secret disclosure is detected in this repository, report it immediately to the repository owner and perform an immediate credential rotation.
