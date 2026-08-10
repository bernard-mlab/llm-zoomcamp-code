import numpy as np
import pytest
from qdrant_client import QdrantClient

from arxiv_agent.kb import ensure_collection
from pipeline.ingest import main


class _FakeSparse:
    def __init__(self, indices, values):
        self.indices = indices
        self.values = values


class FakeDenseModel:
    def embed(self, texts, **kwargs):
        for t in texts:
            yield [0.1, 0.2, 0.3, 0.4]


class FakeSparseModel:
    def embed(self, texts, **kwargs):
        for i, t in enumerate(texts):
            yield _FakeSparse(
                np.array([i * 3, i * 3 + 1, i * 3 + 2], dtype=np.int64),
                np.array([1.0, 0.5, 0.3], dtype=np.float32),
            )


def _fake_papers(n=5):
    return [
        {
            "arxiv_id": f"2401.{i:05d}",
            "title": f"Paper {i}",
            "authors": [f"Author {i}"],
            "summary": f"Summary for paper {i}.",
            "published": f"2024-01-0{i%9+1}T00:00:00Z",
            "categories": ["cs.AI"],
            "primary_category": "cs.AI",
        }
        for i in range(n)
    ]


@pytest.fixture()
def mem_client():
    client = QdrantClient(":memory:")
    ensure_collection(client, "test_ingest", dense_dim=4)
    return client


def test_ingest_end_to_count(mem_client):
    papers = _fake_papers(5)
    count = main(
        client=mem_client,
        collection="test_ingest",
        papers=papers,
        dense_model=FakeDenseModel(),
        sparse_model=FakeSparseModel(),
    )
    assert count == 5
    assert mem_client.count("test_ingest").count == 5


def test_ingest_is_idempotent(mem_client):
    papers = _fake_papers(5)
    main(
        client=mem_client,
        collection="test_ingest",
        papers=papers,
        dense_model=FakeDenseModel(),
        sparse_model=FakeSparseModel(),
    )
    main(
        client=mem_client,
        collection="test_ingest",
        papers=papers,
        dense_model=FakeDenseModel(),
        sparse_model=FakeSparseModel(),
    )
    assert mem_client.count("test_ingest").count == 5
