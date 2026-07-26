"""OpenAI-compatible LLM client pointed at the opencode-go proxy (model Hy3)."""
from __future__ import annotations

from typing import Any

from openai import OpenAI

from .config import settings


def get_client() -> OpenAI:
    if not settings.llm_configured:
        raise RuntimeError(
            "LLM not configured: set OPENCODE_GO_API_KEY and OPENCODE_GO_BASE_URL in .env"
        )
    return OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


def chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> Any:
    """Minimal chat wrapper. Returns the raw completion response.

    Tool-call support of Hy3 is detected at startup via capability_probe —
    do NOT assume native function-calling works here.
    """
    client = get_client()
    return client.chat.completions.create(
        model=model or settings.llm_model,
        messages=messages,
        tools=tools,
        **kwargs,
    )