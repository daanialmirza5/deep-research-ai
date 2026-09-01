import asyncio

import pytest

from ai.graph.build import build_research_graph
from ai.graph.state import AgentName
from ai.llm.base import LLMMessage
from ai.tests.fakes import FakeEmbeddingProvider, FakeLLMProvider, FakeTool, FakeVectorStore

pytestmark = pytest.mark.asyncio

EXPECTED_NODE_ORDER: list[AgentName] = [
    "planner",
    "research",
    "retriever",
    "summarizer",
    "fact_checker",
    "writer",
    "reviewer",
    "citation",
    "evaluation",
    "memory",
]


def _scripted_llm_response(messages: list[LLMMessage]) -> str:
    """Several agents share one LLMProvider in the real graph; dispatch on
    each agent's distinct system prompt (the only thing that tells them
    apart from the fake's side) so each gets a reply its own parsing logic
    expects."""
    system = messages[0].content
    if "planning agent" in system:
        return "1. Search\n2. Synthesize"
    if "compress raw search results" in system:
        return "RAG combines retrieval with generation."
    if "fact-checking agent" in system:
        return "VERIFIED: sources are sufficient"
    if "writing agent" in system:
        return "# Report\n\nRAG combines retrieval with generation [1]."
    if "reviewing agent" in system:
        return "APPROVED"
    if "Score the following" in system:
        return "0.9"
    raise AssertionError(f"unexpected system prompt in scripted test: {system!r}")


async def test_graph_runs_start_to_finish_through_all_ten_nodes_with_real_findings() -> None:
    """The Phase 8 exit criterion, as an assertion: a run with real tool
    results flowing through every agent, executing through all 10 nodes
    without looping (the fake LLM always answers VERIFIED/APPROVED)."""
    llm = FakeLLMProvider(response=_scripted_llm_response)
    embeddings = FakeEmbeddingProvider()
    tool = FakeTool()
    vector_store = FakeVectorStore()
    graph = build_research_graph(llm, embeddings, tools=[tool], vector_store=vector_store)

    final_state = await graph.ainvoke(
        {
            "session_id": "s1",
            "project_id": "p1",
            "query": "What is retrieval-augmented generation?",
            "revision_count": 0,
        }
    )

    visited = [msg.split("]")[0].removeprefix("[") for msg in final_state["messages"]]
    assert visited == EXPECTED_NODE_ORDER

    assert final_state["revision_count"] == 0
    assert final_state["fact_check_verdict"] == "verified"
    assert final_state["review_approved"] is True
    assert len(final_state["research_findings"]) == 1
    assert len(final_state["retrieved_context"]) == 1
    assert len(final_state["citations"]) == 1
    assert final_state["quality_score"] == 0.9
    # Token usage (Phase 11) — overwritten each LLM call, not accumulated
    # (see ai/agents/base.py._llm_usage), so this reflects the last caller
    # (evaluation) rather than a running total; per-node totals are what
    # AgentRun.output_state actually persists, covered in test_agents.py.
    assert final_state["prompt_tokens"] == FakeLLMProvider.FAKE_PROMPT_TOKENS
    assert final_state["llm_model"] == "fake-model"

    # Planner, Summarizer, FactChecker, Writer, Reviewer, Evaluation all
    # called the (fake) LLM; Retriever called the (fake) embedding provider
    # and the (fake) vector store — proving the DI wiring, not just that the
    # nodes ran.
    assert len(llm.calls) == 6
    assert len(embeddings.calls) == 1
    assert len(vector_store.calls) == 1
    assert tool.calls == ["What is retrieval-augmented generation?"]


async def test_graph_is_deterministic_across_repeated_runs() -> None:
    graph = build_research_graph(
        FakeLLMProvider(response=_scripted_llm_response),
        FakeEmbeddingProvider(),
        tools=[FakeTool()],
    )

    result_a = await graph.ainvoke(
        {"session_id": "s1", "project_id": "p1", "query": "q", "revision_count": 0}
    )
    result_b = await graph.ainvoke(
        {"session_id": "s2", "project_id": "p1", "query": "q", "revision_count": 0}
    )

    assert result_a["messages"] == result_b["messages"]


async def test_revision_loops_terminate_at_the_cap_instead_of_looping_forever() -> None:
    """Regression test for a real Phase 8 bug: nothing incremented
    revision_count, so an LLM that never says VERIFIED/APPROVED made both
    loops (fact_checker -> research, reviewer -> writer) run forever —
    caught by actually letting a real run go to completion during
    development, not by a unit test in isolation. FactCheckerAgent and
    ReviewerAgent now bump revision_count themselves whenever they fail
    their own gate (ai/graph/routing.py only *reads* the cap)."""
    llm = FakeLLMProvider(response="this is neither VERIFIED nor APPROVED")
    graph = build_research_graph(
        llm, FakeEmbeddingProvider(), tools=[FakeTool()], max_revision_loops=2
    )

    final_state = await asyncio.wait_for(
        graph.ainvoke({"session_id": "s1", "project_id": "p1", "query": "q", "revision_count": 0}),
        timeout=10,
    )

    assert final_state["current_node"] == "memory"
    assert final_state["revision_count"] >= 2
