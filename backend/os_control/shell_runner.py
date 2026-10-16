"""
Sub-Module 5.5: Pseudo-Terminal (PTY) Shell Runner.

Executes local shell commands securely:
  - Enforces execution within WORKSPACE_ROOT.
  - Implements strict timeout limits to prevent hanging.
  - Tracks all running child processes and terminates them on Emergency Kill Switch.
  - Returns combined stdout/stderr, return code, and execution time.
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from typing import Any, Optional

from config import IS_WINDOWS, MAX_TOOL_OUTPUT_CHARS, SHELL_TIMEOUT_SECONDS, WORKSPACE_ROOT
from safety.audit_logger import audit
from safety.kill_switch import kill_switch

log = logging.getLogger("omniagent.shell_runner")


class ShellRunner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running_processes: dict[int, subprocess.Popen] = {}
        # Register with the global kill switch to abort active shell processes
        kill_switch.register(self.terminate_all)

    def terminate_all(self, reason: str = "emergency_abort") -> None:
        with self._lock:
            pids = list(self._running_processes.keys())
        for pid in pids:
            try:
                proc = self._running_processes.get(pid)
                if proc and proc.poll() is None:
                    log.warning("Terminating subprocess PID %s due to %s", pid, reason)
                    if IS_WINDOWS:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
                    else:
                        proc.terminate()
                        try:
                            proc.wait(timeout=1.0)
                        except subprocess.TimeoutExpired:
                            proc.kill()
            except Exception as exc:
                log.debug("Error terminating pid %s: %s", pid, exc)
            finally:
                self._running_processes.pop(pid, None)

    def run_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        session_id: str = ""
    ) -> dict[str, Any]:
        kill_switch.check()

        working_dir = WORKSPACE_ROOT
        if cwd:
            resolved_cwd = (WORKSPACE_ROOT / cwd).resolve()
            try:
                resolved_cwd.relative_to(WORKSPACE_ROOT.resolve())
                working_dir = resolved_cwd
            except ValueError:
                return {
                    "ok": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"Error: Specified cwd '{cwd}' is outside workspace root.",
                    "command": command
                }

        timeout_sec = timeout or SHELL_TIMEOUT_SECONDS
        start_time = time.time()

        # Choose appropriate shell
        if IS_WINDOWS:
            shell_cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
        else:
            shell_cmd = ["/bin/bash", "-c", command]

        log.info("Executing shell command in %s: %s", working_dir, command)

        try:
            proc = subprocess.Popen(
                shell_cmd,
                cwd=str(working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0
            )

            with self._lock:
                self._running_processes[proc.pid] = proc

            try:
                stdout, stderr = proc.communicate(timeout=timeout_sec)
                retcode = proc.returncode
            except subprocess.TimeoutExpired:
                log.warning("Command timed out after %ds: %s", timeout_sec, command)
                if IS_WINDOWS:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
                else:
                    proc.kill()
                stdout, stderr = proc.communicate()
                stderr += f"\n[Process killed: exceeded timeout of {timeout_sec} seconds]"
                retcode = -9
            finally:
                with self._lock:
                    self._running_processes.pop(proc.pid, None)

            elapsed = round(time.time() - start_time, 2)

            # Cap long output to keep context manageable
            if len(stdout) > MAX_TOOL_OUTPUT_CHARS:
                half = MAX_TOOL_OUTPUT_CHARS // 2
                stdout = stdout[:half] + f"\n... [stdout truncated {len(stdout) - MAX_TOOL_OUTPUT_CHARS} chars] ...\n" + stdout[-half:]

            if len(stderr) > MAX_TOOL_OUTPUT_CHARS:
                half = MAX_TOOL_OUTPUT_CHARS // 2
                stderr = stderr[:half] + f"\n... [stderr truncated {len(stderr) - MAX_TOOL_OUTPUT_CHARS} chars] ...\n" + stderr[-half:]

            audit.log(
                "shell_executed",
                session_id=session_id,
                command=command,
                returncode=retcode,
                elapsed_s=elapsed
            )

            return {
                "ok": retcode == 0,
                "returncode": retcode,
                "stdout": stdout,
                "stderr": stderr,
                "elapsed": elapsed,
                "command": command
            }

        except Exception as exc:
            log.error("Failed to execute shell command: %s", exc)
            return {
                "ok": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(exc),
                "elapsed": round(time.time() - start_time, 2),
                "command": command
            }


shell_runner = ShellRunner()
