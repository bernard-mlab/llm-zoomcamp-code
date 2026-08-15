# M3 setup runbook — rebuild the arXiv Research Assistant stack

> **For the AI agent (Claude) doing the setup on the M3:** read this fully,
> then read `AGENTS.md` (the session contract) and `docs/handoffs/session-07.md`
> (why this rebuild is needed + exact state). Follow `AGENTS.md`'s session-start
> protocol: print the Session State block and reconcile against `PROGRESS.md`
> before marking anything done. Hard rule: never claim a rubric item is done
> without pasting real command output (proof rule, `AGENTS.md`).

## Context

This is the **LLM Zoomcamp final project** — an agentic RAG copilot over arXiv
CS.AI/CL/LG papers (agent + hybrid Qdrant KB + reranker + Chainlit UI +
self-hosted Langfuse monitoring). Phases 0–6 are complete in code; Phase 7
(containerization + reproducibility) was nearly done on the original machine
when the colima VM's filesystem corrupted (host disk hit 99% during the image
build). The VM was deleted. Everything is rebuildable from this repo — the only
external dependency is the **OPENCODE_GO LLM proxy** (API key + base URL).

Branch: `project/arxiv-agent` (HEAD = Phase 7 WIP commit). Project files live at
the **repo root** after clone (not nested).

## Prerequisites (one-time, on the M3)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"  # if brew missing
brew install colima docker docker-compose uv
which colima docker docker-compose uv        # all present
gh auth login                                # only if the repo is private
```

`uv` auto-fetches Python 3.12 (project pins `>=3.12,<3.13`) — no separate
Python/mise step needed. The M3 is arm64; every compose image is arm64-compatible.

## Step 1 — get the code

```bash
cd ~/Projects   # or wherever you keep repos
git clone -b project/arxiv-agent git@github.com:bernard-mlab/llm-zoomcamp-code.git
cd llm-zoomcamp-code
git log --oneline -3   # top = "Phase 7 WIP ...", then f46aadd Phase 6, 8d54492 Phase 5
ls                     # confirm arxiv_agent/ pipeline/ interface/ docker-compose.yml at ROOT
```

## Step 2 — environment + deps

```bash
cp .env.example .env
# Edit .env and fill in (these are gitignored, so NOT in the clone):
#   OPENCODE_GO_API_KEY=<from the original machine's .env>
#   OPENCODE_GO_BASE_URL=<from the original machine's .env>
#   OPENCODE_GO_MODEL=Hy3
# Leave LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY as placeholders for now.
uv sync          # installs runtime + dev group (pytest, ruff, bcrypt, jupyterlab)
```

The LLM proxy (OPENCODE_GO) is reachable from the M3 (confirmed by the user).
The agent, eval, and capability probe all call it; tests do NOT (they mock the
LLM), so tests pass even before the key is set.

## Step 3 — bootstrap the stack (automated)

A staged, idempotent helper is at `scripts/bootstrap.sh`. Run it from the repo
root. It handles colima (4 CPU / 8 GiB / 100 GiB), deps, services, ingest,
probe, tests, image build, app, and an end-to-end agent question.

```bash
./scripts/bootstrap.sh            # run everything, in order, with smart skips
# or one stage at a time:
./scripts/bootstrap.sh preflight  # checks tools + .env + disk headroom
./scripts/bootstrap.sh colima
./scripts/bootstrap.sh services   # qdrant + langfuse stack up + healthy
./scripts/bootstrap.sh ingest     # ~15-30min first run (downloads bge-small + SPLADE)
./scripts/bootstrap.sh probe      # tool_calling=yes
./scripts/bootstrap.sh tests      # 32 passed
./scripts/bootstrap.sh build     # docker-compose build app (cold cache ~10-15min)
./scripts/bootstrap.sh app        # Chainlit at :8000
./scripts/bootstrap.sh e2e        # one agent answer with citations
```

Stages are safe to re-run (they detect existing state and skip — e.g. `ingest`
skips if the collection already has points). Expected end state:
- Chainlit at http://localhost:8000 (HTTP 200)
- Qdrant at http://localhost:6333 (`healthz check passed`), ~2950–3000 points
- Langfuse at http://localhost:3000 (healthy), a fresh trace from the e2e run

## Step 4 — Langfuse API keys (manual, ~1 min)

Tracing silently no-ops without keys, so the app serves even if you defer this,
but to get traces + the dashboard you need keys:

1. Open http://localhost:3000 and log in: `admin@arxiv-agent.local` / `adminadmin123!`
2. Settings → API Keys → Create → copy the `pk-lf-...` and `sk-lf-...`
3. Paste into `.env` as `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`
4. `./scripts/bootstrap.sh app` (restarts the app to pick up the keys)

If `langfuse/provision.py` already ran, the user + project exist; just create
keys in the UI. If first-run signup via the UI doesn't create a project, run
`uv run python langfuse/provision.py` which calls the one-shot setup endpoint.

## Step 5 — finish Phase 7 (the actual deliverable)

Once the stack is green, close out the phase:
1. Capture the 3 screenshots the README placeholders reference into
   `docs/screenshots/` (Chainlit chat, Langfuse dashboard, agent answer w/ citations).
2. Update `README.md`'s Screenshots section to point at the real files.
3. In `PROGRESS.md`, check **Phase 7**, **Containerization**, and **Reproducibility**
   — but ONLY after pasting the real verification output into a new
   `docs/handoffs/session-08.md` (proof rule). Then commit + push.

## Verification (the "done" bar — paste real output into the handoff)

```bash
uv run pytest tests/ -q                              # -> 32 passed
curl -s http://localhost:6333/healthz                # -> healthz check passed
curl -s http://localhost:3000/api/public/health      # -> {"status":"OK",...}
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000   # -> 200
uv run python -m arxiv_agent.capability_probe        # -> tool_calling=yes
uv run python -m arxiv_agent.agent "what is mixture of experts?"  # cited arxiv_ids
```

## Gotchas (learned the hard way on the original machine)

- **Keep >=25 GiB host disk free.** The colima `diffdisk` grows on the host; the
  host hitting 99% is what corrupted the previous VM. `scripts/bootstrap.sh
  preflight` warns if you're under 25 GiB.
- **Qdrant image is v1.18.0** (matches the client). Don't downgrade — the old
  v1.11.3 on-disk format panics v1.18.0. A fresh empty volume + reingest is correct.
- **uv 0.12.x**: the repo already uses `[dependency-groups] dev` (not
  `[project.optional-dependencies]`), so bare `uv sync` installs pytest. Don't
  revert `pyproject.toml` to the old form or dev deps silently vanish.
- **`docker-compose` (hyphenated) vs `docker compose` (plugin)**: the repo uses
  the hyphenated form; the v2 plugin also works. `bootstrap.sh` auto-detects.
- **The build needs README.md**: `Dockerfile` copies `README.md` before
  `uv sync --locked --no-dev` (hatchling builds the package and reads the readme).
  Don't remove that COPY line.
- **arXiv API is flaky**: `pipeline/sources/arxiv.py` retries 503s with backoff.
  If ingest dies, just re-run `./scripts/bootstrap.sh ingest`.
- **Never commit `.env`** — it holds the proxy key + Langfuse keys (gitignored).
- **Langfuse `score()` may 500** (a pre-existing migration gap): thumbs feedback
  is still captured via the UI; traces + spans work. Non-blocking.