"""Qdrant hybrid knowledge base (sparse SPLADE + dense bge vectors, RRF fusion).

Collection `arxiv_papers` with named vectors:
- `dense`: bge-small-en-v1.5 (384-d, cosine)
- `text-sparse`: SPLADE_PP_en_v1 (BM25-style sparse)

Implemented in Phase 1 (ingest/upsert) / Phase 2 (search variants + rerank).
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

NAMESPACE_UUID = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "text-sparse"
DEFAULT_DENSE_DIM = 384


def paper_text(paper: dict) -> str:
    return f"{paper['title']}\n{paper['summary']}\n{', '.join(paper.get('categories', []))}"


def ensure_collection(
    client: QdrantClient,
    collection: str,
    dense_dim: int = DEFAULT_DENSE_DIM,
) -> None:
    collections = {c.name for c in client.get_collections().collections}
    if collection in collections:
        return

    client.create_collection(
        collection_name=collection,
        vectors_config={
            DENSE_VECTOR_NAME: VectorParams(size=dense_dim, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: SparseVectorParams(index=SparseIndexParams()),
        },
    )


def _arxiv_id_to_uuid(arxiv_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE_UUID, arxiv_id))


def _build_point(paper: dict, dense_vec, sparse_vec) -> PointStruct:
    return PointStruct(
        id=_arxiv_id_to_uuid(paper["arxiv_id"]),
        vector={
            DENSE_VECTOR_NAME: dense_vec.tolist() if hasattr(dense_vec, "tolist") else list(dense_vec),
            SPARSE_VECTOR_NAME: SparseVector(
                indices=sparse_vec.indices.tolist() if hasattr(sparse_vec.indices, "tolist") else list(sparse_vec.indices),
                values=sparse_vec.values.tolist() if hasattr(sparse_vec.values, "tolist") else list(sparse_vec.values),
            ),
        },
        payload={
            "arxiv_id": paper["arxiv_id"],
            "title": paper["title"],
            "authors": paper["authors"],
            "summary": paper["summary"],
            "published": paper["published"],
            "categories": paper["categories"],
            "primary_category": paper["primary_category"],
        },
    )


def upsert_papers(
    client: QdrantClient,
    collection: str,
    papers: Iterable[dict],
    dense_model,
    sparse_model,
    batch_size: int = 64,
) -> int:
    papers = list(papers)
    total = 0

    for i in range(0, len(papers), batch_size):
        batch = papers[i : i + batch_size]
        texts = [paper_text(p) for p in batch]

        dense_vecs = list(dense_model.embed(texts))
        sparse_vecs = list(sparse_model.embed(texts))

        points = [
            _build_point(paper, dv, sv)
            for paper, dv, sv in zip(batch, dense_vecs, sparse_vecs, strict=True)
        ]

        client.upsert(collection_name=collection, points=points)
        total += len(points)

    return total