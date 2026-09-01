"""The shared state threaded through every node in the research graph (see
docs/architecture.md § 3). Mirrors what gets checkpointed into
research_sessions.graph_state (JSONB) — this is also what the Agent Workflow
Visualization screen reads to render live progress.

A `TypedDict` (not a Pydantic model) because that's what LangGraph's
`StateGraph` expects for merging partial node outputs; `Annotated[..., add]`
fields are appended to across nodes instead of overwritten, which is how
`messages`/`errors` accumulate a running trace across the whole pipeline
instead of each node clobbering the last one's log entries.
"""

import operator
from typing import Annotated, Any, Literal, TypedDict

AgentName = Literal[
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


class ResearchFinding(TypedDict):
    """One search-tool hit (see ai/tools/base.py's SearchResult, which this
    mirrors) — kept as a plain dict shape in state, rather than importing
    the tools module here, so ai/graph/state.py has zero dependency on
    ai/tools/."""

    source: str  # "duckduckgo" | "arxiv" | "wikipedia"
    title: str
    url: str
    snippet: str


class RetrievedChunk(TypedDict):
    """One knowledge-base similarity-search hit (see ai/vectorstore/base.py's
    VectorStore, which this mirrors — kept as a plain dict shape here for the
    same zero-dependency reason as ResearchFinding above)."""

    document_id: str
    chunk_index: int
    chunk_text: str
    score: float  # cosine similarity, higher = more similar
    metadata: dict[str, Any] | None


class ResearchState(TypedDict, total=False):
    # Set once at graph entry.
    session_id: str
    query: str
    # The project whose knowledge base the Retriever agent searches — every
    # research session belongs to exactly one project (research_sessions.project_id).
    project_id: str

    # Planner
    plan: str

    # Research — real tool results (ai/tools/), each traceable back to a
    # source for the Citation agent.
    research_findings: Annotated[list[ResearchFinding], operator.add]

    # Retriever — real vector-search hits from the project's knowledge base
    # (ai/vectorstore/). Annotated like research_findings: a fact-checker
    # revision loop re-enters retriever too, so hits must accumulate across
    # loop iterations rather than the last iteration overwriting the first.
    retrieved_context: Annotated[list[RetrievedChunk], operator.add]

    # Summarizer
    summary: str

    # Fact Checker
    fact_check_verdict: Literal["verified", "unverified"]
    fact_check_notes: str

    # Writer / Reviewer
    draft_report: str
    review_feedback: str
    review_approved: bool

    # Citation
    citations: list[dict[str, Any]]

    # Evaluation
    quality_score: float

    # Loop control — both revision loops (fact-check -> research,
    # review -> writer) share this counter and cap, per
    # docs/database-schema.md's research_sessions.revision_count and
    # Settings.max_revision_loops. Not defaulted by the graph itself —
    # whoever builds the initial state must supply it (0 for a new session,
    # matching research_sessions.revision_count's DB default; see
    # ai/graph/routing.py, which treats a missing value as 0 defensively,
    # but every real caller should set it explicitly).
    revision_count: int

    # Observability — which node is currently/just executing, and a running
    # trace, both surfaced to the frontend via the agent_runs table (Phase 8
    # wires the actual persistence; the graph only needs to carry the values).
    current_node: AgentName
    messages: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]

    # Real per-call token usage (Phase 11) from whichever agent most
    # recently called an LLM — see ai/agents/base.py's _llm_usage(). Plain
    # (overwritten), not accumulated: only the per-node AgentRun.output_state
    # snapshot (app/workers/tasks.py) is read by the Analytics Dashboard, not
    # the final merged state, so there is no running total to keep here.
    prompt_tokens: int
    completion_tokens: int
    llm_model: str
