"""End-to-end proof of Phase 8's exit criteria: submitting a research query
through the real REST API produces a real multi-agent LangGraph run (a real
local Ollama LLM + a real local BGE embedding model, no mocks) and a
persisted Report row, with every step relayed over the same pub/sub channel
app/api/ws.py subscribes to.

Opt-in like the other integration tests (RUN_INTEGRATION_TESTS=1 +
DATABASE_URL against a disposable, already-migrated-and-seeded pg+pgvector
db), additionally skipped if Ollama isn't reachable — the one integration
test here that needs a live LLM, not just a live DB (same reachability check
as ai/tests/test_live_ollama.py).

Redis/Celery: no broker is provisioned in this sandbox (Memurai's Windows
Service installer fails here with an access-denied error — see the Phase 8
PR description). `Container.redis` is swapped for a shared in-process
fakeredis server (confirmed live to support real pub/sub, unlike fakeredis's
TcpFakeServer mode) so the actual publish_event/subscribe_to_session code
path (app/core/pubsub.py) runs unmodified end-to-end. `celery_app.send_task`
is stubbed for the duration of the API call in step 4 below — confirmed live
that leaving it real makes the session-creation request hang for the length
of Celery's full broker-reconnect retry policy (~2 minutes) before failing,
since there's no broker to reach; production always has one, so this never
fires there. The Celery *task function itself*
(app/workers/tasks.py's _run_pipeline_async) is awaited directly rather than
dispatched via send_task/apply_async: routing it through Celery's eager mode
from inside this async test would nest a second asyncio.run() inside the
request's already-running event loop — a test-harness artifact, not a real
bug (in production the worker's asyncio.run() runs in its own separate OS
process with no ambient loop).
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Any
from unittest.mock import patch

import fakeredis
import fakeredis.aioredis as fakeredis_aioredis
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.workers.tasks as tasks_module
from app.core.config import Settings
from app.core.container import Container
from app.core.db import create_engine as create_db_engine
from app.core.db import create_session_factory
from app.core.oauth import build_oauth_registry
from app.core.pubsub import subscribe_to_session
from app.main import app as fastapi_app
from app.models.agent import AgentRun
from app.models.message import Message
from app.models.report import Citation, Report
from app.models.research_session import ResearchSession
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")

EXPECTED_NODE_ORDER = [
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


def _ollama_reachable() -> bool:
    try:
        return httpx.get(f"{OLLAMA_BASE_URL}/api/version", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION_TESTS") != "1",
        reason="opt-in: set RUN_INTEGRATION_TESTS=1 and DATABASE_URL to a disposable pg db",
    ),
    pytest.mark.skipif(
        not _ollama_reachable(), reason=f"no Ollama server reachable at {OLLAMA_BASE_URL}"
    ),
]

_FAKE_REDIS_SERVER = fakeredis.FakeServer()


def _fake_redis() -> fakeredis_aioredis.FakeRedis:
    return fakeredis_aioredis.FakeRedis(server=_FAKE_REDIS_SERVER)


@pytest.fixture(autouse=True)
async def _wire_fake_redis_and_worker_container() -> AsyncIterator[None]:
    # API side: swap the already-built container's redis client so
    # app/api/ws.py subscribes on the same fake server the "worker" (below)
    # publishes to.
    fastapi_app.state.container.redis = _fake_redis()

    # Worker side: app/workers/tasks.py builds its own Container per process
    # in real deployments (see its docstring); here we hand it one explicitly
    # configured for a live local Ollama + the real default BGE model. Must be
    # bge-large-en-v1.5 (1024-dim), not the smaller bge-small used elsewhere
    # for speed — app/models/embedding.py's `embeddings.embedding` column is a
    # fixed `vector(1024)`, and the Retriever agent (Phase 9) now runs a real
    # query against it; a 384-dim query vector against that column raises
    # pgvector's "expected 1024 dimensions, not 384" at the SQL level
    # regardless of how many rows are indexed — caught by this exact test
    # after wiring app/services/pg_vector_store.py in.
    settings = Settings(
        database_url=os.environ["DATABASE_URL"],
        ai_provider="ollama",
        ollama_base_url=OLLAMA_BASE_URL,
        ollama_model=OLLAMA_MODEL,
        embedding_provider="bge",
        bge_model_name="BAAI/bge-large-en-v1.5",
        embedding_dimension=1024,
        max_revision_loops=2,
    )
    engine = create_db_engine(settings.database_url)
    tasks_module._container = Container(
        settings=settings,
        db_engine=engine,
        db_sessionmaker=create_session_factory(engine),
        oauth=build_oauth_registry(settings),
        redis=_fake_redis(),
    )
    yield
    tasks_module._container = None
    await engine.dispose()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(fastapi_app) as c:
        yield c


def _unique_email() -> str:
    return f"{uuid.uuid4().hex}@example.com"


async def test_submitting_a_query_produces_a_streamed_run_and_persisted_report(
    client: TestClient,
) -> None:
    # 1. Register + log in (real REST auth flow).
    email, password = _unique_email(), "correct-horse-battery-staple"
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test Researcher"},
    )
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200, resp.text
    user_id = uuid.UUID(resp.json()["id"])

    # 2. Create a project (real REST contract).
    resp = client.post("/api/v1/projects", json={"name": "RAG Research"}, headers=headers)
    assert resp.status_code == 201, resp.text
    project_id = uuid.UUID(resp.json()["id"])

    # 2.5. Index one relevant document into the project's knowledge base
    # *before* running the pipeline, so the Retriever agent's real pgvector
    # search (app/services/pg_vector_store.py) has something real to find —
    # proving the whole Phase 9 wiring, not just that it runs against an
    # empty table. Uses the same worker Container (bge-large embeddings)
    # configured above, via KnowledgeBaseService directly (no upload endpoint
    # yet — see that service's docstring).
    worker_container = tasks_module._container
    assert worker_container is not None
    async with worker_container.db_sessionmaker() as kb_db:
        kb_service = KnowledgeBaseService(
            kb_db,
            worker_container.embeddings,
            worker_container.object_storage,
            ProjectService(kb_db),
        )
        await kb_service.ingest_text(
            project_id,
            user_id,
            "rag-notes.txt",
            "txt",
            "Retrieval-augmented generation (RAG) combines a retriever that "
            "fetches relevant documents with a generator that conditions its "
            "output on that retrieved context, grounding responses in real "
            "source material instead of relying purely on parametric memory.",
        )

    # 3. Create the research session via the real REST endpoint — the exact
    # `POST /projects/{id}/sessions` call the exit criteria refers to,
    # including its celery_app.send_task(...) enqueue. send_task is stubbed
    # (see module docstring: no broker here, and a real one would just make
    # a real worker process do what step 5 below does directly instead).
    with patch("app.api.v1.sessions.celery_app.send_task") as send_task:
        resp = client.post(
            f"/api/v1/projects/{project_id}/sessions",
            json={"query": "What is retrieval-augmented generation?"},
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    session_id = body["id"]
    assert body["status"] == "queued"
    send_task.assert_called_once_with("research.run_pipeline", args=[session_id])

    # 4. Subscribe to the session's event channel *before* running the
    # pipeline, exactly like app/api/ws.py does, to prove the pub/sub relay
    # (not just the DB writes) actually carries every step.
    collected_events: list[dict[str, Any]] = []

    async def _collect() -> None:
        async for event in subscribe_to_session(_fake_redis(), session_id):
            collected_events.append(event)
            if event.get("type") == "status" and event.get("status") in {"completed", "failed"}:
                break

    collector_task = asyncio.create_task(_collect())
    await asyncio.sleep(0.1)  # let subscribe() register before the pipeline starts publishing

    # 5. Run the actual worker logic directly (see module docstring for why
    # celery_app.send_task/apply_async isn't used here).
    await tasks_module._run_pipeline_async(uuid.UUID(session_id))

    await asyncio.wait_for(collector_task, timeout=5)

    # 6. The pub/sub relay must have carried a valid traversal of the graph,
    # in order. A real LLM (llama3.2:1b here) doesn't reliably approve on the
    # first pass the way the scripted FakeLLM in ai/tests/test_graph.py does,
    # so revision loops (fact_checker->research, reviewer->writer) may
    # legitimately fire up to max_revision_loops times — assert the graph's
    # fixed entry/exit rather than one exact fixed-length sequence.
    node_events = [e for e in collected_events if e.get("type") == "node_update"]
    node_sequence = [e["node"] for e in node_events]
    assert node_sequence[0] == "planner"
    assert node_sequence[-1] == "memory"
    assert set(node_sequence) <= set(EXPECTED_NODE_ORDER)
    # citation/evaluation/memory are downstream of both loops and never repeat.
    for terminal_node in ("citation", "evaluation", "memory"):
        assert node_sequence.count(terminal_node) == 1
    assert collected_events[0] == {"type": "status", "status": "running"}
    assert collected_events[-1]["status"] == "completed"

    # The Retriever agent must have found the document indexed in step 2.5 —
    # proving app/services/pg_vector_store.py's real pgvector search, not
    # just that it ran against an empty table without erroring.
    retriever_messages = [
        m for e in node_events if e["node"] == "retriever" for m in e["messages"]
    ]
    assert any("retrieved 1 chunk" in m for m in retriever_messages)

    # 7. And it must actually be persisted, not just streamed.
    engine = create_async_engine(os.environ["DATABASE_URL"])
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as db:
        research_session = await db.get(ResearchSession, uuid.UUID(session_id))
        assert research_session is not None
        assert research_session.status == "completed"
        assert research_session.completed_at is not None

        agent_runs = (
            await db.execute(select(AgentRun).where(AgentRun.session_id == research_session.id))
        ).scalars().all()
        assert len(agent_runs) == len(node_events)

        messages = (
            await db.execute(select(Message).where(Message.session_id == research_session.id))
        ).scalars().all()
        assert len(messages) >= len(EXPECTED_NODE_ORDER)

        report = (
            await db.execute(select(Report).where(Report.session_id == research_session.id))
        ).scalar_one()
        assert report.content_markdown
        assert report.quality_score is not None

        citations = (
            await db.execute(select(Citation).where(Citation.report_id == report.id))
        ).scalars().all()
        assert isinstance(citations, list)  # count varies with live search results
    await engine.dispose()
