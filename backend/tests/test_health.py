from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_openapi_schema_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "DeepResearch AI API"


def test_docs_ui_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/api/docs")

    assert response.status_code == 200
