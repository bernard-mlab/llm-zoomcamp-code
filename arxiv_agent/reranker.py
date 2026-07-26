"""Cross-encoder reranker (fastembed Xenova/ms-marco-MiniLM-L-6-v2). Phase 2."""
from __future__ import annotations

# rerank(query, docs, top_k) -> top_k docs by cross-encoder score.
# Used by kb.search(mode="hybrid_rerank"). See spec §4.