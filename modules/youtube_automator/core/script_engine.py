"""
Module 4: Multi-Modal LLM Script & Prompt Architect (core/script_engine.py).

Submodule 4.1 — Multi-Provider Free LLM Router (Gemini, OpenRouter, Ollama).
Submodule 4.2 — Solo & Podcast Dialogue Generator.
Submodule 4.3 — Scene Visual Mapper (video/image interleaved prompts).
Submodule 4.4 — Strict JSON Schema Validator with 3-attempt self-healing.
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

import httpx

log = logging.getLogger("youtube.script_engine")

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "youtube_config.json"

# ------------------------------------------------------------------ #
# Expected JSON output schema from the LLM
# ------------------------------------------------------------------ #
EXPECTED_KEYS = {"mode", "title", "description", "tags", "dialogue", "visual_prompts"}


def _load_config() -> dict[str, Any]:
    """Load the YouTube config from disk."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ------------------------------------------------------------------ #
# Submodule 4.1 — Multi-Provider Free LLM Router
# ------------------------------------------------------------------ #

async def _call_gemini(prompt: str, api_key: str) -> str:
    """Call Google Gemini Free Tier (gemini-2.0-flash or gemini-2.5-flash)."""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json"
        }
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{url}?key={api_key}",
            json=payload,
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
    return ""


async def _call_openrouter(prompt: str, api_key: str) -> str:
    """Call OpenRouter free-tier model."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/basitaliyousafzai/OmniAgent",
    }
    payload = {
        "model": "meta-llama/llama-3.2-3b-instruct:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 2048,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
    return ""


async def _call_ollama(prompt: str, model: str = "llama3.2:1b") -> str:
    """Call a local Ollama instance."""
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.9, "num_predict": 2048}
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")


async def _route_llm(prompt: str, config: dict[str, Any]) -> str:
    """Route the prompt to the configured LLM provider."""
    provider = config.get("llm_provider", "gemini")
    if provider == "gemini":
        api_key = config.get("gemini_api_key", "")
        if api_key:
            return await _call_gemini(prompt, api_key)
    if provider == "openrouter" or (provider == "gemini" and not config.get("gemini_api_key")):
        api_key = config.get("openrouter_api_key", "")
        if api_key:
            return await _call_openrouter(prompt, api_key)
    # Fallback to local Ollama
    model = config.get("ollama_model", "llama3.2:1b")
    return await _call_ollama(prompt, model)


# ------------------------------------------------------------------ #
# Submodule 4.2 & 4.3 — Prompt Construction
# ------------------------------------------------------------------ #

def _build_prompt(niche: str, mode: str, past_topics: list[dict[str, Any]]) -> str:
    """Build the master LLM prompt for script generation."""
    past_titles = [t.get("title", "") for t in past_topics if t.get("title")]
    past_block = ""
    if past_titles:
        past_block = (
            "\n\nABSOLUTELY DO NOT repeat or rephrase any of these previously used topics:\n"
            + "\n".join(f"- {t}" for t in past_titles[:30])
        )

    if mode == "podcast":
        dialogue_instruction = (
            "Create a 2-person podcast dialogue (80-95 words total) with exactly these speakers:\n"
            "  - 'Host' (voice: en-US-ChristopherNeural): Asks sharp, provocative questions.\n"
            "  - 'Expert' (voice: en-US-JennyNeural): Delivers counter-intuitive, fascinating insights.\n"
            "Format each dialogue entry as: {\"speaker\": \"Host\" or \"Expert\", \"text\": \"...\"}\n"
            "The dialogue array must have 4-6 turns alternating between Host and Expert."
        )
    else:
        dialogue_instruction = (
            "Create a solo fast-paced authoritative monologue (80-95 words total) by 'Narrator' "
            "(voice: en-US-ChristopherNeural).\n"
            "Format as a single entry: {\"speaker\": \"Narrator\", \"text\": \"...\"}\n"
            "The dialogue array must have exactly 1 entry."
        )

    prompt = f"""You are an elite YouTube Shorts scriptwriter specializing in the "{niche}" niche.

CRITICAL RULES:
1. NEVER start with "Did you know", "Welcome back", "In this video", or any generic YouTube opener.
2. Open with a PATTERN-INTERRUPT HOOK in the first sentence — a shocking fact, bold claim, or provocative question that grabs attention in 1.5 seconds.
3. The script must be punchy, surprising, and impossible to scroll past.
4. Total word count MUST be between 80 and 95 words.
{past_block}

PRODUCTION MODE: {mode}

{dialogue_instruction}

VISUAL SCENES:
Generate exactly 4 to 5 visual scene cues. Each must have:
  - "type": either "video" (portrait 9:16 b-roll footage) or "image" (high-res portrait photo for Ken Burns motion)
  - "query": a concrete 2-3 word Pexels search query (e.g., "ocean waves", "city skyline night")
Alternate between "video" and "image" types.

OUTPUT FORMAT — Return ONLY valid JSON with this exact structure:
{{
  "mode": "{mode}",
  "title": "An attention-grabbing YouTube title (max 70 chars)",
  "description": "A compelling YouTube description with relevant keywords (max 200 chars)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "dialogue": [
    {{"speaker": "...", "text": "..."}}
  ],
  "visual_prompts": [
    {{"type": "video", "query": "..."}},
    {{"type": "image", "query": "..."}}
  ]
}}

Return ONLY the JSON object. No markdown, no code fences, no explanation."""

    return prompt


# ------------------------------------------------------------------ #
# Submodule 4.4 — Strict JSON Schema Validator
# ------------------------------------------------------------------ #

def _extract_json(raw: str) -> Optional[dict[str, Any]]:
    """Extract and validate JSON from raw LLM output with self-healing."""
    # Strip markdown code fences if present
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Try direct parse
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Try to find JSON object with regex
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _validate_script(data: dict[str, Any]) -> tuple[bool, str]:
    """Validate the script JSON has all required fields and correct structure."""
    missing = EXPECTED_KEYS - set(data.keys())
    if missing:
        return False, f"Missing keys: {missing}"

    if not isinstance(data.get("dialogue"), list) or len(data["dialogue"]) == 0:
        return False, "dialogue must be a non-empty list"

    for i, entry in enumerate(data["dialogue"]):
        if not isinstance(entry, dict):
            return False, f"dialogue[{i}] is not a dict"
        if "speaker" not in entry or "text" not in entry:
            return False, f"dialogue[{i}] missing speaker or text"

    if not isinstance(data.get("visual_prompts"), list) or len(data["visual_prompts"]) < 4:
        return False, "visual_prompts must have at least 4 entries"

    for i, vp in enumerate(data["visual_prompts"]):
        if not isinstance(vp, dict):
            return False, f"visual_prompts[{i}] is not a dict"
        if vp.get("type") not in ("video", "image"):
            return False, f"visual_prompts[{i}].type must be 'video' or 'image'"
        if not vp.get("query"):
            return False, f"visual_prompts[{i}].query is empty"

    if not isinstance(data.get("tags"), list):
        return False, "tags must be a list"

    if not data.get("title"):
        return False, "title is empty"

    return True, "OK"


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

async def generate_script(past_topics: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    """
    Generate a complete YouTube script using the configured LLM.

    Returns a validated dict with keys: mode, title, description, tags,
    dialogue, visual_prompts.

    Raises ValueError if the LLM fails to produce valid output after 3 attempts.
    """
    config = _load_config()
    niche = config.get("niche", "science and technology")
    mode = config.get("production_mode", "solo")
    topics = past_topics or []
    prompt = _build_prompt(niche, mode, topics)

    last_error = "No attempts made"

    for attempt in range(1, 4):
        log.info("Script generation attempt %d/3 (mode=%s, niche=%s)", attempt, mode, niche)
        try:
            raw = await _route_llm(prompt, config)
            if not raw.strip():
                last_error = "LLM returned empty response"
                log.warning("Attempt %d: empty LLM response", attempt)
                continue

            data = _extract_json(raw)
            if data is None:
                last_error = "Failed to parse JSON from LLM output"
                log.warning("Attempt %d: JSON parse failed. Raw (first 500): %s", attempt, raw[:500])
                continue

            valid, reason = _validate_script(data)
            if not valid:
                last_error = f"Schema validation failed: {reason}"
                log.warning("Attempt %d: validation failed — %s", attempt, reason)
                continue

            # Ensure mode matches config
            data["mode"] = mode
            log.info("Script generated successfully: %s", data.get("title", ""))
            return data

        except httpx.HTTPStatusError as exc:
            last_error = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            log.warning("Attempt %d: HTTP error — %s", attempt, last_error)
        except Exception as exc:
            last_error = str(exc)
            log.warning("Attempt %d: unexpected error — %s", attempt, last_error)

        if attempt < 3:
            time.sleep(2)

    raise ValueError(f"Script generation failed after 3 attempts. Last error: {last_error}")


class LLMProviderRouter:
    """Class wrapper for multi-provider LLM routing."""
    def __init__(self, provider: str = "gemini", gemini_api_key: str = "", openrouter_api_key: str = "", ollama_model: str = "llama3.2:1b"):
        self.provider = provider
        self.gemini_api_key = gemini_api_key
        self.openrouter_api_key = openrouter_api_key
        self.ollama_model = ollama_model

    def generate(self, prompt: str) -> str:
        import asyncio
        config = {
            "llm_provider": self.provider,
            "gemini_api_key": self.gemini_api_key,
            "openrouter_api_key": self.openrouter_api_key,
            "ollama_model": self.ollama_model
        }
        return asyncio.run(_route_llm(prompt, config))


class ScriptEngine:
    """Class wrapper for script generation."""
    def __init__(self, llm_provider: str = "gemini", gemini_api_key: Optional[str] = None, openrouter_api_key: Optional[str] = None, ollama_model: str = "llama3.2:1b"):
        self.llm_provider = llm_provider
        self.gemini_api_key = gemini_api_key or ""
        self.openrouter_api_key = openrouter_api_key or ""
        self.ollama_model = ollama_model

    async def generate_script(self, niche: str, mode: str = "solo", topic: Optional[str] = None, past_topics: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
        config = {
            "niche": niche,
            "production_mode": mode,
            "llm_provider": self.llm_provider,
            "gemini_api_key": self.gemini_api_key,
            "openrouter_api_key": self.openrouter_api_key,
            "ollama_model": self.ollama_model
        }
        topics = past_topics or []
        prompt = _build_prompt(niche, mode, topics)
        if topic:
            prompt += f"\n\nSPECIFIC TOPIC REQUIREMENT: Focus the script specifically on: {topic}"

        for attempt in range(1, 4):
            try:
                raw = await _route_llm(prompt, config)
                if not raw.strip():
                    continue
                data = _extract_json(raw)
                if data is None:
                    continue
                valid, reason = _validate_script(data)
                if not valid:
                    continue
                data["mode"] = mode
                return data
            except Exception as e:
                log.warning("Attempt %d failed: %s", attempt, e)
                time.sleep(1)

        # Resilient fallback script template if offline / rate limited
        return {
            "mode": mode,
            "title": f"The {niche} Paradox That Changes Everything",
            "description": f"Discover the shocking truth behind {niche} and what industry experts are hiding from the public.\n\n#shorts #technology #future",
            "tags": [niche.lower(), "shorts", "technology", "breakthrough", "mindblowing"],
            "dialogue": [
                {"speaker": "Host" if mode == "podcast" else "Narrator", "text": f"Everything you think you know about {niche} is completely backwards."},
                {"speaker": "Expert" if mode == "podcast" else "Narrator", "text": "Top researchers just proved that the traditional model breaks down under real-world conditions."},
                {"speaker": "Host" if mode == "podcast" else "Narrator", "text": "Wait, so the systems we rely on every single day are already obsolete?"},
                {"speaker": "Expert" if mode == "podcast" else "Narrator", "text": "Exactly. And the replacement is accelerating faster than anyone predicted."}
            ],
            "visual_prompts": [
                {"type": "video", "query": f"{niche} technology high tech futuristic"},
                {"type": "image", "query": "artificial intelligence circuit brain network"},
                {"type": "video", "query": "modern server room glowing data lights"},
                {"type": "image", "query": "futuristic digital interface holographic neon"}
            ]
        }

