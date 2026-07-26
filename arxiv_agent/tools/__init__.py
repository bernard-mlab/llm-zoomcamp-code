"""Agent tool registry. Phase 3. See spec §5."""
from __future__ import annotations

from . import fetch, rewrite, search

# registry: name -> (callable, json_schema)
# Phase 3: build TOOL_REGISTRY and tool definitions sent to the LLM.