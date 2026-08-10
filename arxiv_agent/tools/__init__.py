"""Agent tool registry. Phase 3. See spec §5."""
from __future__ import annotations

from .fetch import FETCH_TOOL_SCHEMA, fetch_arxiv
from .rewrite import rewrite_query
from .search import SEARCH_TOOL_SCHEMA, search_papers

REWRITE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "rewrite_query",
        "description": "Rewrite a search query into alternative phrasings and keywords to improve retrieval. Returns a list of search queries.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The original query to rewrite.",
                },
            },
            "required": ["query"],
        },
    },
}

TOOL_REGISTRY = {
    "search_papers": search_papers,
    "fetch_arxiv": fetch_arxiv,
    "rewrite_query": rewrite_query,
}

TOOL_DEFS = [
    SEARCH_TOOL_SCHEMA,
    FETCH_TOOL_SCHEMA,
    REWRITE_TOOL_SCHEMA,
]