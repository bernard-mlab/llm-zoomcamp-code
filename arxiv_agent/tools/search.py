"""Tool: search_papers(query, mode) -> top-k arxiv docs from Qdrant. Phase 3."""
from __future__ import annotations

# mode in {keyword, vector, hybrid, hybrid_rerank}. Calls arxiv_agent.kb.search.