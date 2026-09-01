"""End-to-end proof of Phase 11's exit criteria: the Analytics Dashboard's
aggregation endpoints render real (non-mock) session/usage data after at
least one full pipeline run — no mocks: a real Postgres instance, a real
local Ollama LLM, and a real local BGE embedding model.

Opt-in + Ollama-gated like test_research_pipeline.py (see that module's
docstring for the full rationale on the fakeredis/direct-task-call
approach this reuses).
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator, Iterator
from unittest.mock import patch

import fakeredis
import fakeredis.aioredis as fakeredis_aioredis
import httpx
import pytest
from fastapi.testclient import TestClient

import app.workers.tasks as tasks_module
from app.core.config import Settings
from app.core.container import Container
from app.core.db import create_engine as create_db_engine
from app.core.db import create_session_factory
from app.core.oauth import build_oauth_registry
from app.main import app as fastapi_app

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")

_LLM_CALLING_AGENTS = {"planner", "summarizer", "fact_checker", "writer", "reviewer", "evaluation"}


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
    fastapi_app.state.container.redis = _fake_redis()

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


async def test_analytics_endpoints_render_real_data_after_a_full_pipeline_run(
    client: TestClient,
) -> None:
    # 1. Register, log in, create a project — each already emits a real
    # analytics_events row (app/services/auth_service.py,
    # app/services/project_service.py).
    email, password = _unique_email(), "correct-horse-battery-staple"
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Analytics Tester"},
    )
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = client.post("/api/v1/projects", json={"name": "Analytics Project"}, headers=headers)
    assert resp.status_code == 201, resp.text
    project_id = resp.json()["id"]

    # 2. Create + run one real research session end to end (mirrors
    # test_research_pipeline.py's steps 3-5; see that module's docstring for
    # why send_task is stubbed and the task's async body is awaited directly).
    with patch("app.api.v1.sessions.celery_app.send_task"):
        resp = client.post(
            f"/api/v1/projects/{project_id}/sessions",
            json={"query": "What is retrieval-augmented generation?"},
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    session_id = resp.json()["id"]

    await tasks_module._run_pipeline_async(uuid.UUID(session_id))

    # Real per-call token usage means each LLM-calling node takes real
    # wall-clock time; give the worker's pub/sub-independent DB writes (this
    # test doesn't need to observe streaming, just the end state) a moment
    # to settle before querying aggregates in a fresh request.
    await asyncio.sleep(0.5)

    # 3. GET /analytics/overview must reflect this exact run.
    resp = client.get("/api/v1/analytics/overview", headers=headers)
    assert resp.status_code == 200, resp.text
    overview = resp.json()
    assert overview["sessions_run"] == 1
    assert overview["avg_completion_seconds"] is not None
    assert overview["avg_completion_seconds"] > 0
    assert overview["success_rate"] == 1.0
    assert sum(point["count"] for point in overview["sessions_over_time"]) == 1
    gate_names = {gate["agent_name"] for gate in overview["agent_rejection_rates"]}
    assert gate_names == {"fact_checker", "reviewer"}
    for gate in overview["agent_rejection_rates"]:
        assert gate["total_runs"] >= 1
        assert 0.0 <= gate["rejection_rate"] <= 1.0

    # 4. GET /analytics/usage must show real, non-zero token counts for
    # every LLM-calling agent — not estimated from text length (see
    # ai/llm/base.py's LLMResponse).
    resp = client.get("/api/v1/analytics/usage", headers=headers)
    assert resp.status_code == 200, resp.text
    usage = resp.json()
    usage_by_name = {row["agent_name"]: row for row in usage["usage_by_agent"]}
    assert set(usage_by_name) >= _LLM_CALLING_AGENTS
    for agent_name in _LLM_CALLING_AGENTS:
        row = usage_by_name[agent_name]
        assert row["call_count"] >= 1
        assert row["prompt_tokens"] > 0
        assert row["completion_tokens"] > 0

    # 5. GET /analytics/activity must show the real lifecycle events emitted
    # along the way, most-recent first.
    resp = client.get("/api/v1/analytics/activity", headers=headers)
    assert resp.status_code == 200, resp.text
    event_types = [event["event_type"] for event in resp.json()]
    assert "session.completed" in event_types
    assert "session.created" in event_types
    assert "project.created" in event_types
    assert "user.registered" in event_types
    assert event_types.index("session.completed") < event_types.index("session.created")
