# Anti Cross-OS System

Portable asynchronous task continuity and development substrate across Windows 11 and Debian 13 dual-boot environments for Antigravity AI agents.

---

## 1. Overview & Purpose

The **Anti Cross-OS System** solves the task continuity problem on a dual-boot development workstation where Windows and Linux never execute concurrently. It establishes an asynchronous control plane and verification framework so AI agent tasks can transition smoothly between operating systems.

### Core Capabilities
- **Cross-OS Task Handoff (V1):** Asynchronous state handoff across dual-boot reboots using shared NTFS filesystem primitives.
- **Deterministic Project Identity:** Computes consistent project hashes (`project_id`) derived from Git remote URL seeds, ensuring 100% parity across Windows, Linux, CrossOS state, and TencentDB memory hub.
- **Clean Separation of Concerns:**
  - `Source of Truth`: Native repository code, Git working tree, and fresh command outputs.
  - `Task Continuity`: Structured cross-OS handoff metadata stored on shared storage.
  - `Durable Knowledge`: TencentDB / RAG shared memory hub.
- **Validation & Tooling:** Portable Python stdlib CLI, comprehensive test suites, and regression harnesses for NTFS integration.
- **Conversation Migration Research (Experimental):** Specialized tooling for migrating and indexing Antigravity Desktop conversation histories across OS installations. *(Note: Conversation migration is experimental research and not required for core CrossOS V1 handoffs).*

---

## 2. Multi-Agent Operating Model

```text
User
  ↓
GPT Web
  = Primary Orchestrator / Brainstorm / Decision Layer
  ↓
Anti (Local Antigravity on currently booted OS)
  = General Local Worker (Debian 13 or Windows 11)
  ↓
Anti Coordinates:
  ├─ Scout V3 (Read-only symbol and file locator)
  ├─ Specialist Subagents (Domain analysis)
  └─ Executor (Controlled code modification)
  ↓
Fresh Verification (Automated test / command execution)
  ↓
Cross-OS Handoff State (Saved to shared storage)
  ↓
Reboot to alternate OS
  ↓
Anti resumes seamlessly on target OS
```

---

## 3. Repository Structure

- `crossos-v1/`: Core CrossOS toolkit (`crossos_core.py`, `crossos_ctl.py`) and unit test suite.
- `regression/`: Isolated validation suites for hardened CrossOS releases and driver regression checks.
- `conversation-migration/`: Offline helpers (`apply_dish_cleaner_sandbox.py`, `verify_dish_cleaner_sandbox.py`, `MIGRATION_PLAN.json`) for Antigravity Desktop 2.10 index management.
- `*.md`: Comprehensive architecture specifications, forensic reports, and validation audits:
  - `CROSS_OS_HANDOFF_DESIGN.md`: Formal control plane specification.
  - `CROSS_OS_V1_IMPLEMENTATION_REPORT.md`: V1 implementation evidence and integration tests.
  - `DEBIAN_SYSTEM_AUDIT_2026-09-16.md`: Initial Debian 13 pre-deployment system audit.
  - `DEBIAN_LIVE_DEPLOYMENT_REPORT.md`: Antigravity environment deployment report.
  - `DEBIAN_POST_RESTART_VERIFICATION.md`: Runtime verification of skills, agents, and MCP servers.
  - `DEBIAN_SANDBOX_MIGRATION_PREP_REPORT.md`: Forensic audit of conversation sandbox packages.
  - `DEBIAN_DESKTOP_INDEX_RESOLUTION_REPORT.md`: Architecture resolution of Desktop protobuf index.

---

## 4. Security & Safety

See [SECURITY.md](SECURITY.md) for data governance, credential safety, and local isolation boundaries.
