"""
Sub-Module 3.6: Autonomous Self-Learning & Experience Distillation Engine.

Enables OmniAgent to train itself continuously from every desktop task it executes.
Features:
  - Persistent episodic memory stored in `.omniagent_data/learned_memory.json`.
  - Distills successful tool call trajectories, UI patterns, shortcuts, and recovery steps.
  - Semantic and keyword retrieval of relevant past experiences for zero-shot tasks.
  - Dynamic in-context injection into the ReAct loop so the agent gets smarter with every run.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

from config import WORKSPACE_ROOT

log = logging.getLogger("omniagent.self_learner")

MEMORY_FILE = Path(WORKSPACE_ROOT) / ".omniagent_data" / "learned_memory.json"


class SelfLearner:
    def __init__(self, memory_path: Path = MEMORY_FILE) -> None:
        self.memory_path = memory_path
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        try:
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.memory_path.exists():
                initial_data: dict[str, Any] = {
                    "version": "1.0",
                    "total_trained_tasks": 0,
                    "last_updated": time.time(),
                    "memories": []
                }
                self.memory_path.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("Could not initialize learned memory storage: %s", exc)

    def load_all_memories(self) -> list[dict[str, Any]]:
        try:
            if not self.memory_path.exists():
                return []
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            return data.get("memories", [])
        except Exception as exc:
            log.warning("Failed to load learned memories: %s", exc)
            return []

    def record_experience(
        self,
        task_intent: str,
        action_sequence: list[str],
        key_insights: str,
        tags: Optional[list[str]] = None,
        success: bool = True
    ) -> dict[str, Any]:
        """
        Stores a distilled experience into the permanent memory bank.
        """
        try:
            memories = self.load_all_memories()
            
            # Avoid duplicate recordings for virtually identical tasks
            norm_intent = task_intent.strip().lower()
            existing_idx = next((i for i, m in enumerate(memories) if m.get("task_intent", "").lower() == norm_intent), -1)

            entry = {
                "id": f"mem_{int(time.time())}_{len(memories)}",
                "task_intent": task_intent.strip(),
                "action_sequence": action_sequence,
                "key_insights": key_insights.strip(),
                "tags": tags or [t for t in re.findall(r"\w+", norm_intent) if len(t) > 3],
                "success": success,
                "timestamp": time.time(),
                "use_count": 1
            }

            if existing_idx >= 0:
                memories[existing_idx]["action_sequence"] = action_sequence
                memories[existing_idx]["key_insights"] = key_insights
                memories[existing_idx]["use_count"] = memories[existing_idx].get("use_count", 1) + 1
                memories[existing_idx]["timestamp"] = time.time()
                entry = memories[existing_idx]
            else:
                memories.append(entry)

            payload = {
                "version": "1.0",
                "total_trained_tasks": len(memories),
                "last_updated": time.time(),
                "memories": memories[-200:]  # Keep latest 200 high-value skills
            }
            self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            log.info("Self-Learner recorded task experience: '%s' (Total skills: %d)", task_intent, len(memories))
            return {"ok": True, "recorded": True, "memory_id": entry["id"]}
        except Exception as exc:
            log.error("Failed to record learned experience: %s", exc)
            return {"ok": False, "error": str(exc)}

    def retrieve_relevant_experiences(self, current_goal: str, limit: int = 3) -> list[dict[str, Any]]:
        """
        Finds past trained experiences relevant to the user's active goal.
        """
        memories = self.load_all_memories()
        if not memories or not current_goal:
            return []

        goal_words = set(re.findall(r"\w+", current_goal.lower()))
        scored: list[tuple[float, dict[str, Any]]] = []

        for m in memories:
            score = 0.0
            m_text = (m.get("task_intent", "") + " " + " ".join(m.get("tags", [])) + " " + m.get("key_insights", "")).lower()
            m_words = set(re.findall(r"\w+", m_text))

            overlap = goal_words.intersection(m_words)
            if overlap:
                score = len(overlap) / (len(goal_words) + 1.0)
                # Boost if exact phrase matches
                if m.get("task_intent", "").lower() in current_goal.lower():
                    score += 1.5
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def distill_from_trajectory(
        self,
        goal: str,
        history: list[dict[str, Any]],
        completed: bool
    ) -> Optional[dict[str, Any]]:
        """
        Analyzes a finished session history, extracts the tools that succeeded,
        and saves the learned lesson into memory.
        """
        if not completed or not goal or len(history) <= 2:
            return None

        tools_used: list[str] = []
        for msg in history:
            if msg.get("role") == "assistant" and "tool_calls" in msg:
                for tc in msg.get("tool_calls", []):
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    try:
                        args = json.loads(fn.get("arguments", "{}"))
                    except Exception:
                        args = {}
                    
                    # Create descriptive step representation
                    step_summary = name
                    if "target_app" in args:
                        step_summary += f"({args.get('target_app')}:{args.get('action', '')})"
                    elif "url" in args:
                        step_summary += f"(url={args.get('url')[:30]})"
                    elif "query" in args:
                        step_summary += f"(query={args.get('query')[:30]})"
                    elif "app_name_or_title" in args:
                        step_summary += f"(app={args.get('app_name_or_title')})"
                    
                    tools_used.append(step_summary)

        if not tools_used:
            return None

        insights = f"Successfully executed {len(tools_used)} sequential step(s) to achieve goal '{goal}'. Key steps: {' -> '.join(tools_used[:6])}."
        return self.record_experience(
            task_intent=goal,
            action_sequence=tools_used,
            key_insights=insights,
            success=True
        )


self_learner = SelfLearner()
