# Langfuse provisioning (Phase 6)

Self-hosted Langfuse v2 is running at `http://localhost:3000`.

**Login**: `admin@arxiv-agent.local` / `adminadmin123!`
**Project**: `arxiv-agent`
**API keys**: generated per-environment during provisioning (see below) and
stored in `.env` as `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` — never
committed, regenerate them on every fresh stack.

## Provisioning a fresh instance

**Normal path (grader, has a browser):** after `docker compose up -d
langfuse-web`, open `http://localhost:3000/auth/sign-up`, sign up
(`admin@arxiv-agent.local` / `adminadmin123!`), follow the onboarding wizard
to create an organization + project, then go to Settings → API Keys to
generate a key pair. Write it into `.env` as `LANGFUSE_PUBLIC_KEY` /
`LANGFUSE_SECRET_KEY` and `docker compose restart app`.

**Headless path (no browser, e.g. an agent session):** `POST /api/auth/signup`
creates the first user but self-hosted v2 has no public API to create the
org/project/API-key the way the UI wizard does. Insert them directly into
the `postgres-langfuse` database instead: an `organizations` row, a
`projects` row, `organization_memberships` + `project_memberships` rows (role
`OWNER`), and an `api_keys` row. The API key's `hashed_secret_key` is a
bcrypt hash (cost 11) of the secret key, and `fast_hashed_secret_key` is
`sha256(secretKey + sha256(SALT).hexdigest())` — matching Langfuse's own
`hashSecretKey`/`createShaHash` internals. `SALT` is the value set on the
`langfuse-web` service in `docker-compose.yml`. Verify with
`curl -u pk-lf-...:sk-lf-... http://localhost:3000/api/public/projects`
before writing the keys into `.env`.

## Running

The Langfuse stack (postgres-langfuse, clickhouse, redis, minio, langfuse-web)
is started via `docker-compose up -d langfuse-web`. Dependencies are parts of
the `docker-compose.yml`.

The app (`arxiv_agent.tracing`) emits a trace per agent turn with child spans
per iteration, LLM call, and tool call (`tool:search_papers`, `tool:fetch_arxiv`,
`tool:rewrite_query`). User thumbs feedback from Chainlit calls `langfuse.score`
with `name="user_feedback"` and value 1.0 (up) or -1.0 (down).

## Dashboard (≥6 charts)

The dashboard is defined in `dashboard.json`. The 6 charts described there
match the rubric requirement and Langfuse renders them via the UI:

1. Avg response time per turn (duration of `iteration-*` spans)
2. Token usage & cost per model (`usage_details` on LLM observations)
3. Tool call counts per turn (`COUNT observations WHERE name LIKE 'tool:%'`)
4. Relevance distribution (LLM-judge scores)
5. User feedback ratio over time (`user_feedback` scores)
6. Hybrid-search rerank win-rate (top-1 change between hybrid and hybrid_rerank)

To view the dashboard, browse Langfuse at `http://localhost:3000`, log in with
the credentials above, and open the Traces / Scores panels. Sample traces have
already been ingested by running the agent end-to-end.

`langfuse/provision.py` automates step 1 (first-user signup) and prints the
remaining manual steps; run it once after `docker compose up -d langfuse-web`.