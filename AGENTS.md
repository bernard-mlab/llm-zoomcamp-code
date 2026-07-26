# AGENTS.md — arXiv Research Assistant (session contract)

This file binds any AI coding agent (opencode, claude, etc.) working in this
repo. It is the operational contract for session continuity and
anti-hallucination. Read it fully before doing anything.

**Ground-truth files (read before any work):**
1. `docs/superpowers/specs/2026-07-26-arxiv-agent-design.md` — the approved
   spec. Settled decisions. Do not re-litigate without an ADR.
2. `PROGRESS.md` — rubric + phase checklist. Each item has an artifact path
   and a verification command.
3. `docs/handoffs/session-NN.md` — latest handoff wins.
4. `docs/decisions/ADR-NN.md` — deviations from this spec.

## Session-start protocol (mandatory, in order, before any code/edit)

1. Read the spec, the latest handoff, and `PROGRESS.md`.
2. Print a **Session State** block (see below) and STOP. Do not edit,
   commit, or build until the user acknowledges the state is correct.
3. Only after acknowledgement, proceed to the next task the user requests.

## Session State block (the FIRST thing you output each session)

```
[Session start] reading spec + latest handoff + PROGRESS.md

Environment fingerprint:
  colima:        <running|stopped>   (`colima status`)
  docker:        <ok|fail>            (`docker version ...`)
  compose ps:    <services up|none>
  qdrant:        <healthz ok + N points | down>
  langfuse:      <health ok | down>
  Hy3 tool-call: <yes|no|partial|unknown>   (`uv run python -m arxiv_agent.capability_probe`)
  open key:      OPENCODE_GO_API_KEY=<set|unset in env>

Reconciliation vs PROGRESS.md:
  - <for each checked item, paste the green verification output or flag drift>
  - <list any drift>

Next task (from latest handoff): <one line>
```

Then wait for the user. If a probe contradicts PROGRESS.md (a "done" item
fails its command), do NOT silently fix — surface the drift and reconcile
`PROGRESS.md` first.

## Proof rule (no completion without proof)

A rubric item / phase may be marked done in `PROGRESS.md` only if ALL hold:
1. The named artifact exists at its path.
2. Its verification command runs green.
3. The command's real output (not paraphrased) is pasted into the session
   handoff.

Paraphrased "it works" claims are invalid.

## Decision rule (no hallucinated rationale)

The spec + ADRs are the only source of decisions. Referencing a decision
requires citing its ADR number or spec section. Un-cited "decisions" are
treated as not-made. A deviation from the spec requires writing a new
`docs/decisions/ADR-NN.md` (context, decision, alternatives, status,
discovery command) BEFORE acting on it.

## Hy3 capability rule (biggest hallucination vector)

Never assume `Hy3` (via the opencode-go proxy) supports OpenAI
function-calling. At the start of any session that touches the agent, run
`uv run python -m arxiv_agent.capability_probe` and record the result
(`tool_calling: yes|no|partial`) in the Session State block and (first run)
in `docs/decisions/ADR-01.md`. The agent's loop implementation branch
(native tool calls vs instruction-based plan-act) follows this probe, not
assumption.

## Handoff rule (end every session)

Before ending a session, write `docs/handoffs/session-NN.md` (increment the
number) with: state fingerprint at close, what changed (files + commands +
output), rubric delta (unchecked→checked with proof links), open
decisions/blockers (never silently deferred), next session's first task
(exact command), and the known-good verification command set.

## Tooling & environment

- Python via `uv` only (no raw pip). `uv sync`, `uv add`, `uv run`.
- Docker via **colima** locally (`colima start` before `docker compose`).
- LLM: OpenAI-compatible client pointed at the opencode-go proxy; model id
  `Hy3`; env-swappable. Keys come from `.env` (see `.env.example`); do NOT
  commit secrets.

## Commit policy

Do not commit unless the user explicitly asks. Stage only intended files.
Never commit secrets / `.env`.