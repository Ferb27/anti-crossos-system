# DEBIAN PRE-DEPLOYMENT AUDIT REPORT (READ-ONLY)
**Date:** 2026-09-16  
**Auditor:** Antigravity Agent (Debian Local Worker)  
**Target System:** Lenovo Legion Slim 7 16IRH8 — Dual Boot Windows 11 / Debian GNU/Linux 13 (trixie)  
**Execution Mode:** Strictly Read-Only (0 packages installed, 0 files modified outside workspace, 0 partition changes)  
**Audit File:** `/home/ferb27/anti-crossos-system/DEBIAN_SYSTEM_AUDIT_2026-09-16.md`  

---

## A. Executive Summary

| Category | Finding | Status | Evidence Level |
| :--- | :--- | :--- | :--- |
| **Audit Status** | Read-only scan completed. Zero state modifications. | `PASS` | `VERIFIED` |
| **Overall Classification** | **`HANDOFF_PATCH_REQUIRED`** | `ACTION_REQUIRED` | `VERIFIED` |
| **Debian OS & Kernel** | Debian 13 (trixie) 13.6, Linux kernel `6.12.105+deb13-amd64` | `HEALTHY` | `VERIFIED` |
| **Desktop / Session** | GNOME 47 on Wayland (`gdm3`), display running on dGPU | `ACTIVE` | `VERIFIED` |
| **GPU & Driver** | NVIDIA RTX 4060 Max-Q/Mobile (8GB VRAM), driver `550.163.01` | `FUNCTIONAL` | `VERIFIED` |
| **CUDA Toolkit** | Driver CUDA 12.4 supported; `nvcc` NOT installed | `ABSENT` | `VERIFIED` |
| **Storage / Dual Boot** | 2x NVMe SSDs; Windows NTFS partitions auto-mounted via `udisks2` | `ACCESSIBLE` | `VERIFIED` |
| **Windows D: Partition** | `/dev/nvme0n1p4` (UUID `3C8CC1178CC0CC98`, Label `Store data`) | `LOCATED` | `VERIFIED` |
| **Windows D: Mountpoint** | Auto-mounted at `/media/ferb27/Store data`, NOT `/mnt/d` | `MISMATCH` | `VERIFIED` |
| **Antigravity Status** | Version `1.1.21` running from `~/.local/opt/antigravity` | `ACTIVE` | `VERIFIED` |
| **Existing `.gemini`** | Old handoff from Aug 26, 2026 present (69 skills, 14 agents) | `DIRTY_LEGACY` | `VERIFIED` |
| **Python & Packaging** | Python `3.13.5`, PEP 668 active (`EXTERNALLY-MANAGED`), system pip absent | `PEP_668_BLOCK` | `VERIFIED` |
| **uv Package Manager** | `uv 0.12.6` installed and ready on PATH | `READY` | `VERIFIED` |
| **Handoff Package** | Present on Windows D: (`/media/ferb27/Store data/Debian_handoff`) | `ACCESSIBLE` | `VERIFIED` |
| **TencentDB / RAG Hub** | Present on Windows D: (`/media/ferb27/Store data/codex_base`) | `ACCESSIBLE` | `VERIFIED` |
| **Setup Script Sanity** | `setup_debian.sh` contains hardcoded device `/dev/nvme0n1p4`, invalid `/mnt/d` path, and pip assumptions | `PATCH_NEEDED` | `VERIFIED` |

---

## B. Debian OS / Kernel / Desktop

* **Debian Version:** Debian GNU/Linux 13 (trixie) — `DEBIAN_VERSION_FULL=13.6` (`VERIFIED`: `/etc/os-release`).
* **Kernel:** `Linux gtr 6.12.105+deb13-amd64 #1 SMP PREEMPT_DYNAMIC Debian 6.12.105-1 (2026-08-24) x86_64 GNU/Linux` (`VERIFIED`: `uname -a`).
* **Architecture:** `x86_64` (`VERIFIED`).
* **Hostname:** `gtr` (`VERIFIED`: `hostnamectl`).
* **Hardware Platform:** Lenovo Legion Slim 7 16IRH8, Laptop chassis (`VERIFIED`: `hostnamectl`).
* **BIOS / Firmware:** Version `M0CN35WW` (Date: 2023-12-19) (`VERIFIED`).
* **Boot Mode:** UEFI (`VERIFIED`: `/sys/firmware/efi` exists, `efivarfs` mounted).
* **Desktop Environment:** GNOME Shell (`VERIFIED`: `XDG_CURRENT_DESKTOP=GNOME`).
* **Session Type:** Wayland (`VERIFIED`: `XDG_SESSION_TYPE=wayland`, `gnome-shell` PID 2215, `Xwayland` PID 2490).
* **Display Manager:** GDM3 (`VERIFIED`: `gdm3` PID 1367).

---

## C. Hardware & GPU

### 1. GPU Detection & Driver
* **Device:** NVIDIA Corporation AD107M [GeForce RTX 4060 Max-Q / Mobile] [10de:28e0] (rev a1) (`VERIFIED`: `lspci -nnk`).
* **Subsystem:** Lenovo Device [17aa:3e67] (`VERIFIED`).
* **Display Mode:** Only discrete NVIDIA GPU is exposed on the PCI bus (MUX switch or dGPU mode active; no Intel iGPU detected in `lspci`) (`VERIFIED`).
* **Kernel Driver in use:** `nvidia` proprietary module (`VERIFIED`).
* **Driver Version:** `550.163.01` (`VERIFIED`: `nvidia-smi`).
* **Total VRAM:** 8188 MiB (8 GB GDDR6) (`VERIFIED`: `nvidia-smi`).
* **Current Power / Temp:** 12W idle / 60W cap, 49°C (`VERIFIED`).
* **Active GPU Processes:** GNOME Shell (319 MiB), Antigravity UI & helper processes (254 MiB total), Nautilus (33 MiB), GNOME Control Center (37 MiB) (`VERIFIED`).

### 2. CUDA Capabilities
* **Driver CUDA API Support:** CUDA 12.4 (`VERIFIED`: `nvidia-smi`).
* **CUDA Toolkit / `nvcc`:** NOT INSTALLED (`VERIFIED`: `which nvcc` returned not found).
* *Note:* PyTorch / ONNX / TensorRT runtimes requiring CUDA can execute via bundled CUDA wheel runtimes (e.g. via `uv`), but compilation tools requiring `nvcc` are absent.

### 3. Secure Boot
* **Status:** `SecureBoot disabled` (`VERIFIED`: `mokutil --sb-state`).
* **Impact:** Third-party DKMS / proprietary NVIDIA kernel modules load without MOK key signing requirements.

---

## D. Storage Map

> **CRITICAL VERIFICATION:** Windows Disk 0 / Disk 1 mapping **does NOT** match Linux `/dev/nvme0n1` / `/dev/nvme1n1`.

```
Physical Disk 1: /dev/nvme1n1 (953.9 GB — SK Hynix)
├── nvme1n1p1:   16 MB   [None]    MSR (Microsoft Reserved)
├── nvme1n1p2:  475.3 GB [ntfs]    Windows E: ("App and Study") — UUID: 54A67375A6735688
├── nvme1n1p3:  239.3 GB [ntfs]    Windows Games partition ("Games") — UUID: AC62A0BD62A08DA0
├── nvme1n1p4:  977 MB   [vfat]    Debian EFI System Partition — UUID: AA5A-AA65 (/boot/efi)
├── nvme1n1p5:  226 GB   [ext4]    Debian Root & Home — UUID: 28ece3ee-e5db-4bf5-b643-28c754f92811 (/)
└── nvme1n1p6:   12.3 GB [swap]    Debian Swap — UUID: fbe8357e-006e-48e0-bd31-4a64305d7b06 ([SWAP])

Physical Disk 0: /dev/nvme0n1 (476.9 GB — Micron)
├── nvme0n1p1:  100 MB   [vfat]    Windows EFI System Partition — UUID: 32E3-EF36
├── nvme0n1p2:   16 MB   [None]    MSR (Microsoft Reserved)
├── nvme0n1p3:  330.3 GB [ntfs]    Windows C: System Drive — UUID: 026EE4786EE465BF
└── nvme0n1p4:  146.5 GB [ntfs]    Windows D: ("Store data") — UUID: 3C8CC1178CC0CC98
```

---

## E. Verified Windows Shared Partitions

### 1. Windows D: Candidate (Primary Shared Data)
* **Device:** `/dev/nvme0n1p4` (`VERIFIED`).
* **UUID:** `3C8CC1178CC0CC98` (`VERIFIED`).
* **PARTUUID:** `8cb506e0-abac-4d62-8a63-710e7ccb2b82` (`VERIFIED`).
* **Label:** `Store data` (`VERIFIED`).
* **Filesystem:** `ntfs` (`VERIFIED`).
* **Size:** 146.5 GB (Used: 103 GB, Avail: 45 GB) (`VERIFIED`).
* **Current Active Mountpoint:** `/media/ferb27/Store data` (`VERIFIED`).
* **Mount Driver:** Kernel `ntfs3` (`VERIFIED`).
* **Mount Options:** `rw,nosuid,nodev,relatime,uid=1000,gid=1000,iocharset=utf8` (`VERIFIED`).
* **Target Payloads Confirmed on Partition:**
  - `codex_base` directory present (`VERIFIED`).
  - `Debian_handoff` directory present (`VERIFIED`).
  - `anti-machine-audit` directory present (`VERIFIED`).
* **Confidence:** 100% `VERIFIED`.

### 2. Windows E: Candidate (Apps & Study)
* **Device:** `/dev/nvme1n1p2` (`VERIFIED`).
* **UUID:** `54A67375A6735688` (`VERIFIED`).
* **PARTUUID:** `0aeef1f5-0924-4d8c-8df1-30b5c113da67` (`VERIFIED`).
* **Label:** `App and Study` (`VERIFIED`).
* **Filesystem:** `ntfs` (`VERIFIED`).
* **Size:** 475.3 GB (Used: 329 GB, Avail: 147 GB) (`VERIFIED`).
* **Current Active Mountpoint:** `/media/ferb27/App and Study` (`VERIFIED`).
* **Mount Driver:** Kernel `ntfs3` (`VERIFIED`).
* **Mount Options:** `rw,nosuid,nodev,relatime,uid=1000,gid=1000,iocharset=utf8` (`VERIFIED`).
* **Confidence:** 100% `VERIFIED`.

### 3. Windows C: System Partition
* **Device:** `/dev/nvme0n1p3` (`VERIFIED`).
* **UUID:** `026EE4786EE465BF` (`VERIFIED`).
* **Label:** None (`VERIFIED`).
* **Size:** 330.3 GB (`VERIFIED`).
* **Current Active Mountpoint:** `/media/ferb27/026EE4786EE465BF` (`VERIFIED`).

---

## F. Existing Mounts / `/etc/fstab`

### 1. File `/etc/fstab` Static Configuration
```text
UUID=28ece3ee-e5db-4bf5-b643-28c754f92811 /               ext4    errors=remount-ro 0       1
UUID=AA5A-AA65                             /boot/efi       vfat    umask=0077      0       1
UUID=fbe8357e-006e-48e0-bd31-4a64305d7b06 none            swap    sw              0       0
```
* **Analysis:**
  - Neither Windows D: nor Windows E: is configured in `/etc/fstab` (`VERIFIED`).
  - The mountpoint `/mnt/d` DOES NOT EXIST in `/etc/fstab` or on disk (`/mnt` is empty) (`VERIFIED`).

### 2. Dynamic Mount State
* Partitions are mounted via GNOME/udisks2 at login under `/media/ferb27/...` using native kernel `ntfs3` with `uid=1000,gid=1000,rw` (`VERIFIED`).
* No hibernated or dirty filesystem state was encountered; drives mounted read-write without read-only fallback (`VERIFIED`).
* **Deployment Consequence:** Any command or script expecting `/mnt/d/...` (e.g. `python3 /mnt/d/Debian_handoff/...` or `python3 /mnt/d/codex_base/...`) will fail unless:
  1. An `/etc/fstab` entry is added with UUID `3C8CC1178CC0CC98` pointing to `/mnt/d`, OR
  2. A symlink `/mnt/d -> /media/ferb27/Store data` is created, OR
  3. Scripts use `/media/ferb27/Store data` or `CODEX_BASE_DIR` environment variable.

---

## G. Antigravity Installation

* **Binary Locations:**
  - `/home/ferb27/.local/bin/agy` (`VERIFIED`).
  - `/home/ferb27/.local/bin/antigravity` (`VERIFIED`).
* **Install Directory:** `/home/ferb27/.local/opt/antigravity/` (User-level install) (`VERIFIED`).
* **CLI Version (`agy --version`):** `1.1.21` (`VERIFIED`).
* **Language Server IDE Version:** `2.10.0` (`VERIFIED`: language server process arg `--override_ide_version 2.10.0`).
* **Process Status:** Active and running (`antigravity` GUI, language server, network service, audio service) (`VERIFIED`).
* **User Data Directory:** `/home/ferb27/.config/Antigravity` (`VERIFIED`).
* **State Directory:** `/home/ferb27/.gemini/antigravity` (`VERIFIED`).

---

## H. Existing `.gemini` State

* **Directory Structure in `~/.gemini/`:**
  - `~/.gemini/antigravity` (Active brain, logs, conversations, state) (`VERIFIED`).
  - `~/.gemini/antigravity-backup` (Created Aug 26) (`VERIFIED`).
  - `~/.gemini/antigravity-cli` (Created Aug 26) (`VERIFIED`).
  - `~/.gemini/antigravity-ide` (Created Aug 26) (`VERIFIED`).
  - `~/.gemini/config` (Active configuration root) (`VERIFIED`).
* **Symlink Check:**
  - `/home/ferb27/.gemini/antigravity/mcp_config.json -> /home/ferb27/.gemini/config/mcp_config.json` (`VERIFIED`).
* **Current Config Files:**
  - `~/.gemini/config/mcp_config.json`: 0 bytes (empty file) (`VERIFIED`).
  - `~/.gemini/config/config.json`: Contains live user settings (`enableTerminalSandbox: false`, `autoExecutionPolicy: CASCADE_COMMANDS_AUTO_EXECUTION_EAGER`, `themeMode: THEME_MODE_DARK`, `remoteControlHostname: kien-golden-aurora`, `useAiCredits: true`) (`VERIFIED`).
  - `~/.gemini/config/AGENTS.md`: Exists (timestamped Aug 26 18:51) (`VERIFIED`).

---

## I. Skills / Agents / Scout

### 1. Skills
* **Current Count on Debian:** 69 skills in `~/.gemini/config/skills` + 43 science skills in `~/.gemini/config/plugins/science/skills` (`VERIFIED`).
* **Count in Handoff Package:** 53 curated core engineering skills in `Debian_handoff/skills` (`VERIFIED`).
* **Delta Analysis:** The existing Debian directory contains 16 legacy or supplementary skill directories not present in the 53-skill handoff package (e.g. `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `speckit-*`).
* **Action Required:** Deployment must decide whether to cleanly synchronize or preserve non-conflicting skills.

### 2. Subagents
* **Current Count on Debian:** 14 subagent definitions in `~/.gemini/config/agents/` (`architect.md`, `code-reviewer.md`, `code-simplifier.md`, `code-skeptic.md`, `database-reviewer.md`, `planner.md`, `python-reviewer.md`, `refactor-cleaner.md`, `security-auditor.md`, `solo-code-engineer.md`, `tdd-guide.md`, `test-engineer.md`, `typescript-reviewer.md`, `web-performance-auditor.md`) (`VERIFIED`).
* **Count in Handoff Package:** Exactly the same 14 subagents (`VERIFIED`).

### 3. Orchestrators & Instructions
* `~/.gemini/config/orchestrators/`: 3 files (`full-stack-feature.md`, `security-audit.md`, `spec-driven-implement.md`) (`VERIFIED`).
* `~/.gemini/config/instruction/`: 6 files (`custom-framework-rules.md`, `rules-database.md`, `rules-git.md`, `rules-python.md`, `rules-typescript.md`, `security-patterns.md`) (`VERIFIED`).

### 4. Workflow Check (`GPT Web → Codex → Anti`)
* **Stale Workflow Status:** `NOT PRESENT`. Grep across `~/.gemini/config` confirmed zero occurrences of obsolete `GPT Web → Codex → Anti` routing (`VERIFIED`). Current rules adhere to `User → GPT Web → Anti → Subagents/Scout`.

### 5. Scout V3
* **Debian Local State:** Scout V3 (`scout_run.py`) is NOT deployed to `/home/ferb27` or system paths (`VERIFIED`).
* **Handoff Package State:** Located in `/media/ferb27/Store data/Debian_handoff/ai-scout-v3` (`VERIFIED`).
* **Dependencies:** Uses Python standard library only (`urllib.request`, `json`, `pathlib`) (`VERIFIED`). Requires no external pip wheels. Fully compatible with Python 3.13.

---

## J. Development Toolchain

| Binary | Path | Version | Status |
| :--- | :--- | :--- | :--- |
| `git` | `/home/ferb27/.local/bin/git` | `2.47.3` | `INSTALLED` |
| `git-lfs` | Not found | None | `MISSING` |
| `gh` | Not found | None | `MISSING` |
| `ssh` | `/usr/bin/ssh` | OpenSSH 10.0p2 | `INSTALLED` |
| `curl` | `/usr/bin/curl` | 8.14.1 | `INSTALLED` |
| `node` | `/home/ferb27/.local/bin/node` | `v22.14.0` | `INSTALLED` |
| `npm` | `/home/ferb27/.local/bin/npm` | `10.9.2` | `INSTALLED` |
| `pnpm` | Not found | None | `MISSING` |
| `gcc` | `/usr/bin/gcc` | 14.2.0 | `INSTALLED` |
| `g++` | `/usr/bin/g++` | 14.2.0 | `INSTALLED` |
| `make` | `/usr/bin/make` | 4.4.1 | `INSTALLED` |
| `cmake` | Not found | None | `MISSING` |
| `ninja` | Not found | None | `MISSING` |
| `docker` | Not found | None | `MISSING` |

---

## K. Git

* **Global Config:** `/home/ferb27/.gitconfig` DOES NOT EXIST (`VERIFIED`).
* **System Config:** No system git config defined (`VERIFIED`).
* **Effective Settings:**
  - `core.autocrlf`: Default `false` (native Linux LF line endings) (`VERIFIED`).
  - `core.filemode`: Default `true` (executable bits tracked) (`VERIFIED`).
  - `core.symlinks`: Default `true` (`VERIFIED`).
  - `init.defaultBranch`: Default (`master` unless configured) (`VERIFIED`).
  - `credential.helper`: Not configured (`VERIFIED`).
* **GitHub CLI (`gh`):** Not installed (`VERIFIED`).

---

## L. Python Packaging / PEP 668

* **System Python:** `3.13.5` at `/usr/bin/python3` (`VERIFIED`).
* **PEP 668 State:** ACTIVE. `/usr/lib/python3.13/EXTERNALLY-MANAGED` is present (`VERIFIED`).
* **System `pip`:** NOT INSTALLED (`/usr/bin/python3: No module named pip`) (`VERIFIED`).
* **`pipx`:** NOT INSTALLED (`VERIFIED`).
* **`python3 -m venv`:** Standard library module functional (`VERIFIED`).
* **`uv`:** `uv 0.12.6` (x86_64-unknown-linux-gnu) INSTALLED at `/home/ferb27/.local/bin/uv` (`VERIFIED`).
* **System Dist-Packages:** Pre-installed system packages in `/usr/lib/python3/dist-packages` include `httpx (0.28.1)`, `pydantic (2.10.6)`, `rich (13.9.4)`, `requests (2.32.3)`, `cryptography (43.0.0)`, `numpy (2.2.4)`, `anyio (4.8.0)` (`VERIFIED`).
* **Packaging Strategy for Deployment:**
  - MUST NOT execute `sudo apt install python3-pip && pip install ...` into system Python.
  - Recommended: Utilize `uv` to manage dedicated virtual environments (e.g. `uv venv ~/.gemini/venvs/mcp` and `uv pip install ...`) or `uv tool` for isolated CLI utilities.

---

## M. Big Data Environment

| Tool / Framework | Installed | Path / Version | Notes |
| :--- | :--- | :--- | :--- |
| **Java (JRE / JDK)** | `NO` | None | `java` and `javac` commands not found |
| **Scala** | `NO` | None | Scala compiler / repl absent |
| **Apache Hadoop** | `NO` | None | `hadoop` CLI absent |
| **Apache Spark** | `NO` | None | `spark-submit` absent |
| **Apache Kafka** | `NO` | None | `kafka-server-start.sh` absent |
| **Docker / Compose** | `NO` | None | Docker engine absent |
| **Jupyter** | `NO` | None | `jupyter` absent from system site-packages |
| **PySpark** | `NO` | None | `import pyspark` failed |
| **Pandas** | `NO` | None | `import pandas` failed |
| **NumPy** | `YES` | `2.2.4` | System dist-package available |

---

## N. MCP Readiness

* **NotebookLM MCP:**
  - Python module `notebooklm`: NOT INSTALLED (`VERIFIED`).
  - Runner script: Located in handoff at `mcp/notebooklm/run_mcp.py` (`VERIFIED`).
* **Office PowerPoint MCP:**
  - Python module `python-pptx` / `ppt_mcp_server`: NOT INSTALLED (`VERIFIED`).
  - Handoff configuration specifies `python3 -m ppt_mcp_server` (`VERIFIED`).
* **KiCad MCP:**
  - `kicad-cli`: NOT INSTALLED (`VERIFIED`).
  - Runner script: Located in handoff at `mcp/kicad/run_mcp.py` (`VERIFIED`).
* **Pixel MCP:**
  - Skipped completely as instructed. Absent from both handoff and target configs (`VERIFIED`).
* **MCP Readiness Conclusion:** All 3 target MCP servers require dependencies to be installed into a virtual environment or system before they can run.

---

## O. TencentDB / RAG Accessibility

* **Disk Partition:** Windows D: (`/dev/nvme0n1p4`, UUID `3C8CC1178CC0CC98`) (`VERIFIED`).
* **Current Access Path:** `/media/ferb27/Store data/codex_base` (`VERIFIED`).
* **Internal Structure:**
  - `bridges/codex-memory` present (`VERIFIED`).
  - `bridges/codex-memory/bridge.py` present (43.7 KB) (`VERIFIED`).
  - `tencentdb-memory/data/projects` contains 22 active project stores (`VERIFIED`).
* **Bridge Client Compatibility:**
  - `debian_memory_bridge.py` uses standard library only (`VERIFIED`).
  - `find_codex_base()` automatically probes `/media/*/*/codex_base` (`VERIFIED`).
  - Successfully resolves `/media/ferb27/Store data/codex_base` without requiring `/mnt/d` (`VERIFIED`).
* **Security & Write Discipline:** No database records or learning entries were modified during this audit (`VERIFIED`).

---

## P. Handoff Package Accessibility

* **Physical Location:** `/media/ferb27/Store data/Debian_handoff` (`VERIFIED`).
* **Contents Inventory:**
  - `53` skills in `skills/` (`VERIFIED`).
  - `14` subagents in `configs/agents/` (`VERIFIED`).
  - `3` MCP configurations in `configs/mcp_config.json` (`notebook-lm`, `office-powerpoint`, `kicad`) (`VERIFIED`).
  - `Scout V3` in `ai-scout-v3/` (`VERIFIED`).
  - `debian_memory_bridge.py` in `tencentdb-sync-bridge/` (`VERIFIED`).
  - `setup_debian.sh` (174 lines) (`VERIFIED`).
* **Access Status:** Completely readable without mounting any new partitions (`VERIFIED`).

---

## Q. Setup Script Assumption Check

Audit of `/media/ferb27/Store data/Debian_handoff/setup_debian.sh`:

| Assumption in Script | Debian Reality | Status | Details |
| :--- | :--- | :--- | :--- |
| **Mount device `/dev/nvme0n1p4`** | While currently `/dev/nvme0n1p4`, device names are non-deterministic in Linux | `SCRIPT_ASSUMPTION_INVALID` | Must use `UUID=3C8CC1178CC0CC98` rather than `/dev/nvme0n1p4` |
| **Mount driver `ntfs-3g`** | Native kernel `ntfs3` driver is loaded and active | `SCRIPT_ASSUMPTION_INVALID` | `ntfs-3g` is not installed; Debian 13 uses in-kernel `ntfs3` |
| **Mountpoint `/mnt/d`** | Disk is auto-mounted at `/media/ferb27/Store data` | `SCRIPT_ASSUMPTION_INVALID` | Script checks `/mnt/d/codex_base` which does not exist unless created |
| **Pip install via `python3-pip`** | PEP 668 is active; system pip is missing | `SCRIPT_ASSUMPTION_INVALID` | `pip install` on system Python fails; must use `uv venv` or venv |
| **MCP execution via `python3`** | `mcp_config.json` calls `python3` directly | `SCRIPT_ASSUMPTION_INVALID` | Target packages are not in system Python; runner needs venv python path |
| **Config overwrite (`config.json`)** | Active `config.json` has custom UI/theme/sandbox settings | `SCRIPT_ASSUMPTION_INVALID` | Blind overwrite wipes `enableTerminalSandbox: false` and theme seeds |
| **Python 3 / Git availability** | Python 3.13.5 and Git 2.47.3 are present | `SCRIPT_ASSUMPTION_VALID` | Dependency checks pass |
| **Directory paths (`~/.gemini`)** | Matches active Antigravity paths | `SCRIPT_ASSUMPTION_VALID` | Directory structure is standard |

---

## R. Network / SSH

* **Network Interfaces:**
  - `lo`: 127.0.0.1 (`VERIFIED`).
  - `wlp0s20f3`: Wi-Fi interface connected, IPv4 `192.168.1.36/24` (`VERIFIED`).
* **Default Route:** `192.168.1.1 dev wlp0s20f3` (`VERIFIED`).
* **DNS Resolver:** `192.168.1.1` via NetworkManager (`VERIFIED`).
* **SSH Server:** OpenSSH Server (`ssh.service`) is **ACTIVE** and **ENABLED** (`VERIFIED`).
* **Firewall:** `ufw` not installed; standard open outbound, port 22 reachable on local subnet (`VERIFIED`).
* **Remote Worker Feasibility:** Debian can readily serve as a remote SSH worker node from Windows or local LAN (`VERIFIED`).

---

## S. Delta: Handoff Expectations vs Debian Reality

| Area | Handoff Expects | Debian Actual | Delta Severity | Deployment Impact |
| :--- | :--- | :--- | :--- | :--- |
| **Mountpoint** | `/mnt/d` | `/media/ferb27/Store data` | `MEDIUM` | Requires either `/etc/fstab` entry, symlink `/mnt/d`, or updating path references |
| **Mount Method** | `mount -t ntfs-3g /dev/nvme0n1p4` | In-kernel `ntfs3` auto-mounted via udisks2 | `MEDIUM` | Do not install ntfs-3g or hardcode nvme device names |
| **Python Packages** | `pip install` into system | PEP 668 active, pip absent, `uv 0.12.6` present | `HIGH` | Must use `uv venv` to isolate MCP packages |
| **Skills Directory** | 53 curated skills | 69 legacy skills in `~/.gemini/config/skills` | `LOW` | Needs cleanup or selective overwrite to prevent orphan skills |
| **MCP Config** | Calls `/usr/bin/python3` | Dependencies missing in system Python | `HIGH` | `mcp_config.json` command paths must point to venv Python |
| **User Settings** | Overwrite `config.json` | Active `config.json` has live user preferences | `MEDIUM` | Must merge rather than overwrite `config.json` |
| **GPU / CUDA** | NVIDIA RTX 4060 | RTX 4060 active, driver 550.163.01, no nvcc | `INFO` | GPU functional; runtime libraries installable via wheel/uv |

---

## T. Risks

1. **[BLOCKING - SCRIPT] Running unpatched `setup_debian.sh`:**
   Will fail at mount verification, attempt invalid device mounting, and fail on pip installation due to PEP 668.
2. **[HIGH] MCP Service Failure:**
   If `mcp_config.json` is deployed pointing to `python3`, Antigravity will fail to launch MCP servers because `notebooklm` and `pptx` packages are not in system Python.
3. **[MEDIUM] Config Wipe:**
   Directly copying `configs/config.json` will overwrite user-configured theme colors, remote hostnames, and sandbox policies.
4. **[LOW] Path Inconsistencies for Prompts:**
   Prompts referencing `/mnt/d/...` will not resolve until `/mnt/d` is symlinked or mounted in fstab.

---

## U. Deployment Preconditions

Before `setup_debian.sh` can be executed, the following steps must be staged:
1. **Fix Mount Access:**
   Create `/mnt/d` directory and symlink it to `/media/ferb27/Store data` (`ln -s "/media/ferb27/Store data" /mnt/d`), OR add a persistent UUID entry in `/etc/fstab`.
2. **Patch Setup Script for PEP 668:**
   Update `setup_debian.sh` to use `uv venv ~/.gemini/venvs/mcp` and install dependencies inside that venv instead of calling system pip.
3. **Update `mcp_config.json`:**
   Set python executable path to `$HOME/.gemini/venvs/mcp/bin/python3`.
4. **Preserve `config.json`:**
   Merge handoff settings with existing `~/.gemini/config/config.json` instead of executing a raw `cp`.

---

## V. Recommended Next Step

1. **Report Status to GPT Web:**
   Present this audit report to GPT Web for orchestration approval.
2. **Author `setup_debian_v2.sh` (or patch existing):**
   Incorporate UUID-based mounting, `uv`-based virtual environments, and safe config merging.
3. **Deploy with Zero System Disruption:**
   Execute the patched script only after GPT Web and User grant explicit permission.

---

# Verification Handshake & Confirmation
* **Packages installed:** `NO` (0 packages installed)
* **Partitions mounted/unmounted:** `NO` (0 partition changes)
* **`/etc/fstab` modified:** `NO` (untouched)
* **`~/.gemini` modified:** `NO` (untouched)
* **TencentDB / RAG modified:** `NO` (untouched)
* **Handoff package modified:** `NO` (untouched)
* **System configuration modified:** `NO` (untouched)
* **`setup_debian.sh` executed:** `NO`
