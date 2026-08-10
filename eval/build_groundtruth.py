"""Generate ~150-200 ground-truth Q&A pairs from held-out arxiv papers.

Phase 4 / Phase 2. Output: eval/groundtruth.csv with columns
question, expected_arxiv_ids (semicolon-separated).

Uses papers from Qdrant (the last 150 by published date) as the ground truth
source. For each paper, asks the LLM to generate 1 question whose answer is
found in that paper. Stores the question with the expected arxiv_id.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from qdrant_client import QdrantClient

from arxiv_agent.config import settings
from arxiv_agent.llm import chat
from arxiv_agent.kb import ensure_collection

GROUNDTRUTH_PATH = Path(__file__).parent / "groundtruth.csv"
NUM_PAPERS = 50

QUESTION_GEN_PROMPT = """You are generating test questions for a research paper retrieval system.

Given the title and abstract of an arXiv paper, write ONE specific question that
a researcher might ask, where this paper would be a relevant result.

The question should:
- Be answerable from the paper's content
- Use natural researcher language (not copy the title)
- Be specific enough that not every paper matches, but general enough to be useful

Return ONLY the question text, no quotes, no explanation.

Title: {title}
Abstract: {summary}
"""


def fetch_held_out_papers(client: QdrantClient, collection: str, n: int = NUM_PAPERS) -> list[dict]:
    points, _ = client.scroll(
        collection_name=collection,
        limit=n,
        with_payload=True,
        with_vectors=False,
        offset=None,
    )
    papers = []
    for p in points:
        if p.payload:
            papers.append(p.payload)
    return papers


def generate_question(title: str, summary: str, model: str | None = None) -> str:
    prompt = QUESTION_GEN_PROMPT.format(title=title, summary=summary)
    messages = [
        {"role": "system", "content": "You generate concise research questions."},
        {"role": "user", "content": prompt},
    ]
    try:
        response = chat(messages, model=model or settings.llm_model)
        question = (response.choices[0].message.content or "").strip()
        if question.startswith('"') and question.endswith('"'):
            question = question[1:-1]
        return question
    except Exception:
        return ""


def main(num_papers: int = NUM_PAPERS, output: Path | None = None) -> int:
    output = output or GROUNDTRUTH_PATH
    client = QdrantClient(url=settings.qdrant_url)

    papers = fetch_held_out_papers(client, settings.qdrant_collection, num_papers)
    print(f"fetched {len(papers)} held-out papers from Qdrant")

    rows = []
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "expected_arxiv_id", "expected_title"])
        writer.writeheader()

        for i, paper in enumerate(papers):
            question = generate_question(paper.get("title", ""), paper.get("summary", ""))
            if not question or len(question) < 10:
                continue
            row = {
                "question": question,
                "expected_arxiv_id": paper.get("arxiv_id", ""),
                "expected_title": paper.get("title", ""),
            }
            rows.append(row)
            writer.writerow(row)
            f.flush()
            print(f"  [{i + 1}/{len(papers)}] {paper.get('arxiv_id', '')}: {question[:80]}")

    print(f"wrote {len(rows)} ground-truth Q&A pairs to {output}")
    return len(rows)


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count > 0 else 1)