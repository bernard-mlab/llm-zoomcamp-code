# Design: arXiv AI Research Assistant — LLM Zoomcamp Final Project

**Status**: approved (2026-07-26)
**Spec owner**: project lead
**Repo**: `Assignment/arxiv-research-assistant` (git worktree, branch `project/arxiv-agent`)

## 1. Problem statement & demo pitch

A conversational research copilot over arXiv CS.AI papers. A user asks an
open-ended ML question; the agent reasons, searches a local knowledge base
(hybrid), optionally pulls fresh arxiv metadata, rewrites queries, re-ranks,
and answers with **cited arxiv IDs**. Delivers all core rubric points plus
the three best-practice bonuses (hybrid search, reranking, query rewriting)
and self-hosted Langfuse monitoring.

Project name: **`arxiv-research-assistant`**.

## 2. Architecture overview

```
                ┌─────────── Chainlit (UI, :8000) ───────────┐
                │   ask question  |  thumbs feedback          │
                └─────────────────────┬───────────────────────┘
                                      │
                          ┌───────────▼────────────┐
                          │   Agent loop (handwritten) │  tools: search_papers,
                          │   - tool registry (3 fns) │  fetch_arxiv,
                          │   - instructions/dev msg │  rewrite_query
                          └───┬───────────────┬──────────┘
                              │               │
                  ┌───────────▼────┐   ┌──────▼────────┐
                  │ LLM client     │   │ KB (Qdrant)   │  collection:
                  │ OpenAI-compat  │   │ hybrid fusion │  arxiv_papers
                  │ -> opencode-go │   └───────────────┘  (sparse+dense)
                  │    model: Hy3  │            ▲
                  └────────────────┘            │
                              ▲                 │ ingest once/recurring
                              │                 │
                  ┌───────────┴─────────────────┴───┐
                  │ dlt pipeline: arXiv API -> chunk ─┐
                  │ -> embed (fastembed/bge-small) ───┘── Qdrant upsert
                  └───────────────────────────────────┘

   Tracing: agent/LLM/search/tool calls emit spans to Langfuse (self-hosted)
   Eval:    offline notebooks compare retrieval variants + LLM-as-judge
```

## 3. Data & ingestion (dlt) — rubric: ingestion 2 pts

- **Source**: arXiv API (`http://export.arxiv.org/api/query`) via a `dlt`
  REST source. Pull ~3,000 CS.AI papers (categories `cs.AI`, `cs.CL`, `cs.LG`
  slice) — fields: `arxiv_id`, `title`, `authors`, `summary`, `published`,
  `categories`, `primary_category`, optionally `comment`. dlt handles
  pagination, retries, and incremental load state so re-runs only fetch new
  papers.
- **Chunking**: each paper = 1 document with 1 chunk
  (title + summary + categories) since arxiv abstracts are ~200–300 tokens.
  Optionally split long abstracts >600 tokens. `doc_id = arxiv_id`,
  `chunk_id = arxiv_id`.
- **Embedding**: `fastembed` `BAAI/bge-small-en-v1.5` for dense vectors;
  Qdrant built-in sparse (BM25-style) for keyword. Embedder is a swappable
  module.
- **Pipeline run**: `python -m pipeline.ingest` (automated) and idempotent
  via dlt. Loads Qdrant collection `arxiv_papers` with payload + both vector
  types.
- **Reproducibility**: dataset rebuildable from the API (no committed data);
  an eval snapshot may be committed for determinism.

## 4. Knowledge base & retrieval — rubric: retrieval flow 2 pts + retrieval eval 2 pts + hybrid/rerank/rewrite bonuses

- **Qdrant collection** `arxiv_papers`: dense vector (bge-small) + sparse
  vector (BM25 via Qdrant sparse vectors) on the same text.
- **Retrieval variants to evaluate (offline)** → "multiple retrieval
  approaches, best used":
  1. keyword-only (sparse)
  2. vector-only (dense)
  3. hybrid with Qdrant native fusion (RRF) — default
  4. hybrid + cross-encoder rerank (`Xenova/ms-marco-MiniLM-L-6-v2` ONNX)
     top-20 → top-5
- **Query rewriting**: agent `rewrite_query` tool produces expanded keyword
  sets for the sparse side; offline eval compares "with rewrite vs without"
  for the hybrid variant.
- **Ground truth**: generate ~150–200 Q&A pairs with LLM from a held-out paper
  subset (question → expected `arxiv_id`(s)); compute **hit-rate@5** and
  **MRR** per variant. Persist `eval/retrieval_results.csv`.

## 5. Agent (handwritten loop) — rubric: retrieval flow + best-practice bonuses

- **Tools** (registry, JSON-schema tool defs sent to the LLM; fall back to
  instruction-based tool use if `Hy3` lacks native function-calling):
  - `search_papers(query, mode)` → hybrid Qdrant search → top-k
    `{arxiv_id, title, summary, score}`. `mode` ∈ {keyword, vector, hybrid,
    hybrid_rerank}.
  - `fetch_arxiv(arxiv_id)` → live arxiv API call → fresh metadata for
    citation/verification.
  - `rewrite_query(query)` → LLM-side tool returning alternative
    phrasings/keywords (drives the sparse side of the next search).
- **Loop**: Module-1 style while-loop with iteration cap (6) and token budget
  safety; dev message restricts scope to arxiv CS scope, requires citations,
  declines off-topic.
- **Function-calling strategy for `Hy3`**: try native tool calls; if the
  model doesn't emit them, fall back to a "plan-then-act" prompt where the
  model emits a JSON action we parse. Detected at startup via
  `capability_probe.py` and recorded in an ADR + PROGRESS.

## 6. LLM evaluation — rubric: LLM eval 2 pts

- **Approaches compared (offline on the Q&A set)**:
  1. prompt A (concise + citations) vs prompt B (reasoning + citations) —
     usefulness comparison
  2. `Hy3` vs a second OpenAI-compatible model (env-swappable) if available;
     otherwise documented rationale
  3. with vs without query rewriting
- **Judge**: LLM-as-judge scoring `RELEVANT/PARTLY/NON` + 1–5 usefulness,
  logged per answer. Persist `eval/llm_results.csv`. Document the best config.

## 7. Interface (Chainlit) — rubric: interface 2 pts

Chat UI at `:8000`. Each assistant message shows the answer and cited arxiv
IDs as clickable badges. Thumbs up/down feedback (sent to Langfuse + a
feedback span). Persisted conversation history per Chainlit user. A small
sidebar shows the agent's last retrieval (mode, #results) for transparency.

## 8. Monitoring (self-hosted Langfuse) — rubric: monitoring 2 pts (feedback + ≥5 charts)

- **Tracing**: every user turn = a Langfuse trace; child spans for each agent
  iteration, each `search_papers` (mode, k, scores), each `llm` call (model,
  tokens, cost), each `fetch_arxiv`. Implemented via the `langfuse` Python
  SDK.
- **Feedback**: Chainlit thumbs → `langfuse.score(feedback=1/-1)`.
- **Dashboard (≥5 charts)** in self-hosted Langfuse, provisioned via API /
  a setup script:
  1. Avg response time per turn
  2. Token usage & cost per model
  3. Tool call counts per turn (search/fetch/rewrite)
  4. Relevance distribution (LLM-judge)
  5. User feedback ratio over time
  6. Hybrid-search rerank win-rate (#times rerank changed top-1)

## 9. Containerization — rubric: containerization 2 pts ("everything in docker-compose")

- **`docker-compose.yml`** services:
  - `qdrant` (Qdrant)
  - `langfuse-web` + `langfuse-worker` + deps: `postgres-langfuse`,
    `clickhouse`, `redis`, `minio`
  - `app` (Chainlit service, builds from Dockerfile using `uv`)
  - `ingest` (one-shot profile: `docker compose --profile ingest run ingest`)
- **Dockerfile**: `python:3.12-slim` + uv + `uv sync --locked`,
  `CMD chainlit run app.py`.
- **Runtime note**: runs on **colima** locally
  (`colima start && docker compose up -d`); documented in README.

## 10. Reproducibility — rubric: reproducibility 2 pts

Pinned versions in `pyproject.toml` + `uv.lock`. `.env.example` lists
`OPENCODE_GO_API_KEY`, `OPENCODE_GO_BASE_URL`, `OPENCODE_GO_MODEL=Hy3`,
Qdrant/Langfuse URLs. README: colima setup, ingest, eval, run, dashboard
URLs. Dataset rebuildable from the arxiv API; eval outputs committed.

## 11. Repository layout

```
pyproject.toml, uv.lock, .env.example, .gitignore, README.md
docker-compose.yml, Dockerfile, langfuse/ (provisioning)
pipeline/
  ingest.py, sources/arxiv.py
arxiv_agent/
  config.py, llm.py, kb.py, reranker.py,
  tools/{__init__,search.py,fetch.py,rewrite.py},
  agent.py, tracing.py, capability_probe.py
interface/
  app.py, Dockerfile-app
eval/
  build_groundtruth.py, eval_retrieval.py, eval_rag.py,
  retrieval_results.csv, llm_results.csv
notebooks/ (optional), tests/ (optional)
PROGRESS.md, AGENTS.md
docs/superpowers/specs/2026-07-26-arxiv-agent-design.md
docs/handoffs/session-NN.md
docs/decisions/ADR-NN.md
docs/plans/<phased-plan>.md
```

## 12. Rubric → deliverable mapping

| Criterion | Where | Points |
|---|---|---|
| Problem description | README §1 + this design doc | 2 |
| Retrieval flow | KB + LLM used | 2 |
| Retrieval eval | `eval/eval_retrieval.py` + results | 2 |
| LLM eval | `eval/eval_rag.py` + results | 2 |
| Interface | Chainlit `:8000` | 2 |
| Ingestion | dlt `pipeline/ingest.py` (automated) | 2 |
| Monitoring | Langfuse + 6 charts | 2 |
| Containerization | full `docker-compose.yml` | 2 |
| Reproducibility | README + `uv.lock` + `.env.example` | 2 |
| Hybrid search | Qdrant fusion, evaluated | +1 |
| Reranking | cross-encoder ONNX | +1 |
| Query rewriting | `rewrite_query` tool + eval | +1 |
| Cloud deploy | final optional phase | +2 (bonus) |

## 13. Phased plan, checkpoints & session hand-offs

- **Phase 0 — Scaffold**: worktree, `uv init`, pyproject, repo skeleton,
  `.env.example`, README stub, design + plan, `PROGRESS.md` initialized.
  Checkpoint: `docker compose config` valid; `uv sync` green.
- **Phase 1 — Ingestion + KB**: dlt arxiv source → Qdrant hybrid collection.
  Checkpoint: `python -m pipeline.ingest` populates a collection; verify
  point count.
- **Phase 2 — Retrieval + Rerank**: `kb.py`, reranker; offline retrieval
  eval over 4 variants + rewrite. Checkpoint: `eval/retrieval_results.csv`,
  best variant chosen.
- **Phase 3 — Agent**: tool registry + handwritten loop (with `Hy3`
  tool-call detection), citations. Checkpoint: CLI smoke run answers a
  sample question with citations.
- **Phase 4 — LLM eval**: ground-truth Q&A, LLM-as-judge, prompt/model/
  rewrite comparisons. Checkpoint: `eval/llm_results.csv`, best config
  locked.
- **Phase 5 — Interface (Chainlit)**: chat UI + thumbs. Checkpoint: local
  `chainlit run` works end-to-end.
- **Phase 6 — Monitoring (Langfuse)**: tracing spans + feedback + 6-chart
  dashboard provisioning. Checkpoint: dashboard renders; feedback scores
  appear.
- **Phase 7 — Containerization + Reproducibility**: full docker-compose
  (colima), README finalized. Checkpoint: clean-machine `docker compose up
  -d` runs app + qdrant + langfuse.
- **Phase 8 (bonus) — Cloud deploy**: optional fly.io/render + cloud Qdrant.
  Checkpoint: public URL answering questions.

## 14. Session continuity & anti-hallucination guardrails

### 14.1 Ground-truth files (read-only by default; append-only by protocol)
Three files form the immutable project state. Every session **must read
them before any work**:
- `docs/superpowers/specs/2026-07-26-arxiv-agent-design.md` — the spec
  (this file). Settled decisions.
- `PROGRESS.md` — phase + rubric checklist with artifact paths and a
  *verification command per item*.
- `docs/handoffs/session-NN.md` — latest handoff (newest wins).
- `docs/decisions/ADR-NN.md` — architecture decision records, created only
  when deviating from the spec.

### 14.2 Session-start reality-check protocol (mandatory, before any code)
Encoded in `AGENTS.md`. At the start of every new session, in this order,
and a "Session State" summary printed before touching anything:

1. **Read** spec + latest handoff + PROGRESS.md.
2. **Re-derive claim** for each rubric/phase: for each PROGRESS.md checkbox
   marked done, run its verification command and confirm it still passes.
3. **Probe live environment** and record a fingerprint:
   - `colima status` (running?)
   - `docker compose ps` (services up?)
   - Qdrant `/healthz` + `arxiv_papers` collection point count (matches
     PROGRESS number?)
   - Langfuse `/api/public/health`
   - **Capability probe** to the LLM endpoint: a 1-token completion + a tiny
     tool-call probe against `Hy3` → record `tool_calling: yes/no/partial`.
     *This is the single biggest hallucination vector — never assume `Hy3`
     supports function calling; always verify and record.*
4. **Reconcile**: if any probe contradicts PROGRESS.md ("done" but command
   fails, or Qdrant count wrong), STOP, surface the discrepancy, and
   reconcile PROGRESS.md before any new work. A session never builds on a
   hallucinated foundation.

### 14.3 No-completion-without-proof rule (anti-hallucination on "done")
A rubric item / phase is marked done only if **all three** hold:
1. The named artifact exists at its path.
2. Its verification command runs green.
3. The command's real output (not paraphrased) is pasted into the handoff.

Paraphrased claims without output are invalid.

### 14.4 Decision log (prevents re-litigating & hallucinated rationale)
Any deviation from the spec becomes an `ADR-NN.md` with: context, decision,
alternatives, status, and the verification command used to discover it. A
future session reads ADRs before re-opening a question, so it cannot
hallucinate a different reason.

### 14.5 Handoff document structure (so the next session resumes cold)
Every session ends by writing `docs/handoffs/session-NN.md` with:
- **State fingerprint** at close: colima, docker, Qdrant count, Langfuse
  URL, `Hy3` tool-call probe result.
- **What changed this session**: files touched, commands run + their output.
- **Rubric delta**: which PROGRESS.md boxes went unchecked → checked, with
  proof links.
- **Open decisions / blockers**: never silently deferred.
- **Next session's first task**: exact starting command.
- **Known-good verification command set**: commands that should all pass
  before next session starts new work.

### 14.6 PROGRESS.md schema (concrete, falsifiable)
Each line ties a rubric/phase item to an artifact + a single command whose
exit code/output is the proof:
```
- [ ] Retrieval eval | eval/eval_retrieval.py exists | `uv run python eval/eval_retrieval.py` prints >=4 variant rows, best=hybrid_rerank
- [ ] Hy3 tool-call capability | docs/decisions/ADR-01.md | capability_probe.py prints tool_calling=yes|no
```
A checkbox is checked only with pasted green output in the latest handoff.

### 14.7 Drift guards against the two specific hallucination failures
- **"It works" claims**: §14.3 + §14.2.4. No proof → not done.
- **"We decided X" hallucination**: spec + ADRs are the only source of
  decisions; a session referencing a decision must cite its ADR number or
  spec section. Un-cited "decisions" are treated as not-made.

### 14.8 First-message contract for the agent (encoded in AGENTS.md)
At session start the assistant outputs exactly: a one-line "Reading spec +
PROGRESS + handoff…", then the Session State block (fingerprint +
reconciliation result), then asks whether to proceed to the next task or
pause. It does not edit, commit, or build until the user acknowledges the
state is correct.