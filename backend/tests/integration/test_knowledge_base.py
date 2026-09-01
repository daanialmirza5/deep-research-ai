"""End-to-end proof of Phase 9's exit criteria: ingesting text into a
project's knowledge base and querying `GET /knowledge-base/search` returns
relevant chunks ranked by real pgvector cosine similarity — no mocks: a real
Postgres+pgvector instance and the real configured embedding provider (BGE,
the same 1024-dim default the `embeddings` table's Vector column is fixed
to; see app/models/embedding.py's EMBEDDING_DIMENSION).

Opt-in like the other integration tests (RUN_INTEGRATION_TESTS=1 +
DATABASE_URL against a disposable, already-migrated db). Ingestion goes
through KnowledgeBaseService directly rather than a REST endpoint — Document
*upload* endpoints are Phase 10 (see that service's docstring); search goes
through the real `GET /knowledge-base/search` endpoint.
"""

import os
import uuid
from collections.abc import Iterator

import pytest
from ai.embeddings.factory import get_embedding_provider
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.object_storage import ObjectStorage
from app.main import app as fastapi_app
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION_TESTS") != "1",
        reason="opt-in: set RUN_INTEGRATION_TESTS=1 and DATABASE_URL to a disposable pg db",
    ),
]


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(fastapi_app) as c:
        yield c


def _unique_email() -> str:
    return f"{uuid.uuid4().hex}@example.com"


def _register_and_login(client: TestClient) -> tuple[dict[str, str], uuid.UUID]:
    email, password = _unique_email(), "correct-horse-battery-staple"
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "KB Tester"},
    )
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200, resp.text
    return headers, uuid.UUID(resp.json()["id"])


async def test_search_ranks_ingested_chunks_by_cosine_similarity_and_is_project_scoped(
    client: TestClient,
) -> None:
    headers, user_id = _register_and_login(client)

    resp = client.post("/api/v1/projects", json={"name": "KB Test Project A"}, headers=headers)
    assert resp.status_code == 201, resp.text
    project_a = uuid.UUID(resp.json()["id"])

    resp = client.post("/api/v1/projects", json={"name": "KB Test Project B"}, headers=headers)
    assert resp.status_code == 201, resp.text
    project_b = uuid.UUID(resp.json()["id"])

    settings = Settings(
        database_url=os.environ["DATABASE_URL"],
        embedding_provider="bge",
        bge_model_name="BAAI/bge-large-en-v1.5",
        embedding_dimension=1024,
    )
    embeddings = get_embedding_provider(settings)
    engine = create_async_engine(settings.database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as db:
        kb_service = KnowledgeBaseService(
            db, embeddings, ObjectStorage(settings), ProjectService(db)
        )
        await kb_service.ingest_text(
            project_a,
            user_id,
            "cats.txt",
            "txt",
            "Cats are small domesticated carnivorous mammals valued as household pets.",
        )
        await kb_service.ingest_text(
            project_a,
            user_id,
            "cars.txt",
            "txt",
            "Cars are wheeled motor vehicles used for transportation on roads.",
        )
        await kb_service.ingest_text(
            project_a,
            user_id,
            "cooking.txt",
            "txt",
            "Cooking is the art of preparing food using heat to make it safe and flavorful.",
        )
        # Same topic as the most-relevant chunk above, but in a different
        # project — must never appear in project_a's search results.
        await kb_service.ingest_text(
            project_b,
            user_id,
            "kittens.txt",
            "txt",
            "Kittens are baby cats, small furry pets that people keep at home.",
        )

    resp = client.get(
        "/api/v1/knowledge-base/search",
        params={
            "project_id": str(project_a),
            "q": "small pet animals like cats and dogs",
            "top_k": 3,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    results = resp.json()

    assert len(results) == 3
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)  # ranked most-similar first
    # The cats chunk is the most semantically relevant of the three.
    assert "carnivorous" in results[0]["chunk_text"].lower()
    # Nothing from project_b's knowledge base leaked into project_a's results.
    assert all("kitten" not in r["chunk_text"].lower() for r in results)

    await engine.dispose()


async def test_search_rejects_a_project_that_is_not_the_caller_s(client: TestClient) -> None:
    headers, _ = _register_and_login(client)
    other_headers, _ = _register_and_login(client)

    resp = client.post(
        "/api/v1/projects", json={"name": "Someone else's project"}, headers=other_headers
    )
    assert resp.status_code == 201, resp.text
    other_project_id = resp.json()["id"]

    resp = client.get(
        "/api/v1/knowledge-base/search",
        params={"project_id": other_project_id, "q": "anything"},
        headers=headers,
    )
    assert resp.status_code == 404
