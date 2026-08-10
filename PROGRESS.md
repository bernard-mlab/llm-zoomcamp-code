# PROGRESS.md — arXiv Research Assistant

Phased build tracker + rubric checklist. Each line: `[ ] item | artifact path | verification command`. A checkbox is checked ONLY when the verification command runs green AND its real output is pasted in the latest `docs/handoffs/session-NN.md` (proof rule, AGENTS.md §Proof rule).

Current phase: **Phase 1 — Ingestion + KB**

## Phases

- [x] Phase 0 — Scaffold | repo skeleton + design + plan + guardrails | `test -f pyproject.toml && test -f AGENTS.md && test -f PROGRESS.md`
- [x] Phase 1 — Ingestion + KB | `pipeline/ingest.py`, Qdrant collection `arxiv_papers` | `uv run python -m pipeline.ingest` prints upserted count == Qdrant point count (verified Session 01: 2176 papers ingested; dense search returns relevant results)
- [ ] Phase 2 — Retrieval + Rerank | `arxiv_agent/kb.py`, `arxiv_agent/reranker.py`, `eval/eval_retrieval.py` | `uv run python eval/eval_retrieval.py` prints >=4 variant rows; `eval/retrieval_results.csv` best=hybrid_rerank
- [ ] Phase 3 — Agent | `arxiv_agent/agent.py` + `tools/` | `uv run python -m arxiv_agent.agent "what is retrieval-augmented generation?"` prints an answer with >=1 cited arxiv_id
- [ ] Phase 4 — LLM eval | `eval/build_groundtruth.py`, `eval/eval_rag.py` | `uv run python eval/eval_rag.py` writes `eval/llm_results.csv` with >=1 best-config row documented in README
- [ ] Phase 5 — Interface (Chainlit) | `interface/app.py` | `uv run chainlit run interface/app.py --port 8000 --headless` starts; `curl localhost:8000` nonzero
- [ ] Phase 6 — Monitoring (Langfuse) | `langfuse/` provisioning + tracing in `arxiv_agent/tracing.py` | self-hosted Langfuse dashboard shows >=6 charts and feedback scores appear after one Chainlit thumbs click
- [ ] Phase 7 — Containerization + Reproducibility | `docker-compose.yml`, `Dockerfile`, README | `colima start && docker compose up -d` brings up app+qdrant+langfuse; README run instructions complete; `uv.lock` present
- [ ] Phase 8 (bonus) — Cloud deploy | deploy config | public URL answers a question with citations

## Rubric checklist (each tied to proof)

### Core
- [ ] Problem description (2) | README §1 + design doc | README has "Problem" section describing arxiv agent use case
- [ ] Retrieval flow — KB + LLM used (2) | `arxiv_agent/kb.py` + `arxiv_agent/llm.py` | both exist and are called from `agent.py`
- [ ] Retrieval evaluation — multiple approaches, best used (2) | `eval/retrieval_results.csv` | file has >=4 variant rows with hit-rate@5 + MRR; best highlighted
- [ ] LLM evaluation — multiple approaches, best used (2) | `eval/llm_results.csv` | file compares >=2 prompt variants (and/or models) with LLM-as-judge scores; best documented
- [ ] Interface — UI (2) | `interface/app.py` (Chainlit) | `docker compose up` serves Chainlit at :8000
- [x] Ingestion pipeline — automated (2) | `pipeline/ingest.py` (dlt) | `uv run python -m pipeline.ingest` runs unattended and populates Qdrant (verified: 2176 papers)
- [ ] Monitoring — feedback + dashboard >=5 charts (2) | `arxiv_agent/tracing.py` + `langfuse/` | dashboard shows >=6 charts; thumbs send feedback scores
- [ ] Containerization — everything in docker-compose (2) | `docker-compose.yml` | `docker compose config` valid; app+qdrant+langfuse(+deps) all defined
- [ ] Reproducibility (2) | README + `uv.lock` + `.env.example` | README run steps complete; `uv.lock` present; `.env.example` lists all keys

### Best practices (bonus)
- [ ] Hybrid search (text + vector), at least evaluated (+1) | `eval/retrieval_results.csv` | a "hybrid" row exists and is evaluated alongside keyword-only and vector-only
- [ ] Document re-ranking (+1) | `arxiv_agent/reranker.py` | cross-encoder rerank applied + a "hybrid_rerank" eval row exists
- [ ] User query rewriting (+1) | `tools/rewrite.py` | `rewrite_query` tool wired + an eval row comparing with/without rewrite exists

### Bonus (not covered in course)
- [ ] Cloud deployment (+2) | deploy config | public URL answering questions
- [ ] Extra (+up to 3) | README "Highlights" section | reviewer-visible extras listed

## Capability probe (seen at every session touching the agent)

- [x] Hy3 tool-call capability | `docs/decisions/ADR-01-hy3-tool-calling.md` | `uv run python -m arxiv_agent.capability_probe` prints `tool_calling=yes` (verified Session 01: native function-calling confirmed)

## Session log

- Session 00: scaffolded repo, spec, AGENTS, PROGRESS, plan. Handoff: `docs/handoffs/session-00.md`. (No prior state; clean machine.)
- Session 01: Phase 1 complete (dlt source + Qdrant KB + 2176 papers ingested; 10 tests green; ADR-01 written). Handoff: `docs/handoffs/session-01.md`.