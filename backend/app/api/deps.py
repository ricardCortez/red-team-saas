"""API dependencies: DB session, auth, role checks"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal
from app.core.security import JWTHandler
from app.models.user import User

security = HTTPBearer()


def get_db():
    """Yield a database session, closing it when done"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT and return the active user"""
    token = credentials.credentials
    payload = JWTHandler.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def require_role(roles: List[str]):
    """Return a dependency that enforces one of the given roles (superusers always pass)"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user
        role_value = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else current_user.role
        )
        if role_value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_value}' not authorized. Required: {roles}",
            )
        return current_user
    return role_checker
