"""Offline retrieval evaluation: 4 variants + (with/without) rewrite.

Variants: keyword-only, vector-only, hybrid (RRF), hybrid + cross-encoder rerank.
Metrics: hit-rate@5, MRR. Output: eval/retrieval_results.csv. Phase 2.

Run: `uv run python eval/eval_retrieval.py`.
"""
from __future__ import annotations


def main() -> None:
    raise NotImplementedError("Phase 2")


if __name__ == "__main__":
    main()