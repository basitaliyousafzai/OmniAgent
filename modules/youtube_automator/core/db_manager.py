"""
Module 3: SQLite WAL State & Idempotency Engine (core/db_manager.py).

Submodule 3.1 — Concurrent WAL Engine: PRAGMA journal_mode=WAL for concurrent access.
Submodule 3.2 — Daily Upload Ledger (daily_uploads): one row per calendar day.
Submodule 3.3 — Anti-Repetition Topic Memory (topic_history): last-30 negative constraint.
Submodule 3.4 — Execution Telemetry Table (execution_logs): granular step progress.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("youtube.db_manager")

# Resolve storage path relative to this file
_MODULE_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = _MODULE_ROOT / "storage" / "db" / "youtube_agent.db"


class DBManager:
    """Thread-safe SQLite WAL manager for the YouTube Automator pipeline."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------ #
    # Submodule 3.1 — Concurrent WAL Engine
    # ------------------------------------------------------------------ #
    def connect(self) -> sqlite3.Connection:
        """Open or return the existing WAL-mode connection."""
        if self._conn is not None:
            return self._conn
        self._conn = sqlite3.connect(str(self._db_path), timeout=10)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA busy_timeout=5000;")
        self._create_tables()
        log.info("SQLite WAL connected: %s", self._db_path)
        return self._conn

    def close(self) -> None:
        """Gracefully close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self) -> None:
        """Create all required tables if they do not already exist."""
        conn = self._conn
        if conn is None:
            return

        # Submodule 3.2 — Daily Upload Ledger
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_uploads (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_date     TEXT    NOT NULL UNIQUE,
                title           TEXT    NOT NULL DEFAULT '',
                description     TEXT    NOT NULL DEFAULT '',
                tags            TEXT    NOT NULL DEFAULT '[]',
                production_mode TEXT    NOT NULL DEFAULT 'solo',
                video_path      TEXT    NOT NULL DEFAULT '',
                youtube_id      TEXT    NOT NULL DEFAULT '',
                duration_sec    REAL    NOT NULL DEFAULT 0.0,
                file_size_bytes INTEGER NOT NULL DEFAULT 0,
                status          TEXT    NOT NULL DEFAULT 'PENDING',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            );
        """)

        # Submodule 3.3 — Anti-Repetition Topic Memory
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                hook       TEXT    NOT NULL DEFAULT '',
                niche      TEXT    NOT NULL DEFAULT '',
                created_at TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            );
        """)

        # Submodule 3.4 — Execution Telemetry Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date   TEXT    NOT NULL,
                step_name  TEXT    NOT NULL,
                status     TEXT    NOT NULL DEFAULT 'RUNNING',
                message    TEXT    NOT NULL DEFAULT '',
                details    TEXT    NOT NULL DEFAULT '{}',
                started_at TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                ended_at   TEXT
            );
        """)

        conn.commit()

    # ------------------------------------------------------------------ #
    # Submodule 3.2 — Daily Upload Ledger Operations
    # ------------------------------------------------------------------ #
    def has_completed_today(self) -> bool:
        """Return True if a COMPLETED upload already exists for today's date."""
        conn = self.connect()
        today = date.today().isoformat()
        row = conn.execute(
            "SELECT id FROM daily_uploads WHERE upload_date = ? AND status = 'COMPLETED'",
            (today,)
        ).fetchone()
        return row is not None

    def has_any_today(self) -> bool:
        """Return True if any upload record (any status) exists for today."""
        conn = self.connect()
        today = date.today().isoformat()
        row = conn.execute(
            "SELECT id FROM daily_uploads WHERE upload_date = ?",
            (today,)
        ).fetchone()
        return row is not None

    def create_daily_record(
        self,
        title: str,
        description: str,
        tags: list[str],
        production_mode: str,
        video_path: str = "",
        status: str = "RENDERING"
    ) -> int:
        """Insert today's upload record and return its row ID."""
        conn = self.connect()
        today = date.today().isoformat()
        cursor = conn.execute(
            """
            INSERT OR REPLACE INTO daily_uploads
                (upload_date, title, description, tags, production_mode, video_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (today, title, description, json.dumps(tags), production_mode, video_path, status)
        )
        conn.commit()
        return cursor.lastrowid or 0

    def update_daily_record(self, **kwargs: Any) -> None:
        """Update today's daily record with supplied column values."""
        conn = self.connect()
        today = date.today().isoformat()
        if not kwargs:
            return
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [today]
        conn.execute(
            f"UPDATE daily_uploads SET {set_clause} WHERE upload_date = ?",
            values
        )
        conn.commit()

    def get_daily_record(self, target_date: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Fetch today's (or a specific date's) upload record as a dict."""
        conn = self.connect()
        d = target_date or date.today().isoformat()
        row = conn.execute(
            "SELECT * FROM daily_uploads WHERE upload_date = ?", (d,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_recent_uploads(self, limit: int = 30) -> list[dict[str, Any]]:
        """Return the most recent upload records."""
        conn = self.connect()
        rows = conn.execute(
            "SELECT * FROM daily_uploads ORDER BY upload_date DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Submodule 3.3 — Anti-Repetition Topic Memory
    # ------------------------------------------------------------------ #
    def add_topic(self, title: str, hook: str = "", niche: str = "") -> None:
        """Record a topic in the deduplication memory."""
        conn = self.connect()
        conn.execute(
            "INSERT INTO topic_history (title, hook, niche) VALUES (?, ?, ?)",
            (title, hook, niche)
        )
        conn.commit()

    def get_recent_topics(self, limit: int = 30) -> list[dict[str, Any]]:
        """Fetch the last N topics for negative constraint injection."""
        conn = self.connect()
        rows = conn.execute(
            "SELECT title, hook FROM topic_history ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Submodule 3.4 — Execution Telemetry Logging
    # ------------------------------------------------------------------ #
    def log_step(
        self,
        step_name: str,
        status: str = "RUNNING",
        message: str = "",
        details: Optional[dict[str, Any]] = None
    ) -> int:
        """Insert a telemetry log entry for a pipeline step."""
        conn = self.connect()
        today = date.today().isoformat()
        cursor = conn.execute(
            """
            INSERT INTO execution_logs (run_date, step_name, status, message, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (today, step_name, status, message, json.dumps(details or {}))
        )
        conn.commit()
        return cursor.lastrowid or 0

    def update_step(self, log_id: int, status: str, message: str = "") -> None:
        """Mark a telemetry log entry as completed or failed."""
        conn = self.connect()
        conn.execute(
            """
            UPDATE execution_logs
            SET status = ?, message = ?, ended_at = datetime('now','localtime')
            WHERE id = ?
            """,
            (status, message, log_id)
        )
        conn.commit()

    def get_today_logs(self) -> list[dict[str, Any]]:
        """Return all execution log entries for today."""
        conn = self.connect()
        today = date.today().isoformat()
        rows = conn.execute(
            "SELECT * FROM execution_logs WHERE run_date = ? ORDER BY id ASC",
            (today,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics for the dashboard."""
        conn = self.connect()
        total = conn.execute("SELECT COUNT(*) FROM daily_uploads").fetchone()[0]
        completed = conn.execute(
            "SELECT COUNT(*) FROM daily_uploads WHERE status = 'COMPLETED'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM daily_uploads WHERE status = 'FAILED'"
        ).fetchone()[0]
        topics = conn.execute("SELECT COUNT(*) FROM topic_history").fetchone()[0]
        latest = conn.execute(
            "SELECT * FROM daily_uploads ORDER BY upload_date DESC LIMIT 1"
        ).fetchone()
        return {
            "total_uploads": total,
            "completed_uploads": completed,
            "failed_uploads": failed,
            "total_topics": topics,
            "latest": dict(latest) if latest else None,
        }

    # ------------------------------------------------------------------ #
    # Compatibility Aliases for Orchestrator & Router Integration
    # ------------------------------------------------------------------ #
    @property
    def db_path(self) -> Path:
        return self._db_path

    def is_today_uploaded(self, today_date: Optional[str] = None) -> bool:
        conn = self.connect()
        d = today_date or date.today().isoformat()
        row = conn.execute(
            "SELECT id FROM daily_uploads WHERE upload_date = ? AND status = 'COMPLETED'",
            (d,)
        ).fetchone()
        return row is not None

    def record_daily_upload_start(self, upload_date: str, production_mode: str) -> None:
        self.create_daily_record(
            title="Rendering...",
            description="",
            tags=[],
            production_mode=production_mode,
            status="RENDERING"
        )

    def complete_daily_upload(
        self,
        upload_date: str,
        title: str,
        description: str,
        tags: str,
        video_path: str,
        youtube_id: str = "",
        duration_sec: float = 0.0,
        file_size_bytes: int = 0
    ) -> None:
        conn = self.connect()
        cursor = conn.execute(
            """
            UPDATE daily_uploads
            SET title = ?, description = ?, tags = ?, video_path = ?, youtube_id = ?,
                duration_sec = ?, file_size_bytes = ?, status = 'COMPLETED'
            WHERE upload_date = ?
            """,
            (title, description, tags, video_path, str(youtube_id or ""), duration_sec, file_size_bytes, upload_date)
        )
        if cursor.rowcount == 0:
            conn.execute(
                """
                INSERT INTO daily_uploads
                    (upload_date, title, description, tags, video_path, youtube_id, duration_sec, file_size_bytes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED')
                """,
                (upload_date, title, description, tags, video_path, str(youtube_id or ""), duration_sec, file_size_bytes)
            )
        conn.commit()

    def fail_daily_upload(self, upload_date: str, reason: str) -> None:
        conn = self.connect()
        conn.execute(
            "UPDATE daily_uploads SET status = 'FAILED', description = ? WHERE upload_date = ?",
            (f"Failed: {reason}", upload_date)
        )
        conn.commit()

    def record_topic(self, title: str, niche: str = "", hook: str = "") -> None:
        self.add_topic(title=title, hook=hook, niche=niche)

    def log_event(self, run_id: str, stage: str, status: str, detail: str) -> None:
        self.log_step(step_name=stage, status=status, message=detail, details={"run_id": run_id})

    def get_all_uploads(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.get_recent_uploads(limit=limit)

    def get_today_upload(self, target_date: Optional[str] = None) -> Optional[dict[str, Any]]:
        return self.get_daily_record(target_date)

    def get_recent_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT id, run_date, step_name AS stage, status, message AS details, started_at AS created_at FROM execution_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# Singleton instance and class alias
class DatabaseManager(DBManager):
    """Explicit class subclass for backwards and architectural compatibility."""
    pass


db = DBManager()

