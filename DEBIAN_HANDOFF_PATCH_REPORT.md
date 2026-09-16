# DEBIAN HANDOFF PATCH REPORT (PHASE 1)
**Date:** 2026-09-16  
**Auditor / Engineer:** Antigravity Agent (Debian Local Worker)  
**Host Platform:** Debian GNU/Linux 13.6 (trixie), Kernel 6.12.105+deb13-amd64  
**Shared Partition:** Windows D: (`Store data`, UUID `3C8CC1178CC0CC98`) mounted at `/media/ferb27/Store data`  
**Report File:** `/home/ferb27/anti-crossos-system/DEBIAN_HANDOFF_PATCH_REPORT.md`  

---

## A. Result
**`PASS`**

Package `Debian_handoff` on Windows D: has been successfully patched and verified against Debian 13 actual system evidence. All runtime hardcoded dependencies (`/mnt/d`, `/dev/nvme0n1p4`, `ntfs-3g`, system `pip`) have been replaced with dynamic mount discovery, isolated `uv` virtual environment management (`~/.gemini/venvs/mcp`), and safe key-wise config merging. The script supports `--dry-run` simulation, which executed with zero state modifications. `~/.gemini/` live configuration and `codex_base` remain 100% untouched.

---

## B. Shared Storage Discovery

* **Partition Discovery:** Automatically discovers filesystem via UUID `3C8CC1178CC0CC98` (`findmnt -rn -S UUID=3C8CC1178CC0CC98`), `/media/*/*/codex_base`, or `CODEX_BASE_DIR` override (`VERIFIED`).
* **Active Verified Mountpoint:** `/media/ferb27/Store data` (`VERIFIED`).
* **Filesystem Driver:** Kernel native `ntfs3` (`VERIFIED`).
* **Mounting Guard:** Script will abort with `SHARED_STORAGE_NOT_MOUNTED` if the partition is not mounted; it does NOT attempt intrusive `mount` or modify `/etc/fstab` (`VERIFIED`).

---

## C. Files Patched in `Debian_handoff/`

| File | Change Summary |
| :--- | :--- |
| **`setup_debian.sh`** | Rewritten to v2.0.0. Added dynamic storage discovery, `--dry-run` flag, PEP 668 compliant `uv venv` preparation, key-wise JSON config merge, idempotent skill/agent sync, and clean verification phases. |
| **`configs/mcp_config.json`** | Replaced `python3` with isolated venv interpreter template `__HOME__/.gemini/venvs/mcp/bin/python`. Preserved 3 target servers (`notebook-lm`, `office-powerpoint`, `kicad`). Excluded `pixel-mcp`. |
| **`mcp/kicad/run_mcp.py`** | Added graceful missing dependency handling: exits with informative stderr if `kicad-cli` or `mcp_server_kicad` is absent, preventing raw unhandled stack traces. |
| **`mcp/notebooklm/run_mcp.py`** | Added graceful missing module handling for `notebooklm_mcp`. |
| **`QUICKSTART.md`** | Removed obsolete instructions (`/mnt/d`, `ntfs-3g`, system `pip`). Documented dynamic discovery, `uv venv` package installation, and `--dry-run` testing. |
| **`README.md`** | Updated architecture documentation to reflect Debian native realities (PEP 668, kernel `ntfs3`, set-based skill preservation, plugin tree protection). |
| **`tencentdb-sync-bridge/TENCENTDB-LINUX-SYNC-GUIDE.md`** | Removed hardcoded mount instructions; documented automatic mount discovery via GNOME/udisks2 and Python bridge client. |

---

## D. Mount Logic Changes

* **Previous Behavior:** Assumed `/mnt/d/codex_base`, suggested `sudo mount -t ntfs-3g /dev/nvme0n1p4 /mnt/d`.
* **Patched Behavior:** Probes `CODEX_BASE_DIR` -> probes active mountpoint for `UUID=3C8CC1178CC0CC98` -> probes `/mnt/*/codex_base` -> probes `/media/*/*/codex_base`.
* **Zero Runtime Dependency:** No requirement for `/mnt/d` directory, symlinks, or fstab modifications.

---

## E. Python / `uv` Changes

* **Previous Behavior:** Encouraged `sudo apt install python3-pip` and `pip install ...` directly into system Python.
* **Problem:** Debian 13 enforces PEP 668 via `/usr/lib/python3.13/EXTERNALLY-MANAGED`, and system pip is absent.
* **Patched Behavior:** Dedicated isolated virtual environment defined at:
  ```text
  ~/.gemini/venvs/mcp/
  ```
  managed via `uv venv ~/.gemini/venvs/mcp`. Packages are installed into this venv via `uv pip install --python ...`.

---

## F. MCP Changes

* **Interpreter Path:** Configured in `mcp_config.json` as:
  ```json
  "command": "__HOME__/.gemini/venvs/mcp/bin/python"
  ```
  The setup script expands `__HOME__` to the user's home directory during deployment without hardcoding usernames.
* **Target Servers:**
  1. `notebook-lm` (`notebooklm_mcp_server` via `run_mcp.py`)
  2. `office-powerpoint` (`python-pptx` / `ppt_mcp_server`)
  3. `kicad` (`mcp-server-kicad` via `run_mcp.py`, requires `kicad-cli`)
* **Pixel MCP:** Completely excluded (`VERIFIED`).

---

## G. Config Merge Strategy

* **Previous Behavior:** Blind overwrite via `cp configs/config.json ~/.gemini/config/config.json`.
* **Patched Behavior:** Key-wise JSON merge in Python:
  - **Preserved Live Debian Settings:** `themeMode`, `customThemeSeedsDark`, `customThemeSeedsLight`, `remoteControlHostname`, `useAiCredits`, `enableTerminalSandbox`, `conversationWidth`.
  - **Applied Handoff Keys:** `autoExecutionPolicy`, `artifactReviewMode`, `nonWorkspaceFileAccessPolicy`.
  - Backs up existing file before write; verifies JSON parse after write.

---

## H. Skill Sync Strategy & Set Comparison

Exact set difference computed between handoff package and live Debian:

```text
HANDOFF_CORE count: 53
LIVE_CORE count:    69
COMMON count:       53
HANDOFF_ONLY (0):   []
LIVE_ONLY (16):     [
  'huashu-design',
  'mobile-app-ui-design',
  'playwright',
  'receiving-code-review',
  'speckit-analyze',
  'speckit-checklist',
  'speckit-clarify',
  'speckit-constitution',
  'speckit-converge',
  'speckit-implement',
  'speckit-plan',
  'speckit-specify',
  'speckit-tasks',
  'speckit-taskstoissues',
  'test-driven-development',
  'verification-before-completion'
]
```

* **Sync Policy:**
  - `COMMON` (53 skills): Synchronized / updated from handoff package.
  - `HANDOFF_ONLY` (0 skills): None.
  - `LIVE_ONLY` (16 skills): **Preserved 100%**. Zero deletions or destructive pruning of non-curated skills.
  - Note on audit discrepancy: `ponytail-audit`, `ponytail-debt`, and `ponytail-gain` were verified present in both `HANDOFF_CORE` and `LIVE_CORE` (`COMMON`).

---

## I. Protected Plugin Trees

* **Path:** `~/.gemini/config/plugins/science/skills` (43 science skills)
* **Policy:** **Strictly Protected**. The setup script treats `plugins/` as outside the core sync scope. Zero files in `plugins/` are copied, moved, or deleted.

---

## J. Scout Deployment Strategy

* **Package Files:** Located in `Debian_handoff/ai-scout-v3/` (`scout_run.py`, `orcarouter_provider.py`, `openrouter_provider.py`, `tokenrouter_provider.py`, `scout_schema.py`).
* **Target Location:** `~/.gemini/antigravity/ai-scout-v3/`.
* **Zero External Dependencies:** Built with Python standard library only (`urllib.request`, `json`, `pathlib`). Compatible with Python 3.13.
* **Contract:** Read-only evidence gathering; never modifies repository or system code.

---

## K. TencentDB Bridge Status

* **Client Script:** `debian_memory_bridge.py` in `Debian_handoff/tencentdb-sync-bridge/`.
* **Discovery Verification:** Uses standard library `find_codex_base()` which automatically discovers `/media/*/*/codex_base` and resolves `/media/ferb27/Store data/codex_base` without requiring `/mnt/d`.
* **Scope:** Bootstrap JSONL file-based shared memory access (`learning.jsonl`). Vector daemon MCP integration deferred to future phase.

---

## L. Static Verification Results

All automated checks passed:
* **Bash Syntax (`bash -n setup_debian.sh`):** `PASS` (0 syntax errors)
* **Dry-Run Test (`./setup_debian.sh --dry-run`):** `PASS` (clean execution, 0 changes applied)
* **JSON Validation (`python3 -m json.tool` on all JSONs):** `PASS` (all JSON files parse validly)
* **Python Syntax (`python3 -m py_compile` on all `.py` files):** `PASS` (0 compilation errors)
* **Storage Independence:** Zero active `/mnt/d` or `/dev/nvme` hardcoded requirements (`PASS`)
* **PIP Independence:** Zero system `pip` / `pip3` install commands in script (`PASS`)
* **MCP Schema:** Verified 3 servers (`notebook-lm`, `office-powerpoint`, `kicad`) pointing to venv (`PASS`)
* **Pixel MCP:** Completely absent (`PASS`)

---

## M. Security Scan

* **Scanned Patterns:** API keys (`sk-*`, `AIza*`), Authorization Bearer tokens, private SSH/RSA keys.
* **Result:** `CLEAN` (0 secrets detected in `Debian_handoff`).

---

## N. Rollback Snapshot

Before any modifications were written, a complete rollback snapshot was captured:
* **Location:** `/media/ferb27/Store data/Debian_handoff_archive/20260916_164325_debian_patch/`
* **Contents:**
  - `manifest.json` (SHA-256 hashes and file metadata)
  - Original `setup_debian.sh`
  - Original `configs/mcp_config.json`
  - Original `mcp/kicad/run_mcp.py`
  - Original `mcp/notebooklm/run_mcp.py`
  - Original `QUICKSTART.md`
  - Original `README.md`
  - Original `tencentdb-sync-bridge/TENCENTDB-LINUX-SYNC-GUIDE.md`

---

## O. Remaining Deployment Actions (Next Steps)

1. **Review by GPT Web Orchestrator:**
   Inspect this report and approve proceeding to Phase 2 (Live Deployment).
2. **Execute Deployment:**
   Run `bash "/media/ferb27/Store data/Debian_handoff/setup_debian.sh"` to materialize configurations into `~/.gemini/`.
3. **MCP Venv Package Installation:**
   Run `uv pip install --python ~/.gemini/venvs/mcp/bin/python python-pptx mcp fastmcp notebooklm-mcp-server` to install runtime packages.
4. **Handshake Verification:**
   Verify `Is Solo-Code Harness active?` in Antigravity chat.

---

# Verification Handshake & Confirmation
* **`~/.gemini` modified:** `NO` (0 configuration changes applied)
* **`codex_base` modified:** `NO` (untouched)
* **`/etc/fstab` modified:** `NO` (untouched)
* **System packages installed:** `NO` (0 packages installed)
* **`setup_debian.sh` executed live:** `NO` (only `--dry-run` was simulated)
* **Pixel MCP included:** `NO`
