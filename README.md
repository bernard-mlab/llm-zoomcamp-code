# arXiv AI Research Assistant

A conversational research copilot over arXiv CS.AI / CS.CL / CS.LG papers. Ask
an open-ended ML question; the agent reasons, searches a hybrid (keyword +
vector) knowledge base, rewrites queries, re-ranks, optionally fetches fresh
arxiv metadata, and answers with **cited arxiv IDs**.

> LLM Zoomcamp final project. See
> [`docs/superpowers/specs/2026-07-26-arxiv-agent-design.md`](docs/superpowers/specs/2026-07-26-arxiv-agent-design.md)
> for the full design and
> [`PROGRESS.md`](PROGRESS.md) for the build tracker.

## Problem

Researchers struggle to get grounded, cited answers over the fast-moving
arxiv literature. This project builds an agentic RAG system over arXiv
that decides when and how to search, cites its sources, and exposes a chat
interface with monitoring and evaluation.

## Stack

- **LLM**: `Hy3` via an OpenAI-compatible proxy (opencode-go), env-swappable.
- **Knowledge base**: Qdrant with native hybrid (sparse BM25 + dense bge)
  and fusion.
- **Ingestion**: dlt pulling the arXiv API (incremental state).
- **Agent**: handwritten loop (Module-1 style) with a 3-tool registry
  (`search_papers`, `fetch_arxiv`, `rewrite_query`).
- **Interface**: Chainlit (chat + thumbs feedback).
- **Monitoring**: self-hosted Langfuse (tracing + 6-chart dashboard).
- **Containerization**: full docker-compose, runs on colima.

## Quick start (macOS / colima)

```bash
colima start
cp .env.example .env        # fill in OPENCODE_GO_API_KEY etc.
uv sync
docker compose up -d qdrant langfuse-web   # bring up deps
uv run python -m pipeline.ingest          # populate the KB
docker compose up -d app                   # serve Chainlit at :8000
```

See [`README.md`](README.md) (to be expanded) for full run / eval / dashboard
instructions.

## Evaluation

### Retrieval evaluation

`eval/eval_retrieval.py` evaluates 5 retrieval variants against an
LLM-generated ground-truth Q&A set (21 pairs). Metrics: hit-rate@5 and MRR.

| Variant | hit_rate@5 | MRR | n |
|---|---|---|---|
| keyword | 0.905 | 0.778 | 21 |
| vector | 0.905 | 0.825 | 21 |
| hybrid (RRF) | 1.000 | 0.841 | 21 |
| **hybrid_rerank** | **1.000** | **0.929** | 21 |
| hybrid_rerank_rewrite | 0.800 | 0.800 | 5 |

**Best variant: `hybrid_rerank`** (hit_rate@5=1.000, MRR=0.929). Used in
production. Query rewriting (`hybrid_rerank_rewrite`) did not improve over
the original queries on a 5-question subset — the LLM-generated ground-truth
questions were already well-phrased. The `rewrite_query` tool remains
available to the agent for cases where the user's initial query is vague.

### LLM evaluation

`eval/eval_rag.py` compares two prompt templates over the ground-truth Q&A
set, scored by LLM-as-judge (relevance: RELEVANT/PARTLY/NON, usefulness 1-5).

| Config | RELEVANT | Avg usefulness | n |
|---|---|---|---|
| prompt_a (concise + citations) | 4/4 | 5.00 | 4 |
| prompt_b (reasoning + citations) | 4/4 | 5.00 | 4 |

Both prompts produced RELEVANT answers with maximum usefulness. The agent
uses `prompt_a` (concise) as the default for faster responses, with `prompt_b`
(reasoning) available as an alternative. The eval was run on a 4-question
subset due to LLM API latency (~27s per call); the methodology is
documented for reproducibility.

See `eval/llm_results.csv` and `eval/retrieval_results.csv` for full results.

## Best config (production)

- **Retrieval**: `hybrid_rerank` (Qdrant RRF fusion + cross-encoder rerank)
- **LLM**: `Hy3` via opencode-go proxy, native function-calling
- **Prompt**: `prompt_a` (concise + citations)
- **Agent**: handwritten loop, iteration cap 6, 3-tool registry

## Status

Phases 0-4 complete (scaffold, ingestion, retrieval, agent, LLM eval).
See [`PROGRESS.md`](PROGRESS.md) for the phase tracker and
[`docs/handoffs/`](docs/handoffs/) for session handoffs.