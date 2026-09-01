"""Conditional-edge routing predicates, factored out of build.py so they're
directly unit-testable without needing to run the whole graph (the stub
FactChecker/Reviewer agents always return "verified"/"approved", so the
loop-back branches can't be exercised by actually running the Phase 7 graph
end-to-end — that only becomes possible once Phase 8's real FactChecker can
produce "unverified").
"""

from ai.graph.state import ResearchState


def route_after_fact_check(state: ResearchState, *, max_revision_loops: int) -> str:
    unverified = state.get("fact_check_verdict") == "unverified"
    under_cap = state.get("revision_count", 0) < max_revision_loops
    return "research" if (unverified and under_cap) else "writer"


def route_after_review(state: ResearchState, *, max_revision_loops: int) -> str:
    needs_revision = not state.get("review_approved", True)
    under_cap = state.get("revision_count", 0) < max_revision_loops
    return "writer" if (needs_revision and under_cap) else "citation"
