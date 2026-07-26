"""Qdrant hybrid knowledge base (sparse BM25 + dense bge vectors, RRF fusion).

Implemented in Phase 1 (ingest) / Phase 2 (retrieval + rerank eval).
"""
from __future__ import annotations

# Phase 1/2: create collection with sparse + dense, upsert, and search variants
# (keyword / vector / hybrid / hybrid_rerank). See spec §4.