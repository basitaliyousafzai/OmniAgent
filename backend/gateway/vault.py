"""
Sub-Module 2.4: Local Secret Vault.

API keys live exclusively in ./.env.local inside the project folder. Non-secret
runtime settings (provider, model, voice options ...) are persisted as JSON in
./.omniagent_data/settings.json.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any

from dotenv import dotenv_values

from config import DEFAULT_SETTINGS, ENV_FILE, SETTINGS_FILE

# Provider id -> environment variable holding its API key
KEY_NAMES: dict[str, str] = {
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
    "vllm": "VLLM_API_KEY",
    "lmstudio": "LMSTUDIO_API_KEY",
}


class Vault:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._secrets: dict[str, str] = {}
        self._settings: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.reload()

    # -- persistence -------------------------------------------------------------
    def reload(self) -> None:
        with self._lock:
            self._secrets = {}
            if ENV_FILE.exists():
                for k, v in dotenv_values(ENV_FILE).items():
                    if v is not None:
                        self._secrets[k] = v
            # Process environment can supply keys too (never written back to disk)
            for env_name in KEY_NAMES.values():
                if env_name not in self._secrets and os.environ.get(env_name):
                    self._secrets[env_name] = os.environ[env_name]
            self._settings = dict(DEFAULT_SETTINGS)
            if SETTINGS_FILE.exists():
                try:
                    stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                    if isinstance(stored, dict):
                        for k, v in stored.items():
                            if k in DEFAULT_SETTINGS:
                                self._settings[k] = v
                except (json.JSONDecodeError, OSError):
                    pass

    def _write_env(self) -> None:
        lines = [
            "# OmniAgent OS local secret vault - stays inside this project folder.",
            "# Delete this file (or run UNINSTALL_AND_CLEANUP.bat) to erase stored keys.",
        ]
        for k in sorted(self._secrets):
            v = self._secrets[k].replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k}="{v}"')
        tmp = ENV_FILE.with_suffix(".tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, ENV_FILE)

    def _write_settings(self) -> None:
        tmp = SETTINGS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")
        os.replace(tmp, SETTINGS_FILE)

    # -- secrets -------------------------------------------------------------------
    def get_key(self, provider: str) -> str:
        env_name = KEY_NAMES.get(provider, "")
        with self._lock:
            return self._secrets.get(env_name, "") if env_name else ""

    def set_keys(self, keys: dict[str, str]) -> None:
        with self._lock:
            for provider, value in keys.items():
                env_name = KEY_NAMES.get(provider)
                if not env_name:
                    continue
                value = (value or "").strip()
                if value == "":
                    self._secrets.pop(env_name, None)
                elif "•" in value or value.startswith("****"):
                    continue  # masked value echoed back by the UI - unchanged
                else:
                    self._secrets[env_name] = value
            self._write_env()

    def key_status(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        with self._lock:
            for provider, env_name in KEY_NAMES.items():
                v = self._secrets.get(env_name, "")
                out[provider] = {"configured": bool(v), "masked": self.mask(v)}
        return out

    @staticmethod
    def mask(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "••••"
        return f"{value[:4]}••••{value[-4:]}"

    # -- settings ------------------------------------------------------------------
    def settings(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._settings)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._settings.get(key, default)

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            for k, v in updates.items():
                if k not in DEFAULT_SETTINGS:
                    continue
                default = DEFAULT_SETTINGS[k]
                try:
                    if isinstance(default, bool):
                        v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on")
                    elif isinstance(default, int):
                        v = int(v)
                    elif isinstance(default, float):
                        v = float(v)
                    elif isinstance(default, list):
                        v = [str(x) for x in v] if isinstance(v, list) else [s.strip() for s in str(v).split(",") if s.strip()]
                    else:
                        v = str(v)
                except (TypeError, ValueError):
                    continue
                self._settings[k] = v
            self._write_settings()
            return dict(self._settings)


vault = Vault()
