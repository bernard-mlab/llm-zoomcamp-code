# Langfuse provisioning (Phase 6)

Self-hosted Langfuse v2 is running at `http://localhost:3000`.

**Login**: `admin@arxiv-agent.local` / `adminadmin123!`
**Project**: `arxiv-agent`
**API keys** (already configured in `.env`):
- `LANGFUSE_PUBLIC_KEY=pk-lf-c027cf3f3b7a6daa`
- `LANGFUSE_SECRET_KEY=sk-lf-...`

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

## One-time setup

If you start from a clean database, Langfuse v2 needs:
1. First user signup via the web UI at `http://localhost:3000` (Sign up with
   email + password — creates user only, no project).
2. Create a project + API key through the UI (Settings → API Keys).
3. Copy the keys into `.env` as `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`.
4. Restart the app: `docker-compose restart app`.

For this setup the organization/project/api-key were inserted directly into
the Postgres database (see `langfuse/provision.py` for the SQL) — useful when
the web UI's NextAuth flow is hard to script.