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
    Fusion,
    FusionQuery,
    PointStruct,
    Prefetch,
    QueryResponse,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

NAMESPACE_UUID = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "text-sparse"
DEFAULT_DENSE_DIM = 384

VALID_MODES = {"keyword", "vector", "hybrid", "hybrid_rerank"}


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

def _query_to_dense_vec(query: str, dense_model) -> list[float]:
    return list(dense_model.embed([query]))[0].tolist()


def _query_to_sparse_vec(query: str, sparse_model) -> SparseVector:
    sv = list(sparse_model.embed([query]))[0]
    return SparseVector(
        indices=sv.indices.tolist() if hasattr(sv.indices, "tolist") else list(sv.indices),
        values=sv.values.tolist() if hasattr(sv.values, "tolist") else list(sv.values),
    )


def _points_to_dicts(response, limit: int) -> list[dict]:
    results = []
    for i, point in enumerate(response.points[:limit]):
        payload = point.payload or {}
        results.append(
            {
                "arxiv_id": payload.get("arxiv_id", ""),
                "title": payload.get("title", ""),
                "authors": payload.get("authors", []),
                "summary": payload.get("summary", ""),
                "published": payload.get("published", ""),
                "categories": payload.get("categories", []),
                "primary_category": payload.get("primary_category", ""),
                "score": point.score,
            }
        )
    return results


def search(
    client: QdrantClient,
    collection: str,
    query: str,
    mode: str = "hybrid",
    dense_model=None,
    sparse_model=None,
    limit: int = 5,
) -> list[dict]:
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {VALID_MODES}, got {mode!r}")

    if mode == "keyword":
        sv = _query_to_sparse_vec(query, sparse_model)
        response = client.query_points(
            collection_name=collection,
            query=sv,
            using=SPARSE_VECTOR_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return _points_to_dicts(response, limit)

    if mode == "vector":
        dv = _query_to_dense_vec(query, dense_model)
        response = client.query_points(
            collection_name=collection,
            query=dv,
            using=DENSE_VECTOR_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return _points_to_dicts(response, limit)

    if mode in ("hybrid", "hybrid_rerank"):
        fetch_limit = limit * 4 if mode == "hybrid_rerank" else limit
        dv = _query_to_dense_vec(query, dense_model)
        sv = _query_to_sparse_vec(query, sparse_model)

        response = client.query_points(
            collection_name=collection,
            prefetch=[
                Prefetch(query=dv, using=DENSE_VECTOR_NAME, limit=fetch_limit),
                Prefetch(query=sv, using=SPARSE_VECTOR_NAME, limit=fetch_limit),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=fetch_limit if mode == "hybrid_rerank" else limit,
            with_payload=True,
            with_vectors=False,
        )
        results = _points_to_dicts(response, fetch_limit if mode == "hybrid_rerank" else limit)

        if mode == "hybrid":
            return results

        from arxiv_agent.reranker import Reranker

        reranker = Reranker()
        return reranker.rerank(query, results, top_k=limit)
