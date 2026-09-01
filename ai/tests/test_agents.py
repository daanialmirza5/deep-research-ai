import pytest

from ai.agents import (
    CitationAgent,
    EvaluationAgent,
    FactCheckerAgent,
    MemoryAgent,
    PlannerAgent,
    ResearchAgent,
    RetrieverAgent,
    ReviewerAgent,
    SummarizerAgent,
    WriterAgent,
)
from ai.graph.state import ResearchFinding, ResearchState, RetrievedChunk
from ai.tests.fakes import FakeEmbeddingProvider, FakeLLMProvider, FakeTool, FakeVectorStore

pytestmark = pytest.mark.asyncio

SAMPLE_FINDING = ResearchFinding(
    source="fake_tool",
    title="RAG Explained",
    url="https://example.com/rag",
    snippet="RAG combines retrieval and generation.",
)

SAMPLE_CHUNK = RetrievedChunk(
    document_id="doc-1",
    chunk_index=0,
    chunk_text="From the knowledge base: RAG grounds generation in retrieved documents.",
    score=0.87,
    metadata=None,
)


def make_state(**overrides: object) -> ResearchState:
    base: ResearchState = {
        "session_id": "s1",
        "project_id": "p1",
        "query": "What is retrieval-augmented generation?",
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


async def test_planner_calls_llm_and_sets_plan() -> None:
    llm = FakeLLMProvider(response="1. Search\n2. Synthesize")
    agent = PlannerAgent(llm)

    update = await agent(make_state())

    assert update["plan"] == "1. Search\n2. Synthesize"
    assert update["current_node"] == "planner"
    assert len(llm.calls) == 1
    assert llm.calls[0][-1].content == "What is retrieval-augmented generation?"
    # Real per-call token usage (Phase 11) flows through into the node's
    # returned dict via BaseAgent._llm_usage(), for AgentRun.output_state.
    assert update["prompt_tokens"] == FakeLLMProvider.FAKE_PROMPT_TOKENS
    assert update["completion_tokens"] == FakeLLMProvider.FAKE_COMPLETION_TOKENS
    assert update["llm_model"] == "fake-model"


async def test_research_agent_fans_out_to_every_tool() -> None:
    tool_a = FakeTool([SAMPLE_FINDING])
    tool_b = FakeTool(
        [ResearchFinding(source="fake_tool", title="Other", url="https://x.com", snippet="x")]
    )
    agent = ResearchAgent([tool_a, tool_b])

    update = await agent(make_state())

    assert len(update["research_findings"]) == 2
    assert tool_a.calls == ["What is retrieval-augmented generation?"]
    assert tool_b.calls == ["What is retrieval-augmented generation?"]


async def test_retriever_searches_the_vector_store_with_the_embedded_query() -> None:
    embeddings = FakeEmbeddingProvider(dimension=4)
    vector_store = FakeVectorStore([SAMPLE_CHUNK])

    update = await RetrieverAgent(embeddings, vector_store)(make_state())

    assert update["retrieved_context"] == [SAMPLE_CHUNK]
    assert embeddings.calls == [["What is retrieval-augmented generation?"]]
    [(query_embedding, project_id, top_k)] = vector_store.calls
    assert query_embedding == [0.1, 0.1, 0.1, 0.1]
    assert project_id == "p1"
    assert top_k == 5


async def test_retriever_returns_empty_context_when_nothing_is_indexed() -> None:
    embeddings = FakeEmbeddingProvider(dimension=4)
    vector_store = FakeVectorStore([])

    update = await RetrieverAgent(embeddings, vector_store)(make_state())

    assert update["retrieved_context"] == []


async def test_summarizer_skips_llm_call_when_no_findings_or_context() -> None:
    llm = FakeLLMProvider()
    update = await SummarizerAgent(llm)(make_state(research_findings=[], retrieved_context=[]))

    assert update["summary"] == ""
    assert len(llm.calls) == 0


async def test_summarizer_calls_llm_when_findings_exist() -> None:
    llm = FakeLLMProvider(response="RAG combines retrieval with generation.")
    update = await SummarizerAgent(llm)(make_state(research_findings=[SAMPLE_FINDING]))

    assert update["summary"] == "RAG combines retrieval with generation."
    assert "RAG Explained" in llm.calls[0][-1].content


async def test_summarizer_calls_llm_when_only_retrieved_context_exists() -> None:
    llm = FakeLLMProvider(response="Summary from the knowledge base.")
    update = await SummarizerAgent(llm)(
        make_state(research_findings=[], retrieved_context=[SAMPLE_CHUNK])
    )

    assert update["summary"] == "Summary from the knowledge base."
    assert "grounds generation in retrieved documents" in llm.calls[0][-1].content


async def test_fact_checker_unverified_without_findings_skips_llm() -> None:
    llm = FakeLLMProvider()
    update = await FactCheckerAgent(llm)(make_state(research_findings=[]))

    assert update["fact_check_verdict"] == "unverified"
    assert len(llm.calls) == 0


async def test_fact_checker_parses_verified_verdict() -> None:
    llm = FakeLLMProvider(response="VERIFIED: sources are sufficient")
    update = await FactCheckerAgent(llm)(make_state(research_findings=[SAMPLE_FINDING]))

    assert update["fact_check_verdict"] == "verified"


async def test_fact_checker_parses_unverified_verdict() -> None:
    llm = FakeLLMProvider(response="UNVERIFIED: not enough detail")
    update = await FactCheckerAgent(llm)(make_state(research_findings=[SAMPLE_FINDING]))

    assert update["fact_check_verdict"] == "unverified"


async def test_writer_calls_llm_with_sources_and_summary() -> None:
    llm = FakeLLMProvider(response="Draft report body.")
    update = await WriterAgent(llm)(
        make_state(summary="A summary.", research_findings=[SAMPLE_FINDING])
    )

    assert update["draft_report"] == "Draft report body."
    prompt = llm.calls[0][-1].content
    assert "A summary." in prompt
    assert "RAG Explained" in prompt


async def test_writer_includes_review_feedback_when_present() -> None:
    llm = FakeLLMProvider(response="Revised draft.")
    await WriterAgent(llm)(make_state(review_feedback="Add more detail on X"))

    assert "Add more detail on X" in llm.calls[0][-1].content


async def test_reviewer_parses_approved() -> None:
    llm = FakeLLMProvider(response="APPROVED")
    update = await ReviewerAgent(llm)(make_state(draft_report="A report."))

    assert update["review_approved"] is True
    assert update["review_feedback"] == ""


async def test_reviewer_parses_revise() -> None:
    llm = FakeLLMProvider(response="REVISE: needs more citations")
    update = await ReviewerAgent(llm)(make_state(draft_report="A report."))

    assert update["review_approved"] is False
    assert "needs more citations" in update["review_feedback"]


async def test_citation_builds_entries_from_findings() -> None:
    update = await CitationAgent()(make_state(research_findings=[SAMPLE_FINDING]))

    assert update["citations"] == [
        {"source_type": "fake_tool", "title": "RAG Explained", "url": "https://example.com/rag"}
    ]


async def test_evaluation_parses_a_numeric_score() -> None:
    llm = FakeLLMProvider(response="0.85")
    update = await EvaluationAgent(llm)(make_state(draft_report="A report."))

    assert update["quality_score"] == 0.85


async def test_evaluation_clamps_out_of_range_scores() -> None:
    llm = FakeLLMProvider(response="1.5")
    update = await EvaluationAgent(llm)(make_state(draft_report="A report."))

    assert update["quality_score"] == 1.0


async def test_memory_stub_is_terminal_and_harmless() -> None:
    update = await MemoryAgent()(make_state())
    assert update["current_node"] == "memory"
