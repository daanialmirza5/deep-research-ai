"""Real-database model tests — insert/relationship/cascade-delete behavior
that can only be verified against a live Postgres+pgvector instance (SQLite
doesn't support the Vector column type or our CHECK constraints identically).

Skipped by default: opt in with `RUN_INTEGRATION_TESTS=1` and a working
`DATABASE_URL` pointed at a disposable database (docker-compose's `postgres`
service, or any local Postgres+pgvector instance). Not run by `make test` —
that's the full stack's job once Phase 12/13 wires up a CI Postgres service.

This exact test caught a real bug during Phase 4 development: User/Project/
RefreshToken/ApiKey relationships were missing `cascade="all, delete-orphan"`
+ `passive_deletes=True`, so deleting a user raised a NOT NULL violation
(SQLAlchemy tried to null the child FK instead of deferring to the DB's
ON DELETE CASCADE) instead of cascading correctly.
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    Agent,
    AgentRun,
    Citation,
    Document,
    Embedding,
    Message,
    Project,
    Report,
    ResearchSession,
    User,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="opt-in: set RUN_INTEGRATION_TESTS=1 and DATABASE_URL to a disposable pg+pgvector db",
)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as s:
        yield s
    await engine.dispose()


async def test_insert_full_graph_and_cascade_delete(session: AsyncSession) -> None:
    user = User(email="ada@example.com", full_name="Ada Lovelace", role="member")
    project = Project(owner=user, name="Analytical Engine Research")
    research_session = ResearchSession(
        project=project, user=user, query="What is the impact of RAG on scientific research?"
    )
    document = Document(
        project=project, uploader=user, source_type="pdf", storage_path="dra-documents/test.pdf"
    )
    embedding = Embedding(
        document=document, chunk_index=0, chunk_text="hello world", embedding=[0.01] * 1024
    )
    message = Message(session=research_session, role="user", content="Hi")
    agent = Agent(name="test-planner", type="planner")
    agent_run = AgentRun(session=research_session, agent=agent, status="completed")
    report = Report(session=research_session, title="Draft Report", content_markdown="# Findings")
    citation = Citation(report=report, source_type="arxiv", title="Attention Is All You Need")

    session.add_all(
        [
            user,
            project,
            research_session,
            document,
            embedding,
            message,
            agent,
            agent_run,
            report,
            citation,
        ]
    )
    await session.commit()

    fetched = (
        await session.execute(select(User).where(User.email == "ada@example.com"))
    ).scalar_one()
    await session.refresh(fetched, attribute_names=["projects"])
    assert len(fetched.projects) == 1

    fetched_embedding = (
        await session.execute(select(Embedding).where(Embedding.id == embedding.id))
    ).scalar_one()
    assert len(fetched_embedding.embedding) == 1024

    # `agents` is a reference table seeded independently of this test (see
    # app/scripts/seed.py, required since Phase 8 for AgentRun.agent_id) —
    # count before/after rather than assuming the table starts empty. Other
    # tables (projects/embeddings/reports) can likewise hold rows from other
    # tests' own live data (e.g. test_research_pipeline.py's persisted
    # sessions), so every check below is scoped to *this* test's own ids
    # rather than asserting a table is globally empty.
    agents_before_delete = (await session.execute(select(Agent))).scalars().all()
    project_id, embedding_id, report_id = project.id, embedding.id, report.id

    # Deleting the user must cascade through project -> session ->
    # message/agent_run/report/citation, and document -> embedding, while
    # leaving the `agents` reference table untouched.
    await session.delete(fetched)
    await session.commit()

    assert (await session.get(Project, project_id)) is None
    assert (await session.get(Embedding, embedding_id)) is None
    assert (await session.get(Report, report_id)) is None
    remaining_agents = (await session.execute(select(Agent))).scalars().all()
    assert len(remaining_agents) == len(agents_before_delete)
    assert any(a.name == "test-planner" for a in remaining_agents)

    test_agent = next(a for a in remaining_agents if a.name == "test-planner")
    await session.delete(test_agent)
    await session.commit()
