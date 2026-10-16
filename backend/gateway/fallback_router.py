"""
Sub-Module 2.2: Dynamic Failover & Model Switcher.

Tries the user's primary provider first, then walks the configured fallback
chain. Providers without credentials are skipped. When the network is down or
every cloud provider fails, the router lands on the local Ollama instance
(if it is running) so the agent keeps working fully offline.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable, Optional

from gateway.provider_gateway import LOCAL_PROVIDERS, ProviderError, gateway
from gateway.vault import vault
from safety.audit_logger import audit
from schemas import AssistantTurn

log = logging.getLogger("omniagent.fallback")

FailoverCallback = Optional[Callable[[str, str, str], Awaitable[None]]]


class FallbackRouter:
    def __init__(self) -> None:
        # provider -> unix time until which it is considered unhealthy
        self._cooldown: dict[str, float] = {}

    def _chain(self) -> list[str]:
        s = vault.settings()
        primary = s["provider"]
        chain = [primary] + [p for p in s.get("fallback_chain", []) if p != primary]
        if "ollama" not in chain:
            chain.append("ollama")
        return chain

    def provider_health(self) -> dict[str, Any]:
        now = time.time()
        return {p: {"cooldown_s": max(0, int(t - now))} for p, t in self._cooldown.items() if t > now}

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        on_delta=None,
        on_failover: FailoverCallback = None,
        session_id: str = "",
    ) -> AssistantTurn:
        errors: list[str] = []
        chain = self._chain()
        now = time.time()
        ollama_checked: bool | None = None

        for idx, provider in enumerate(chain):
            if not gateway.is_configured(provider):
                errors.append(f"{provider}: not configured")
                continue
            if self._cooldown.get(provider, 0) > now and idx != 0:
                errors.append(f"{provider}: cooling down after recent failure")
                continue
            if provider == "ollama":
                if ollama_checked is None:
                    ollama_checked = (await gateway.ollama_status())["online"]
                if not ollama_checked:
                    errors.append("ollama: local server not reachable")
                    continue
            model = gateway.model_for(provider)
            try:
                turn = await gateway.complete(provider, model, messages, tools, on_delta=on_delta)
                self._cooldown.pop(provider, None)
                if idx > 0:
                    audit.log("provider_failover", session_id=session_id, used=provider, model=model, errors=errors)
                return turn
            except ProviderError as exc:
                log.warning("Provider %s failed: %s", provider, exc)
                errors.append(str(exc))
                if not exc.fallback_ok:
                    raise
                if provider not in LOCAL_PROVIDERS:
                    self._cooldown[provider] = time.time() + (300 if exc.status in (401, 403) else 45)
                nxt = next((p for p in chain[idx + 1:] if gateway.is_configured(p)), None)
                if on_failover and nxt:
                    await on_failover(provider, nxt, str(exc))
        raise ProviderError(
            "router",
            "All providers failed or are unconfigured. Configure an API key in Settings or start Ollama locally.\n- "
            + "\n- ".join(errors),
            fallback_ok=False,
        )


fallback_router = FallbackRouter()
