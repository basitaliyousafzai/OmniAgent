"""
Sub-Module 2.1: Unified Provider Switchboard.

A single async interface over:
  * OpenRouter            (OpenAI-compatible, https://openrouter.ai/api/v1)
  * OpenAI native         (GPT-4o, o3-mini, ...)
  * xAI native            (Grok, OpenAI-compatible, https://api.x.ai/v1)
  * Ollama / vLLM / LM Studio (local OpenAI-compatible endpoints)
  * Anthropic native      (Claude, Messages API)

Internally every conversation is kept in OpenAI chat format; this module
converts to the Anthropic schema on the fly. Responses are streamed: text deltas
are forwarded to `on_delta` while tool-call fragments are accumulated into
complete `ToolCall` objects.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import re
from typing import Any, Awaitable, Callable, Optional

import httpx

from gateway.vault import vault
from schemas import AssistantTurn, TokenUsage, ToolCall, new_id

log = logging.getLogger("omniagent.gateway")

DeltaCallback = Optional[Callable[[str], Awaitable[None]]]

OPENAI_COMPATIBLE = ("gemini", "openrouter", "openai", "xai", "ollama", "vllm", "lmstudio")
ALL_PROVIDERS = OPENAI_COMPATIBLE + ("anthropic",)
LOCAL_PROVIDERS = ("ollama", "vllm", "lmstudio")

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-2.5-flash",
    "openrouter": "anthropic/claude-sonnet-4.5",
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-latest",
    "xai": "grok-2-vision-1212",
    "ollama": "llama3.1",
    "vllm": "default",
    "lmstudio": "local-model",
}

AVAILABLE_GEMINI_MODELS = [
    {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (Recommended - Fastest & Flagship)", "context": "1M tokens"},
    {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro (Deep Multimodal Reasoning)", "context": "2M tokens"},
    {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash (Next-Gen Realtime)", "context": "1M tokens"},
    {"id": "gemini-2.0-flash-exp", "label": "Gemini 2.0 Flash Exp (Experimental)", "context": "1M tokens"},
    {"id": "gemini-1.5-flash", "label": "Gemini 1.5 Flash (High Quota Fallback)", "context": "1M tokens"},
    {"id": "gemini-1.5-pro", "label": "Gemini 1.5 Pro (Complex Context)", "context": "2M tokens"},
]

PROVIDER_LABELS: dict[str, str] = {
    "gemini": "Google Gemini",
    "openrouter": "OpenRouter",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "xai": "xAI Grok",
    "ollama": "Ollama (local)",
    "vllm": "vLLM (local)",
    "lmstudio": "LM Studio (local)",
}

# USD per 1M tokens (input, output) - used for the cost optimizer read-out.
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "o3-mini": (1.10, 4.40),
    "o1": (15.00, 60.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3.5-sonnet": (3.00, 15.00),
    "claude-3-7-sonnet": (3.00, 15.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-3-opus": (15.00, 75.00),
    "grok-2": (2.00, 10.00),
    "grok-3": (3.00, 15.00),
    "grok-beta": (5.00, 15.00),
}


class ProviderError(RuntimeError):
    def __init__(self, provider: str, message: str, fallback_ok: bool = True, status: int | None = None) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider = provider
        self.fallback_ok = fallback_ok
        self.status = status


def estimate_cost(model: str, usage: TokenUsage) -> float:
    lowered = model.lower()
    best: tuple[float, float] | None = None
    best_len = 0
    for key, price in PRICING.items():
        if key in lowered and len(key) > best_len:
            best, best_len = price, len(key)
    if not best:
        return 0.0
    return round(usage.prompt_tokens / 1e6 * best[0] + usage.completion_tokens / 1e6 * best[1], 6)


def _parse_arguments(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        pass
    # Repair common streaming artefacts: code fences, trailing commas, truncated braces
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw).strip()
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    if cleaned.count("{") > cleaned.count("}"):
        cleaned += "}" * (cleaned.count("{") - cleaned.count("}"))
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        return {"__invalid_json__": raw}


def strip_images(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace image parts with a text marker (for non-vision models)."""
    out = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if part.get("type") == "image_url":
                    parts.append({"type": "text", "text": "[screenshot omitted: current model has no vision support]"})
                else:
                    parts.append(part)
            msg = {**msg, "content": parts}
        out.append(msg)
    return out


def _flatten_text_content(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Some local servers only accept string content when no images are present."""
    out = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list) and all(p.get("type") == "text" for p in content):
            msg = {**msg, "content": "\n".join(p.get("text", "") for p in content)}
        out.append(msg)
    return out


def _has_images(messages: list[dict[str, Any]]) -> bool:
    return any(
        isinstance(m.get("content"), list) and any(p.get("type") == "image_url" for p in m["content"])
        for m in messages
    )


# --------------------------------------------------------------------------- #
# Anthropic conversion
# --------------------------------------------------------------------------- #
def _data_url_to_anthropic(url: str) -> dict[str, Any] | None:
    m = re.match(r"data:(image/[\w.+-]+);base64,(.+)", url, re.DOTALL)
    if not m:
        return None
    return {"type": "image", "source": {"type": "base64", "media_type": m.group(1), "data": m.group(2)}}


def to_anthropic(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    converted: list[dict[str, Any]] = []

    def push(role: str, blocks: list[dict[str, Any]]) -> None:
        if not blocks:
            return
        if converted and converted[-1]["role"] == role:
            converted[-1]["content"].extend(blocks)
        else:
            converted.append({"role": role, "content": blocks})

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            system_parts.append(content if isinstance(content, str) else " ".join(p.get("text", "") for p in content or []))
            continue
        if role == "tool":
            text = content if isinstance(content, str) else json.dumps(content)
            push("user", [{"type": "tool_result", "tool_use_id": msg.get("tool_call_id", ""), "content": text or "(empty)"}])
            continue
        blocks: list[dict[str, Any]] = []
        if isinstance(content, str):
            if content.strip():
                blocks.append({"type": "text", "text": content})
        elif isinstance(content, list):
            for part in content:
                if part.get("type") == "text" and part.get("text", "").strip():
                    blocks.append({"type": "text", "text": part["text"]})
                elif part.get("type") == "image_url":
                    img = _data_url_to_anthropic(part.get("image_url", {}).get("url", ""))
                    if img:
                        blocks.append(img)
        if role == "assistant":
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function", {})
                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id") or new_id("toolu_"),
                    "name": fn.get("name", ""),
                    "input": _parse_arguments(fn.get("arguments", "")),
                })
            push("assistant", blocks)
        else:
            push("user", blocks)

    if converted and converted[0]["role"] != "user":
        converted.insert(0, {"role": "user", "content": [{"type": "text", "text": "(conversation continues)"}]})
    # Anthropic requires tool_result blocks to come first inside a user turn
    for turn in converted:
        if turn["role"] == "user":
            turn["content"].sort(key=lambda b: 0 if b.get("type") == "tool_result" else 1)
    return "\n\n".join(p for p in system_parts if p), converted


def tools_to_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for t in tools:
        fn = t.get("function", t)
        out.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return out


# --------------------------------------------------------------------------- #
# Gateway
# --------------------------------------------------------------------------- #
class ProviderGateway:
    def __init__(self) -> None:
        self._clients: dict[tuple[str, str, str], Any] = {}

    # -- configuration ------------------------------------------------------------
    def base_url(self, provider: str) -> str | None:
        s = vault.settings()
        return {
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "openrouter": "https://openrouter.ai/api/v1",
            "openai": None,
            "xai": "https://api.x.ai/v1",
            "ollama": s["ollama_base_url"].rstrip("/") + "/v1",
            "vllm": s["vllm_base_url"].rstrip("/"),
            "lmstudio": s["lmstudio_base_url"].rstrip("/"),
        }.get(provider)

    def api_key(self, provider: str) -> str:
        if provider == "ollama":
            return "ollama"
        key = vault.get_key(provider)
        if not key and provider in ("vllm", "lmstudio"):
            return "local"
        return key

    def is_configured(self, provider: str) -> bool:
        return provider in LOCAL_PROVIDERS or bool(vault.get_key(provider))

    def model_for(self, provider: str) -> str:
        s = vault.settings()
        if provider == s["provider"] and s.get("model"):
            return s["model"]
        if provider == "ollama":
            return s.get("ollama_model") or DEFAULT_MODELS["ollama"]
        return DEFAULT_MODELS.get(provider, "")

    def _openai_client(self, provider: str):
        from openai import AsyncOpenAI

        key = self.api_key(provider)
        base = self.base_url(provider) or ""
        cache_key = (provider, key, base)
        if cache_key not in self._clients:
            headers = {}
            if provider == "openrouter":
                headers = {"HTTP-Referer": "http://localhost:3000", "X-Title": "OmniAgent OS"}
            timeout = httpx.Timeout(600.0 if provider in LOCAL_PROVIDERS else 180.0, connect=10.0)
            self._clients[cache_key] = AsyncOpenAI(
                api_key=key, base_url=base or None, default_headers=headers or None, timeout=timeout, max_retries=1
            )
        return self._clients[cache_key]

    def _anthropic_client(self):
        from anthropic import AsyncAnthropic

        key = self.api_key("anthropic")
        cache_key = ("anthropic", key, "")
        if cache_key not in self._clients:
            self._clients[cache_key] = AsyncAnthropic(api_key=key, timeout=httpx.Timeout(180.0, connect=10.0), max_retries=1)
        return self._clients[cache_key]

    # -- health ---------------------------------------------------------------------
    async def ollama_status(self) -> dict[str, Any]:
        base = vault.get("ollama_base_url", "http://127.0.0.1:11434").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                r = await client.get(f"{base}/api/tags")
                r.raise_for_status()
                models = [m.get("name", "") for m in r.json().get("models", [])]
                return {"online": True, "models": models, "base_url": base}
        except Exception as exc:  # noqa: BLE001
            return {"online": False, "models": [], "base_url": base, "error": str(exc)[:200]}

    async def internet_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.head("https://openrouter.ai")
            return True
        except Exception:  # noqa: BLE001
            return False

    # -- completion -------------------------------------------------------------------
    async def complete(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        on_delta: DeltaCallback = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AssistantTurn:
        if provider not in ALL_PROVIDERS:
            raise ProviderError(provider, f"Unknown provider '{provider}'.", fallback_ok=False)
        if not self.is_configured(provider):
            raise ProviderError(provider, "No API key configured. Add it in Settings.", fallback_ok=True)
        s = vault.settings()
        temperature = s["temperature"] if temperature is None else temperature
        max_tokens = s["max_output_tokens"] if max_tokens is None else max_tokens
        messages = copy.deepcopy(messages)
        try:
            if provider == "anthropic":
                return await self._complete_anthropic(model, messages, tools, on_delta, temperature, max_tokens)
            return await self._complete_openai(provider, model, messages, tools, on_delta, temperature, max_tokens)
        except ProviderError as exc:
            if _has_images(messages) and exc.status == 400 and re.search(r"image|vision|multimodal|content type", str(exc), re.I):
                log.info("Retrying %s/%s without images (model lacks vision).", provider, model)
                stripped = strip_images(messages)
                if provider == "anthropic":
                    return await self._complete_anthropic(model, stripped, tools, on_delta, temperature, max_tokens)
                return await self._complete_openai(provider, model, stripped, tools, on_delta, temperature, max_tokens)
            raise

    async def _complete_openai(self, provider, model, messages, tools, on_delta, temperature, max_tokens) -> AssistantTurn:
        import openai

        client = self._openai_client(provider)
        if not _has_images(messages):
            messages = _flatten_text_content(messages)
        kwargs: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
        reasoning_model = bool(re.match(r"^(o\d|openai/o\d)", model))
        if reasoning_model:
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens
            kwargs["temperature"] = temperature
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if provider in ("openai", "openrouter", "xai"):
            kwargs["stream_options"] = {"include_usage": True}

        content_parts: list[str] = []
        tool_acc: dict[int, dict[str, str]] = {}
        usage = TokenUsage()
        finish = ""
        try:
            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if getattr(chunk, "usage", None):
                    usage = TokenUsage(
                        prompt_tokens=chunk.usage.prompt_tokens or 0,
                        completion_tokens=chunk.usage.completion_tokens or 0,
                    )
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                if delta is not None:
                    if delta.content:
                        content_parts.append(delta.content)
                        if on_delta:
                            await on_delta(delta.content)
                    for tc in delta.tool_calls or []:
                        idx = tc.index if tc.index is not None else len(tool_acc)
                        slot = tool_acc.setdefault(idx, {"id": "", "name": "", "arguments": "", "extra_content": None})
                        if tc.id:
                            slot["id"] = tc.id
                        extra = getattr(tc, "extra_content", None)
                        if extra:
                            slot["extra_content"] = extra
                        if tc.function is not None:
                            if tc.function.name:
                                slot["name"] += tc.function.name
                            if tc.function.arguments:
                                slot["arguments"] += tc.function.arguments
                if choice.finish_reason:
                    finish = choice.finish_reason
        except openai.AuthenticationError as exc:
            raise ProviderError(provider, f"Authentication failed: {exc.message}", True, 401) from exc
        except openai.PermissionDeniedError as exc:
            raise ProviderError(provider, f"Permission denied: {exc.message}", True, 403) from exc
        except openai.RateLimitError as exc:
            raise ProviderError(provider, f"Rate limited / quota exceeded: {exc.message}", True, 429) from exc
        except openai.NotFoundError as exc:
            raise ProviderError(provider, f"Model or endpoint not found: {exc.message}", True, 404) from exc
        except openai.BadRequestError as exc:
            raise ProviderError(provider, f"Bad request: {exc.message}", False, 400) from exc
        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            raise ProviderError(provider, f"Connection failed: {exc}", True, None) from exc
        except openai.APIStatusError as exc:
            # 1. Gemini 503 high demand spike auto-retry with fallback model
            if provider == "gemini" and exc.status_code == 503:
                log.warning("Gemini 503 spike detected. Retrying with gemini-1.5-flash...")
                await asyncio.sleep(1.0)
                try:
                    return await self._complete_openai(provider, "gemini-1.5-flash", messages, tools, on_delta, temperature, max_tokens)
                except Exception as retry_exc:
                    log.warning("Gemini retry failed: %s", retry_exc)

            # 2. OpenRouter 402 credit threshold auto-downscale & free model fallback
            if provider == "openrouter" and exc.status_code == 402:
                afford_match = re.search(r"can only afford (\d+)", exc.message)
                if afford_match:
                    afford = int(afford_match.group(1))
                    if afford >= 120 and max_tokens > afford:
                        log.warning("OpenRouter 402: Auto-scaling max_tokens down to %d", afford - 15)
                        try:
                            return await self._complete_openai(provider, model, messages, tools, on_delta, temperature, afford - 15)
                        except Exception as retry_exc:
                            log.warning("OpenRouter token scale retry failed: %s", retry_exc)

                # Fallback to free zero-credit OpenRouter model
                free_model = "google/gemini-2.0-flash-exp:free"
                if model != free_model:
                    log.warning("OpenRouter 402: Falling back to free model %s...", free_model)
                    try:
                        return await self._complete_openai(provider, free_model, messages, tools, on_delta, temperature, 1024)
                    except Exception as free_exc:
                        log.warning("OpenRouter free fallback failed: %s", free_exc)

            can_fallback = exc.status_code >= 500 or exc.status_code in (402, 429)
            raise ProviderError(provider, f"HTTP {exc.status_code}: {exc.message}", can_fallback, exc.status_code) from exc

        tool_calls = []
        for idx in sorted(tool_acc):
            slot = tool_acc[idx]
            if not slot["name"]:
                continue
            tool_calls.append(
                ToolCall(
                    id=slot["id"] or new_id("call_"),
                    name=slot["name"],
                    arguments=_parse_arguments(slot["arguments"]),
                    extra_content=slot.get("extra_content")
                )
            )
        if usage.total == 0:
            prompt_chars = sum(len(json.dumps(m.get("content", ""))) for m in messages)
            usage = TokenUsage(prompt_tokens=prompt_chars // 4, completion_tokens=len("".join(content_parts)) // 4)
        return AssistantTurn(content="".join(content_parts), tool_calls=tool_calls, usage=usage,
                             provider=provider, model=model, finish_reason=finish)

    async def _complete_anthropic(self, model, messages, tools, on_delta, temperature, max_tokens) -> AssistantTurn:
        import anthropic

        client = self._anthropic_client()
        system, converted = to_anthropic(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": converted,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools_to_anthropic(tools)
        try:
            async with client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if event.type == "content_block_delta" and getattr(event.delta, "type", "") == "text_delta":
                        if on_delta:
                            await on_delta(event.delta.text)
                final = await stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise ProviderError("anthropic", f"Authentication failed: {exc.message}", True, 401) from exc
        except anthropic.PermissionDeniedError as exc:
            raise ProviderError("anthropic", f"Permission denied: {exc.message}", True, 403) from exc
        except anthropic.RateLimitError as exc:
            raise ProviderError("anthropic", f"Rate limited: {exc.message}", True, 429) from exc
        except anthropic.NotFoundError as exc:
            raise ProviderError("anthropic", f"Model not found: {exc.message}", True, 404) from exc
        except anthropic.BadRequestError as exc:
            raise ProviderError("anthropic", f"Bad request: {exc.message}", False, 400) from exc
        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
            raise ProviderError("anthropic", f"Connection failed: {exc}", True, None) from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError("anthropic", f"HTTP {exc.status_code}: {exc.message}", exc.status_code >= 500, exc.status_code) from exc

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in final.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input or {})))
        usage = TokenUsage(prompt_tokens=final.usage.input_tokens or 0, completion_tokens=final.usage.output_tokens or 0)
        return AssistantTurn(content="".join(text_parts), tool_calls=tool_calls, usage=usage,
                             provider="anthropic", model=model, finish_reason=final.stop_reason or "")


gateway = ProviderGateway()
