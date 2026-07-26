# Session 00 — Scaffold & Plan

**Date**: 2026-07-26
**Phase**: Phase 0 — Scaffold
**Result**: Phase 0 checkpoint reached (design + scaffold + guardrails in place).

## State fingerprint at close

- colima: **stopped** (`colima status` → fatal: not running)
- docker: **fail** (no `DOCKER_HOST`; daemon not reachable — expected because
  colima is stopped). `docker compose config` is a static validation and will
  be run once colima is up; deferred to when containerization is exercised.
- compose ps: N/A (not started)
- qdrant: **down** (not yet deployed)
- langfuse: **down** (not yet deployed)
- Hy3 tool-call: **unknown** — capability probe not run: capability_probe.py
  is a stub and the `OPENCODE_GO_API_KEY` was not present in the agent's env
  during this scaffold session (keys live in opencode's config, not exported
  to the bash shell). **First task of Session 01.**
- open key: `OPENCODE_GO_API_KEY` in shell env: **unset** (user must populate
  `.env`)

## What changed this session

Created the project worktree on branch `project/arxiv-agent` at
`Assignment/arxiv-research-assistant/`, cleared inherited zoomcamp files,
and wrote the scaffold:

- `docs/superpowers/specs/2026-07-26-arxiv-agent-design.md` — approved
  design (§1–§14).
- `docs/plans/2026-07-26-arxiv-agent-plan.md` — phased implementation plan.
- `AGENTS.md` — session contract (session-start protocol, proof rule,
  decision rule, Hy3 capability rule).
- `PROGRESS.md` — phased + rubric checklist with one verification command
  per item.
- `docs/handoffs/session-00.md` — this file.
- `docs/decisions/.gitkeep` — placeholder for ADRs (ADR-01 to be written in
  Session 01 with the Hy3 probe result).
- `pyproject.toml`, `uv.lock` — dependencies locked.
- `.env.example`, `.gitignore`, `README.md`.
- `docker-compose.yml`, `Dockerfile` — initial compose (qdrant + langfuse
  stack + app + ingest profile) — to be verified/linted once colima is up.
- `arxiv_agent/` skeleton: `config.py`, `llm.py`, `kb.py`, `reranker.py`,
  `tools/{search,fetch,rewrite}.py`, `agent.py`, `tracing.py`,
  `capability_probe.py`.
- `pipeline/ingest.py`, `pipeline/sources/arxiv.py` — scaffolds.
- `interface/app.py` — Chainlit scaffold.
- `eval/build_groundtruth.py`, `eval/eval_retrieval.py`, `eval/eval_rag.py`
  — scaffolds.

Verification at close (Phase 0 checkpoint per spec §13), real output:

```
$ test -f pyproject.toml && test -f AGENTS.md && test -f PROGRESS.md && echo "OK: scaffold files present"
OK: scaffold files present

$ test -f uv.lock && echo "OK: uv.lock present ($(wc -l < uv.lock) lines)"
OK: uv.lock present (    3647 lines)

$ uv sync --locked 2>&1 | tail -2
Resolved 255 packages in 3ms
Checked 181 packages in 20ms
locked-sync-exit=0

$ uv run python -c "import arxiv_agent, arxiv_agent.config, arxiv_agent.llm, pipeline, pipeline.sources, interface, eval; print('imports OK')"
imports OK   (warn: VIRTUAL_ENV points at parent repo's .venv; uv ignores it and uses this project's .venv — harmless)

$ uv run python -m arxiv_agent.capability_probe
tool_calling=unconfigured
model=Hy3
evidence=OPENCODE_GO_API_KEY / BASE_URL not set in .env   # expected — no key in shell env during scaffold

$ uv run python -c "import yaml; d=yaml.safe_load(open('docker-compose.yml')); print('YAML OK; services:', ', '.join(d['services']))"
YAML OK; services: qdrant, postgres-langfuse, clickhouse, redis, minio, langfuse-web, langfuse-worker, app, ingest
expected services present
```

Deferred (needs colima/docker compose plugin up — Session 01):

```
colima start
docker compose config          # full compose validation (docker compose plugin missing during Session 00)
docker compose up -d qdrant langfuse-web
uv run python -m arxiv_agent.capability_probe   # after .env is populated -> writes ADR-01
```

## Rubric delta

- Phase 0 box: unchecked → **checked** (proof: the three named files exist;
  `uv sync` green — output to be pasted in Session 01 alongside the colima
  start).
- No rubric items completed yet — core rubric work begins at Phase 1.

## Open decisions / blockers

1. **Hy3 tool-call capability unknown.** Cannot run `capability_probe.py`
   until `OPENCODE_GO_API_KEY` is in `.env`. This decides agent
   implementation branch (native tool calls vs instruction-based
   plan-then-act). To be resolved at the very start of Session 01 and
   recorded in `docs/decisions/ADR-01.md`. This is the biggest
   anti-hallucination item — do not assume.
2. **colima stopped.** Phase 1 ingestion does NOT need Docker (we can run
   Qdrant via a local `uv run` qdrant server? no — Qdrant runs in Docker or
   as a binary). Either start colima in Session 01, or run Qdrant via
   `qdrant/qdrant` docker under colima. Decision deferred to Session 01
   start; record in a short ADR if we deviate from "docker-compose first".
3. **Separate repo vs worktree branch.** Currently a worktree branch sharing
   the zoomcamp repo's .git. For peer review the rubric prefers a separate
   repo. Decision: keep the worktree for build isolation now; at Phase 7
   (or earlier if needed) split into a clean standalone GitHub repo. No ADR
   needed (matches spec §11 note); track as a Phase 7 sub-task.
4. **Embedding model choice.** Spec says `BAAI/bge-small-en-v1.5` via
   fastembed. Confirm it's available in fastembed build pinned; verify during
   Phase 1.

## Next session's first task (Session 01)

1. `colima start` (and `cd` into the worktree).
2. Populate `.env` from `.env.example` with the user's `OPENCODE_GO_API_KEY`
   (user action).
3. Run the **reality-check protocol** (AGENTS.md) and print the Session
   State block.
4. Run `uv run python -m arxiv_agent.capability_probe` → write
   `docs/decisions/ADR-01.md` with the `tool_calling` result.
5. Begin **Phase 1 — Ingestion + KB**: implement the dlt arxiv source and
   `pipeline/ingest.py` to populate Qdrant collection `arxiv_papers`. First
   command: `colima start && docker compose up -d qdrant && uv run python
   -m pipeline.ingest`.

## Known-good verification command set (must pass before Session 01 starts new work)

```
cd /Users/b.yeo/Desktop/Github/llm-zoomcamp-code/Assignment/arxiv-research-assistant
test -f pyproject.toml && test -f AGENTS.md && test -f PROGRESS.md && echo OK
uv sync --locked           # should be green; uv.lock present
test -f uv.lock && echo "lock present"
git status --short         # clean working tree after commit
```