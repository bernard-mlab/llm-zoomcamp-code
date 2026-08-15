"""dlt arXiv source — paginated pull of CS.AI/CL/LG papers.

Returns documents: {arxiv_id, title, authors, summary, published,
categories, primary_category}. dlt handles incremental state so re-runs only
fetch new papers. See spec §3.
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator

import dlt
import requests

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

ARXIV_API_URL = "http://export.arxiv.org/api/query"
BATCH_SIZE = 100
RATE_LIMIT_SECONDS = 3
RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 5.0


def parse_atom(xml_string: str) -> list[dict]:
    root = ET.fromstring(xml_string)
    entries = root.findall(f"{ATOM_NS}entry")
    papers = []
    for entry in entries:
        id_text = entry.findtext(f"{ATOM_NS}id", "")
        arxiv_id = _strip_arxiv_id(id_text)

        authors = []
        for author_el in entry.findall(f"{ATOM_NS}author"):
            name = author_el.findtext(f"{ATOM_NS}name", "")
            if name:
                authors.append(name)

        categories = [
            cat.get("term", "")
            for cat in entry.findall(f"{ATOM_NS}category")
            if cat.get("term")
        ]

        primary_cat_el = entry.find(f"{ARXIV_NS}primary_category")
        primary_category = primary_cat_el.get("term", "") if primary_cat_el is not None else ""

        papers.append(
            {
                "arxiv_id": arxiv_id,
                "title": entry.findtext(f"{ATOM_NS}title", "").strip(),
                "authors": authors,
                "summary": entry.findtext(f"{ATOM_NS}summary", "").strip(),
                "published": entry.findtext(f"{ATOM_NS}published", ""),
                "categories": categories,
                "primary_category": primary_category,
            }
        )
    return papers


def _strip_arxiv_id(id_url: str) -> str:
    prefix = "http://arxiv.org/abs/"
    bare = id_url[len(prefix):] if id_url.startswith(prefix) else id_url
    if bare.endswith("v1") or bare.endswith("v2") or bare.endswith("v3"):
        bare = bare.rsplit("v", 1)[0]
    return bare


def _build_search_query(categories: tuple[str, ...]) -> str:
    return " OR ".join(f"cat:{c}" for c in categories)


def _get_with_retry(params: dict) -> requests.Response:
    last_exc: requests.RequestException | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = requests.get(ARXIV_API_URL, params=params, timeout=60)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_BASE_DELAY * (2**attempt))
    raise last_exc  # type: ignore[misc]


@dlt.resource(primary_key="arxiv_id")
def fetch_papers(
    max_results: int = 3000,
    categories: tuple[str, ...] = ("cs.AI",),
) -> Iterator[dict]:
    search_query = _build_search_query(categories)
    retrieved = 0
    start = 0

    first_batch = True
    while retrieved < max_results:
        if not first_batch:
            time.sleep(RATE_LIMIT_SECONDS)
        first_batch = False

        batch_limit = min(BATCH_SIZE, max_results - retrieved)
        params = {
            "search_query": search_query,
            "start": start,
            "max_results": batch_limit,
        }
        response = _get_with_retry(params)

        papers = parse_atom(response.text)
        if not papers:
            break

        for paper in papers:
            yield paper

        retrieved += len(papers)
        start += len(papers)

        if len(papers) < batch_limit:
            break