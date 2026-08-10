"""Offline LLM evaluation: prompt/model comparisons with LLM-as-judge.

Compares prompt A (concise+citations) vs prompt B (reasoning+citations)
using a fixed RAG pipeline over the 21 ground-truth Q&A pairs.
Judge scores relevance (RELEVANT/PARTLY/NON) + usefulness (1-5).
Output: eval/llm_results.csv. Phase 4.

Run: `uv run python eval/eval_rag.py`.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from qdrant_client import QdrantClient

from arxiv_agent.config import settings
from arxiv_agent.kb import search
from arxiv_agent.llm import chat

GROUNDTRUTH_PATH = Path(__file__).parent / "groundtruth.csv"
RESULTS_PATH = Path(__file__).parent / "llm_results.csv"

PROMPT_A = """You're an arXiv research assistant. Answer the QUESTION based on the CONTEXT from arXiv papers.
Cite arxiv_ids in square brackets, e.g. [arxiv:2401.00001]. Be concise.

QUESTION: {question}

CONTEXT:
{context}
""".strip()

PROMPT_B = """You're an arXiv research assistant. Answer the QUESTION based on the CONTEXT from arXiv papers.
Think step by step about which papers are relevant, then give a detailed answer with citations [arxiv:2401.00001].

QUESTION: {question}

CONTEXT:
{context}
""".strip()

JUDGE_PROMPT = """You are an expert evaluator for a RAG system.
Analyze the relevance and usefulness of the generated answer to the question.

Question: {question}
Generated Answer: {answer}

Provide your evaluation as JSON (no code blocks):
{{"relevance": "RELEVANT" | "PARTLY_RELEVANT" | "NON_RELEVANT", "usefulness": 1-5, "explanation": "brief"}}
""".strip()

PROMPTS = {"prompt_a": PROMPT_A, "prompt_b": PROMPT_B}


def load_groundtruth(path: Path = GROUNDTRUTH_PATH) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fixed_rag(question: str, prompt_template: str, client, collection, dense_model, sparse_model) -> str:
    results = search(
        client,
        collection,
        query=question,
        mode="hybrid_rerank",
        dense_model=dense_model,
        sparse_model=sparse_model,
        limit=5,
    )
    context = "\n\n".join(
        f"[arxiv:{r['arxiv_id']}] {r['title']}\n{r['summary']}" for r in results
    )
    prompt = prompt_template.format(question=question, context=context)
    response = chat([{"role": "user", "content": prompt}])
    return response.choices[0].message.content or ""


def judge(question: str, answer: str) -> dict:
    prompt = JUDGE_PROMPT.format(question=question, answer=answer)
    response = chat([{"role": "user", "content": prompt}])
    content = (response.choices[0].message.content or "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"relevance": "UNKNOWN", "usefulness": 0, "explanation": "parse error"}


def main() -> int:
    from fastembed import TextEmbedding, SparseTextEmbedding

    print("Loading ground truth...")
    gt_rows = load_groundtruth()
    print(f"  {len(gt_rows)} Q&A pairs")

    client = QdrantClient(url=settings.qdrant_url)
    print("Loading embedders...")
    dense_model = TextEmbedding(model_name=settings.embed_model)
    sparse_model = SparseTextEmbedding(model_name="prithivida/Splade_PP_en_v1")

    configs = [("prompt_a", PROMPT_A), ("prompt_b", PROMPT_B)]

    with open(RESULTS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "question",
                "config",
                "answer",
                "relevance",
                "usefulness",
                "judge_explanation",
            ],
        )
        writer.writeheader()
        f.flush()

        for i, row in enumerate(gt_rows):
            question = row["question"]
            for config_name, prompt_template in configs:
                print(f"  [{i + 1}/{len(gt_rows)}] {config_name}: generating answer...")
                answer = fixed_rag(
                    question, prompt_template, client, settings.qdrant_collection, dense_model, sparse_model
                )
                print(f"    judging...")
                judge_result = judge(question, answer)
                out_row = {
                    "question": question,
                    "config": config_name,
                    "answer": answer[:500],
                    "relevance": judge_result.get("relevance", "UNKNOWN"),
                    "usefulness": judge_result.get("usefulness", 0),
                    "judge_explanation": judge_result.get("explanation", ""),
                }
                writer.writerow(out_row)
                f.flush()
                print(f"    {judge_result.get('relevance')} / {judge_result.get('usefulness')}")

    print(f"\nWrote results to {RESULTS_PATH}")

    print("\n=== Summary ===")
    with open(RESULTS_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    for config_name in ["prompt_a", "prompt_b"]:
        config_rows = [r for r in rows if r["config"] == config_name]
        rel = [r for r in config_rows if r["relevance"] == "RELEVANT"]
        avg_use = sum(int(r["usefulness"]) for r in config_rows if r["usefulness"]) / max(len(config_rows), 1)
        print(f"  {config_name}: {len(rel)}/{len(config_rows)} RELEVANT, avg usefulness={avg_use:.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())