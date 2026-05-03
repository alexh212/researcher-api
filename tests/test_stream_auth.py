from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_stream_requires_authorization_header():
    response = client.get("/api/research/stream?question=test")
    assert response.status_code == 401


def test_stream_rejects_malformed_authorization_header():
    response = client.get(
        "/api/research/stream?question=test",
        headers={"Authorization": "Token abc"},
    )
    assert response.status_code == 401
