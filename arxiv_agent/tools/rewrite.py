"""Tool: rewrite_query(query) -> alternative phrasings/keywords. Phase 3 / Phase 2."""
from __future__ import annotations

import json

from arxiv_agent.llm import chat
from arxiv_agent.config import settings

REWRITE_PROMPT = """You are a search query rewriter for an arXiv research paper database.
Given a user question, produce 3-5 alternative search queries or keyword phrases
that would help find relevant arXiv CS papers. Include abbreviations, synonyms,
and technical terms.

Return ONLY a JSON list of strings, no explanation.

User question: {question}
"""

def rewrite_query(query: str, model: str | None = None) -> list[str]:
    prompt = REWRITE_PROMPT.format(question=query)
    messages = [
        {"role": "system", "content": "You produce JSON search query expansions."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = chat(messages, model=model or settings.llm_model)
        content = response.choices[0].message.content or ""
        queries = json.loads(content)
        if isinstance(queries, list):
            result = [query] + [str(q) for q in queries]
            return list(dict.fromkeys(result))
    except (json.JSONDecodeError, Exception):
        pass

    return [query]
