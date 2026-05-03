import pytest
from fastapi.testclient import TestClient
from access import UserContext
from auth import get_authenticated_user
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def authenticated_user_override():
    def fake_user() -> UserContext:
        return UserContext(
            id="user-1",
            email="user@example.com",
            signed_in=True,
            display_name=None,
            avatar_url=None,
        )

    app.dependency_overrides[get_authenticated_user] = fake_user
    yield
    app.dependency_overrides.pop(get_authenticated_user, None)


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


def test_num_agents_boundary_values_are_valid():
    # 2 and 12 are the valid boundaries — confirm they pass validation
    # (they'll fail downstream without real API keys, but not with a 400)
    r2 = client.get("/api/research/stream?question=test&num_agents=2")
    r12 = client.get("/api/research/stream?question=test&num_agents=12")
    assert r2.status_code != 400
    assert r12.status_code != 400
