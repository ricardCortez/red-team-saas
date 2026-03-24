"""Unit tests – security utilities (no DB required)"""
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
