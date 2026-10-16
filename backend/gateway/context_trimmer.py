"""
Sub-Module 2.3: Token Optimizer & Context Trimmer.

Keeps the prompt inside a token budget while preserving what matters most:
  1. the system prompt,
  2. the user's original goal,
  3. the most recent turns (never splitting an assistant tool call from its results),
  4. only the N most recent screenshots (older ones become text markers),
  5. older, very long tool outputs are truncated.
"""
from __future__ import annotations

import copy
import json
from typing import Any

IMAGE_TOKEN_COST = 1100
OLD_TOOL_OUTPUT_LIMIT = 1500
RECENT_WINDOW = 6


def estimate_tokens(msg: dict[str, Any]) -> int:
    content = msg.get("content")
    tokens = 4
    if isinstance(content, str):
        tokens += len(content) // 4
    elif isinstance(content, list):
        for part in content:
            if part.get("type") == "image_url":
                tokens += IMAGE_TOKEN_COST
            else:
                tokens += len(part.get("text", "")) // 4
    for tc in msg.get("tool_calls") or []:
        tokens += len(json.dumps(tc)) // 4
    return tokens


def total_tokens(messages: list[dict[str, Any]]) -> int:
    return sum(estimate_tokens(m) for m in messages)


def _limit_images(messages: list[dict[str, Any]], max_images: int) -> None:
    seen = 0
    for msg in reversed(messages):
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        new_parts = []
        for part in reversed(content):
            if part.get("type") == "image_url":
                seen += 1
                if seen > max_images:
                    new_parts.append({"type": "text", "text": "[older screenshot removed to save context]"})
                    continue
            new_parts.append(part)
        msg["content"] = list(reversed(new_parts))


def _truncate_old_tool_outputs(messages: list[dict[str, Any]]) -> None:
    cutoff = max(0, len(messages) - RECENT_WINDOW)
    for msg in messages[:cutoff]:
        if msg.get("role") == "tool" and isinstance(msg.get("content"), str) and len(msg["content"]) > OLD_TOOL_OUTPUT_LIMIT:
            c = msg["content"]
            msg["content"] = c[: OLD_TOOL_OUTPUT_LIMIT // 2] + f"\n...[{len(c) - OLD_TOOL_OUTPUT_LIMIT} chars trimmed]...\n" + c[-OLD_TOOL_OUTPUT_LIMIT // 2:]


def _safe_start(tail: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop leading messages until the window starts at a user (non-tool) message."""
    i = 0
    while i < len(tail) and tail[i].get("role") != "user":
        i += 1
    return tail[i:] if i < len(tail) else tail[-1:]


def trim_context(messages: list[dict[str, Any]], token_budget: int, max_images: int = 2) -> list[dict[str, Any]]:
    msgs = copy.deepcopy(messages)
    _limit_images(msgs, max_images)
    _truncate_old_tool_outputs(msgs)
    if total_tokens(msgs) <= token_budget:
        return msgs

    head: list[dict[str, Any]] = []
    idx = 0
    while idx < len(msgs) and msgs[idx].get("role") == "system":
        head.append(msgs[idx])
        idx += 1
    goal = None
    if idx < len(msgs) and msgs[idx].get("role") == "user":
        goal = msgs[idx]
        idx += 1
    body = msgs[idx:]

    fixed = head + ([goal] if goal else [])
    budget_left = token_budget - total_tokens(fixed) - 50
    kept: list[dict[str, Any]] = []
    used = 0
    for msg in reversed(body):
        cost = estimate_tokens(msg)
        if used + cost > budget_left and kept:
            break
        kept.append(msg)
        used += cost
    kept.reverse()
    kept = _safe_start(kept) if kept and kept[0].get("role") in ("tool", "assistant") else kept
    dropped = len(body) - len(kept)
    note = []
    if dropped > 0:
        note = [{"role": "user", "content": f"[Context optimizer: {dropped} earlier messages were trimmed to stay within the token budget.]"}]
    result = fixed + note + kept
    # Merge accidental consecutive user messages produced by the note insertion
    merged: list[dict[str, Any]] = []
    for m in result:
        if merged and m.get("role") == "user" and merged[-1].get("role") == "user" \
                and isinstance(m.get("content"), str) and isinstance(merged[-1].get("content"), str):
            merged[-1] = {**merged[-1], "content": merged[-1]["content"] + "\n\n" + m["content"]}
        else:
            merged.append(m)
    return merged
