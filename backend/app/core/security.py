"""Security utilities: JWT, encryption, passwords"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Encryption
try:
    cipher = Fernet(settings.ENCRYPTION_KEY.encode() if len(settings.ENCRYPTION_KEY) >= 32
                    else Fernet.generate_key())
except Exception:
    cipher = Fernet(Fernet.generate_key())


class JWTHandler:
    """JWT token management"""

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except jwt.InvalidTokenError:
            return None


class PasswordHandler:
    """Password hashing and verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return pwd_context.verify(plain_password, hashed_password)


class EncryptionHandler:
    """Field-level encryption for sensitive data"""

    @staticmethod
    def encrypt(data: str) -> str:
        """Encrypt string"""
        try:
            return cipher.encrypt(data.encode()).decode()
        except Exception:
            return data

    @staticmethod
    def decrypt(encrypted_data: str) -> str:
        """Decrypt string"""
        try:
            return cipher.decrypt(encrypted_data.encode()).decode()
        except Exception:
            return encrypted_data
