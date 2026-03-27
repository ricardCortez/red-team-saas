"""Integration tests – authentication API endpoints"""


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_status_healthy(self, client):
        resp = client.get("/health")
        assert resp.json()["status"] == "ok"


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_contains_project_name(self, client):
        data = client.get("/").json()
        assert data["name"] == "Red Team SaaS"

    def test_root_contains_architecture(self, client):
        data = client.get("/").json()
        assert data["architecture"] in ("A", "B", "C")

    def test_root_contains_total_tools(self, client):
        data = client.get("/").json()
        assert data["total_tools"] > 0


class TestRegisterEndpoint:
    def test_register_returns_201(self, client, test_user_data):
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert resp.status_code == 201

    def test_register_response_has_id(self, client, test_user_data):
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert "id" in resp.json()

    def test_register_response_email_matches(self, client, test_user_data):
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert resp.json()["email"] == test_user_data["email"]

    def test_register_response_username_matches(self, client, test_user_data):
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert resp.json()["username"] == test_user_data["username"]

    def test_register_response_no_password_field(self, client, test_user_data):
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert "password" not in resp.json()
        assert "hashed_password" not in resp.json()

    def test_register_response_is_active(self, client, test_user_data):
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert resp.json()["is_active"] is True

    def test_register_response_has_role(self, client, test_user_data):
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert "role" in resp.json()

    def test_register_duplicate_email_returns_400(self, client, test_user_data):
        client.post("/api/v1/auth/register", json=test_user_data)
        test_user_data["username"] = "differentuser"
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert resp.status_code == 400

    def test_register_duplicate_username_returns_400(self, client, test_user_data):
        client.post("/api/v1/auth/register", json=test_user_data)
        test_user_data["email"] = "other@example.com"
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert resp.status_code == 400

    def test_register_invalid_email_returns_422(self, client, test_user_data):
        test_user_data["email"] = "not-an-email"
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert resp.status_code == 422

    def test_register_missing_password_returns_422(self, client, test_user_data):
        del test_user_data["password"]
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        assert resp.status_code == 422


class TestLoginEndpoint:
    def test_login_returns_200(self, client, test_user_data, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            params={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        assert resp.status_code == 200

    def test_login_returns_access_token(self, client, test_user_data, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            params={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        data = resp.json()
        assert "access_token" in data
        assert data["access_token"] != ""

    def test_login_returns_refresh_token(self, client, test_user_data, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            params={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        assert "refresh_token" in resp.json()

    def test_login_token_type_bearer(self, client, test_user_data, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            params={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        assert resp.json()["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client, test_user_data, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            params={"email": test_user_data["email"], "password": "WrongPassword"},
        )
        assert resp.status_code == 401

    def test_login_wrong_email_returns_401(self, client, test_user_data, registered_user):
        resp = client.post(
            "/api/v1/auth/login",
            params={"email": "ghost@example.com", "password": test_user_data["password"]},
        )
        assert resp.status_code == 401

    def test_login_missing_params_returns_422(self, client):
        resp = client.post("/api/v1/auth/login")
        assert resp.status_code == 422


class TestRefreshEndpoint:
    def test_refresh_returns_200(self, client, test_user_data, registered_user, refresh_token_value):
        resp = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": refresh_token_value},
        )
        assert resp.status_code == 200

    def test_refresh_returns_new_access_token(
        self, client, test_user_data, registered_user, refresh_token_value
    ):
        resp = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": refresh_token_value},
        )
        data = resp.json()
        assert "access_token" in data
        assert data["access_token"] != ""

    def test_refresh_invalid_token_returns_401(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_refresh_with_access_token_returns_401(self, client, auth_token):
        # Access tokens must not be accepted as refresh tokens
        resp = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": auth_token},
        )
        assert resp.status_code == 401


class TestMeEndpoint:
    def test_me_returns_200(self, client, auth_token):
        resp = client.get("/api/v1/auth/me", params={"token": auth_token})
        assert resp.status_code == 200

    def test_me_returns_correct_email(self, client, test_user_data, auth_token):
        resp = client.get("/api/v1/auth/me", params={"token": auth_token})
        assert resp.json()["email"] == test_user_data["email"]

    def test_me_no_token_returns_401(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token_returns_401(self, client):
        resp = client.get("/api/v1/auth/me", params={"token": "bad.token.value"})
        assert resp.status_code == 401

    def test_me_response_no_password(self, client, auth_token):
        resp = client.get("/api/v1/auth/me", params={"token": auth_token})
        body = resp.json()
        assert "password" not in body
        assert "hashed_password" not in body
