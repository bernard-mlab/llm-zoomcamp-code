"""Tool: fetch_arxiv(arxiv_id) -> live arxiv API metadata. Phase 3."""
from __future__ import annotations

# GET http://export.arxiv.org/api/query?id_list=<arxiv_id>. See spec §5.