"""
Sub-Module 6.2: User Approval Gate Bridge.

Pauses the agentic loop when a high-risk action is detected, emits an
`approval_request` event over the WebSocket bus and blocks until the human
clicks ALLOW / DENY (or the request times out, which counts as DENY).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

from config import APPROVAL_TIMEOUT_SECONDS
from safety.audit_logger import audit
from schemas import ApprovalDecision, ApprovalRequest

Emitter = Callable[[dict[str, Any]], Awaitable[None]]


class ApprovalBridge:
    def __init__(self) -> None:
        self._pending: dict[str, tuple[ApprovalRequest, asyncio.Future[ApprovalDecision]]] = {}
        self._lock = asyncio.Lock()

    async def request(self, req: ApprovalRequest, emit: Emitter) -> ApprovalDecision:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[ApprovalDecision] = loop.create_future()
        async with self._lock:
            self._pending[req.id] = (req, future)
        req.timeout_seconds = req.timeout_seconds or APPROVAL_TIMEOUT_SECONDS
        audit.log(
            "approval_requested",
            session_id=req.session_id,
            approval_id=req.id,
            tool=req.tool_name,
            command=req.exact_command_or_query,
            risk=req.risk_level.value,
            reasons=req.reasons,
        )
        await emit({"type": "approval_request", "data": req.model_dump(mode="json")})
        try:
            decision = await asyncio.wait_for(asyncio.shield(future), timeout=req.timeout_seconds)
        except asyncio.TimeoutError:
            decision = ApprovalDecision(id=req.id, approved=False, decided_by="timeout",
                                        note=f"No response within {req.timeout_seconds}s; auto-denied.")
        except asyncio.CancelledError:
            decision = ApprovalDecision(id=req.id, approved=False, decided_by="system", note="Agent run cancelled.")
            await self._finish(req, decision, emit)
            raise
        await self._finish(req, decision, emit)
        return decision

    async def _finish(self, req: ApprovalRequest, decision: ApprovalDecision, emit: Emitter) -> None:
        async with self._lock:
            entry = self._pending.pop(req.id, None)
        if entry and not entry[1].done():
            entry[1].set_result(decision)
        audit.log(
            "approval_decision",
            session_id=req.session_id,
            approval_id=req.id,
            approved=decision.approved,
            decided_by=decision.decided_by,
            note=decision.note,
            latency_s=round(time.time() - req.created_at, 2),
        )
        try:
            await emit({"type": "approval_resolved", "data": decision.model_dump(mode="json")})
        except Exception:  # noqa: BLE001 - socket may already be closed
            pass

    def resolve(self, approval_id: str, approved: bool, decided_by: str = "user", note: str = "") -> bool:
        entry = self._pending.get(approval_id)
        if not entry:
            return False
        _, future = entry
        if future.done():
            return False
        future.set_result(ApprovalDecision(id=approval_id, approved=approved, decided_by=decided_by, note=note))  # type: ignore[arg-type]
        return True

    def deny_all(self, reason: str, decided_by: str = "kill_switch") -> int:
        count = 0
        for approval_id in list(self._pending.keys()):
            if self.resolve(approval_id, False, decided_by=decided_by, note=reason):
                count += 1
        return count

    def pending_for(self, session_id: str | None = None) -> list[dict[str, Any]]:
        return [
            req.model_dump(mode="json")
            for req, fut in self._pending.values()
            if not fut.done() and (session_id is None or req.session_id == session_id)
        ]


approval_bridge = ApprovalBridge()
