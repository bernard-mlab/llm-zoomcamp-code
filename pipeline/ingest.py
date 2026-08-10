"""Automated dlt ingestion: arXiv API -> chunk -> embed -> Qdrant upsert.

Phase 1. Run: `uv run python -m pipeline.ingest`.
"""
from __future__ import annotations

import sys
from collections.abc import Iterable

from qdrant_client import QdrantClient

from arxiv_agent.config import settings
from arxiv_agent.kb import ensure_collection, upsert_papers


def _get_real_embedders():
    from fastembed import TextEmbedding, SparseTextEmbedding

    dense = TextEmbedding(model_name=settings.embed_model)
    sparse = SparseTextEmbedding(model_name="prithivida/Splade_PP_en_v1")
    return dense, sparse


def main(
    client: QdrantClient | None = None,
    collection: str | None = None,
    papers: Iterable[dict] | None = None,
    dense_model=None,
    sparse_model=None,
    max_results: int | None = None,
) -> int:
    collection = collection or settings.qdrant_collection

    if client is None:
        client = QdrantClient(url=settings.qdrant_url)

    ensure_collection(client, collection)

    if dense_model is None or sparse_model is None:
        dense_model, sparse_model = _get_real_embedders()

    if papers is None:
        from pipeline.sources.arxiv import fetch_papers

        papers = fetch_papers(
            max_results=max_results or settings.arxiv_max_results,
            categories=settings.arxiv_categories,
        )

    count = upsert_papers(client, collection, papers, dense_model, sparse_model)
    print(f"ingested {count} papers into {collection}")
    return count


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count > 0 else 1)
