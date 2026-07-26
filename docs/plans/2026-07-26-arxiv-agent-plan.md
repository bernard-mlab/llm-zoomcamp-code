# arXiv Research Assistant — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an agentic RAG copilot over arXiv CS.AI/CL/LG papers that
answers with cited arxiv IDs, evaluates retrieval + LLM, and ships with a
Chainlit UI + self-hosted Langfuse monitoring, fully containerized.

**Architecture:** Handwritten agent loop (Module-1 style) over a 3-tool
registry (`search_papers`, `fetch_arxiv`, `rewrite_query`); Qdrant hybrid
(sparse BM25 + dense bge) knowledge base; dlt ingestion of the arXiv API;
Chainlit interface; self-hosted Langfuse tracing + dashboard; full
docker-compose on colima.

**Tech Stack:** Python 3.12, uv, openai SDK (OpenAI-compatible proxy, model
`Hy3`), qdrant-client, fastembed (bge-small + ms-marco reranker), dlt,
chainlit, langfuse, pandas/scikit-learn (eval), docker compose / colima.

## Global Constraints

- Python via `uv` only (`uv sync`, `uv add`, `uv run`). No raw pip.
- Docker via **colima** locally: `colima start` before `docker compose`.
- LLM: OpenAI-compatible client at `OPENCODE_GO_BASE_URL`, model id
  `OPENCODE_GO_MODEL=Hy3`, key `OPENCODE_GO_API_KEY`. Never assume `Hy3`
  supports function-calling — probe first (ADR-01).
- Never commit secrets / `.env`. `.gitignore` already excludes `.env`,
  `data/`, `eval/*.csv`, `.venv/`.
- Proof rule: a phase/rubric item is "done" only with green verification
  output pasted into the session handoff (AGENTS.md).
- No comments in code unless asked (repo convention).
- Worktree: `Assignment/arxiv-research-assistant`, branch
  `project/arxiv-agent`.

---

## File Structure (already scaffolded in Phase 0)

```
pyproject.toml, uv.lock, .env.example, .gitignore, README.md          # project
AGENTS.md, PROGRESS.md                                                # guardrails
docker-compose.yml, Dockerfile                                        # containerization
arxiv_agent/
  __init__.py, config.py, llm.py, kb.py, reranker.py,
  tools/__init__.py, tools/search.py, tools/fetch.py, tools/rewrite.py,
  agent.py, tracing.py, capability_probe.py
pipeline/
  __init__.py, ingest.py, sources/__init__.py, sources/arxiv.py
interface/
  __init__.py, app.py
eval/
  __init__.py, build_groundtruth.py, eval_retrieval.py, eval_rag.py, .gitkeep
langfuse/README.md                                                    # Phase 6
docs/superpowers/specs/2026-07-26-arxiv-agent-design.md               # spec
docs/decisions/README.md                                              # ADRs
docs/handoffs/session-00.md                                           # handoffs
docs/plans/2026-07-26-arxiv-agent-plan.md                             # this file
notebooks/.gitkeep, tests/.gitkeep
```

Responsibilities:
- `arxiv_agent/config.py` — env-driven `Settings` (one source of truth).
- `arxiv_agent/llm.py` — `get_client()` + `chat()` (protocol-agnostic).
- `arxiv_agent/kb.py` — Qdrant collection create/upsert/search (4 modes).
- `arxiv_agent/reranker.py` — cross-encoder rerank.
- `arxiv_agent/tools/*` — tool callables + JSON schemas.
- `arxiv_agent/agent.py` — the loop; branches on ADR-01.
- `arxiv_agent/tracing.py` — Langfuse spans + score.
- `arxiv_agent/capability_probe.py` — Hy3 tool-call probe.
- `pipeline/sources/arxiv.py` — dlt source; `pipeline/ingest.py` — runner.
- `interface/app.py` — Chainlit UI.
- `eval/*` — offline retrieval + RAG eval scripts.

---

## Phase 0 — Scaffold [DONE]

See `docs/handoffs/session-00.md`. Proof: scaffold files present, `uv sync
--locked` green (255 packages, 3647-line lock), imports OK, compose YAML
valid. Committed pending user approval at end of Session 00.

---

## Phase 1 — Ingestion + Knowledge Base (dlt -> Qdrant)

**Goal:** A reproducible `uv run python -m pipeline.ingest` that pulls
arxiv CS.AI/CL/LG papers and populates a Qdrant collection with dense +
sparse vectors. Endpoint checkpoint: the collection point count equals the
ingested paper count.

**Pre-flight (Session 01 start):**
- [ ] Run the AGENTS.md session-start reality check; print Session State.
- [ ] `colima start`; populate `.env` from `.env.example` with the user's
      `OPENCODE_GO_API_KEY` (user action).
- [ ] `uv run python -m arxiv_agent.capability_probe` → write
      `docs/decisions/ADR-01-hy3-tool-calling.md` with the real result.
- [ ] `docker compose up -d qdrant`; wait for healthcheck.

### Task 1.1: arXiv dlt source

**Files:** Create `pipeline/sources/arxiv.py`; Test `tests/test_arxiv_source.py`.

**Interfaces:**
- Produces: `fetch_papers(max_results, categories) -> Iterator[dict]` where
  each dict = `{arxiv_id, title, authors (list[str]), summary, published
  (ISO), categories (list[str]), primary_category}`. Raises on HTTP error.
- Consumes: `arxiv_agent.config.settings.arxiv_categories`,
  `settings.arxiv_max_results`.

- [ ] **Step 1: Write the failing test** (offline; mock `requests.get` with
      a tiny arxiv Atom XML fixture in `tests/fixtures/one_paper.xml`)

```python
# tests/test_arxiv_source.py
from pipeline.sources.arxiv import parse_atom, fetch_papers

def test_parse_atom_extracts_one_paper():
    xml = open("tests/fixtures/one_paper.xml").read()
    docs = parse_atom(xml)
    assert len(docs) == 1
    d = docs[0]
    assert d["arxiv_id"] == "2401.00001"
    assert "Retrieval-Augmented" in d["title"]
    assert isinstance(d["authors"], list) and d["authors"]
    assert d["summary"]
    assert d["primary_category"] == "cs.AI"
```

- [ ] **Step 2: Run to verify it fails**
      `uv run pytest tests/test_arxiv_source.py -v` → FAIL (module empty).
- [ ] **Step 3: Implement** — Atom parsing with `xml.etree.ElementTree`
      (namespace `http://www.w3.org/2005/Atom`, arxiv `http://arxiv.org/schemas/atom`).
      `fetch_papers` paginates `http://export.arxiv.org/api/query?search_query=cat:cs.AI&start=S&max_results=M`
      in batches of 100, sleeps ≥3s between calls (arxiv rate limit), yields
      parsed dicts. Wrap as a `dlt.resource` with `primary_key="arxiv_id"`.
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(ingest): arxiv dlt source with atom parsing"`.

### Task 1.2: Qdrant collection + upsert (dense + sparse)

**Files:** Create/expand `arxiv_agent/kb.py`; Test `tests/test_kb.py`.

**Interfaces:**
- Produces:
  - `ensure_collection(client, collection, embed_dim)` — creates with named
    vectors `dense` (bge-small, 384-d) + sparse `text-sparse` (Qdrant
    `SparseVector` via `models.SparseVectorParams`).
  - `upsert_papers(client, collection, papers, embedder)` — embeds
    `"{title}\n{summary}\n{categories joined}"` dense; lets Qdrant compute
    sparse (payload text) OR computes sparse via Qdrant's built-in sparse
    embedding (enable `SparseVectorParams` with `modifier=...`) — confirm
    against Qdrant v1.11 docs. Upsert with payload + vectors.
- Consumes: `fastembed.TextEmbedding(settings.embed_model)`.

- [ ] **Step 0: Confirm Qdrant sparse-vector API for v1.11** — `find-docs`
      skill or Qdrant docs: how to enable + query sparse vectors (BM25) in
      `qdrant-client` >=1.11. Record the exact `SparseVectorParams` shape
      and the hybrid query request in a short note in `kb.py` docstring.
- [ ] **Step 1: Failing test** — spin an in-memory `QdrantClient(":memory:")`,
      `ensure_collection`, upsert 3 fake papers, assert `count` == 3 and a
      `query_points` dense search returns the relevant paper first.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `ensure_collection` + `upsert_papers`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(kb): qdrant hybrid collection upsert"`.

### Task 1.3: dlt runner `pipeline.ingest`

**Files:** Modify `pipeline/ingest.py`; Test `tests/test_ingest.py` (integration, marks `@pytest.mark.integration`, skipped if Qdrant down).

**Interfaces:** `main()` runs the dlt pipeline over `fetch_papers` into a
local intermediate, then `upsert_papers` into Qdrant. Prints final point
count. Idempotent (upsert by `arxiv_id`).

- [ ] **Step 1: Failing test** — `test_ingest_end_to_count`: bring up the
      in-memory Qdrant, monkeypatch `fetch_papers` to return 5 fake papers
      (avoid network), run `main()`, assert collection count == 5.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `main()`: `dlt.pipeline(...).run(fetch_papers(...))`
      into a `papers` table (a delta path), then drain rows →
      `upsert_papers(qdrant, collection, rows, embedder)`. Use dlt state to
      record last `published` for incremental runs. Print count.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(ingest): dlt runner populating qdrant"`.

### Task 1.4: Live ingest + checkpoint

- [ ] `colima start && docker compose up -d qdrant`.
- [ ] `uv run python -m pipeline.ingest` (pull ~3000 papers; may take
      ~10-20 min due to arxiv rate limits). Paste the final count into
      `docs/handoffs/session-01.md`.
- [ ] Verify: `curl -s http://localhost:6333/collections/arxiv_papers | uv run python -c "import sys,json; d=json.load(sys.stdin); print('points', d['result']['points_count'])"`
      — count matches the printed ingest count.
- [ ] Update PROGRESS.md Phase 1 → checked (with proof link to handoff).
- [ ] Commit PROGRESS + handoff: `git commit -m "chore: phase 1 checkpoint"`.

**Phase 1 checkpoint:** `python -m pipeline.ingest` prints upserted count
equal to Qdrant point count.

---

## Phase 2 — Retrieval + Rerank + Retrieval Eval

**Goal:** Implement the 4 retrieval modes and evaluate hit-rate@5 + MRR
over an LLM-generated ground truth; choose the best variant.

### Tasks (elaborated at Session 02 start, per the multi-session protocol):

- Task 2.1 `kb.search(query, mode)` — modes: `keyword`, `vector`, `hybrid`
  (Qdrant RRF fusion), `hybrid_rerank`. Failing test per mode against the
  in-memory fixture; commit.
- Task 2.2 `reranker.rerank(query, docs, top_k)` — fastembed
  `Xenova/ms-marco-MiniLM-L-6-v2`; unit test ordering; commit.
- Task 2.3 `tools/rewrite.rewrite_query(query)` — LLM keyword expansion;
  unit test with a stubbed `chat`; commit.
- Task 2.4 `eval/build_groundtruth.py` — hold out 50 papers; ask `Hy3` to
  generate 150 Q&A pairs each mapping to ≥1 expected `arxiv_id`; commit
  `eval/groundtruth.csv` (this file IS committed — not gitignored).
- Task 2.5 `eval/eval_retrieval.py` — compute the 4 variants ×
  {with,without rewrite} → `eval/retrieval_results.csv`; print best.
- Task 2.6 **Checkpoint** — paste output into handoff; mark PROGRESS Phase 2
  + retrieval-eval rubric + hybrid/rerank/rewrite bonus boxes; commit.

**Phase 2 checkpoint:** `eval/retrieval_results.csv` has ≥4 variant rows
(hit-rate@5 + MRR); best variant highlighted and used in production.

> Note: the `eval/*.csv` exception in `.gitignore` (only the generated
> results CSVs are ignored; `eval/groundtruth.csv` and final
> `eval/retrieval_results.csv` should be committed for peer review — adjust
> `.gitignore` at Task 2.5 to `!eval/groundtruth.csv !eval/retrieval_results.csv`).

---

## Phase 3 — Agent (handwritten loop, branch on ADR-01)

**Goal:** A CLI-runnable agent that answers a question with ≥1 cited arxiv_id.

### Tasks (elaborated at Session 03 start):

- Task 3.1 `tools/search.py` — `search_papers(query, mode)` callable +
  JSON schema; unit test against in-memory Qdrant.
- Task 3.2 `tools/fetch.py` — `fetch_arxiv(arxiv_id)` live arxiv API;
  unit test with mocked response.
- Task 3.3 `tools/rewrite.py` — wired to `rewrite_query`.
- Task 3.4 `tools/__init__.py` — `TOOL_REGISTRY: dict[str, (callable, schema)]`
  and `TOOL_DEFS: list[dict]`.
- Task 3.5 `agent.py` — the loop. Two implementations selected by ADR-01:
  - if `tool_calling=="yes"`: native function-calling while-loop
    (Module-1 style, iteration cap 6).
  - else: instruction-based plan-then-act: model emits JSON
    `{"action": "search_papers", "args": {...}}`; we parse + execute +
    feed result back; loop until `{"action": "final_answer", "args": {...}}`.
  - dev message: restrict to arxiv CS scope, require cited arxiv_ids,
    decline off-topic. Wrap iterations in Langfuse spans (Phase 6 wires
    real tracing; here stub the span context).
- Task 3.6 integration test — `agent_loop("What is retrieval-augmented
  generation?")` returns a string containing ≥1 regex `\b\d{4}\.\d{4,5}\b`
  (an arxiv id).
- Task 3.7 **Checkpoint** — paste CLI output to handoff; mark PROGRESS
  Phase 3; commit.

**Phase 3 checkpoint:** `uv run python -m arxiv_agent.agent "..."` prints
an answer with ≥1 cited arxiv_id.

---

## Phase 4 — LLM Evaluation

**Goal:** Compare ≥2 LLM approaches with LLM-as-judge; lock best config.

### Tasks (elaborated at Session 04 start):

- Task 4.1 `eval/eval_rag.py` — runs the agent (or the fixed RAG) over the
  ground-truth Q&A set under configs:
  - prompt A (concise+citations) vs prompt B (reasoning+citations)
  - `Hy3` vs `SECONDARY_MODEL` (if set)
  - with vs without `rewrite_query`
- Task 4.2 judge — `Hy3` (or secondary, suitably) scores each answer
  `RELEVANT/PARTLY/NON` + usefulness 1-5; write `eval/llm_results.csv`.
- Task 4.3 README §"Best config" documents the chosen config.
- Task 4.4 **Checkpoint** — mark PROGRESS Phase 4 + LLM-eval rubric; commit.

**Phase 4 checkpoint:** `eval/llm_results.csv` compares ≥2 configs with
judge scores; best documented in README.

---

## Phase 5 — Chainlit Interface

### Tasks (elaborated at Session 05):

- Task 5.1 `interface/app.py` — `@cl.on_message` → `arxiv_agent.agent_loop`;
  render answer + cited arxiv_id badges (Chainlit `cl.Step`/elements). Keep a
  sidebar `cl.ChatSettings` showing last retrieval (mode, #results).
- Task 5.2 `@cl.action` thumbs up/down → calls `tracing.score(...)` (Phase 6
  implements real; stub here).
- Task 5.3 local smoke — `uv run chainlit run interface/app.py --port 8000
  --headless`; `curl localhost:8000` returns nonzero HTML; chat works in a
  browser.
- Task 5.4 **Checkpoint** — mark PROGRESS Phase 5 + interface rubric; commit.

**Phase 5 checkpoint:** `chainlit run` serves on :8000 and answers with
citations; thumbs fires feedback.

---

## Phase 6 — Langfuse Monitoring

### Tasks (elaborated at Session 06):

- Task 6.1 `docker compose up -d langfuse-web langfuse-worker` (+deps);
  run `langfuse/provision.py` (Task 6.3) to make a project; write public/
  secret keys into `.env`.
- Task 6.2 `arxiv_agent/tracing.py` — `Langfuse` client + contextmanager
  spans: `trace(user_turn)` > `span(iteration)` > spans for `search`/`llm`/
  `fetch`. Score API for thumbs.
- Task 6.3 `langfuse/provision.py` + `dashboard.json` — create a project
  + ≥6 charts via Langfuse HTTP API:
  1. Avg response time per turn
  2. Token usage & cost per model
  3. Tool call counts per turn
  4. Relevance distribution (LLM-judge)
  5. User feedback ratio over time
  6. Hybrid-search rerank win-rate
- Task 6.4 wire `tracing` into `agent.py` + `interface/app.py` thumbs.
- Task 6.5 **Checkpoint** — dashboard shows ≥6 charts; one thumbs click
  registers a score; paste screenshot URLs to handoff; mark PROGRESS Phase 6
  + monitoring rubric; commit.

**Phase 6 checkpoint:** self-hosted Langfuse dashboard shows ≥6 charts and
feedback scores appear.

---

## Phase 7 — Containerization + Reproducibility

### Tasks (elaborated at Session 07):

- Task 7.1 Re-lint `docker-compose.yml` against real Langfuse v3
  self-host compose (image tags, volumes, envs) using `find-docs`; fix.
- Task 7.2 `Dockerfile` — `python:3.12-slim` + uv + `uv sync --locked
  --no-dev`; `CMD chainlit run`.
- Task 7.3 `docker compose config` valid; `colima start && docker compose
  up -d --build` brings up app + qdrant + langfuse; app reachable at :8000.
- Task 7.4 README — full run steps (colima, `.env`, ingest, eval, run,
  dashboard URLs, screenshots). Add an app preview video/screenshot.
- Task 7.5 Reproducibility — verify `uv.lock` present, `.env.example`
  complete, dataset rebuildable; mark PROGRESS Phase 7 + containerization +
  reproducibility rubrics; commit.

**Phase 7 checkpoint:** clean-machine `docker compose up -d` runs the full
stack; README complete.

---

## Phase 8 (bonus) — Cloud Deploy

### Tasks (elaborated only if time permits, after Phase 7):

- Task 8.1 Choose platform (fly.io for app+langfuse, or render + cloud
  Qdrant; record choice in an ADR).
- Task 8.2 Externalize config (env-driven; stateless app); deploy; verify
  public URL answers with citations.
- Task 8.3 README §"Deploy"; mark PROGRESS Phase 8 + cloud bonus; commit.

**Phase 8 checkpoint:** public URL answers a question with citations.

---

## Self-Review (plan vs spec)

- **Spec coverage:** §1 problem→README (Ph7), §3 data→Ph1, §4 retrieval→Ph2,
  §5 agent→Ph3, §6 LLM eval→Ph4, §7 interface→Ph5, §8 monitoring→Ph6,
  §9 containerization→Ph7, §10 reproducibility→Ph7, §11 layout→Ph0,
  §12 rubric→PROGRESS, §13 phases→this plan, §14 guardrails→AGENTS/handoffs.
  All covered. Cloud (§13 Ph8) is bonus and optional.
- **Placeholder scan:** Phases 2-8 tasks are intentionally task-level
  outlines to be elaborated at each session start (the spec is a
  multi-session phased build; Phase 1 outcomes + ADR-01 shape later
  code). This is deliberate scope decomposition, not hand-waving within a
  task. Phase 1 is fully detailed with real tests + code paths.
- **Type consistency:** `fetch_papers` → `upsert_papers` → `kb.search` share
  the `{arxiv_id, title, summary, ...}` shape. `TOOL_REGISTRY` keys
  (`search_papers`, `fetch_arxiv`, `rewrite_query`) match `agent.py` usage.
  `tracing.score` matches `interface/app.py` thumbs call.

## Execution Handoff

This is a multi-session project. Each phase = one session (or more), ending
in a checkpoint commit + handoff. At each session start, run the AGENTS.md
session-start protocol (read spec/handoff/PROGRESS, fingerprint
environment, run capability_probe), then elaborate the upcoming phase's
tasks into bite-sized steps via this plan + the executing-plans skill.

**Two execution options for the next session (Phase 1):**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per Phase 1
   task with two-stage review between tasks; fast, isolated.
2. **Inline Execution** — execute Phase 1 tasks in-session with checkpoints
   for your review.

**Which approach?** (Decide at the start of Session 01.)