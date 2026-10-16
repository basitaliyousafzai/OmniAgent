"""Master Module 2: Multi-Provider Model Gateway."""
from gateway.vault import vault
from gateway.provider_gateway import gateway, ProviderError, ALL_PROVIDERS, PROVIDER_LABELS, DEFAULT_MODELS, estimate_cost
from gateway.fallback_router import fallback_router
from gateway.context_trimmer import trim_context, total_tokens

__all__ = [
    "vault", "gateway", "ProviderError", "ALL_PROVIDERS", "PROVIDER_LABELS", "DEFAULT_MODELS",
    "estimate_cost", "fallback_router", "trim_context", "total_tokens",
]
