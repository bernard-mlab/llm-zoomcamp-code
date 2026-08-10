from unittest.mock import MagicMock, patch

import pytest

from arxiv_agent.tools import TOOL_DEFS, TOOL_REGISTRY


def test_registry_has_three_tools():
    assert set(TOOL_REGISTRY.keys()) == {"search_papers", "fetch_arxiv", "rewrite_query"}


def test_tool_defs_has_three_schemas():
    assert len(TOOL_DEFS) == 3
    names = {d["function"]["name"] for d in TOOL_DEFS}
    assert names == {"search_papers", "fetch_arxiv", "rewrite_query"}


def test_all_tool_schemas_have_required_fields():
    for schema in TOOL_DEFS:
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert "parameters" in schema["function"]
        assert schema["function"]["parameters"]["type"] == "object"


@patch("arxiv_agent.tools.fetch.requests.get")
def test_fetch_arxiv_returns_dict(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
    <entry>
        <id>http://arxiv.org/abs/2401.00001v1</id>
        <title>Test Paper</title>
        <summary>A test summary.</summary>
        <published>2024-01-01T00:00:00Z</published>
        <author><name>Test Author</name></author>
        <category term="cs.AI"/>
        <primary_category xmlns="http://arxiv.org/schemas/atom" term="cs.AI"/>
    </entry>
</feed>"""
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    from arxiv_agent.tools.fetch import fetch_arxiv

    result = fetch_arxiv("2401.00001")
    assert result is not None
    assert result["arxiv_id"] == "2401.00001"
    assert result["title"] == "Test Paper"


@patch("arxiv_agent.tools.fetch.requests.get")
def test_fetch_arxiv_returns_none_for_missing(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    from arxiv_agent.tools.fetch import fetch_arxiv

    result = fetch_arxiv("9999.99999")
    assert result is None