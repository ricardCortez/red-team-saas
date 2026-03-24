"""Unit tests – AuthService business logic"""
import pytest

from app.services.auth_service import AuthService
from app.schemas.user import UserCreate


def _make_user_data(
    email="svc@example.com",
    username="svcuser",
    password="TestPass123!",
    full_name="Service User",
):
    return UserCreate(email=email, username=username, password=password, full_name=full_name)


class TestRegisterUser:
    def test_register_success(self, db_session):
        data = _make_user_data()
        user = AuthService.register_user(db_session, data)
        assert user.id is not None
        assert user.email == data.email
        assert user.username == data.username

    def test_register_hashes_password(self, db_session):
        data = _make_user_data()
        user = AuthService.register_user(db_session, data)
        assert user.hashed_password != data.password

    def test_register_sets_active(self, db_session):
        data = _make_user_data()
        user = AuthService.register_user(db_session, data)
        assert user.is_active is True

    def test_register_sets_full_name(self, db_session):
        data = _make_user_data(full_name="Full Name Here")
        user = AuthService.register_user(db_session, data)
        assert user.full_name == "Full Name Here"

    def test_register_duplicate_email_raises(self, db_session):
        data = _make_user_data()
        AuthService.register_user(db_session, data)
        with pytest.raises(ValueError, match="already exists"):
            AuthService.register_user(db_session, _make_user_data(username="other"))

    def test_register_duplicate_username_raises(self, db_session):
        data = _make_user_data()
        AuthService.register_user(db_session, data)
        with pytest.raises(ValueError, match="already exists"):
            AuthService.register_user(db_session, _make_user_data(email="other@x.com"))

    def test_register_persists_to_db(self, db_session):
        data = _make_user_data()
        AuthService.register_user(db_session, data)
        from app.models.user import User
        found = db_session.query(User).filter(User.email == data.email).first()
        assert found is not None


class TestAuthenticateUser:
    def test_authenticate_success(self, db_session):
        data = _make_user_data()
        AuthService.register_user(db_session, data)
        user = AuthService.authenticate_user(db_session, data.email, data.password)
        assert user is not None
        assert user.email == data.email

    def test_authenticate_wrong_password_returns_none(self, db_session):
        data = _make_user_data()
        AuthService.register_user(db_session, data)
        result = AuthService.authenticate_user(db_session, data.email, "WrongPassword!")
        assert result is None

    def test_authenticate_nonexistent_email_returns_none(self, db_session):
        result = AuthService.authenticate_user(db_session, "ghost@example.com", "pass")
        assert result is None

    def test_authenticate_inactive_user_returns_none(self, db_session):
        data = _make_user_data()
        user = AuthService.register_user(db_session, data)
        user.is_active = False
        db_session.commit()
        result = AuthService.authenticate_user(db_session, data.email, data.password)
        assert result is None


class TestCreateTokens:
    def test_tokens_returned(self, db_session):
        data = _make_user_data()
        user = AuthService.register_user(db_session, data)
        tokens = AuthService.create_tokens(user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

    def test_access_token_is_valid_jwt(self, db_session):
        from app.core.security import JWTHandler
        data = _make_user_data()
        user = AuthService.register_user(db_session, data)
        tokens = AuthService.create_tokens(user)
        payload = JWTHandler.verify_token(tokens["access_token"])
        assert payload is not None
        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email

    def test_refresh_token_has_refresh_type(self, db_session):
        from app.core.security import JWTHandler
        data = _make_user_data()
        user = AuthService.register_user(db_session, data)
        tokens = AuthService.create_tokens(user)
        payload = JWTHandler.verify_token(tokens["refresh_token"])
        assert payload is not None
        assert payload.get("type") == "refresh"


class TestGetUserById:
    def test_get_existing_user(self, db_session):
        data = _make_user_data()
        created = AuthService.register_user(db_session, data)
        found = AuthService.get_user_by_id(db_session, created.id)
        assert found is not None
        assert found.id == created.id

    def test_get_nonexistent_user_returns_none(self, db_session):
        result = AuthService.get_user_by_id(db_session, 99999)
        assert result is None
