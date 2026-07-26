# Langfuse provisioning (Phase 6)

This directory provisions the self-hosted Langfuse project, API keys, and a
>=6-chart dashboard via the Langfuse HTTP API.

- `provision.py` — create a Langfuse project, write `LANGFUSE_PUBLIC_KEY` /
  `LANGFUSE_SECRET_KEY` into `.env`, and create the dashboard charts.
- `dashboard.json` — the dashboard definition (>=6 charts, see spec §8).

Charts (spec §8):
1. Avg response time per turn
2. Token usage & cost per model
3. Tool call counts per turn (search/fetch/rewrite)
4. Relevance distribution (LLM-judge)
5. User feedback ratio over time
6. Hybrid-search rerank win-rate (#times rerank changed top-1)

Run in Phase 6 (after Langfuse stack is up):

```bash
colima start && docker compose up -d langfuse-web
uv run python langfuse/provision.py
```