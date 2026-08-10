# ADR-01: Hy3 tool-calling capability

**Date**: 2026-08-10 (Session 01)
**Status**: accepted
**Discovery command**: `uv run python -m arxiv_agent.capability_probe`

## Context

The spec (§5) defines two possible agent loop implementations, chosen at
runtime based on whether the LLM supports native OpenAI function-calling:

- **Native branch**: Module-1 style while-loop using the OpenAI `tools` param
  with JSON-schema tool definitions.
- **Fallback branch**: instruction-based plan-then-act where the model emits
  a JSON action string we parse.

AGENTS.md mandates never assuming `Hy3` (via the opencode-go proxy) supports
function-calling. The capability probe is the gate.

## Discovery output (verbatim, Session 01)

```
$ uv run python -m arxiv_agent.capability_probe
tool_calling=yes
model=hy3
evidence=[{"name": "search_papers", "args": "{\"query\": \"retrieval-augmented generation\"}"}]
```

The model emitted a native `tool_calls` array with a `search_papers`
function call whose arguments parsed as valid JSON.

## Decision

Use the **native function-calling branch** of the handwritten agent loop.
Do not implement the instruction-based plan-then-act fallback (YAGNI).

## Alternatives considered

1. **Implement both branches with runtime detection** — rejected: adds
   complexity and a code path we will never exercise. The probe is cheap
   and can be re-run if the model or proxy changes; if a future probe
   returns `no`, we add the fallback then.
2. **Instruction-based plan-then-act only** — rejected: the probe proves
   native tool calls work; falling back would be deliberately worse.

## Re-verification

Any session touching the agent re-runs the probe (AGENTS.md §Hy3 capability
rule). If a future probe returns `no` or `partial`, this ADR is superseded
by ADR-02 (native branch disabled, fallback implemented).
