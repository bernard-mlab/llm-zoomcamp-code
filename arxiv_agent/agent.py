"""Handwritten agent loop (Module-1 style, generalized to a 3-tool registry).

Phase 3. Branches on Hy3 tool-calling capability (see capability_probe and
ADR-01): native function-calling if supported, else instruction-based
plan-then-act. See spec §5 and AGENTS.md (Hy3 capability rule).
"""
from __future__ import annotations


def agent_loop(question: str, model: str | None = None, max_iterations: int = 6) -> str:
    # Phase 3: implement the while loop with tool registry, citations,
    # iteration cap, and Langfuse tracing spans.
    raise NotImplementedError("Phase 3")


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "What is retrieval-augmented generation?"
    print(agent_loop(q))