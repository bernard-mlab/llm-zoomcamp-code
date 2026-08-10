# Session 03 — Phase 3: Agent (handwritten loop)

**Date**: 2026-08-10
**Phase**: Phase 3 — Agent
**Result**: Phase 3 checkpoint reached (agent loop working with live LLM + Qdrant; 28 tests green; 5 citations in real answer).

## State fingerprint at close

- colima: **running** (arch: aarch64, runtime: docker)
- docker: **ok** (Server v28.3.3)
- compose ps: `arxiv-research-assistant-qdrant-1` (Up, healthy)
- qdrant: **healthz ok + 2176 points** (status: green)
- langfuse: **down** (not started — Phase 6)
- Hy3 tool-call: **yes** (re-confirmed at session start; ADR-01 accepted)
- open key: `OPENCODE_GO_API_KEY` **set** in `.env`

## What changed this session

### Pre-flight
- Ran AGENTS.md session-start protocol; printed Session State block.
- Re-confirmed 18/18 tests green; Qdrant has 2176 points; Hy3 tool-calling confirmed.
- **Found + fixed drift**: `test_dense_search_returns_relevant` was flaky — `FakeDenseModel` used `hash()` which is randomized per Python process. Replaced with deterministic `sum(ord(c) % 10) / 10.0`. Verified stable across 3 runs.

### Task 3.1-3.3: Tool registry (commit `e7cf3a7`)
- `tools/search.py`: `search_papers(query, mode)` callable + `SEARCH_TOOL_SCHEMA` (JSON schema for function-calling).
- `tools/fetch.py`: `fetch_arxiv(arxiv_id)` live arxiv API via `requests.get` + `parse_atom` + `FETCH_TOOL_SCHEMA`.
- `tools/__init__.py`: `TOOL_REGISTRY` (name→callable) + `TOOL_DEFS` (JSON schemas for all 3 tools) + `REWRITE_TOOL_SCHEMA`.
- `tests/test_tools.py`: 5 tests (registry size, schema fields, fetch returns dict, fetch returns None for missing).
- TDD: RED → ImportError; GREEN → 5/5 passing.

### Task 3.4: Agent loop (commit `3f5e73c`)
- `arxiv_agent/agent.py`: handwritten while-loop using native function-calling (per ADR-01):
  - `INSTRUCTIONS` dev message: restricts to arxiv CS scope, requires citations, encourages multiple searches.
  - `_make_call(call)`: dispatches to `TOOL_REGISTRY`, returns `{"role": "tool", "tool_call_id": ..., "content": ...}` (Chat Completions API format).
  - `agent_loop(question, model, max_iterations=6)`: sends messages + `TOOL_DEFS` to LLM; appends assistant messages + tool results; loops until no tool_calls or iteration cap.
- **Key fix**: initial implementation used Responses API format (`function_call_output`) → 400 error. Switched to Chat Completions API format (`role: "tool"` + `tool_call_id`).
- `tests/test_agent.py`: 5 tests (make_call dispatch, unknown tool, tool error, loop returns string, loop handles tool calls then final answer). All use mocked LLM — no real API calls in unit tests.
- TDD: RED → AttributeError (mock structure wrong); fix mock structure → GREEN → 5/5 passing.

### Integration test (live, commit `3f5e73c`)
Ran `uv run python -m arxiv_agent.agent "What is retrieval-augmented generation?"`:

**Answer** (truncated, full in commit message):
> RAG is a technique that combines a pre-trained generative language model with an external, non-parametric "memory" (a retriever over a knowledge source) so the model can pull in relevant documents at inference time and condition its generation on them **[arxiv:2005.11401]**...
>
> The foundational formulation (Lewis et al., 2020) pairs:
> - **Parametric memory** — a pre-trained seq2seq model...
> - **Non-parametric memory** — a dense vector index (e.g., Wikipedia)...
>
> Pure parametric LMs... suffer from hallucinations, stale knowledge, and lack of verifiability **[arxiv:2005.11401, arxiv:2403.03187]**...

**5 cited arxiv_ids**: `2005.11401`, `2403.03187`, `2406.00083`, `2507.04069`, `2403.09727`

### Test suite at close
```
$ uv run pytest tests/ -v
tests/test_agent.py .....        [ 17%]
tests/test_arxiv_source.py ...    [ 28%]
tests/test_ingest.py ..           [ 35%]
tests/test_kb.py .....            [ 53%]
tests/test_rewrite.py ...        [ 64%]
tests/test_search.py .....       [ 82%]
tests/test_tools.py .....        [100%]
28 passed in 1.32s
```

## Rubric delta

- [x] Phase 3 — Agent (verified: live answer with 5 cited arxiv_ids)
- [x] Retrieval flow — KB + LLM used (2 pts): `agent.py` calls `kb.search` via `search_papers` tool + LLM via `chat`

## Open decisions / blockers

1. **Agent answer quality**: the live test produced a rich, well-cited answer. The agent made multiple tool calls (search + rewrite) across iterations. No issues observed.
2. **No Langfuse tracing yet**: agent loop has no tracing spans (Phase 6). The `tracing.py` stub is still a placeholder.
3. **`content=None` in assistant message**: when the LLM issues tool calls, `assistant_msg.content` is sometimes `None`. We set `"content": assistant_msg.content or ""` to avoid sending null content. This works but could be cleaner.
4. **Iteration cap not hit**: the agent completed in fewer than 6 iterations. The cap is a safety net.

## Next session's first task (Session 04)

**Phase 4 — LLM Evaluation**

1. Run AGENTS.md session-start protocol.
2. `uv run pytest tests/ -v` (verify 28 tests still pass).
3. `eval/eval_rag.py`: run the agent (or fixed RAG) over the 21 ground-truth Q&A pairs under configs:
   - prompt A (concise+citations) vs prompt B (reasoning+citations)
   - `Hy3` vs `SECONDARY_MODEL` (if set)
   - with vs without `rewrite_query`
4. LLM-as-judge scores `RELEVANT/PARTLY/NON` + usefulness 1–5; write `eval/llm_results.csv`.
5. Add "with rewrite vs without rewrite" retrieval eval row to `eval_retrieval.py`.
6. README §"Best config" documents the chosen config.
7. Checkpoint: commit + handoff.

First command: `uv run pytest tests/ -v` (verify all 28 tests still pass).

## Known-good verification command set (must pass before Session 04 starts new work)

```
cd /Users/b.yeo/Desktop/Github/llm-zoomcamp-code/Assignment/arxiv-research-assistant
git status --short                    # clean working tree
uv run pytest tests/ -v               # 28 passed
colima status                         # running
curl -s http://localhost:6333/healthz # healthz check passed
curl -s http://localhost:6333/collections/arxiv_papers | python3 -c "import sys,json; print('points:', json.load(sys.stdin)['result']['points_count'])"
                                      # points: 2176
uv run python -m arxiv_agent.agent "What is RAG?"  # returns answer with citations
```