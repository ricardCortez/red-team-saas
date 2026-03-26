"""API Key management service — Phase 17"""
import secrets
import string
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.models.security import APIKey
from app.core.security import PasswordHandler


_ALPHABET = string.ascii_letters + string.digits
_KEY_PREFIX = "rtsa_"
_RANDOM_LEN = 40


class APIKeyService:

    @staticmethod
    def generate_api_key(
        user_id: int,
        db: Session,
        name: str,
        scopes: list = None,
        expires_in_days: int = None,
        description: str = None,
    ) -> dict:
        """
        Generate a new API key.

        Returns dict with 'key' (shown ONCE), 'key_id', 'key_prefix',
        'expires_at', and 'message'.
        """
        random_part = "".join(secrets.choice(_ALPHABET) for _ in range(_RANDOM_LEN))
        full_key = _KEY_PREFIX + random_part
        key_prefix = full_key[:20]

        key_hash = PasswordHandler.hash_password(full_key)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        api_key = APIKey(
            user_id=user_id,
            name=name,
            description=description,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes or ["read:*"],
            expires_at=expires_at,
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        return {
            "key": full_key,
            "key_id": api_key.id,
            "key_prefix": api_key.key_prefix,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "message": "Store this key securely — it will not be shown again.",
        }

    @staticmethod
    def validate_api_key(full_key: str, db: Session) -> dict:
        """
        Validate an API key.

        Returns dict with 'valid', 'user_id', 'scopes', 'key_id' or 'error'.
        """
        if len(full_key) < 20:
            return {"valid": False, "error": "API key too short"}

        key_prefix = full_key[:20]

        api_key = (
            db.query(APIKey)
            .filter(
                APIKey.key_prefix == key_prefix,
                APIKey.is_active == True,
                APIKey.is_revoked == False,
            )
            .first()
        )

        if not api_key:
            return {"valid": False, "error": "API key not found or inactive"}

        # Check expiry
        if api_key.expires_at:
            expires = api_key.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires:
                return {"valid": False, "error": "API key expired"}

        # Verify hash
        if not PasswordHandler.verify_password(full_key, api_key.key_hash):
            return {"valid": False, "error": "Invalid API key"}

        # Update last_used_at
        api_key.last_used_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "valid": True,
            "user_id": api_key.user_id,
            "scopes": api_key.scopes,
            "key_id": api_key.id,
        }

    @staticmethod
    def rotate_api_key(key_id: int, db: Session) -> dict:
        """
        Rotate an API key: revoke the old one and issue a new one.

        Returns same dict as generate_api_key().
        """
        old_key = db.query(APIKey).filter(APIKey.id == key_id).first()

        if not old_key:
            return {"error": "Key not found"}

        # Issue new key with same settings
        expires_in_days = None
        if old_key.expires_at:
            expires = old_key.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            remaining = (expires - datetime.now(timezone.utc)).days
            expires_in_days = max(1, remaining)

        new_key_info = APIKeyService.generate_api_key(
            user_id=old_key.user_id,
            db=db,
            name=f"{old_key.name} (rotated)",
            scopes=old_key.scopes,
            expires_in_days=expires_in_days,
        )

        # Revoke old key and link to new one
        old_key.is_revoked = True
        old_key.revoked_reason = "Rotated"
        old_key.revoked_at = datetime.now(timezone.utc)

        new_api_key = db.query(APIKey).filter(APIKey.id == new_key_info["key_id"]).first()
        if new_api_key:
            new_api_key.rotated_from = key_id

        db.commit()
        return new_key_info

    @staticmethod
    def revoke_api_key(key_id: int, db: Session, reason: str = None) -> bool:
        """Revoke an API key. Returns True on success."""
        api_key = db.query(APIKey).filter(APIKey.id == key_id).first()

        if not api_key:
            return False

        api_key.is_revoked = True
        api_key.revoked_reason = reason or "Manual revocation"
        api_key.revoked_at = datetime.now(timezone.utc)
        db.commit()
        return True
