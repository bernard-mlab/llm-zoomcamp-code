from unittest.mock import MagicMock, patch

from arxiv_agent.tools.rewrite import rewrite_query


@patch("arxiv_agent.tools.rewrite.chat")
def test_rewrite_query_returns_list(mock_chat):
    mock_msg = MagicMock()
    mock_msg.message.content = '["retrieval augmented generation", "RAG", "knowledge-intensive NLP"]'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_msg]
    mock_chat.return_value = mock_resp

    result = rewrite_query("What is retrieval-augmented generation?")
    assert isinstance(result, list)
    assert len(result) >= 2
    assert "retrieval augmented generation" in result


@patch("arxiv_agent.tools.rewrite.chat")
def test_rewrite_query_handles_json_error(mock_chat):
    mock_msg = MagicMock()
    mock_msg.message.content = "This is not JSON at all."
    mock_resp = MagicMock()
    mock_resp.choices = [mock_msg]
    mock_chat.return_value = mock_resp

    result = rewrite_query("What is RAG?")
    assert isinstance(result, list)
    assert len(result) >= 1


@patch("arxiv_agent.tools.rewrite.chat")
def test_rewrite_query_includes_original(mock_chat):
    mock_msg = MagicMock()
    mock_msg.message.content = '["RAG", "retrieval augmentation"]'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_msg]
    mock_chat.return_value = mock_resp

    result = rewrite_query("What is retrieval-augmented generation?")
    assert any("retrieval" in r.lower() or "rag" in r.lower() for r in result)