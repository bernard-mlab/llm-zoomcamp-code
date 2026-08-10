import uuid

import numpy as np
import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
)

from arxiv_agent.kb import ensure_collection, upsert_papers, paper_text

COLLECTION = "test_arxiv_papers"
DENSE_DIM = 4


class FakeDenseModel:
    def embed(self, texts, **kwargs):
        for i, t in enumerate(texts):
            vec = np.zeros(DENSE_DIM, dtype=np.float32)
            vec[0] = len(t) / 100.0
            vec[1] = hash(t) % 10 / 10.0
            yield vec


class FakeSparseModel:
    def embed(self, texts, **kwargs):
        for i, t in enumerate(texts):
            indices = np.array([i * 3, i * 3 + 1, i * 3 + 2], dtype=np.int64)
            values = np.array([1.0, 0.5, 0.3], dtype=np.float32)
            yield _FakeSparse(indices, values)


class _FakeSparse:
    def __init__(self, indices, values):
        self.indices = indices
        self.values = values


def _fake_papers():
    return [
        {
            "arxiv_id": "2401.00001",
            "title": "Retrieval-Augmented Generation",
            "authors": ["Jane Doe"],
            "summary": "A paper about RAG systems.",
            "published": "2024-01-01T00:00:00Z",
            "categories": ["cs.AI", "cs.CL"],
            "primary_category": "cs.AI",
        },
        {
            "arxiv_id": "2401.00002",
            "title": "Mixture of Experts",
            "authors": ["John Smith"],
            "summary": "Scaling with sparse MoE layers.",
            "published": "2024-01-02T00:00:00Z",
            "categories": ["cs.LG"],
            "primary_category": "cs.LG",
        },
        {
            "arxiv_id": "2401.00003",
            "title": "Vision Transformers",
            "authors": ["Alice Brown"],
            "summary": "Applying transformers to images.",
            "published": "2024-01-03T00:00:00Z",
            "categories": ["cs.CV"],
            "primary_category": "cs.CV",
        },
    ]


@pytest.fixture()
def mem_client():
    client = QdrantClient(":memory:")
    ensure_collection(client, COLLECTION, dense_dim=DENSE_DIM)
    yield client


def test_ensure_collection_creates_collection(mem_client):
    info = mem_client.get_collection(COLLECTION)
    assert info is not None


def test_upsert_papers_count(mem_client):
    papers = _fake_papers()
    upsert_papers(mem_client, COLLECTION, papers, FakeDenseModel(), FakeSparseModel())
    count = mem_client.count(COLLECTION).count
    assert count == 3


def test_upsert_preserves_payload(mem_client):
    papers = _fake_papers()
    upsert_papers(mem_client, COLLECTION, papers, FakeDenseModel(), FakeSparseModel())
    points, _ = mem_client.scroll(COLLECTION, limit=3, with_payload=True, with_vectors=False)
    titles = {p.payload["title"] for p in points}
    assert "Retrieval-Augmented Generation" in titles


def test_dense_search_returns_relevant(mem_client):
    papers = _fake_papers()
    upsert_papers(mem_client, COLLECTION, papers, FakeDenseModel(), FakeSparseModel())

    query_text = paper_text(papers[0])
    query_vec = list(FakeDenseModel().embed([query_text]))[0]
    results = mem_client.query_points(
        COLLECTION,
        query=query_vec,
        using="dense",
        limit=1,
    ).points
    assert len(results) == 1
    assert results[0].payload["arxiv_id"] == "2401.00001"


def test_paper_text_concatenates_fields():
    paper = _fake_papers()[0]
    text = paper_text(paper)
    assert "Retrieval-Augmented Generation" in text
    assert "RAG systems" in text
    assert "cs.AI" in text
