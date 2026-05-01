"""Smoke tests so CI validates imports and the FastAPI app responds."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_openapi_schema_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert body.get("openapi")
    assert "paths" in body
