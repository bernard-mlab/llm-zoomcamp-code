import numpy as np
import pytest
from qdrant_client import QdrantClient

from arxiv_agent.kb import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    ensure_collection,
    upsert_papers,
    search,
    paper_text,
)
from arxiv_agent.reranker import Reranker

COLLECTION = "test_search"
DENSE_DIM = 4


class _FakeSparse:
    def __init__(self, indices, values):
        self.indices = indices
        self.values = values


class FakeDenseModel:
    def embed(self, texts, **kwargs):
        for i, t in enumerate(texts):
            vec = np.zeros(DENSE_DIM, dtype=np.float32)
            vec[0] = (i + 1) / 10.0
            vec[1] = (len(t) % 5) / 5.0
            yield vec


class FakeSparseModel:
    def embed(self, texts, **kwargs):
        for i, t in enumerate(texts):
            indices = np.array([i * 3, i * 3 + 1, i * 3 + 2], dtype=np.int64)
            values = np.array([1.0, 0.5, 0.3], dtype=np.float32)
            yield _FakeSparse(indices, values)


def _fake_papers():
    return [
        {
            "arxiv_id": "2401.00001",
            "title": "Retrieval-Augmented Generation for NLP",
            "authors": ["Jane"],
            "summary": "A paper about RAG systems for knowledge-intensive tasks.",
            "published": "2024-01-01T00:00:00Z",
            "categories": ["cs.AI", "cs.CL"],
            "primary_category": "cs.AI",
        },
        {
            "arxiv_id": "2401.00002",
            "title": "Mixture of Experts at Scale",
            "authors": ["John"],
            "summary": "Scaling transformers with sparse MoE layers.",
            "published": "2024-01-02T00:00:00Z",
            "categories": ["cs.LG"],
            "primary_category": "cs.LG",
        },
        {
            "arxiv_id": "2401.00003",
            "title": "Vision Transformers for Images",
            "authors": ["Alice"],
            "summary": "Applying self-attention to image recognition.",
            "published": "2024-01-03T00:00:00Z",
            "categories": ["cs.CV"],
            "primary_category": "cs.CV",
        },
    ]


@pytest.fixture()
def mem_client():
    client = QdrantClient(":memory:")
    ensure_collection(client, COLLECTION, dense_dim=DENSE_DIM)
    upsert_papers(client, COLLECTION, _fake_papers(), FakeDenseModel(), FakeSparseModel())
    return client


def test_search_keyword_mode(mem_client):
    results = search(
        mem_client,
        COLLECTION,
        query="Retrieval",
        mode="keyword",
        dense_model=FakeDenseModel(),
        sparse_model=FakeSparseModel(),
        limit=3,
    )
    assert isinstance(results, list)
    assert len(results) > 0
    assert all("arxiv_id" in r for r in results)


def test_search_vector_mode(mem_client):
    results = search(
        mem_client,
        COLLECTION,
        query="Retrieval-Augmented Generation",
        mode="vector",
        dense_model=FakeDenseModel(),
        sparse_model=FakeSparseModel(),
        limit=3,
    )
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_hybrid_mode(mem_client):
    results = search(
        mem_client,
        COLLECTION,
        query="Retrieval",
        mode="hybrid",
        dense_model=FakeDenseModel(),
        sparse_model=FakeSparseModel(),
        limit=3,
    )
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_returns_dicts_with_payload(mem_client):
    results = search(
        mem_client,
        COLLECTION,
        query="test",
        mode="vector",
        dense_model=FakeDenseModel(),
        sparse_model=FakeSparseModel(),
        limit=2,
    )
    assert all("title" in r for r in results)
    assert all("summary" in r for r in results)
    assert all("score" in r for r in results)


def test_search_invalid_mode_raises(mem_client):
    with pytest.raises(ValueError):
        search(
            mem_client,
            COLLECTION,
            query="test",
            mode="invalid",
            dense_model=FakeDenseModel(),
            sparse_model=FakeSparseModel(),
        )