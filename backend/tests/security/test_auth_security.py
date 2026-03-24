"""Security tests – validate crypto, token, and API security properties"""
from datetime import timedelta

import pytest

from app.core.security import JWTHandler, PasswordHandler
from app.core.config import settings


class TestPasswordSecurity:
    def test_password_not_stored_in_plaintext(self):
        plain = "SuperSecret99!"
        hashed = PasswordHandler.hash_password(plain)
        assert plain not in hashed

    def test_bcrypt_prefix_confirms_algorithm(self):
        hashed = PasswordHandler.hash_password("TestPass!")
        assert hashed.startswith("$2")  # bcrypt marker

    def test_bcrypt_rounds_adequate(self):
        """Rounds must be >= 12 for bcrypt to be considered secure."""
        hashed = PasswordHandler.hash_password("TestPass!")
        # bcrypt hash format: $2b$<rounds>$...
        parts = hashed.split("$")
        rounds = int(parts[2])
        assert rounds >= 12, f"bcrypt rounds {rounds} < 12 – insufficient security"

    def test_different_passwords_produce_different_hashes(self):
        h1 = PasswordHandler.hash_password("Password1!")
        h2 = PasswordHandler.hash_password("Password2!")
        assert h1 != h2

    def test_same_password_produces_different_hashes(self):
        pw = "SamePassword1!"
        h1 = PasswordHandler.hash_password(pw)
        h2 = PasswordHandler.hash_password(pw)
        assert h1 != h2  # proves salting

    def test_verify_rejects_slightly_modified_password(self):
        pw = "Correct-Password-1!"
        hashed = PasswordHandler.hash_password(pw)
        assert PasswordHandler.verify_password("correct-Password-1!", hashed) is False

    def test_verify_rejects_empty_password(self):
        hashed = PasswordHandler.hash_password("SomePass1!")
        assert PasswordHandler.verify_password("", hashed) is False


class TestJWTSecurity:
    def test_secret_key_not_default(self):
        """Default placeholder key must not be used in a properly configured environment."""
        # We set a custom key in conftest.py env vars; verify it's being used
        assert settings.SECRET_KEY != ""
        assert len(settings.SECRET_KEY) >= 10

    def test_algorithm_is_hs256(self):
        assert settings.ALGORITHM == "HS256"

    def test_token_signature_validated(self):
        """Altering any byte of the signature must invalidate the token."""
        token = JWTHandler.create_access_token({"sub": "1"})
        header, payload, sig = token.split(".")
        tampered = f"{header}.{payload}.{'A' * len(sig)}"
        assert JWTHandler.verify_token(tampered) is None

    def test_token_payload_tamper_detected(self):
        """Changing the payload without re-signing must be rejected."""
        import base64, json
        token = JWTHandler.create_access_token({"sub": "1", "role": "pentester"})
        header, payload_b64, sig = token.split(".")

        # Decode and alter payload
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        data["role"] = "admin"
        new_payload = base64.urlsafe_b64encode(
            json.dumps(data).encode()
        ).rstrip(b"=").decode()

        tampered = f"{header}.{new_payload}.{sig}"
        assert JWTHandler.verify_token(tampered) is None

    def test_expired_token_rejected(self):
        token = JWTHandler.create_access_token(
            {"sub": "1"}, expires_delta=timedelta(seconds=-1)
        )
        assert JWTHandler.verify_token(token) is None

    def test_access_token_not_usable_as_refresh(self):
        """Access tokens must not pass the 'type == refresh' check."""
        token = JWTHandler.create_access_token({"sub": "1"})
        payload = JWTHandler.verify_token(token)
        assert payload is not None
        assert payload.get("type") != "refresh"

    def test_refresh_token_has_correct_type(self):
        token = JWTHandler.create_refresh_token({"sub": "1"})
        payload = JWTHandler.verify_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"


class TestAPISecurityHeaders:
    def test_register_with_missing_body_returns_422_not_500(self, client):
        resp = client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422

    def test_login_no_credentials_returns_422(self, client):
        resp = client.post("/api/v1/auth/login")
        assert resp.status_code == 422

    def test_me_without_token_returns_401(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_refresh_with_garbage_token_returns_401(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": "garbage"},
        )
        assert resp.status_code == 401

    def test_register_response_never_exposes_hashed_password(self, client, test_user_data):
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        body = resp.text
        assert "hashed_password" not in body
        assert "password" not in body or "TestPass" not in body
