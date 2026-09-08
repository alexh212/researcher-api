from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_question_returns_400():
    response = client.get("/api/research/stream?question=")
    assert response.status_code == 400


def test_whitespace_only_question_returns_400():
    response = client.get("/api/research/stream?question=   ")
    assert response.status_code == 400


def test_num_agents_too_low_returns_400():
    response = client.get("/api/research/stream?question=test&num_agents=1")
    assert response.status_code == 400


def test_num_agents_too_high_returns_400():
    response = client.get("/api/research/stream?question=test&num_agents=13")
    assert response.status_code == 400


def test_num_agents_boundary_values_are_valid(monkeypatch):
    # 2 and 12 are the valid boundaries — confirm they pass validation.
    # Validation runs before the stream opens, so stubbing plan_research to raise
    # keeps this test on the validation path and off the network: an accepted
    # value still returns 200, and a rejected one would raise 400 before the
    # generator is ever built.
    async def fail_before_network(*args, **kwargs):
        raise RuntimeError("network calls are not allowed in this test")

    monkeypatch.setattr("main.plan_research", fail_before_network)

    r2 = client.get("/api/research/stream?question=test&num_agents=2")
    r12 = client.get("/api/research/stream?question=test&num_agents=12")
    assert r2.status_code == 200
    assert r12.status_code == 200
