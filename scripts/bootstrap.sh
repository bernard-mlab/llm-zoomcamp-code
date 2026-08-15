#!/usr/bin/env bash
# arxiv-research-assistant — bootstrap the full stack on a fresh machine.
# Run from the project root (where pyproject.toml + arxiv_agent/ live).
# Usage:  ./scripts/bootstrap.sh            # run every stage
#         ./scripts/bootstrap.sh <stage>    # run one stage
# Stages: preflight colima deps services langfuse ingest probe tests build app e2e summary
set -uo pipefail

STAGE="${1:-all}"
ROOT_OK=0
if [[ -f pyproject.toml && -d arxiv_agent ]]; then ROOT_OK=1; fi

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
elif docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
else
  COMPOSE=()
fi

say() { printf '\n\033[1;36m[%s]\033[0m %s\n' "$1" "$2"; }
ok()  { printf '  \033[1;32mOK\033[0m %s\n' "$1"; }
warn(){ printf '  \033[1;33mWARN\033[0m %s\n' "$1"; }
fail(){ printf '  \033[1;31mFAIL\033[0m %s\n' "$1"; }

req() { command -v "$1" >/dev/null 2>&1 || { fail "missing required tool: $1"; return 1; }; }

preflight() {
  say "PREFLIGHT" "checking prerequisites"
  if [[ $ROOT_OK -ne 1 ]]; then fail "not at project root (need pyproject.toml + arxiv_agent/)"; return 1; fi
  req brew || return 1
  req colima || { warn "install with: brew install colima"; return 1; }
  req docker || { warn "install with: brew install docker"; return 1; }
  if [[ ${#COMPOSE[@]} -eq 0 ]]; then fail "neither docker-compose nor 'docker compose' found; brew install docker-compose"; return 1; fi
  req uv || { warn "install with: brew install uv"; return 1; }
  free_gb=$(df -g "$HOME" | awk 'NR==2{print $4}')
  if (( free_gb < 25 )); then warn "only ${free_gb}GiB free on / — the colima disk + image build need >=25GiB headroom (a full host disk killed the previous VM)"; fi
  if [[ ! -f .env ]]; then
    fail ".env missing — copy from .env.example and fill OPENCODE_GO_API_KEY / OPENCODE_GO_BASE_URL first"
    printf '    cp .env.example .env  &&  edit OPENCODE_GO_* lines\n'
    return 1
  fi
  if ! grep -q '^OPENCODE_GO_API_KEY=.\+' .env; then warn "OPENCODE_GO_API_KEY is empty in .env — probe + e2e will fail (tests + build still run)"; fi
  ok "prerequisites present (compose=${COMPOSE[*]})"
}

colima_stage() {
  say "COLIMA" "starting the Docker runtime (target 4 CPU / 8GiB / 100GiB)"
  if colima status >/dev/null 2>&1; then ok "colima already running"; else
    if colima list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx colima; then
      colima start || { fail "colima start failed"; return 1; }
    else
      colima start --cpu 4 --memory 8 --disk 100 || { fail "colima start failed"; return 1; }
    fi
  fi
  docker info >/dev/null 2>&1 || { fail "docker daemon not reachable after colima start"; return 1; }
  mem=$(colima list 2>/dev/null | awk 'NR==2{print $5}' | tr -d 'GiB')
  ok "colima running ($(colima list 2>/dev/null | awk 'NR==2{printf "%s CPU / %s / %s disk",$3,$5,$6}'))"
  if awk "BEGIN{exit !($mem<4)}" 2>/dev/null; then warn "memory <4GiB — redispose: colima stop && colima start --cpu 4 --memory 8 --disk 100 (or colima delete to recreate)"; fi
}

deps() {
  say "DEPS" "uv sync (runtime + dev group, fetches Python 3.12 if needed)"
  uv sync || { fail "uv sync failed"; return 1; }
  uv run python -c "import pytest" 2>/dev/null && ok "dev group installed (pytest present)" || warn "pytest missing — run: uv sync (dev group)"
}

wait_http() {
  local url="$1" tries="${2:-30}" expect="${3:-200}"
  for ((i=1;i<=tries;i++)); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo 000)
    [[ "$code" == "$expect" || "$code" == "200" ]] && return 0
    sleep 5
  done
  return 1
}

services() {
  say "SERVICES" "bring up Qdrant + Langfuse stack"
  [[ ${#COMPOSE[@]} -gt 0 ]] || { fail "no compose command"; return 1; }
  "${COMPOSE[@]}" up -d qdrant langfuse-web >/dev/null 2>&1 || { fail "compose up failed"; return 1; }
  say "SERVICES" "waiting for Qdrant :6333 (up to ~3min)"
  wait_http http://localhost:6333/healthz 36 && ok "qdrant healthz" || { fail "qdrant not healthy"; return 1; }
  say "SERVICES" "waiting for Langfuse :3000 (up to ~5min)"
  wait_http http://localhost:3000/api/public/health 60 && ok "langfuse healthy" || warn "langfuse not healthy yet (may still be migrating) — continue, recheck later"
  "${COMPOSE[@]}" ps 2>/dev/null || true
}

langfuse_stage() {
  say "LANGFUSE" "one-time project + user setup (best-effort via provision.py)"
  if wait_http http://localhost:3000/api/public/health 12; then
    uv run python langfuse/provision.py || warn "provision.py did not complete — that's OK if setup already done"
  else
    warn "langfuse not reachable — run this stage again after 'services'"
  fi
  cat <<'NOTE'
  To get API keys (browser, ~1 min):
    1. open http://localhost:3000
    2. login: admin@arxiv-agent.local / adminadmin123!
    3. Settings -> API Keys -> Create -> copy the pk-lf-... and sk-lf-...
    4. paste into .env as LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
    5. (optional) scripts/bootstrap.sh app   # restart app to pick up the keys
  Tracing silently no-ops without keys, so the app still serves if you defer this.
NOTE
}

qdrant_points() {
  curl -s http://localhost:6333/collections/arxiv_papers 2>/dev/null | \
    uv run python -c "import sys,json; d=json.load(sys.stdin); print((d.get('result') or {}).get('points_count') or 0)" 2>/dev/null || echo 0
}

ingest() {
  say "INGEST" "ensure the KB is populated (downloads bge-small + SPLADE on first run, ~15-30min)"
  pts=$(qdrant_points)
  if (( pts > 0 )); then ok "collection already has ${pts} points — skipping ingest"; return 0; fi
  uv run python -m pipeline.ingest || { fail "ingest failed (arXiv API can be flaky — re-run: ./scripts/bootstrap.sh ingest)"; return 1; }
  pts=$(qdrant_points)
  (( pts > 0 )) && ok "ingested; collection now has ${pts} points" || { fail "ingest reported but 0 points"; return 1; }
}

probe() {
  say "PROBE" "Hy3 tool-calling capability check (requires OPENCODE_GO_* in .env)"
  if ! grep -q '^OPENCODE_GO_API_KEY=.\+' .env; then warn "OPENCODE_GO_API_KEY empty in .env — skipping probe"; return 0; fi
  uv run python -m arxiv_agent.capability_probe || { warn "probe failed — check OPENODE_GO_BASE_URL / key"; return 0; }
  ok "probe complete (expect tool_calling=yes above)"
}

tests() {
  say "TESTS" "pytest (no LLM calls — safe without API key)"
  uv run pytest tests/ -q || { fail "tests failed"; return 1; }
  ok "tests passed"
}

build() {
  say "BUILD" "docker-compose build app (cold cache ~10-15min; uses 'uv sync --locked --no-dev')"
  [[ ${#COMPOSE[@]} -gt 0 ]] || { fail "no compose command"; return 1; }
  "${COMPOSE[@]}" build app || { fail "build failed — check disk space (>=25GiB) and Dockerfile"; return 1; }
  ok "app image built"
}

app() {
  say "APP" "serve Chainlit at :8000"
  [[ ${#COMPOSE[@]} -gt 0 ]] || { fail "no compose command"; return 1; }
  "${COMPOSE[@]}" up -d app >/dev/null 2>&1 || { fail "compose up app failed"; return 1; }
  say "APP" "waiting for :8000 (up to ~3min)"
  wait_http http://localhost:8000 36 && ok "app serving HTTP 200 at http://localhost:8000" || { fail "app not up"; return 1; }
}

e2e() {
  say "E2E" "one agent question (requires OPENCODE_GO_* + populated KB)"
  if ! grep -q '^OPENCODE_GO_API_KEY=.\+' .env; then warn "OPENCODE_GO_API_KEY empty — skipping e2e (fill .env and rerun)"; return 0; fi
  pts=$(qdrant_points); (( pts > 0 )) || { warn "KB empty — run './scripts/bootstrap.sh ingest' first"; return 0; }
  uv run python -m arxiv_agent.agent "what is retrieval-augmented generation?" || { warn "agent run failed"; return 0; }
  ok "agent answered — check Langfuse at http://localhost:3000 for the trace"
}

summary() {
  cat <<'SUM'

  ===== arxiv-research-assistant: bootstrap summary =====
  Services:
    Chainlit chat UI : http://localhost:8000
    Qdrant           : http://localhost:6333  (healthz at /healthz)
    Langfuse         : http://localhost:3000  (login admin@arxiv-agent.local / adminadmin123!)
  Remaining manual items (if not done):
    - Add Langfuse API keys to .env (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY), then ./scripts/bootstrap.sh app
    - Capture screenshots into docs/screenshots/ (README has placeholders)
    - Mark Phase 7 + Reproducibility done in PROGRESS.md with proof, then git commit + push
  See docs/setup/m3-rebuild.md for the full runbook.
SUM
}

all() {
  preflight || return 1
  colima_stage || return 1
  deps || return 1
  services || return 1
  langfuse_stage
  ingest || return 1
  probe
  tests || return 1
  build || return 1
  app || { warn "app stage failed — you can still run host-side without it"; }
  e2e
  summary
}

case "$STAGE" in
  all)      all ;;
  preflight) preflight ;;
  colima)   colima_stage ;;
  deps)     deps ;;
  services) services ;;
  langfuse) langfuse_stage ;;
  ingest)   ingest ;;
  probe)    probe ;;
  tests)    tests ;;
  build)    build ;;
  app)      app ;;
  e2e)      e2e ;;
  summary)  summary ;;
  *) echo "unknown stage: $STAGE"; echo "stages: preflight colima deps services langfuse ingest probe tests build app e2e summary all"; exit 2 ;;
esac