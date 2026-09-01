"""Assembles the LangGraph StateGraph described in docs/architecture.md § 3.

Providers are constructed by the caller and passed in (constructor
injection all the way down) — this module never reaches into Settings or a
DI container itself, keeping `ai/` importable/testable independent of the
backend (see docs/architecture.md's clean-architecture layering).
"""

from functools import partial

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

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
from ai.embeddings.base import EmbeddingProvider
from ai.graph.routing import route_after_fact_check, route_after_review
from ai.graph.state import ResearchState
from ai.llm.base import LLMProvider
from ai.tools.arxiv_search import ArxivTool
from ai.tools.base import BaseTool
from ai.tools.web_search import DuckDuckGoTool
from ai.tools.wikipedia_search import WikipediaTool
from ai.vectorstore.base import VectorStore
from ai.vectorstore.null_store import NullVectorStore

DEFAULT_MAX_REVISION_LOOPS = 2


def _default_tools() -> list[BaseTool]:
    return [DuckDuckGoTool(), ArxivTool(), WikipediaTool()]


def build_research_graph(
    llm: LLMProvider,
    embeddings: EmbeddingProvider,
    *,
    max_revision_loops: int = DEFAULT_MAX_REVISION_LOOPS,
    tools: list[BaseTool] | None = None,
    vector_store: VectorStore | None = None,
) -> CompiledStateGraph[ResearchState]:
    graph: StateGraph[ResearchState] = StateGraph(ResearchState)

    graph.add_node("planner", PlannerAgent(llm))
    graph.add_node("research", ResearchAgent(tools if tools is not None else _default_tools()))
    graph.add_node(
        "retriever", RetrieverAgent(embeddings, vector_store or NullVectorStore())
    )
    graph.add_node("summarizer", SummarizerAgent(llm))
    graph.add_node("fact_checker", FactCheckerAgent(llm))
    graph.add_node("writer", WriterAgent(llm))
    graph.add_node("reviewer", ReviewerAgent(llm))
    graph.add_node("citation", CitationAgent())
    graph.add_node("evaluation", EvaluationAgent(llm))
    graph.add_node("memory", MemoryAgent())

    graph.set_entry_point("planner")
    graph.add_edge("planner", "research")
    graph.add_edge("research", "retriever")
    graph.add_edge("retriever", "summarizer")
    graph.add_edge("summarizer", "fact_checker")

    graph.add_conditional_edges(
        "fact_checker",
        partial(route_after_fact_check, max_revision_loops=max_revision_loops),
        {"research": "research", "writer": "writer"},
    )

    graph.add_edge("writer", "reviewer")

    graph.add_conditional_edges(
        "reviewer",
        partial(route_after_review, max_revision_loops=max_revision_loops),
        {"writer": "writer", "citation": "citation"},
    )

    graph.add_edge("citation", "evaluation")
    graph.add_edge("evaluation", "memory")
    graph.add_edge("memory", END)

    return graph.compile()
