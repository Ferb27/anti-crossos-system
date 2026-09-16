# ANTIGRAVITY DEBIAN VERSION & INSTALLATION AUDIT REPORT
**Phase:** Phase 0 — Antigravity Version / Installation Normalization  
**Date:** 2026-09-16  
**Auditor:** Antigravity Agent (Debian Local Worker)  
**Host Platform:** Debian GNU/Linux 13.6 (trixie), x86_64, Kernel 6.12.105+deb13-amd64  
**Audit File:** `/home/ferb27/anti-crossos-system/ANTIGRAVITY_DEBIAN_VERSION_AUDIT.md`  

---

## A. Result
**`READY_FOR_HANDOFF_PATCH`**

Antigravity installation origin has been identified without ambiguity. No conflicting duplicate installations exist. Antigravity CLI (`agy`) was updated via its official built-in updater (`agy update`) from `1.1.21` to `1.2.4`. The desktop app and language server remain stable at version `2.10.0`. All configuration schemas required for the handoff (`config.json`, `mcp_config.json`, `AGENTS.md`, subagents, skills) are verified fully supported. Zero state loss or configuration corruption occurred.

---

## B. Before Versions

* **Desktop Application (`antigravity`):** `2.10.0` (`VERIFIED`: `package.json` inside `/home/ferb27/.local/opt/antigravity/resources/app.asar`)
* **CLI (`agy`):** `1.1.21` (`VERIFIED`: `agy --version`)
* **IDE / Backend / Language Server:** `2.10.0` (`VERIFIED`: language server process argument `--override_ide_version 2.10.0` from `/home/ferb27/.local/opt/antigravity/resources/bin/language_server`)

---

## C. Installation Origin

* **Active Binaries:**
  - CLI: `/home/ferb27/.local/bin/agy` (ELF 64-bit LSB executable, 217 MB) (`VERIFIED`)
  - Desktop: `/home/ferb27/.local/bin/antigravity` -> symlink to `/home/ferb27/.local/opt/antigravity/antigravity` (`VERIFIED`)
  - Language Server: `/home/ferb27/.local/opt/antigravity/resources/bin/language_server` (`VERIFIED`)
* **Installation Channel:**
  - User-level standalone directory installation at `/home/ferb27/.local/opt/antigravity/` (`VERIFIED`).
  - Desktop entry registered at `~/.local/share/applications/antigravity.desktop` (`VERIFIED`).
  - **Not** installed via APT/dpkg (`dpkg -S` confirmed no Debian package ownership) (`VERIFIED`).
  - **Not** running from AppImage (`electron-updater` logs confirm: `APPIMAGE env is not defined, current application is not an AppImage`) (`VERIFIED`).
* **Update Mechanisms Defined in Binary/Assets:**
  - CLI: Built-in `agy update` subcommand (`VERIFIED`).
  - Desktop: Configured in `app-update.yml` with provider `generic`, URL `https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/manifest/` (`VERIFIED`).

---

## D. Official Current Versions

Official source: `https://antigravity.google/changelog` and internal `agy changelog`:

* **Antigravity CLI:**
  - Current Latest Tag: `1.2.4` (`VERIFIED`: official changelog and `agy changelog`).
  - Notable fixes in 1.2.4: MCP tool schema augmentation fix, `/skills reload` subcommand, custom subagents MCP inheritance fix (`enable_mcp_tools: true`), and log output resilience.
* **Antigravity 2.0 Desktop:**
  - Current Latest Tag: `2.14.0` (`VERIFIED`: official changelog at `https://antigravity.google/changelog`).
  - Rollout note: "New versions are rolled out gradually and may take a few days to reach all users." (`VERIFIED`).
  - Baseline on current machine: `2.10.0` (active and functional).

---

## E. Update Action Performed

### 1. Antigravity CLI (`agy`)
* **Action:** Executed official update command: `agy update`.
* **Execution Evidence:**
  ```text
  ⟳ Checking for updates... (current version 1.1.21)
  ✓ Found new version 1.2.4.
  ⟳ Downloading update...
  ⟳ Extracting files...
  ✓ Verification successful.
  ⟳ Installing update...
  ✓ Update successful! Please restart agy.
  ```
* **Privilege Used:** User-level only (`ferb27`), zero `sudo` required (`VERIFIED`).

### 2. Antigravity Desktop App (`antigravity`) & Language Server
* **Action:** **`NO UPDATE PERFORMED`**
* **Rationale:**
  - The desktop application is actively hosting the live agent session (GDM Wayland session, process PID 3198 / 3311). Terminating or forcefully replacing unpacked Electron application directories in-place while running risks crashing the active pair-programming environment.
  - The desktop auto-updater relies on AppImage runtime packaging on Linux, whereas this machine uses an unpacked user-level directory installation.
  - Version `2.10.0` is completely stable and fully compatible with all required schemas (skills, subagents, MCP, and configuration flags).

---

## F. After Versions

* **Desktop Application (`antigravity`):** `2.10.0` (`VERIFIED`)
* **CLI (`agy`):** `1.2.4` (`VERIFIED`: `agy --version` output)
* **IDE / Backend / Language Server:** `2.10.0` (`VERIFIED`)

---

## G. Duplicate Installation Check

| Path Scanned | Result | Details |
| :--- | :--- | :--- |
| `/home/ferb27/.local/bin/` | `CLEAN` | Contains active `agy` and symlink `antigravity` |
| `/usr/bin/` | `CLEAN` | Zero antigravity / agy binaries |
| `/usr/local/bin/` | `CLEAN` | Empty directory |
| `/opt/` | `CLEAN` | Contains only unrelated `brave.com` directory |
| `dpkg -l` | `CLEAN` | No dpkg package named antigravity |
| Desktop Entries | `CLEAN` | Only single entry at `~/.local/share/applications/antigravity.desktop` |

* **Conclusion:** `DUPLICATE_INSTALL: NO`. Only one single, unambiguous installation exists on Debian (`VERIFIED`).

---

## H. State Preservation Check

* **`~/.gemini/config/`:** Completely untouched (`VERIFIED`: directory timestamp preserved, all files intact).
* **`~/.gemini/antigravity/`:** Completely untouched outside standard runtime session conversation logs (`VERIFIED`).
* **Authentication:** Intact (`VERIFIED`: `agy models` authenticated against Google backend without credential re-prompt).
* **Workspace:** Open and active (`/home/ferb27/anti-crossos-system`) (`VERIFIED`).

---

## I. Config Compatibility

| Feature / Config Field | Supported | Evidence |
| :--- | :--- | :--- |
| **`artifactReviewMode`** | `SUPPORTED` | Documented in `antigravity-guide` (`app.md`) and accepted by settings schema. |
| **`autoExecutionPolicy`** | `SUPPORTED` | Currently active in `~/.gemini/config/config.json` (`CASCADE_COMMANDS_AUTO_EXECUTION_EAGER`). |
| **`enableTerminalSandbox`** | `SUPPORTED` | Active in `config.json` (`false`), documented in `app.md` and CLI flags (`--sandbox`). |
| **`nonWorkspaceFileAccessPolicy`** | `SUPPORTED` | Active in `config.json` (`AGENT_SETTING_POLICY_ALLOW`), documented in `app.md`. |
| **`mcp_config.json` Schema** | `SUPPORTED` | Standard schema confirmed via `agy mcp add --help` (`mcpServers.<name>.command/args/env/type`). |
| **`AGENTS.md`** | `SUPPORTED` | Automatically loaded at session boot by Solo-Code Harness. |
| **Custom Agents (`~/.gemini/config/agents/`)** | `SUPPORTED` | 14 subagent markdown definitions recognized and available for invocation. |
| **Skills (`~/.gemini/config/skills/`)** | `SUPPORTED` | Fully recognized and parsed by Antigravity engine; reloadable via `/skills reload`. |

---

## J. Remaining Risks

1. **[LOW] In-Memory CLI Session:**
   `agy update` replaced the binary on disk (`/home/ferb27/.local/bin/agy`). Any existing terminal session running `agy` will pick up the new 1.2.4 binary on next command or subshell invocation.
2. **[NONE - RESOLVED] Version Ambiguity:**
   The relationship between Desktop (2.10.0), Language Server (2.10.0), and CLI (1.2.4) is now fully mapped and verified.

---

# Verification Handshake & Confirmation
* **Packages installed via apt/system:** `NO` (0 system packages modified)
* **Partitions mounted/unmounted:** `NO` (0 partition changes)
* **`/etc/fstab` modified:** `NO` (untouched)
* **`~/.gemini` modified by us:** `NO` (configuration preserved)
* **`Debian_handoff` modified:** `NO` (read-only)
* **TencentDB / RAG modified:** `NO` (untouched)
* **System configuration modified:** `NO` (untouched)
* **`setup_debian.sh` executed:** `NO`
