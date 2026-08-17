"""capability_probe — detect Hy3 tool-calling support via the opencode-go proxy.

Run before assuming Hy3 supports native tool-calling — never assume, always
probe. Records tool_calling = yes | no | partial plus the supporting evidence.
"""
from __future__ import annotations

import json
import sys

from .config import settings
from .llm import chat


def probe() -> dict:
    """Return {tool_calling, model, evidence}.

    - 'yes'   : the model returned a tool_calls array with our search schema
    - 'no'    : the endpoint rejected the tools param or ignored it
    - 'partial': returned text that looks like a tool call but not native
    """
    result = {"model": settings.llm_model, "tool_calling": "unknown", "evidence": ""}
    if not settings.llm_configured:
        result["tool_calling"] = "unconfigured"
        result["evidence"] = "OPENCODE_GO_API_KEY / BASE_URL not set in .env"
        return result

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_papers",
                "description": "Search arxiv papers by query.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]
    messages = [
        {"role": "system", "content": "You can call the search_papers tool."},
        {"role": "user", "content": "Find recent papers on retrieval-augmented generation."},
    ]
    try:
        resp = chat(messages, tools=tools)
    except Exception as e:  # noqa: BLE001
        result["tool_calling"] = "no"
        result["evidence"] = f"tools param rejected: {type(e).__name__}: {e}"
        return result

    msg = resp.choices[0].message
    if getattr(msg, "tool_calls", None):
        result["tool_calling"] = "yes"
        result["evidence"] = json.dumps(
            [
                {"name": tc.function.name, "args": tc.function.arguments}
                for tc in msg.tool_calls
            ]
        )
    else:
        content = (msg.content or "").strip()
        looks_like_json_action = "search_papers" in content
        result["tool_calling"] = "partial" if looks_like_json_action else "no"
        result["evidence"] = f"content={content[:300]!r}"
    return result


if __name__ == "__main__":
    out = probe()
    print(f"tool_calling={out['tool_calling']}")
    print(f"model={out['model']}")
    print(f"evidence={out['evidence']}")
    sys.exit(0 if out["tool_calling"] in {"yes", "no", "partial"} else 1)