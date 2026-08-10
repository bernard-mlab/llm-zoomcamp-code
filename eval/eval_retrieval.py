"""Offline retrieval evaluation: 4 variants + (with/without) rewrite.

Variants: keyword-only, vector-only, hybrid (RRF), hybrid + cross-encoder rerank.
Metrics: hit-rate@5, MRR. Output: eval/retrieval_results.csv. Phase 2.

Run: `uv run python eval/eval_retrieval.py`.
"""
from __future__ import annotations

import csv
import sys
from collections.abc import Iterable
from pathlib import Path

from qdrant_client import QdrantClient

from arxiv_agent.config import settings
from arxiv_agent.kb import search

GROUNDTRUTH_PATH = Path(__file__).parent / "groundtruth.csv"
RESULTS_PATH = Path(__file__).parent / "retrieval_results.csv"
TOP_K = 5

VARIANTS = [
    "keyword",
    "vector",
    "hybrid",
    "hybrid_rerank",
]


def load_groundtruth(path: Path = GROUNDTRUTH_PATH) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def hit_rate(retrieved_ids: list[str], expected_id: str, k: int = TOP_K) -> int:
    return 1 if expected_id in retrieved_ids[:k] else 0


def reciprocal_rank(retrieved_ids: list[str], expected_id: str) -> float:
    for i, rid in enumerate(retrieved_ids):
        if rid == expected_id:
            return 1.0 / (i + 1)
    return 0.0


def evaluate_variant(
    client: QdrantClient,
    collection: str,
    gt_rows: list[dict],
    mode: str,
    dense_model,
    sparse_model,
) -> dict:
    hits = 0
    rr_sum = 0.0
    total = len(gt_rows)

    for row in gt_rows:
        question = row["question"]
        expected_id = row["expected_arxiv_id"]

        results = search(
            client,
            collection,
            query=question,
            mode=mode,
            dense_model=dense_model,
            sparse_model=sparse_model,
            limit=TOP_K,
        )
        retrieved_ids = [r["arxiv_id"] for r in results]
        hits += hit_rate(retrieved_ids, expected_id)
        rr_sum += reciprocal_rank(retrieved_ids, expected_id)

    hr = hits / total if total > 0 else 0.0
    mrr = rr_sum / total if total > 0 else 0.0
    return {"variant": mode, "hit_rate@5": hr, "mrr": mrr, "num_questions": total}


def main() -> int:
    from fastembed import TextEmbedding, SparseTextEmbedding

    print("Loading ground truth...")
    gt_rows = load_groundtruth()
    print(f"  {len(gt_rows)} Q&A pairs")

    client = QdrantClient(url=settings.qdrant_url)
    print("Loading embedders...")
    dense_model = TextEmbedding(model_name=settings.embed_model)
    sparse_model = SparseTextEmbedding(model_name="prithivida/Splade_PP_en_v1")

    results = []
    for mode in VARIANTS:
        print(f"Evaluating {mode}...")
        result = evaluate_variant(client, settings.qdrant_collection, gt_rows, mode, dense_model, sparse_model)
        results.append(result)
        print(f"  hit_rate@5={result['hit_rate@5']:.3f}, mrr={result['mrr']:.3f}")

    best = max(results, key=lambda r: r["mrr"])
    best_row = {"variant": "BEST", "hit_rate@5": best["hit_rate@5"], "mrr": best["mrr"], "num_questions": best["num_questions"]}
    print(f"\nBest variant: {best['variant']} (hit_rate@5={best['hit_rate@5']:.3f}, mrr={best['mrr']:.3f})")

    with open(RESULTS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["variant", "hit_rate@5", "mrr", "num_questions"])
        writer.writeheader()
        for r in results:
            writer.writerow(r)
        writer.writerow(best_row)

    print(f"Wrote results to {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())