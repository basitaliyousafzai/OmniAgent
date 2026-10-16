"""
OmniAgent OS - Shared state schemas (Pydantic v2).

These models describe the data exchanged between the agent core, the safety
fabric, the REST API and the WebSocket event bus.
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class RiskLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"].index(self.value)

    @classmethod
    def max(cls, *levels: "RiskLevel") -> "RiskLevel":
        best = cls.NONE
        for lvl in levels:
            if lvl.rank > best.rank:
                best = lvl
        return best


class GuardrailMatch(BaseModel):
    rule_id: str
    category: Literal["filesystem", "disk", "registry", "network", "process", "sql", "security", "path", "system"]
    level: RiskLevel
    description: str
    snippet: str = ""


class RiskAssessment(BaseModel):
    level: RiskLevel = RiskLevel.NONE
    matches: list[GuardrailMatch] = Field(default_factory=list)
    blocked: bool = False  # True => never executable, even with approval
    block_reason: str = ""

    @property
    def requires_approval(self) -> bool:
        return self.level.rank >= RiskLevel.MEDIUM.rank

    def summary(self) -> str:
        if not self.matches:
            return "No dangerous patterns detected."
        return "; ".join(f"[{m.level.value}] {m.description}" for m in self.matches)


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    extra_content: Optional[dict[str, Any]] = None


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class AssistantTurn(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""
    finish_reason: str = ""


class ApprovalRequest(BaseModel):
    id: str = Field(default_factory=lambda: new_id("apr_"))
    session_id: str
    tool_name: str
    action_description: str
    exact_command_or_query: str
    risk_level: RiskLevel
    reasons: list[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    timeout_seconds: int = 300


class ApprovalDecision(BaseModel):
    id: str
    approved: bool
    decided_by: Literal["user", "timeout", "kill_switch", "system"] = "user"
    note: str = ""


class ToolResult(BaseModel):
    tool_call_id: str
    name: str
    ok: bool
    output: str
    image_b64: Optional[str] = None
    image_mime: str = "image/jpeg"
    screenshot_file: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ProviderSettings(BaseModel):
    provider: str
    model: str
    fallback_chain: list[str]
    ollama_base_url: str
    ollama_model: str
    vllm_base_url: str
    lmstudio_base_url: str
    temperature: float
    max_output_tokens: int
    context_token_budget: int
    max_images_in_context: int
    screenshot_max_width: int
    screenshot_jpeg_quality: int
    whisper_model: str
    tts_enabled: bool
    tts_rate: int
    auto_screenshot_after_gui_action: bool
    gui_action_delay: float


class SettingsUpdate(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)
    api_keys: dict[str, str] = Field(default_factory=dict)


class FileWriteRequest(BaseModel):
    path: str
    content: str


class TTSRequest(BaseModel):
    text: str


class FocusRequest(BaseModel):
    target: str


class WSEvent(BaseModel):
    type: str
    session_id: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    ts: float = Field(default_factory=time.time)
