"""dlt arXiv source — paginated pull of CS.AI/CL/LG papers. Phase 1.

Returns documents: {arxiv_id, title, authors, summary, published,
categories, primary_category}. dlt handles incremental state so re-runs only
fetch new papers. See spec §3.
"""
from __future__ import annotations

import dlt


@dlt.source
def arxiv_source(max_results: int = 3000, categories: tuple[str, ...] = ("cs.AI",)):
    # Phase 1: implement the REST resource with pagination over
    # http://export.arxiv.org/api/query?search_query=cat:cs.AI&start=..&max_results=..
    raise NotImplementedError("Phase 1")