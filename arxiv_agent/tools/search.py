"""Tool: search_papers(query, mode) -> top-k arxiv docs from Qdrant. Phase 3."""
from __future__ import annotations

from qdrant_client import QdrantClient

from arxiv_agent.config import settings
from arxiv_agent.kb import search

SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_papers",
        "description": "Search arXiv papers by query. Returns relevant papers with arxiv_id, title, summary, and score.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query — keywords or a natural language question.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["keyword", "vector", "hybrid", "hybrid_rerank"],
                    "description": "Retrieval mode. Use 'hybrid_rerank' for best results.",
                    "default": "hybrid_rerank",
                },
            },
            "required": ["query"],
        },
    },
}


def search_papers(query: str, mode: str = "hybrid_rerank") -> list[dict]:
    client = QdrantClient(url=settings.qdrant_url)

    from fastembed import TextEmbedding, SparseTextEmbedding

    dense_model = TextEmbedding(model_name=settings.embed_model)
    sparse_model = SparseTextEmbedding(model_name="prithivida/Splade_PP_en_v1")

    results = search(
        client,
        settings.qdrant_collection,
        query=query,
        mode=mode,
        dense_model=dense_model,
        sparse_model=sparse_model,
        limit=5,
    )
    return [
        {
            "arxiv_id": r["arxiv_id"],
            "title": r["title"],
            "summary": r["summary"][:300],
            "score": r.get("score", 0),
        }
        for r in results
    ]