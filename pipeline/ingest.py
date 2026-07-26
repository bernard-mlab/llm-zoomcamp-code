"""Automated dlt ingestion: arXiv API -> chunk -> embed -> Qdrant upsert.

Phase 1. Run: `uv run python -m pipeline.ingest`.
"""
from __future__ import annotations

from arxiv_agent.config import settings


def main() -> None:
    # Phase 1: build the dlt pipeline over arxiv_source, embed each paper
    # (title + summary + categories) with fastembed, and upsert into Qdrant
    # collection `arxiv_papers` with dense + sparse vectors.
    print(f"ingest target: {settings.qdrant_url} collection={settings.qdrant_collection}")
    raise NotImplementedError("Phase 1")


if __name__ == "__main__":
    main()