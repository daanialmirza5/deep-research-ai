from ai.graph.routing import route_after_fact_check, route_after_review
from ai.graph.state import ResearchState


def make_state(**overrides: object) -> ResearchState:
    base: ResearchState = {"session_id": "s1", "query": "q"}
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def test_fact_check_loops_back_to_research_when_unverified_and_under_cap() -> None:
    state = make_state(fact_check_verdict="unverified", revision_count=0)
    assert route_after_fact_check(state, max_revision_loops=2) == "research"


def test_fact_check_forces_forward_once_revision_cap_is_hit() -> None:
    state = make_state(fact_check_verdict="unverified", revision_count=2)
    assert route_after_fact_check(state, max_revision_loops=2) == "writer"


def test_fact_check_proceeds_to_writer_when_verified() -> None:
    state = make_state(fact_check_verdict="verified", revision_count=0)
    assert route_after_fact_check(state, max_revision_loops=2) == "writer"


def test_review_loops_back_to_writer_when_not_approved_and_under_cap() -> None:
    state = make_state(review_approved=False, revision_count=0)
    assert route_after_review(state, max_revision_loops=2) == "writer"


def test_review_forces_forward_once_revision_cap_is_hit() -> None:
    state = make_state(review_approved=False, revision_count=2)
    assert route_after_review(state, max_revision_loops=2) == "citation"


def test_review_proceeds_to_citation_when_approved() -> None:
    state = make_state(review_approved=True, revision_count=0)
    assert route_after_review(state, max_revision_loops=2) == "citation"
