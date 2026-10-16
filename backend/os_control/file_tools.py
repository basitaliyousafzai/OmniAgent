"""
Sub-Module 5.4: Sandboxed Filesystem Tools.

Provides safe workspace-confined file reading, writing, directory traversal,
and content search. All operations strictly enforce relative path containment
inside WORKSPACE_ROOT to adhere to the Zero-Pollution Contract.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from config import IGNORED_DIR_NAMES, MAX_READ_FILE_BYTES, WORKSPACE_ROOT
from safety.guardrails import guardrails


def _resolve_safe_path(rel_path: str) -> Path:
    """Resolves path and confirms it is within WORKSPACE_ROOT."""
    cleaned = rel_path.strip().lstrip("/\\")
    target = (WORKSPACE_ROOT / cleaned).resolve()
    try:
        target.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        raise PermissionError(f"Access denied: Path '{rel_path}' is outside workspace root.")
    return target


def read_file_content(relative_path: str) -> dict[str, Any]:
    assessment = guardrails.assess_file_read(relative_path)
    if assessment.blocked:
        return {"ok": False, "error": assessment.block_reason}

    try:
        path = _resolve_safe_path(relative_path)
        if not path.exists():
            return {"ok": False, "error": f"File '{relative_path}' does not exist."}
        if path.is_dir():
            return {"ok": False, "error": f"'{relative_path}' is a directory, not a file."}

        size = path.stat().st_size
        if size > MAX_READ_FILE_BYTES:
            # Read first chunk with note
            content = path.read_text(encoding="utf-8", errors="replace")[:MAX_READ_FILE_BYTES]
            return {
                "ok": True,
                "path": relative_path,
                "content": content,
                "truncated": True,
                "total_bytes": size,
                "note": f"File content truncated at {MAX_READ_FILE_BYTES} bytes."
            }

        content = path.read_text(encoding="utf-8", errors="replace")
        return {"ok": True, "path": relative_path, "content": content, "total_bytes": size}

    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def write_file_content(relative_path: str, content: str) -> dict[str, Any]:
    assessment = guardrails.assess_file_write(relative_path, content)
    if assessment.blocked:
        return {"ok": False, "error": assessment.block_reason}

    try:
        path = _resolve_safe_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"ok": True, "path": relative_path, "bytes_written": len(content.encode("utf-8"))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def list_dir(relative_path: str = ".", recursive: bool = False, max_items: int = 200) -> dict[str, Any]:
    try:
        base = _resolve_safe_path(relative_path)
        if not base.exists():
            return {"ok": False, "error": f"Directory '{relative_path}' does not exist."}
        if not base.is_dir():
            return {"ok": False, "error": f"'{relative_path}' is a file, not a directory."}

        items: list[dict[str, Any]] = []

        if not recursive:
            for entry in sorted(base.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if entry.name in IGNORED_DIR_NAMES:
                    continue
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if entry.is_file() else 0,
                    "path": entry.relative_to(WORKSPACE_ROOT).as_posix()
                })
                if len(items) >= max_items:
                    break
        else:
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIR_NAMES]
                for d in dirs:
                    p = Path(root) / d
                    items.append({
                        "name": d,
                        "is_dir": True,
                        "size": 0,
                        "path": p.relative_to(WORKSPACE_ROOT).as_posix()
                    })
                    if len(items) >= max_items:
                        break
                for f in files:
                    p = Path(root) / f
                    items.append({
                        "name": f,
                        "is_dir": False,
                        "size": p.stat().st_size,
                        "path": p.relative_to(WORKSPACE_ROOT).as_posix()
                    })
                    if len(items) >= max_items:
                        break
                if len(items) >= max_items:
                    break

        return {"ok": True, "path": relative_path, "items": items, "count": len(items)}

    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def search_workspace_code(query: str, max_results: int = 50) -> dict[str, Any]:
    """Simple fast case-insensitive substring search across non-ignored files."""
    if not query:
        return {"ok": True, "results": []}

    results: list[dict[str, Any]] = []
    q_lower = query.lower()

    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIR_NAMES]
        for f in files:
            file_path = Path(root) / f
            try:
                # Skip large files or known binary extensions
                if file_path.stat().st_size > 1_000_000:
                    continue
                if file_path.suffix.lower() in {".exe", ".dll", ".zip", ".tar", ".gz", ".png", ".jpg", ".bin"}:
                    continue

                lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                for line_idx, line in enumerate(lines, 1):
                    if q_lower in line.lower():
                        results.append({
                            "file": file_path.relative_to(WORKSPACE_ROOT).as_posix(),
                            "line": line_idx,
                            "content": line.strip()[:200]
                        })
                        if len(results) >= max_results:
                            return {"ok": True, "query": query, "results": results, "capped": True}
            except Exception:
                continue

    return {"ok": True, "query": query, "results": results, "capped": False}
