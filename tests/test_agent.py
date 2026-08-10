import json
from unittest.mock import MagicMock, patch

from arxiv_agent.agent import agent_loop, _make_call


def test_make_call_dispatches_search():
    call = MagicMock()
    call.function.name = "rewrite_query"
    call.function.arguments = '{"query": "test query"}'
    call.id = "call_1"

    with patch.dict("arxiv_agent.agent.TOOL_REGISTRY", {"rewrite_query": lambda **k: ["test query"]}):
        result = _make_call(call)
    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call_1"
    assert "test query" in result["content"]


def test_make_call_handles_unknown_tool():
    call = MagicMock()
    call.function.name = "nonexistent"
    call.function.arguments = "{}"
    call.id = "call_2"

    result = _make_call(call)
    assert "error" in result["content"]


def test_make_call_handles_tool_error():
    call = MagicMock()
    call.function.name = "search_papers"
    call.function.arguments = '{"query": "test"}'
    call.id = "call_3"

    def boom(**kwargs):
        raise RuntimeError("boom")

    with patch.dict("arxiv_agent.agent.TOOL_REGISTRY", {"search_papers": boom}):
        result = _make_call(call)
    assert "error" in result["content"]
    assert "boom" in result["content"]


def test_agent_loop_returns_string():
    """Unit test with mocked LLM — verifies loop structure, not real LLM calls."""
    choice = MagicMock()
    choice.message.content = "RAG combines retrieval with generation [arxiv:2401.00001]."
    choice.message.tool_calls = None
    mock_resp = MagicMock()
    mock_resp.choices = [choice]

    with patch("arxiv_agent.agent.chat", return_value=mock_resp):
        result = agent_loop("What is RAG?", max_iterations=3)
    assert isinstance(result, str)
    assert "arxiv:2401.00001" in result


def test_agent_loop_handles_tool_calls_then_final_answer():
    """Two-turn: LLM calls search, we return results, LLM gives final answer."""
    tc = MagicMock()
    tc.id = "call_1"
    tc.function.name = "search_papers"
    tc.function.arguments = '{"query": "retrieval augmented generation", "mode": "hybrid_rerank"}'

    call_choice = MagicMock()
    call_choice.message.content = None
    call_choice.message.tool_calls = [tc]
    resp1 = MagicMock()
    resp1.choices = [call_choice]

    final_choice = MagicMock()
    final_choice.message.content = "RAG is a technique [arxiv:2401.00001]."
    final_choice.message.tool_calls = None
    resp2 = MagicMock()
    resp2.choices = [final_choice]

    mock_results = [{"arxiv_id": "2401.00001", "title": "RAG Paper", "summary": "A RAG paper.", "score": 0.9}]

    with patch("arxiv_agent.agent.chat", side_effect=[resp1, resp2]):
        with patch.dict("arxiv_agent.agent.TOOL_REGISTRY", {"search_papers": lambda **k: mock_results}):
            result = agent_loop("What is RAG?", max_iterations=5)

    assert "arxiv:2401.00001" in result