"""Handwritten agent loop (Module-1 style, generalized to a 3-tool registry).

Phase 3. Uses native function-calling (ADR-01 confirmed Hy3 supports it).
See spec §5 and AGENTS.md (Hy3 capability rule).
"""
from __future__ import annotations

import json
import sys

from arxiv_agent.config import settings
from arxiv_agent.llm import chat
from arxiv_agent.tools import TOOL_DEFS, TOOL_REGISTRY

INSTRUCTIONS = """You're an arXiv research assistant.
You help researchers find and understand papers from arXiv CS.AI/CL/LG.

You have access to tools:
- search_papers: Search arXiv papers by query. Use 'hybrid_rerank' for best results.
- fetch_arxiv: Fetch full metadata for a specific arXiv paper by ID.
- rewrite_query: Rewrite a query into alternative keywords.

When answering:
- Always cite arxiv_ids of the papers you reference (e.g. [arxiv:2401.00001]).
- Make multiple searches if needed — try different keywords and modes.
- If the question is not about CS/AI/ML research, politely decline.
- Base your answer on the retrieved papers, not your general knowledge.
- Ask if the user wants to explore related topics.

Make multiple searches. First perform search, analyze the results, and then
perform more searches with different keywords if the initial results are incomplete.
""".strip()


def _make_call(call) -> dict:
    name = call.function.name
    args = json.loads(call.function.arguments)
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        result = {"error": f"Unknown tool: {name}"}
    else:
        try:
            result = fn(**args)
        except Exception as e:
            result = {"error": f"{type(e).__name__}: {e}"}
    return {
        "role": "tool",
        "tool_call_id": call.id,
        "content": json.dumps(result, indent=2, default=str),
    }


def agent_loop(question: str, model: str | None = None, max_iterations: int = 6) -> str:
    messages = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": question},
    ]
    model = model or settings.llm_model

    for iteration in range(1, max_iterations + 1):
        response = chat(messages, model=model, tools=TOOL_DEFS)

        if not response.choices:
            break

        assistant_msg = response.choices[0].message

        tool_calls = getattr(assistant_msg, "tool_calls", None)

        if not tool_calls:
            return assistant_msg.content or ""

        reply = {"role": "assistant", "content": assistant_msg.content or ""}
        reply["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ]
        messages.append(reply)

        for tc in tool_calls:
            call_output = _make_call(tc)
            messages.append(call_output)

    return "I could not find enough information to answer within the iteration budget."


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What is retrieval-augmented generation?"
    print(agent_loop(q))