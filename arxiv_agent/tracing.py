"""Langfuse tracing helpers. Phase 6.

Every user turn = a Langfuse trace; child spans per agent iteration,
search/llm/fetch call. See spec §8 and AGENTS.md.
"""
from __future__ import annotations

# Phase 6: wrap agent/search/llm in langfuse spans; expose score() for thumbs.