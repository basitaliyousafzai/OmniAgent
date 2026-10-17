"""
OmniAgent OS - Central configuration.

Every path used by the backend is derived from PROJECT_ROOT so that all runtime
artifacts (caches, model weights, screenshots, logs, settings) stay strictly
inside the project folder. Importing this module also redirects third-party
cache locations (HuggingFace, Torch, XDG) into the project before any heavy
library is imported.
"""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

BACKEND_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = BACKEND_DIR.parent

# The workspace the agent is allowed to read/write. Defaults to the project root
# but can be pointed to any sub-folder through OMNIAGENT_WORKSPACE.
_ws_override = os.environ.get("OMNIAGENT_WORKSPACE", "").strip()
WORKSPACE_ROOT: Path = (Path(_ws_override).resolve() if _ws_override else PROJECT_ROOT)

DATA_DIR: Path = PROJECT_ROOT / ".omniagent_data"
SCREENSHOT_DIR: Path = DATA_DIR / "screenshots"
AUDIO_TMP_DIR: Path = DATA_DIR / "audio_tmp"
LOG_DIR: Path = DATA_DIR / "logs"
SETTINGS_FILE: Path = DATA_DIR / "settings.json"
CACHE_DIR: Path = PROJECT_ROOT / ".cache"
MODEL_CACHE_DIR: Path = CACHE_DIR / "models"
WHISPER_CACHE_DIR: Path = MODEL_CACHE_DIR / "whisper"
ENV_FILE: Path = PROJECT_ROOT / ".env.local"
AUDIT_LOG_FILE: Path = PROJECT_ROOT / "workspace_audit.log"

for _d in (DATA_DIR, SCREENSHOT_DIR, AUDIO_TMP_DIR, LOG_DIR, CACHE_DIR, MODEL_CACHE_DIR, WHISPER_CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Redirect third-party caches into the project (zero-pollution contract).
os.environ.setdefault("HF_HOME", str(CACHE_DIR / "huggingface"))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(CACHE_DIR / "huggingface" / "hub"))
os.environ.setdefault("TORCH_HOME", str(CACHE_DIR / "torch"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("PYTHONPYCACHEPREFIX", str(CACHE_DIR / "pycache"))

IS_WINDOWS: bool = sys.platform.startswith("win")
IS_MAC: bool = sys.platform == "darwin"
IS_LINUX: bool = sys.platform.startswith("linux")
OS_NAME: str = f"{platform.system()} {platform.release()}"

BACKEND_HOST: str = os.environ.get("OMNIAGENT_HOST", "127.0.0.1")
BACKEND_PORT: int = int(os.environ.get("OMNIAGENT_PORT", "8000"))
FRONTEND_PORT: int = int(os.environ.get("OMNIAGENT_FRONTEND_PORT", "3000"))

# Agent loop limits
MAX_AGENT_STEPS: int = int(os.environ.get("OMNIAGENT_MAX_STEPS", "40"))
APPROVAL_TIMEOUT_SECONDS: int = int(os.environ.get("OMNIAGENT_APPROVAL_TIMEOUT", "300"))
SHELL_TIMEOUT_SECONDS: int = int(os.environ.get("OMNIAGENT_SHELL_TIMEOUT", "120"))
MAX_TOOL_OUTPUT_CHARS: int = 12_000
MAX_READ_FILE_BYTES: int = 2_000_000
MAX_SCREENSHOTS_KEPT: int = 60

# Directories never indexed / listed by the agent tooling.
IGNORED_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git", ".venv", "venv", "node_modules", "__pycache__", ".cache", ".runtime",
        ".omniagent_data", "dist", "build", ".vite", ".idea", ".vs", ".mypy_cache",
        ".pytest_cache", ".ruff_cache", "bin", "obj",
    }
)

DEFAULT_SETTINGS: dict = {
    "provider": "gemini",
    "model": "gemini-3.1-flash-lite",
    "fallback_chain": ["gemini", "openrouter", "anthropic", "openai", "xai", "ollama"],
    "ollama_base_url": "http://127.0.0.1:11434",
    "ollama_model": "llama3.1",
    "vllm_base_url": "http://127.0.0.1:8001/v1",
    "lmstudio_base_url": "http://127.0.0.1:1234/v1",
    "temperature": 0.2,
    "max_output_tokens": 4096,
    "context_token_budget": 60000,
    "max_images_in_context": 2,
    "screenshot_max_width": 1366,
    "screenshot_jpeg_quality": 70,
    "whisper_model": "base",
    "tts_enabled": False,
    "tts_rate": 185,
    "auto_screenshot_after_gui_action": True,
    "gui_action_delay": 0.6,
}
