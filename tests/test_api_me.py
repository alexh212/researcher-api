from fastapi.testclient import TestClient

import auth
import main

client = TestClient(main.app)


def test_api_me_requires_authorization_header():
    response = client.get("/api/me")
    assert response.status_code == 401


def test_api_me_rejects_malformed_authorization_header():
    response = client.get("/api/me", headers={"Authorization": "Token abc"})
    assert response.status_code == 401


def test_api_me_rejects_invalid_token(monkeypatch):
    def fake_fetch(_token: str):
        return None

    monkeypatch.setattr(auth, "fetch_supabase_user", fake_fetch)
    response = client.get("/api/me", headers={"Authorization": "Bearer bad-token"})
    assert response.status_code == 401


def test_api_me_returns_user_and_upserts(monkeypatch):
    calls: list[dict[str, object]] = []

    def fake_fetch(_token: str):
        return {
            "id": "user-1",
            "email": "user@example.com",
            "user_metadata": {
                "full_name": "Alex",
                "avatar_url": "https://example.com/avatar.png",
            },
        }

    async def fake_upsert(user):
        calls.append({"id": user.id, "email": user.email})

    monkeypatch.setattr(auth, "fetch_supabase_user", fake_fetch)
    monkeypatch.setattr(main, "upsert_user", fake_upsert)

    response = client.get("/api/me", headers={"Authorization": "Bearer good-token"})
    assert response.status_code == 200
    assert response.json() == {
        "id": "user-1",
        "email": "user@example.com",
        "display_name": "Alex",
        "avatar_url": "https://example.com/avatar.png",
    }
    assert calls == [{"id": "user-1", "email": "user@example.com"}]


def test_api_me_repeat_request_still_succeeds(monkeypatch):
    def fake_fetch(_token: str):
        return {"id": "user-1", "email": "user@example.com", "user_metadata": {}}

    async def fake_upsert(_user):
        return None

    monkeypatch.setattr(auth, "fetch_supabase_user", fake_fetch)
    monkeypatch.setattr(main, "upsert_user", fake_upsert)

    first = client.get("/api/me", headers={"Authorization": "Bearer good-token"})
    second = client.get("/api/me", headers={"Authorization": "Bearer good-token"})

    assert first.status_code == 200
    assert second.status_code == 200
