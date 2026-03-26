"""Integration tests for wordlist API endpoints (Phase 10)"""
import pytest


def _register_login(client, email: str, password: str = "Pass123!"):
    """Register a user with auto-derived username and return (token, user_id)."""
    username = email.split("@")[0].replace(".", "_").replace("-", "_")
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password, "full_name": "Test User"},
    )
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["id"]
    resp = client.post("/api/v1/auth/login", params={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"], user_id


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestWordlistsListEndpoint:
    def test_list_wordlists_requires_auth(self, client):
        resp = client.get("/api/v1/wordlists")
        assert resp.status_code in (401, 403)

    def test_list_wordlists_authenticated(self, client, db_session):
        token, _ = _register_login(client, "wl_user1@test.com", "Pass123!")
        resp = client.get("/api/v1/wordlists", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "system" in data
        assert "custom" in data
        assert isinstance(data["system"], list)
        assert isinstance(data["custom"], list)

    def test_system_wordlists_have_required_fields(self, client, db_session):
        token, _ = _register_login(client, "wl_user2@test.com", "Pass123!")
        resp = client.get("/api/v1/wordlists", headers=_auth_headers(token))
        data = resp.json()
        for entry in data["system"]:
            assert "name" in entry
            assert "path" in entry
            assert "type" in entry


class TestCreateCustomWordlist:
    def test_create_custom_wordlist(self, client, db_session):
        token, _ = _register_login(client, "wl_user3@test.com", "Pass123!")
        payload = {"name": "mypasswords", "words": ["password1", "admin123", "secret"]}
        resp = client.post(
            "/api/v1/wordlists/custom",
            json=payload,
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["word_count"] == 3
        assert data["type"] == "custom"
        assert "path" in data

    def test_create_custom_wordlist_requires_auth(self, client):
        payload = {"name": "test", "words": ["word1"]}
        resp = client.post("/api/v1/wordlists/custom", json=payload)
        assert resp.status_code in (401, 403)

    def test_create_custom_wordlist_empty_words_rejected(self, client, db_session):
        token, _ = _register_login(client, "wl_user4@test.com", "Pass123!")
        payload = {"name": "empty", "words": []}
        resp = client.post(
            "/api/v1/wordlists/custom",
            json=payload,
            headers=_auth_headers(token),
        )
        assert resp.status_code == 400

    def test_create_custom_wordlist_empty_name_rejected(self, client, db_session):
        token, _ = _register_login(client, "wl_user5@test.com", "Pass123!")
        payload = {"name": "   ", "words": ["word1"]}
        resp = client.post(
            "/api/v1/wordlists/custom",
            json=payload,
            headers=_auth_headers(token),
        )
        assert resp.status_code == 400

    def test_create_wordlist_appears_in_list(self, client, db_session):
        token, _ = _register_login(client, "wl_user6@test.com", "Pass123!")
        words = ["test1", "test2", "test3"]
        client.post(
            "/api/v1/wordlists/custom",
            json={"name": "testlist_unique", "words": words},
            headers=_auth_headers(token),
        )
        resp = client.get("/api/v1/wordlists", headers=_auth_headers(token))
        data = resp.json()
        custom_names = [w["name"] for w in data["custom"]]
        assert any("testlist_unique" in name for name in custom_names)


class TestDeleteCustomWordlist:
    def test_delete_existing_wordlist(self, client, db_session):
        token, _ = _register_login(client, "wl_user7@test.com", "Pass123!")
        # Create
        client.post(
            "/api/v1/wordlists/custom",
            json={"name": "to_delete", "words": ["w1", "w2"]},
            headers=_auth_headers(token),
        )
        # Delete
        resp = client.delete("/api/v1/wordlists/custom/to_delete", headers=_auth_headers(token))
        assert resp.status_code == 204

    def test_delete_nonexistent_wordlist_404(self, client, db_session):
        token, _ = _register_login(client, "wl_user8@test.com", "Pass123!")
        resp = client.delete("/api/v1/wordlists/custom/ghost_list", headers=_auth_headers(token))
        assert resp.status_code == 404

    def test_delete_requires_auth(self, client):
        resp = client.delete("/api/v1/wordlists/custom/something")
        assert resp.status_code in (401, 403)
