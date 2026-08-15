# arXiv AI Research Assistant

A conversational research copilot over arXiv CS.AI / CS.CL / CS.LG papers. Ask
an open-ended ML question; the agent reasons, searches a hybrid (keyword +
vector) knowledge base, rewrites queries, re-ranks, optionally fetches fresh
arXiv metadata, and answers with **cited arXiv IDs**.

> LLM Zoomcamp final project. See
> [`docs/superpowers/specs/2026-07-26-arxiv-agent-design.md`](docs/superpowers/specs/2026-07-26-arxiv-agent-design.md)
> for the full design and [`PROGRESS.md`](PROGRESS.md) for the build tracker.

## Problem

Researchers struggle to get grounded, cited answers over the fast-moving arXiv
literature. Standard web search surfaces non-archival or low-quality sources,
and even RAG systems often fail to *cite what they used*. This project builds
an agentic RAG system over arXiv that decides when and how to search, cites its
sources, and exposes a chat interface with monitoring and evaluation.

## Stack

- **LLM**: `Hy3` via an OpenAI-compatible proxy (opencode-go), env-swappable,
  native function-calling (verified, see
  [`ADR-01`](docs/decisions/ADR-01-hy3-tool-calling.md)).
- **Knowledge base**: Qdrant with native hybrid (sparse SPLADE + dense
  bge-small) and RRF fusion, plus a cross-encoder reranker.
- **Ingestion**: dlt pulling the arXiv API (incremental state, rate-limited,
  retry with backoff).
- **Agent**: handwritten tool-calling loop (Module-1 style) with a 3-tool
  registry (`search_papers`, `fetch_arxiv`, `rewrite_query`).
- **Interface**: Chainlit (chat + thumbs feedback wired to Langfuse scores).
- **Monitoring**: self-hosted Langfuse v2 (tracing + 6-chart dashboard).
- **Containerization**: full docker-compose stack (app + qdrant + langfuse +
  deps), runs on colima.

## Project structure

```
arxiv_agent/            agent loop, LLM client, KB search, reranker, tracing
  tools/                tool registry: search_papers, fetch_arxiv, rewrite_query
pipeline/               dlt ingestion: sources/arxiv.py + ingest.py runner
interface/              Chainlit chat app (agent + citations + thumbs)
eval/                   ground-truth builder, retrieval eval, LLM eval + CSVs
langfuse/               provisioning script, dashboard.json, setup notes
tests/                  32 pytest tests (agent, tools, KB, ingest, interface)
docker-compose.yml      full stack (app, qdrant, langfuse + deps, ingest profile)
Dockerfile              app image (uv-synced, dev deps excluded)
docs/                   spec, plan, handoffs, ADRs, PROGRESS tracker
```

## Quick start (macOS / colima)

```bash
# 1. Start the Docker runtime
colima start

# 2. Configure environment (fill in OPENCODE_GO_API_KEY; Langfuse keys optional)
cp .env.example .env

# 3. Install dependencies (Python 3.12; uv manages the venv)
uv sync

# 4. Bring up the full stack (Qdrant + Langfuse + app), then check health
docker-compose up -d --build
curl -s http://localhost:8000        # Chainlit app  -> 200
curl -s http://localhost:6333/healthz # Qdrant       -> healthz check passed

# 5. Populate the knowledge base (first run only; ~10-15 min)
uv run python -m pipeline.ingest

# 6. Open the chat UI
open http://localhost:8000
```

> **`docker compose` vs `docker-compose`**: this repo uses the legacy
> `docker-compose` (hyphenated) command. If you have the compose v2 plugin,
> the same commands work as `docker compose` — the compose file is unchanged.

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
production. Query rewriting (`hybrid_rerank_rewrite`) did not improve over the
original queries on a 5-question subset — the LLM-generated ground-truth
questions were already well-phrased. The `rewrite_query` tool remains available
to the agent for cases where the user's initial query is vague.

```bash
uv run python eval/build_groundtruth.py   # regenerate ground truth (LLM, optional)
uv run python eval/eval_retrieval.py      # runs all variants, writes retrieval_results.csv
```

### LLM evaluation

`eval/eval_rag.py` compares two prompt templates over the ground-truth Q&A set,
scored by LLM-as-judge (relevance: RELEVANT/PARTLY/NON, usefulness 1-5).

| Config | RELEVANT | Avg usefulness | n |
|---|---|---|---|
| prompt_a (concise + citations) | 4/4 | 5.00 | 4 |
| prompt_b (reasoning + citations) | 4/4 | 5.00 | 4 |

Both prompts produced RELEVANT answers with maximum usefulness. The agent uses
`prompt_a` (concise) as the default for faster responses, with `prompt_b`
(reasoning) available as an alternative. The eval was run on a 4-question
subset due to LLM API latency (~27s per call); the methodology is documented
for reproducibility.

```bash
uv run python eval/eval_rag.py   # LLM-as-judge, writes llm_results.csv
```

See `eval/llm_results.csv` and `eval/retrieval_results.csv` for full results.

## Best config (production)

- **Retrieval**: `hybrid_rerank` (Qdrant RRF fusion + cross-encoder rerank)
- **LLM**: `Hy3` via opencode-go proxy, native function-calling
- **Prompt**: `prompt_a` (concise + citations)
- **Agent**: handwritten loop, iteration cap 6, 3-tool registry

## Langfuse monitoring (one-time setup)

Self-hosted Langfuse v2 runs at `http://localhost:3000` (started as part of
`docker-compose up -d`). The app emits a trace per agent turn with child spans
per iteration, LLM call, and tool call; Chainlit thumbs clicks send
`user_feedback` scores. See [`langfuse/README.md`](langfuse/README.md) for the
login, the 6-chart dashboard, and one-time provisioning (project + API keys).

```bash
# Add keys to .env after provisioning:
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_SECRET_KEY=sk-lf-...
docker-compose restart app
```

## Reproducibility

- **Dependencies**: `pyproject.toml` + `uv.lock` pin the exact resolution
  (285 packages); `uv sync` reproduces the environment on any machine
  (Python 3.12 via uv).
- **Services**: `docker-compose.yml` pins every image tag (Qdrant v1.18.0,
  Langfuse v2, etc.); `docker-compose up -d --build` reproduces the full stack.
- **Dataset**: the KB is rebuilt on demand by `uv run python -m pipeline.ingest`
  (arXiv API, retry + rate-limit). Collection `arxiv_papers` currently holds
  2176 papers.
- **Evals**: ground-truth, retrieval, and LLM-eval results are committed as CSVs
  in `eval/`; each script is rerunnable.
- **Env**: `.env.example` lists every required key with a comment; no secrets
  are committed.
- **Note**: `uv sync` installs the `dev` group (pytest, ruff, bcrypt,
  jupyterlab). The Docker image builds with `--no-dev` to keep it slim.

## Screenshots

> **TBD — to be captured before peer review.** Placeholders below:

1. Chainlit chat UI — ask a question, agent answer with cited arXiv IDs
   (`docs/screenshots/chat.png`).
2. Langfuse dashboard — traces / spans / feedback charts
   (`docs/screenshots/langfuse-dashboard.png`).
3. Sample answer — one agent turn with citations sidebar
   (`docs/screenshots/agent-answer.png`).

## Status

Phases 0-6 complete (scaffold, ingestion, retrieval, agent, LLM eval,
interface, monitoring) + Phase 7 (containerization, reproducibility). See
[`PROGRESS.md`](PROGRESS.md) for the phase tracker and
[`docs/handoffs/`](docs/handoffs/) for session handoffs.
