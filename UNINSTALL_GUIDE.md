# OmniAgent OS: Complete Uninstallation & Zero-Pollution Guide

This document provides a complete inventory of every single component, dependency, runtime artifact, cache directory, and file created by OmniAgent OS, along with verification steps to confirm that your host operating system remains 100% clean.

---

## 1. Zero-Pollution Guarantee

OmniAgent OS operates under a **Strict Sandboxing Contract**:
- **Zero Global Packages**: No global `pip install` or `npm install -g` commands are ever run.
- **Zero System Directory Modification**: Windows system folders (`C:\Windows`, `C:\Program Files`, `~/.bashrc`, or user app data roots) are never altered.
- **Self-Contained Storage**: All runtime artifacts, dependencies, virtual environments, caches, and logs stay strictly inside this project folder:
  ```
  e:\Own Porjects\OmniAgent\
  ```

---

## 2. Itemized Inventory of Installed Components

When OmniAgent OS is installed and executed, it populates only the following local paths:

| Path | Purpose | Removal Mechanism |
| :--- | :--- | :--- |
| **`./.venv/`** | Isolated Python virtual environment (FastAPI, PyAutoGUI, pywinauto, faster-whisper, Anthropic/OpenAI SDKs) | Deleted by `UNINSTALL_AND_CLEANUP.bat` |
| **`./.runtime/`** | Portable standalone CPython runtime (used if host machine has no Python) | Deleted by `UNINSTALL_AND_CLEANUP.bat` |
| **`./frontend/node_modules/`** | Local npm dependencies (React, Vite, Monaco Editor, Tailwind, xterm.js) | Deleted by `UNINSTALL_AND_CLEANUP.bat` |
| **`./frontend/dist/`** | Production build of the Vite React workspace | Deleted by `UNINSTALL_AND_CLEANUP.bat` |
| **`./.cache/`** | Redirected local caches: `pip` wheel cache, `npm` package cache, and Hugging Face Whisper model weights | Deleted by `UNINSTALL_AND_CLEANUP.bat` |
| **`./.omniagent_data/`** | Local runtime data: temporary screen captures, audio snippets, and `settings.json` | Deleted by `UNINSTALL_AND_CLEANUP.bat` |
| **`./workspace_audit.log`** | Append-only chronological JSON-lines safety audit journal | Deleted by `UNINSTALL_AND_CLEANUP.bat` |
| **`./.env.local`** | Local API keys vault (OpenRouter, Anthropic, OpenAI, xAI) | Deleted by `UNINSTALL_AND_CLEANUP.bat` |
| **`./**/__pycache__/`** | Python bytecode cache folders | Cleaned by `UNINSTALL_AND_CLEANUP.bat` |

---

## 3. One-Click Automated Uninstall

To completely wipe all installed environments, caches, and data:

1. Double-click or run:
   ```cmd
   UNINSTALL_AND_CLEANUP.bat
   ```
2. When prompted, press `Y` to confirm.
3. The script will:
   - Identify and terminate any active OmniAgent processes on ports 8000 and 3000 (uvicorn, node, python).
   - Terminate any running Whisper or background subshells.
   - Delete `.venv/`, `.runtime/`, `frontend/node_modules/`, `frontend/dist/`, `.cache/`, `.omniagent_data/`, `.env.local`, and `workspace_audit.log`.
   - Purge all Python `__pycache__` directories.

---

## 4. Manual Verification Steps

If you wish to independently verify that your system is completely clean:

1. **Verify No Lingering Processes**:
   Open Windows Task Manager or run:
   ```powershell
   Get-Process -Name python, node -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*OmniAgent*" }
   ```
   *(Expected output: No matching processes)*

2. **Verify Port Release**:
   ```cmd
   netstat -ano | findstr :8000
   netstat -ano | findstr :3000
   ```
   *(Expected output: No active listeners)*

3. **Verify Host Filesystem**:
   Check that no files were created outside the project folder:
   - `C:\Users\%USERNAME%\.cache` (Untouched — redirected to `./.cache`)
   - `C:\Users\%USERNAME%\.huggingface` (Untouched — redirected to `./.cache/huggingface`)
   - Windows Registry (Untouched — no registry keys were written)

---

## 5. Summary

Running `UNINSTALL_AND_CLEANUP.bat` leaves your computer with **zero residual disk, CPU, or RAM overhead**. The repository returns to its pristine initial state containing only the source code files.
