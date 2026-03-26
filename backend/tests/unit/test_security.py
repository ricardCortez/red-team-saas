"""Unit tests – security utilities + Phase 17 security hardening"""
import time
from datetime import timedelta

from app.core.security import JWTHandler, PasswordHandler, EncryptionHandler


class TestPasswordHandler:
    def test_hash_is_not_plaintext(self):
        pw = "TestPass123!"
        hashed = PasswordHandler.hash_password(pw)
        assert hashed != pw

    def test_hash_starts_with_bcrypt_prefix(self):
        hashed = PasswordHandler.hash_password("TestPass123!")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_hash_is_unique_per_call(self):
        pw = "TestPass123!"
        h1 = PasswordHandler.hash_password(pw)
        h2 = PasswordHandler.hash_password(pw)
        assert h1 != h2  # bcrypt uses random salt

    def test_verify_correct_password(self):
        pw = "TestPass123!"
        hashed = PasswordHandler.hash_password(pw)
        assert PasswordHandler.verify_password(pw, hashed) is True

    def test_verify_wrong_password(self):
        hashed = PasswordHandler.hash_password("TestPass123!")
        assert PasswordHandler.verify_password("WrongPassword!", hashed) is False

    def test_verify_empty_password_fails(self):
        hashed = PasswordHandler.hash_password("TestPass123!")
        assert PasswordHandler.verify_password("", hashed) is False

    def test_hash_length_reasonable(self):
        hashed = PasswordHandler.hash_password("TestPass123!")
        # bcrypt hashes are 60 chars
        assert len(hashed) >= 50


class TestJWTHandler:
    def test_create_access_token_returns_string(self):
        token = JWTHandler.create_access_token({"sub": "1", "email": "a@b.com"})
        assert isinstance(token, str)

    def test_access_token_has_three_parts(self):
        token = JWTHandler.create_access_token({"sub": "1"})
        parts = token.split(".")
        assert len(parts) == 3

    def test_verify_valid_token(self):
        data = {"sub": "42", "email": "user@example.com"}
        token = JWTHandler.create_access_token(data)
        payload = JWTHandler.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["email"] == "user@example.com"

    def test_verify_invalid_token_returns_none(self):
        assert JWTHandler.verify_token("not.a.token") is None

    def test_verify_tampered_token_returns_none(self):
        token = JWTHandler.create_access_token({"sub": "1"})
        tampered = token[:-5] + "XXXXX"
        assert JWTHandler.verify_token(tampered) is None

    def test_verify_empty_string_returns_none(self):
        assert JWTHandler.verify_token("") is None

    def test_create_refresh_token_has_refresh_type(self):
        token = JWTHandler.create_refresh_token({"sub": "1"})
        payload = JWTHandler.verify_token(token)
        assert payload is not None
        assert payload.get("type") == "refresh"

    def test_access_token_contains_expiry(self):
        token = JWTHandler.create_access_token({"sub": "1"})
        payload = JWTHandler.verify_token(token)
        assert "exp" in payload

    def test_custom_expiry_respected(self):
        # Very short lived token (1 second)
        token = JWTHandler.create_access_token(
            {"sub": "1"}, expires_delta=timedelta(seconds=1)
        )
        # Should still be valid immediately
        assert JWTHandler.verify_token(token) is not None

    def test_expired_token_returns_none(self):
        token = JWTHandler.create_access_token(
            {"sub": "1"}, expires_delta=timedelta(seconds=-1)
        )
        assert JWTHandler.verify_token(token) is None


class TestEncryptionHandler:
    def test_encrypt_returns_different_value(self):
        original = "sensitive_data_12345"
        encrypted = EncryptionHandler.encrypt(original)
        assert encrypted != original

    def test_decrypt_roundtrip(self):
        original = "sensitive_data_12345"
        encrypted = EncryptionHandler.encrypt(original)
        decrypted = EncryptionHandler.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_empty_string(self):
        encrypted = EncryptionHandler.encrypt("")
        decrypted = EncryptionHandler.decrypt(encrypted)
        assert decrypted == ""

    def test_encrypt_unicode_string(self):
        original = "contraseña_secreta_ñoño"
        encrypted = EncryptionHandler.encrypt(original)
        decrypted = EncryptionHandler.decrypt(encrypted)
        assert decrypted == original

    def test_decrypt_invalid_data_returns_input(self):
        # Should not raise; falls back to returning input
        result = EncryptionHandler.decrypt("not-valid-fernet-data")
        assert result == "not-valid-fernet-data"


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 17: API Key Service
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from app.services.api_key_service import APIKeyService
from app.services.rate_limiter import RateLimiter
from app.services.ip_validator import IPValidator
from app.services.request_signer import RequestSigner
from app.crud.security import SecurityCRUD
from app.models.security import (
    APIKey, RateLimitConfig, IPWhitelist, SecurityAuditLog, TokenBucket
)


def _make_user(db):
    """Create a minimal User in the test DB."""
    from app.models.user import User
    user = User(
        email=f"sec17_{time.time_ns()}@test.com",
        username=f"sec17_{time.time_ns()}",
        hashed_password=PasswordHandler.hash_password("pw123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestAPIKeyService:

    def test_generate_returns_full_key(self, db_session):
        user = _make_user(db_session)
        result = APIKeyService.generate_api_key(user.id, db_session, name="k1")
        assert result["key"].startswith("rtsa_")
        assert len(result["key"]) == 45

    def test_key_prefix_is_first_20_chars(self, db_session):
        user = _make_user(db_session)
        result = APIKeyService.generate_api_key(user.id, db_session, name="k2")
        assert result["key_prefix"] == result["key"][:20]

    def test_key_hash_differs_from_plaintext(self, db_session):
        user = _make_user(db_session)
        result = APIKeyService.generate_api_key(user.id, db_session, name="k3")
        api_key = db_session.query(APIKey).filter(APIKey.id == result["key_id"]).first()
        assert api_key.key_hash != result["key"]

    def test_validate_correct_key(self, db_session):
        user = _make_user(db_session)
        gen = APIKeyService.generate_api_key(user.id, db_session, name="v1")
        res = APIKeyService.validate_api_key(gen["key"], db_session)
        assert res["valid"] is True
        assert res["user_id"] == user.id

    def test_validate_wrong_key_fails(self, db_session):
        user = _make_user(db_session)
        APIKeyService.generate_api_key(user.id, db_session, name="v2")
        res = APIKeyService.validate_api_key("rtsa_" + "z" * 40, db_session)
        assert res["valid"] is False

    def test_revoked_key_invalid(self, db_session):
        user = _make_user(db_session)
        gen = APIKeyService.generate_api_key(user.id, db_session, name="rev")
        APIKeyService.revoke_api_key(gen["key_id"], db_session)
        res = APIKeyService.validate_api_key(gen["key"], db_session)
        assert res["valid"] is False

    def test_rotate_issues_new_key(self, db_session):
        user = _make_user(db_session)
        gen = APIKeyService.generate_api_key(user.id, db_session, name="rot")
        new = APIKeyService.rotate_api_key(gen["key_id"], db_session)
        assert new["key"] != gen["key"]

    def test_rotate_revokes_old_key(self, db_session):
        user = _make_user(db_session)
        gen = APIKeyService.generate_api_key(user.id, db_session, name="rot2")
        APIKeyService.rotate_api_key(gen["key_id"], db_session)
        old = db_session.query(APIKey).filter(APIKey.id == gen["key_id"]).first()
        assert old.is_revoked is True

    def test_revoke_returns_false_for_missing_key(self, db_session):
        assert APIKeyService.revoke_api_key(999999, db_session) is False

    def test_scopes_stored_correctly(self, db_session):
        user = _make_user(db_session)
        scopes = ["read:findings", "write:reports"]
        gen = APIKeyService.generate_api_key(user.id, db_session, name="sc", scopes=scopes)
        api_key = db_session.query(APIKey).filter(APIKey.id == gen["key_id"]).first()
        assert api_key.scopes == scopes

    def test_expiry_set_when_provided(self, db_session):
        user = _make_user(db_session)
        gen = APIKeyService.generate_api_key(
            user.id, db_session, name="exp", expires_in_days=7
        )
        assert gen["expires_at"] is not None

    def test_last_used_updated_on_validate(self, db_session):
        user = _make_user(db_session)
        gen = APIKeyService.generate_api_key(user.id, db_session, name="lu")
        api_key = db_session.query(APIKey).filter(APIKey.id == gen["key_id"]).first()
        assert api_key.last_used_at is None
        APIKeyService.validate_api_key(gen["key"], db_session)
        db_session.refresh(api_key)
        assert api_key.last_used_at is not None


class TestRateLimiterPhase17:

    def test_first_request_allowed(self, db_session):
        user = _make_user(db_session)
        allowed, _, retry = RateLimiter(db_session).check_rate_limit(
            user.id, "/ep", default_rpm=60, burst_capacity=10
        )
        assert allowed is True
        assert retry == 0

    def test_burst_exhaustion_blocks(self, db_session):
        user = _make_user(db_session)
        ep = f"/burst_{time.time_ns()}"
        for _ in range(3):
            RateLimiter(db_session).check_rate_limit(user.id, ep, default_rpm=60, burst_capacity=3)
        allowed, _, retry = RateLimiter(db_session).check_rate_limit(
            user.id, ep, default_rpm=60, burst_capacity=3
        )
        assert allowed is False
        assert retry > 0

    def test_rate_limit_headers_keys(self, db_session):
        user = _make_user(db_session)
        ep = f"/hdr_{time.time_ns()}"
        RateLimiter(db_session).check_rate_limit(user.id, ep, default_rpm=30, burst_capacity=5)
        headers = RateLimiter(db_session).get_rate_limit_headers(user.id, ep)
        assert "RateLimit-Limit" in headers
        assert "RateLimit-Remaining" in headers
        assert "RateLimit-Reset" in headers


class TestIPValidatorPhase17:

    def test_no_config_allows_all(self, db_session):
        user = _make_user(db_session)
        ok, _ = IPValidator.is_ip_allowed(user.id, "8.8.8.8", db_session)
        assert ok is True

    def test_blacklisted_cidr_blocked(self, db_session):
        user = _make_user(db_session)
        cfg = RateLimitConfig(
            user_id=user.id, requests_per_minute=60, burst_capacity=100,
            endpoint_limits={}, ip_whitelist=[], ip_blacklist=["203.0.113.0/24"],
        )
        db_session.add(cfg)
        db_session.commit()
        ok, reason = IPValidator.is_ip_allowed(user.id, "203.0.113.10", db_session)
        assert ok is False and "blacklisted" in reason

    def test_whitelist_allows_match(self, db_session):
        user = _make_user(db_session)
        cfg = RateLimitConfig(
            user_id=user.id, requests_per_minute=60, burst_capacity=100,
            endpoint_limits={}, ip_whitelist=["192.168.0.0/16"], ip_blacklist=[],
        )
        db_session.add(cfg)
        db_session.commit()
        ok, _ = IPValidator.is_ip_allowed(user.id, "192.168.1.100", db_session)
        assert ok is True

    def test_whitelist_blocks_non_match(self, db_session):
        user = _make_user(db_session)
        cfg = RateLimitConfig(
            user_id=user.id, requests_per_minute=60, burst_capacity=100,
            endpoint_limits={}, ip_whitelist=["10.0.0.0/8"], ip_blacklist=[],
        )
        db_session.add(cfg)
        db_session.commit()
        ok, _ = IPValidator.is_ip_allowed(user.id, "8.8.8.8", db_session)
        assert ok is False

    def test_add_valid_cidr(self, db_session):
        user = _make_user(db_session)
        res = IPValidator.add_whitelist_ip(user.id, "10.0.0.0/8", db_session)
        assert res["success"] is True

    def test_add_invalid_cidr_error(self, db_session):
        user = _make_user(db_session)
        res = IPValidator.add_whitelist_ip(user.id, "bad-cidr", db_session)
        assert res["success"] is False

    def test_validate_cidr_helper(self):
        assert IPValidator.validate_cidr("192.168.0.0/24") is True
        assert IPValidator.validate_cidr("garbage") is False


class TestRequestSignerPhase17:
    SECRET = "test-secret-key"

    def test_sign_returns_64_hex_chars(self):
        sig = RequestSigner.sign_payload({"k": "v"}, self.SECRET)
        assert len(sig) == 64

    def test_sign_deterministic(self):
        p = {"a": 1}
        assert RequestSigner.sign_payload(p, self.SECRET) == RequestSigner.sign_payload(p, self.SECRET)

    def test_signed_webhook_structure(self):
        w = RequestSigner.create_signed_webhook({"event": "ping"}, self.SECRET)
        assert {"payload", "signature", "algorithm"} <= w.keys()
        assert w["algorithm"] == "sha256"

    def test_verify_valid_signature(self):
        ts = int(time.time())
        w = RequestSigner.create_signed_webhook({"x": 1}, self.SECRET, timestamp=ts)
        ok, err = RequestSigner.verify_webhook_signature(
            w["payload"], w["signature"], self.SECRET, timestamp=ts
        )
        assert ok is True and err is None

    def test_verify_tampered_fails(self):
        w = RequestSigner.create_signed_webhook({"x": 1}, self.SECRET)
        tampered = {**w["payload"], "evil": True}
        ok, err = RequestSigner.verify_webhook_signature(tampered, w["signature"], self.SECRET)
        assert ok is False

    def test_verify_stale_timestamp_fails(self):
        ts = int(time.time()) - 600
        w = RequestSigner.create_signed_webhook({"x": 1}, self.SECRET, timestamp=ts)
        ok, err = RequestSigner.verify_webhook_signature(
            w["payload"], w["signature"], self.SECRET, timestamp=ts, tolerance_seconds=300
        )
        assert ok is False and "Timestamp too old" in err

    def test_verify_wrong_secret_fails(self):
        w = RequestSigner.create_signed_webhook({"x": 1}, self.SECRET)
        ok, _ = RequestSigner.verify_webhook_signature(
            w["payload"], w["signature"], "other-secret"
        )
        assert ok is False


class TestSecurityCRUDPhase17:

    def test_log_event_creates_record(self, db_session):
        user = _make_user(db_session)
        SecurityCRUD.log_security_event(
            db_session, user_id=user.id, method="GET",
            endpoint="/api/v1/test", status_code=200, ip_address="127.0.0.1",
        )
        logs = db_session.query(SecurityAuditLog).filter(
            SecurityAuditLog.user_id == user.id
        ).all()
        assert len(logs) == 1

    def test_get_audit_logs_limit(self, db_session):
        user = _make_user(db_session)
        for i in range(5):
            SecurityCRUD.log_security_event(db_session, user_id=user.id, method="POST",
                                            endpoint=f"/ep/{i}")
        logs = SecurityCRUD.get_security_audit_logs(db_session, user.id, limit=3)
        assert len(logs) == 3

    def test_upsert_config_creates_new(self, db_session):
        user = _make_user(db_session)
        cfg = SecurityCRUD.upsert_rate_limit_config(
            db_session, user.id, requests_per_minute=120, burst_capacity=200
        )
        assert cfg.requests_per_minute == 120

    def test_upsert_config_updates_existing(self, db_session):
        user = _make_user(db_session)
        SecurityCRUD.upsert_rate_limit_config(db_session, user.id, requests_per_minute=60)
        cfg = SecurityCRUD.upsert_rate_limit_config(db_session, user.id, requests_per_minute=90)
        assert cfg.requests_per_minute == 90
        count = db_session.query(RateLimitConfig).filter(
            RateLimitConfig.user_id == user.id
        ).count()
        assert count == 1


class TestSecurityEndpoints:
    """Endpoint integration tests via TestClient."""

    def test_create_api_key(self, client, auth_token):
        resp = client.post(
            "/api/v1/security/api-keys",
            json={"name": "My Key"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["key"].startswith("rtsa_")

    def test_list_api_keys(self, client, auth_token):
        client.post(
            "/api/v1/security/api-keys",
            json={"name": "Listed"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        resp = client.get(
            "/api/v1/security/api-keys",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_revoke_api_key(self, client, auth_token):
        cr = client.post(
            "/api/v1/security/api-keys",
            json={"name": "ToRevoke"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        key_id = cr.json()["key_id"]
        resp = client.delete(
            f"/api/v1/security/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 204

    def test_rotate_api_key(self, client, auth_token):
        cr = client.post(
            "/api/v1/security/api-keys",
            json={"name": "ToRotate"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        key_id = cr.json()["key_id"]
        resp = client.post(
            f"/api/v1/security/api-keys/{key_id}/rotate",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["key"] != cr.json()["key"]

    def test_add_ip_whitelist(self, client, auth_token):
        resp = client.post(
            "/api/v1/security/ip-whitelist",
            json={"cidr_block": "10.0.0.0/8"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 201

    def test_add_invalid_cidr_400(self, client, auth_token):
        resp = client.post(
            "/api/v1/security/ip-whitelist",
            json={"cidr_block": "bad"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 400

    def test_list_ip_whitelist(self, client, auth_token):
        resp = client.get(
            "/api/v1/security/ip-whitelist",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200

    def test_upsert_rate_limit_config(self, client, auth_token):
        resp = client.put(
            "/api/v1/security/rate-limit/config",
            json={"requests_per_minute": 30, "burst_capacity": 50},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["requests_per_minute"] == 30

    def test_get_rate_limit_config(self, client, auth_token):
        client.put(
            "/api/v1/security/rate-limit/config",
            json={"requests_per_minute": 45, "burst_capacity": 90},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        resp = client.get(
            "/api/v1/security/rate-limit/config",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200

    def test_audit_logs_endpoint(self, client, auth_token):
        resp = client.get(
            "/api/v1/security/audit-logs",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_webhook_verify_valid(self, client, auth_token):
        secret = "webhook-test-secret"
        w = RequestSigner.create_signed_webhook({"event": "test"}, secret)
        resp = client.post(
            "/api/v1/security/webhook/verify",
            json={"payload": w["payload"], "signature": w["signature"], "secret": secret},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_webhook_verify_invalid(self, client, auth_token):
        resp = client.post(
            "/api/v1/security/webhook/verify",
            json={"payload": {"x": 1}, "signature": "a" * 64, "secret": "wrong"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is False

    def test_revoke_nonexistent_key_404(self, client, auth_token):
        resp = client.delete(
            "/api/v1/security/api-keys/999999",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 404
