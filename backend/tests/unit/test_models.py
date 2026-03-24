"""Unit tests – SQLAlchemy ORM models"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserRoleEnum
from app.core.security import PasswordHandler


class TestUserModel:
    def test_create_user(self, db_session):
        user = User(
            email="model@example.com",
            username="modeluser",
            hashed_password=PasswordHandler.hash_password("pass"),
            full_name="Model User",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == "model@example.com"
        assert user.username == "modeluser"

    def test_user_default_is_active(self, db_session):
        user = User(
            email="active@example.com",
            username="activeuser",
            hashed_password="hashed",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.is_active is True

    def test_user_default_not_superuser(self, db_session):
        user = User(
            email="super@example.com",
            username="superuser2",
            hashed_password="hashed",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.is_superuser is False

    def test_user_default_role_pentester(self, db_session):
        user = User(
            email="role@example.com",
            username="roleuser",
            hashed_password="hashed",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.role == UserRoleEnum.pentester

    def test_user_timestamps_set_on_create(self, db_session):
        user = User(
            email="ts@example.com",
            username="tsuser",
            hashed_password="hashed",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_unique_email_constraint(self, db_session):
        user1 = User(email="dup@example.com", username="u1", hashed_password="h")
        user2 = User(email="dup@example.com", username="u2", hashed_password="h")
        db_session.add(user1)
        db_session.commit()
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_unique_username_constraint(self, db_session):
        user1 = User(email="e1@example.com", username="sameuser", hashed_password="h")
        user2 = User(email="e2@example.com", username="sameuser", hashed_password="h")
        db_session.add(user1)
        db_session.commit()
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_password_not_stored_as_plain(self, db_session):
        plain_password = "MySecretPassword123!"
        user = User(
            email="pw@example.com",
            username="pwuser",
            hashed_password=PasswordHandler.hash_password(plain_password),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.hashed_password != plain_password

    def test_repr_contains_email(self, db_session):
        user = User(email="repr@example.com", username="repruser", hashed_password="h")
        db_session.add(user)
        db_session.commit()
        assert "repr@example.com" in repr(user)

    def test_full_name_optional(self, db_session):
        user = User(
            email="nofull@example.com",
            username="nofullname",
            hashed_password="h",
            full_name=None,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.full_name is None

    def test_all_roles_can_be_assigned(self, db_session):
        for i, role in enumerate(UserRoleEnum):
            user = User(
                email=f"role{i}@example.com",
                username=f"roleuser{i}",
                hashed_password="h",
                role=role,
            )
            db_session.add(user)
        db_session.commit()
        count = db_session.query(User).count()
        assert count == len(UserRoleEnum)
