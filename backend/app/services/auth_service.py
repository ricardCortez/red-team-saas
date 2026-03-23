"""Authentication service"""
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import JWTHandler, PasswordHandler
from app.schemas.user import UserCreate
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service"""

    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """Register new user"""
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()

        if existing_user:
            raise ValueError("User already exists")

        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=PasswordHandler.hash_password(user_data.password),
            full_name=user_data.full_name,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"User registered: {user.email}")
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user"""
        user = db.query(User).filter(User.email == email).first()

        if not user or not PasswordHandler.verify_password(password, user.hashed_password) or not user.is_active:
            return None

        logger.info(f"User authenticated: {user.email}")
        return user

    @staticmethod
    def create_tokens(user: User) -> dict:
        """Create access and refresh tokens"""
        access_token = JWTHandler.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": str(user.role)}
        )
        refresh_token = JWTHandler.create_refresh_token(
            data={"sub": str(user.id), "type": "refresh"}
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
