"""
Sub-Module 6.3: Global Emergency Kill Switch.

A background keyboard hook listens for Ctrl+Esc (and the UI exposes an
"Emergency Stop" button wired to the same trigger). When fired it:
  * sets a process-wide abort flag checked before every synthetic input action,
  * terminates every subprocess spawned by the shell runner,
  * cancels running agent loops and auto-denies pending approvals.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import threading
import time
from typing import Any, Callable

from safety.audit_logger import audit

log = logging.getLogger("omniagent.killswitch")


class EmergencyAbort(RuntimeError):
    """Raised by automation primitives when the kill switch is engaged."""


class KillSwitch:
    def __init__(self) -> None:
        self._event = threading.Event()
        self._callbacks: list[Callable[[str], Any]] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._listener: Any = None
        self._lock = threading.Lock()
        self.last_trigger: dict[str, Any] | None = None
        self.hotkey_active = False

    # -- lifecycle -------------------------------------------------------------
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def register(self, callback: Callable[[str], Any]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def start_hotkey_listener(self) -> bool:
        """Start the global Ctrl+Esc listener. Returns False if unavailable (e.g. headless)."""
        if self._listener is not None:
            return True
        try:
            from pynput import keyboard  # imported lazily: requires a desktop session

            self._listener = keyboard.GlobalHotKeys({"<ctrl>+<esc>": lambda: self.trigger("hotkey Ctrl+Esc")})
            self._listener.daemon = True
            self._listener.start()
            self.hotkey_active = True
            log.info("Emergency kill switch armed (Ctrl+Esc).")
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("Kill-switch hotkey unavailable: %s", exc)
            self._listener = None
            self.hotkey_active = False
            return False

    def stop_hotkey_listener(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:  # noqa: BLE001
                pass
            self._listener = None
            self.hotkey_active = False

    # -- state -----------------------------------------------------------------
    @property
    def engaged(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        if self._event.is_set():
            raise EmergencyAbort("Emergency kill switch is engaged. Reset it from the UI to resume automation.")

    def reset(self) -> None:
        if self._event.is_set():
            self._event.clear()
            audit.log("kill_switch_reset")

    def trigger(self, reason: str = "manual") -> None:
        self._event.set()
        self.last_trigger = {"reason": reason, "ts": time.time()}
        audit.log("kill_switch_triggered", reason=reason)
        log.warning("EMERGENCY STOP triggered: %s", reason)
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                if inspect.iscoroutinefunction(cb):
                    if self._loop is not None and self._loop.is_running():
                        asyncio.run_coroutine_threadsafe(cb(reason), self._loop)
                else:
                    result = cb(reason)
                    if inspect.isawaitable(result) and self._loop is not None:
                        asyncio.run_coroutine_threadsafe(result, self._loop)  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001
                log.error("Kill-switch callback failed: %s", exc)


kill_switch = KillSwitch()
