"""
Sub-Module: Workspace Structure Indexer.

Produces a lightweight compact file tree overview of the workspace to orient the agent.
"""
from __future__ import annotations

import os
from pathlib import Path

from config import IGNORED_DIR_NAMES, WORKSPACE_ROOT


def index_workspace(max_depth: int = 3, max_entries: int = 120) -> str:
    """Generates an ASCII file tree of the workspace directory."""
    lines: list[str] = [f"Workspace Root: {WORKSPACE_ROOT.name}/"]
    count = 0

    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        rel = Path(root).relative_to(WORKSPACE_ROOT)
        depth = len(rel.parts)
        if depth > max_depth:
            dirs.clear()
            continue

        dirs[:] = [d for d in sorted(dirs) if d not in IGNORED_DIR_NAMES]
        indent = "  " * depth

        if rel.parts:
            lines.append(f"{indent}📁 {rel.name}/")
            count += 1

        for f in sorted(files):
            if count >= max_entries:
                lines.append(f"{indent}  ... [additional files omitted]")
                return "\n".join(lines)
            if f.startswith("."):
                continue
            lines.append(f"{indent}  📄 {f}")
            count += 1

    return "\n".join(lines)
