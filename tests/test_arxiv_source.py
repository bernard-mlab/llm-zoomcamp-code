from pathlib import Path

from pipeline.sources.arxiv import parse_atom

FIXTURE = Path(__file__).parent / "fixtures" / "one_paper.xml"


def test_parse_atom_extracts_one_paper():
    xml = FIXTURE.read_text()
    docs = parse_atom(xml)
    assert len(docs) == 1
    d = docs[0]
    assert d["arxiv_id"] == "2401.00001"
    assert "Retrieval-Augmented" in d["title"]
    assert isinstance(d["authors"], list) and d["authors"]
    assert d["summary"]
    assert d["primary_category"] == "cs.AI"


def test_parse_atom_extracts_categories():
    xml = FIXTURE.read_text()
    docs = parse_atom(xml)
    d = docs[0]
    assert "cs.AI" in d["categories"]
    assert "cs.CL" in d["categories"]


def test_parse_atom_empty_feed():
    docs = parse_atom('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>')
    assert docs == []
