"""
Sub-Module 3.1: ReAct Orchestrator & Computer-Use Loop.

Coordinates the autonomous loop:
  [Receive Goal] -> [Observe Screen/Window] -> [Think] -> [Dispatch App Action / Tool] -> [Verify Feedback]
Enforces:
  - Human-in-the-loop safety gating on destructive commands/SQL.
  - Automatic screenshot feedback after GUI actions for vision verification.
  - Token-budget context trimming.
  - Multi-provider dynamic failover (OpenRouter, Claude, GPT-4o, Grok, Ollama).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from agent.patcher import apply_patch
from agent.system_prompt import build_system_prompt
from agent.tool_registry import MASTER_TOOLS
from agent.workspace_indexer import index_workspace
from config import MAX_AGENT_STEPS
from gateway.context_trimmer import trim_context
from gateway.fallback_router import fallback_router
from gateway.vault import vault
from multimodal.screen_capture import screen_capture
from os_control.app_orchestrator import app_orchestrator
from os_control.file_tools import list_dir, read_file_content, search_workspace_code, write_file_content
from os_control.gui_controller import gui_controller
from os_control.shell_runner import shell_runner
from os_control.ui_automation import ui_automation
from os_control.window_manager import find_windows, foreground_window, launch_or_focus
from safety.approval_bridge import approval_bridge
from safety.audit_logger import audit
from safety.guardrails import guardrails
from safety.kill_switch import kill_switch
from schemas import ApprovalRequest, RiskLevel, ToolCall, ToolResult

log = logging.getLogger("omniagent.orchestrator")

Emitter = Callable[[dict[str, Any]], Awaitable[None]]


class AgentOrchestrator:
    def __init__(self) -> None:
        self._active_sessions: dict[str, asyncio.Task] = {}
        self._session_histories: dict[str, list[dict[str, Any]]] = {}

    def is_running(self, session_id: str) -> bool:
        task = self._active_sessions.get(session_id)
        return task is not None and not task.done()

    def abort_session(self, session_id: str) -> bool:
        task = self._active_sessions.get(session_id)
        if task and not task.done():
            task.cancel()
            audit.log("session_aborted", session_id=session_id)
            return True
        return False

    async def execute_tool(
        self,
        tool_call: ToolCall,
        session_id: str,
        emit: Emitter
    ) -> ToolResult:
        kill_switch.check()
        name = tool_call.name
        args = tool_call.arguments
        log.info("Session %s executing tool: %s (%s)", session_id, name, args.keys())

        # ------------------------------------------------------------------ #
        # Safety & Human Approval Gate
        # ------------------------------------------------------------------ #
        assessment = guardrails.assess_tool_call(name, args)
        if assessment.blocked:
            audit.log("tool_blocked_by_guardrails", session_id=session_id, tool=name, reason=assessment.block_reason)
            return ToolResult(
                tool_call_id=tool_call.id,
                name=name,
                ok=False,
                output=f"SAFETY BLOCKED: {assessment.block_reason}"
            )

        if assessment.requires_approval or name == "request_user_confirmation":
            # Human confirmation requested
            desc = args.get("action_description") or assessment.summary()
            cmd = args.get("exact_command_or_query") or args.get("command") or args.get("content") or json.dumps(args)
            level = RiskLevel(args.get("risk_level", assessment.level.value))

            req = ApprovalRequest(
                session_id=session_id,
                tool_name=name,
                action_description=str(desc),
                exact_command_or_query=str(cmd),
                risk_level=level,
                reasons=[m.description for m in assessment.matches]
            )

            decision = await approval_bridge.request(req, emit)
            if not decision.approved:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    name=name,
                    ok=False,
                    output=f"USER REJECTED: The dangerous action was denied by the user. Note: {decision.note}"
                )

            if name == "request_user_confirmation":
                return ToolResult(
                    tool_call_id=tool_call.id,
                    name=name,
                    ok=True,
                    output="Confirmation granted by user. You may proceed with the next step."
                )

        # ------------------------------------------------------------------ #
        # Tool Execution Dispatcher
        # ------------------------------------------------------------------ #
        res_output = ""
        res_ok = True
        extra: dict[str, Any] = {}
        image_b64: Optional[str] = None
        screenshot_file: Optional[str] = None
        is_gui_action = False

        try:
            if name == "launch_or_focus_app":
                app_target = str(args.get("app_name_or_title", ""))
                res = launch_or_focus(app_target)
                res_output = json.dumps(res, indent=2)
                res_ok = res.get("focused", False) or res.get("action") == "launched"
                is_gui_action = True

            elif name == "send_hotkey":
                keys = args.get("keys", [])
                res = gui_controller.send_hotkey(keys)
                res_output = json.dumps(res)
                is_gui_action = True

            elif name == "gui_mouse_action":
                nx = float(args.get("norm_x", 0))
                ny = float(args.get("norm_y", 0))
                ctype = str(args.get("click_type", "left"))
                res = gui_controller.mouse_click(nx, ny, click_type=ctype)
                res_output = json.dumps(res)
                is_gui_action = True

            elif name == "gui_type_string":
                text = str(args.get("text", ""))
                enter = bool(args.get("press_enter", False))
                res = gui_controller.type_string(text, press_enter=enter)
                res_output = json.dumps(res)
                is_gui_action = True

            elif name == "capture_desktop_view":
                grid = bool(args.get("grid", False))
                s = vault.settings()
                cap = screen_capture.capture(
                    max_width=int(s.get("screenshot_max_width", 1366)),
                    quality=int(s.get("screenshot_jpeg_quality", 70)),
                    grid=grid
                )
                image_b64 = cap.b64
                screenshot_file = cap.file_name
                res_output = cap.describe()

            elif name == "execute_shell":
                cmd = str(args.get("command", ""))
                res = shell_runner.run_command(cmd, session_id=session_id)
                res_ok = res["ok"]
                res_output = f"Exit code: {res['returncode']}\nSTDOUT:\n{res['stdout']}\nSTDERR:\n{res['stderr']}"

            elif name == "write_file":
                rel = str(args.get("relative_path", ""))
                content = str(args.get("content", ""))
                res = write_file_content(rel, content)
                res_ok = res["ok"]
                res_output = json.dumps(res)

            elif name == "read_file":
                rel = str(args.get("relative_path", ""))
                res = read_file_content(rel)
                res_ok = res["ok"]
                res_output = res.get("content") if res_ok else json.dumps(res)

            elif name == "list_directory":
                rel = str(args.get("relative_path", "."))
                rec = bool(args.get("recursive", False))
                res = list_dir(rel, recursive=rec)
                res_ok = res["ok"]
                res_output = json.dumps(res, indent=2)

            elif name == "search_code":
                query = str(args.get("query", ""))
                res = search_workspace_code(query)
                res_output = json.dumps(res, indent=2)

            elif name == "apply_patch":
                rel = str(args.get("relative_path", ""))
                target = str(args.get("target", ""))
                replacement = str(args.get("replacement", ""))
                res = apply_patch(rel, target, replacement)
                res_ok = res["ok"]
                res_output = json.dumps(res)

            elif name == "app_action":
                target_app = str(args.get("target_app", ""))
                act = str(args.get("action", ""))
                arg_val = str(args.get("argument", "") or "")
                res = app_orchestrator.dispatch_action(target_app, act, argument=arg_val)
                res_ok = res.get("ok", False)
                res_output = json.dumps(res, indent=2)
                is_gui_action = True

            elif name == "inspect_ui_tree":
                app_target = args.get("app_name_or_title")
                hwnd = 0
                if app_target:
                    wins = find_windows(str(app_target))
                    if wins:
                        hwnd = wins[0].hwnd
                if not hwnd:
                    fg = foreground_window()
                    if fg:
                        hwnd = fg.hwnd
                if not hwnd:
                    res_output = "No active window found to inspect."
                    res_ok = False
                else:
                    tree = ui_automation.dump_control_tree(hwnd)
                    res_output = json.dumps(tree, indent=2)

            elif name == "click_ui_element":
                name_to_click = str(args.get("element_name", ""))
                ctype = args.get("control_type")
                fg = foreground_window()
                if not fg:
                    res_output = "No active foreground window found."
                    res_ok = False
                else:
                    res = ui_automation.click_element(fg.hwnd, name=name_to_click, control_type=ctype)
                    res_ok = res.get("ok", False)
                    res_output = json.dumps(res)
                    is_gui_action = True

            elif name == "browser_navigate":
                target_url = str(args.get("url", ""))
                browser_name = str(args.get("browser", "chrome") or "chrome")
                res = app_orchestrator.browser_open_url(target_url, browser=browser_name)
                res_ok = res.get("ok", False)
                res_output = json.dumps(res, indent=2)
                is_gui_action = True

            elif name == "ssms_run_query":
                sql_q = str(args.get("query", ""))
                db_name = args.get("database")
                if db_name and f"use {db_name.lower()}" not in sql_q.lower():
                    sql_q = f"USE [{db_name}];\nGO\n{sql_q}"
                res = app_orchestrator.ssms_execute_query(sql_q)
                res_ok = res.get("ok", False)
                res_output = json.dumps(res, indent=2)
                is_gui_action = True

            elif name == "save_learned_skill":
                task_intent = str(args.get("task_intent", ""))
                seq = list(args.get("action_sequence", []))
                insights = str(args.get("key_insights", ""))
                from agent.self_learner import self_learner
                res = self_learner.record_experience(task_intent, seq, insights)
                res_ok = res.get("ok", False)
                res_output = json.dumps(res, indent=2)

            else:
                res_ok = False
                res_output = f"Unknown tool: {name}"

        except Exception as exc:
            log.error("Tool execution error: %s", exc, exc_info=True)
            res_ok = False
            res_output = f"Execution error: {exc}"

        # ------------------------------------------------------------------ #
        # Post-action Visual Verification Loop
        # ------------------------------------------------------------------ #
        # If the action touched the GUI and auto_screenshot is enabled, grab
        # a fresh screen capture and attach it to the tool result.
        s = vault.settings()
        if is_gui_action and s.get("auto_screenshot_after_gui_action", True):
            try:
                time.sleep(0.3)
                cap = screen_capture.capture(
                    max_width=int(s.get("screenshot_max_width", 1366)),
                    quality=int(s.get("screenshot_jpeg_quality", 70)),
                    grid=False
                )
                if cap and hasattr(cap, "b64"):
                    image_b64 = cap.b64
                    screenshot_file = getattr(cap, "file_name", None)
                    feedback_desc = "Screen updated successfully."
                    try:
                        feedback_desc = cap.describe()
                    except Exception:
                        feedback_desc = f"Display state captured ({getattr(cap, 'width', 0)}x{getattr(cap, 'height', 0)})."

                    base_out = str(res_output or "").strip()
                    res_output = f"{base_out}\n\n[Visual Feedback]: {feedback_desc}".strip()
            except Exception as cap_exc:
                log.warning("Auto-screenshot verification skipped: %s", cap_exc)

        result = ToolResult(
            tool_call_id=tool_call.id,
            name=name,
            ok=res_ok,
            output=str(res_output if res_output is not None else ""),
            image_b64=image_b64,
            screenshot_file=screenshot_file,
            extra=extra
        )

        audit.log(
            "tool_executed",
            session_id=session_id,
            tool=name,
            ok=res_ok,
            has_screenshot=bool(image_b64)
        )

        return result

    async def run_loop(
        self,
        session_id: str,
        user_goal: str,
        emit: Emitter,
        initial_image_b64: Optional[str] = None
    ) -> None:
        """The main autonomous ReAct loop."""
        audit.log("session_started", session_id=session_id, goal=user_goal)
        await emit({"type": "agent_start", "data": {"session_id": session_id, "goal": user_goal}})

        # Build initial messages with dynamic self-learned experiences
        system_prompt = build_system_prompt(goal=user_goal)
        workspace_overview = index_workspace()

        system_msg = {
            "role": "system",
            "content": f"{system_prompt}\n\nCURRENT WORKSPACE FILE TREE:\n{workspace_overview}"
        }

        user_content: list[dict[str, Any]] = [{"type": "text", "text": user_goal}]
        if initial_image_b64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{initial_image_b64}"}
            })

        user_msg = {"role": "user", "content": user_content}

        # Keep or append to session history
        history = self._session_histories.get(session_id, [system_msg])
        if len(history) <= 1:
            history = [system_msg, user_msg]
        else:
            history.append(user_msg)
        self._session_histories[session_id] = history

        step = 0
        s = vault.settings()
        token_budget = int(s.get("context_token_budget", 60000))
        max_images = int(s.get("max_images_in_context", 2))

        try:
            while step < MAX_AGENT_STEPS:
                kill_switch.check()
                step += 1
                await emit({"type": "agent_step", "data": {"step": step, "max_steps": MAX_AGENT_STEPS}})

                # Optimize context window
                trimmed_messages = trim_context(history, token_budget=token_budget, max_images=max_images)

                # Streaming text delta callback
                async def on_delta(delta: str) -> None:
                    await emit({"type": "agent_thought_delta", "data": {"step": step, "delta": delta}})

                # Call LLM via failover router
                turn = await fallback_router.complete(
                    messages=trimmed_messages,
                    tools=MASTER_TOOLS,
                    on_delta=on_delta,
                    session_id=session_id
                )

                # Record assistant turn in history
                assistant_record: dict[str, Any] = {"role": "assistant"}
                if turn.content:
                    assistant_record["content"] = turn.content
                if turn.tool_calls:
                    assistant_record["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                            **({"extra_content": tc.extra_content} if tc.extra_content else {})
                        }
                        for tc in turn.tool_calls
                    ]
                history.append(assistant_record)

                await emit({
                    "type": "agent_thought",
                    "data": {
                        "step": step,
                        "content": turn.content,
                        "tool_calls": [tc.model_dump() for tc in turn.tool_calls],
                        "provider": turn.provider,
                        "model": turn.model,
                        "usage": turn.usage.model_dump()
                    }
                })

                # If no tool calls were made, the agent finished its reasoning
                if not turn.tool_calls:
                    log.info("Session %s completed at step %d with no further tool calls.", session_id, step)
                    break

                # Execute all tool calls
                for tc in turn.tool_calls:
                    kill_switch.check()
                    await emit({"type": "tool_call_start", "data": {"step": step, "tool_call": tc.model_dump()}})

                    result = await self.execute_tool(tc, session_id, emit)

                    await emit({
                        "type": "tool_call_result",
                        "data": {
                            "step": step,
                            "result": result.model_dump(exclude={"image_b64"}) if result.image_b64 else result.model_dump(),
                            "has_image": bool(result.image_b64)
                        }
                    })

                    # Feed tool result back into history
                    if result.image_b64:
                        tool_msg: dict[str, Any] = {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": [
                                {"type": "text", "text": result.output},
                                {"type": "image_url", "image_url": {"url": f"data:{result.image_mime};base64,{result.image_b64}"}}
                            ]
                        }
                    else:
                        tool_msg = {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": result.output
                        }
                    history.append(tool_msg)

            await emit({
                "type": "agent_done",
                "data": {
                    "session_id": session_id,
                    "steps": step,
                    "completed": step < MAX_AGENT_STEPS
                }
            })
            audit.log("session_completed", session_id=session_id, steps=step)
            # Autonomous Self-Training: Distill and record learned skills permanently into memory bank
            try:
                from agent.self_learner import self_learner
                self_learner.distill_from_trajectory(
                    goal=user_goal,
                    history=history,
                    completed=step < MAX_AGENT_STEPS
                )
            except Exception as learn_exc:
                log.debug("Self-learning auto-training notice: %s", learn_exc)

        except asyncio.CancelledError:
            log.info("Session %s cancelled.", session_id)
            await emit({"type": "agent_cancelled", "data": {"session_id": session_id}})
        except Exception as exc:
            log.error("Session %s encountered error: %s", session_id, exc, exc_info=True)
            await emit({"type": "agent_error", "data": {"session_id": session_id, "error": str(exc)}})
            audit.log("session_error", session_id=session_id, error=str(exc))
        finally:
            self._active_sessions.pop(session_id, None)


orchestrator = AgentOrchestrator()
