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

Retrieval (`eval/eval_retrieval.py`): 4 variants — keyword-only, vector-only,
hybrid (Qdrant RRF fusion), hybrid + cross-encoder rerank — scored with
hit-rate@5 and MRR over an LLM-generated ground-truth Q&A set. Best variant
is used in production.

LLM (`eval/eval_rag.py`): multiple prompts and (optionally) a second model,
scored by LLM-as-judge (relevance + usefulness 1–5).

## Status

Phase 0 (scaffold) complete. See [`PROGRESS.md`](PROGRESS.md) for the phase
tracker and [`docs/handoffs/`](docs/handoffs/) for session handoffs.