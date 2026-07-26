# ADRs (Architecture Decision Records)

Decisions that deviate from the approved design spec
(`docs/superpowers/specs/2026-07-26-arxiv-agent-design.md`) are recorded here.

Naming: `ADR-NN-short-slug.md`. Each record contains:

- **Context** — what situation forced the decision
- **Decision** — what we chose
- **Alternatives considered** — and why rejected
- **Status** — proposed | accepted | superseded by ADR-XX
- **Discovery command** — the exact command whose output drove the decision
  (anti-hallucination: the decision must be reproducible)

## Pending ADRs

- `ADR-01-hy3-tool-calling.md` — to be written in Session 01 after running
  `uv run python -m arxiv_agent.capability_probe`. Decides whether the agent
  loop uses native function-calling or an instruction-based plan-then-act
  fallback. THIS IS THE BIGGEST HALLUCINATION VECTOR — do not implement the
  agent loop before it exists.