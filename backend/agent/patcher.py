"""
Sub-Module 3.3: Targeted AST & String Patcher.

Executes targeted chunk replacements for clean, incremental code updates rather
than overwriting whole files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from config import WORKSPACE_ROOT
from os_control.file_tools import _resolve_safe_path
from safety.guardrails import guardrails


def apply_patch(
    relative_path: str,
    target: str,
    replacement: str,
    allow_multiple: bool = False
) -> dict[str, Any]:
    """
    Replaces an exact target chunk of text with replacement content in the given file.
    """
    assessment = guardrails.assess_file_write(relative_path, replacement)
    if assessment.blocked:
        return {"ok": False, "error": assessment.block_reason}

    try:
        path = _resolve_safe_path(relative_path)
        if not path.exists():
            return {"ok": False, "error": f"File '{relative_path}' does not exist."}

        content = path.read_text(encoding="utf-8")

        count = content.count(target)
        if count == 0:
            return {
                "ok": False,
                "error": f"Target content was not found in '{relative_path}'. Ensure the target string matches exactly."
            }

        if count > 1 and not allow_multiple:
            return {
                "ok": False,
                "error": f"Target content found {count} times in '{relative_path}'. Specify a more unique snippet or set allow_multiple=True."
            }

        new_content = content.replace(target, replacement) if allow_multiple else content.replace(target, replacement, 1)
        path.write_text(new_content, encoding="utf-8")

        return {
            "ok": True,
            "path": relative_path,
            "replacements_made": count if allow_multiple else 1,
            "new_size": len(new_content.encode("utf-8"))
        }

    except Exception as exc:
        return {"ok": False, "error": str(exc)}
