from fastapi.testclient import TestClient

from app.main import create_app


def test_health() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_openapi_has_analyze() -> None:
    client = TestClient(create_app())
    spec = client.get("/openapi.json").json()
    assert "/api/v1/analyze" in spec["paths"]
