import re

import pytest

from interface.app import ARXIV_ID_PATTERN


def test_arxiv_id_pattern_matches_standard_id():
    text = "RAG combines retrieval with generation [arxiv:2005.11401]."
    ids = ARXIV_ID_PATTERN.findall(text)
    assert ids == ["2005.11401"]


def test_arxiv_id_pattern_matches_multiple_ids():
    text = "See [arxiv:2005.11401] and also [arxiv:2403.03187] for more."
    ids = ARXIV_ID_PATTERN.findall(text)
    assert ids == ["2005.11401", "2403.03187"]


def test_arxiv_id_pattern_no_match():
    text = "No citations here."
    ids = ARXIV_ID_PATTERN.findall(text)
    assert ids == []


def test_arxiv_id_pattern_matches_in_brackets():
    text = "References: [arxiv:2406.00083, arxiv:2507.04069]"
    ids = ARXIV_ID_PATTERN.findall(text)
    assert "2406.00083" in ids
    assert "2507.04069" in ids