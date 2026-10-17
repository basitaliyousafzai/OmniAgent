"""Master Module 3: Agentic Reasoning & Prompting Engine."""
from agent.system_prompt import MASTER_SYSTEM_PROMPT, build_system_prompt
from agent.tool_registry import MASTER_TOOLS
from agent.workspace_indexer import index_workspace
from agent.patcher import apply_patch
from agent.orchestrator import orchestrator, AgentOrchestrator
from agent.self_learner import self_learner, SelfLearner

__all__ = [
    "MASTER_SYSTEM_PROMPT", "build_system_prompt", "MASTER_TOOLS",
    "index_workspace", "apply_patch", "orchestrator", "AgentOrchestrator",
    "self_learner", "SelfLearner"
]
