"""
Sub-Module 6.4: Audit Journal.

Chronological, append-only JSON-lines journal stored at ./workspace_audit.log.
Every prompt, tool execution, guardrail verdict and user confirmation is recorded.
The file is size-rotated so it can never grow without bound.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from logging.handlers import RotatingFileHandler
from typing import Any

from config import AUDIT_LOG_FILE

_MAX_FIELD_CHARS = 4000


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > _MAX_FIELD_CHARS:
        return value[:_MAX_FIELD_CHARS] + f"... [truncated {len(value) - _MAX_FIELD_CHARS} chars]"
    if isinstance(value, dict):
        return {k: _truncate(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_truncate(v) for v in value]
    return value


class AuditLogger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._recent: deque[dict[str, Any]] = deque(maxlen=1000)
        self._logger = logging.getLogger("omniagent.audit")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        if not self._logger.handlers:
            handler = RotatingFileHandler(
                AUDIT_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
        self._load_tail()

    def _load_tail(self) -> None:
        if not AUDIT_LOG_FILE.exists():
            return
        try:
            with AUDIT_LOG_FILE.open("r", encoding="utf-8", errors="replace") as fh:
                for line in deque(fh, maxlen=300):
                    line = line.strip()
                    if line:
                        try:
                            self._recent.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except OSError:
            pass

    def log(self, event: str, session_id: str = "", **data: Any) -> dict[str, Any]:
        entry = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "event": event,
            "session_id": session_id,
            "data": _truncate(data),
        }
        with self._lock:
            self._recent.append(entry)
            try:
                self._logger.info(json.dumps(entry, ensure_ascii=False, default=str))
            except Exception:  # noqa: BLE001 - audit logging must never crash the agent
                pass
        return entry

    def tail(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._recent)
        return items[-limit:]


audit = AuditLogger()
