"""Offline LLM evaluation: prompt/model/rewrite comparisons with LLM-as-judge.

Compares prompt A vs B, Hy3 vs secondary model (if set), with vs without
query rewriting. Judge scores relevance + usefulness(1-5). Output:
eval/llm_results.csv and documents the best config in README. Phase 4.

Run: `uv run python eval/eval_rag.py`.
"""
from __future__ import annotations


def main() -> None:
    raise NotImplementedError("Phase 4")


if __name__ == "__main__":
    main()