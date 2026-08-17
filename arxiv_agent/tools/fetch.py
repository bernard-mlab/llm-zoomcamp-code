"""Tool: fetch_arxiv(arxiv_id) -> live arxiv API metadata. Phase 3."""
from __future__ import annotations

import requests

from pipeline.sources.arxiv import parse_atom

ARXIV_ID_LOOKUP_URL = "http://export.arxiv.org/api/query"

FETCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "fetch_arxiv",
        "description": "Fetch full metadata for a specific arXiv paper by its ID (e.g. '2401.00001'). Use this to verify or get details about a paper you found via search.",
        "parameters": {
            "type": "object",
            "properties": {
                "arxiv_id": {
                    "type": "string",
                    "description": "The arXiv paper ID, e.g. '2401.00001'.",
                },
            },
            "required": ["arxiv_id"],
        },
    },
}


def fetch_arxiv(arxiv_id: str) -> dict | None:
    params = {"id_list": arxiv_id, "max_results": 1}
    response = requests.get(ARXIV_ID_LOOKUP_URL, params=params, timeout=15)
    response.raise_for_status()

    papers = parse_atom(response.text)
    if not papers:
        return None

    paper = papers[0]
    return {
        "arxiv_id": paper["arxiv_id"],
        "title": paper["title"],
        "authors": paper["authors"],
        "summary": paper["summary"],
        "published": paper["published"],
        "categories": paper["categories"],
        "primary_category": paper["primary_category"],
    }