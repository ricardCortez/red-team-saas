"""Security models — Phase 17

Tables:
  api_keys, rate_limit_configs, ip_whitelists, request_signatures,
  oauth_providers, oauth_tokens, security_audit_logs, token_buckets
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    JSON, DateTime, ForeignKey, Enum as SAEnum, LargeBinary,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.base import BaseModel


class APIKey(Base, BaseModel):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", foreign_keys=[user_id])

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Key storage (hashed with bcrypt)
    key_hash = Column(String(255), unique=True, nullable=False)
    key_prefix = Column(String(20), nullable=False, index=True)

    # Permissions
    scopes = Column(JSON, default=list)  # ["read:findings", "write:findings"]

    # Lifetime
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(Text, nullable=True)

    # Rotation tracking
    rotated_from = Column(Integer, ForeignKey("api_keys.id"), nullable=True)


class RateLimitConfig(Base, BaseModel):
    __tablename__ = "rate_limit_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user = relationship("User")

    requests_per_minute = Column(Integer, default=60, nullable=False)
    burst_capacity = Column(Integer, default=100, nullable=False)

    # Custom limits by endpoint: {"/api/v1/tools": 10}
    endpoint_limits = Column(JSON, default=dict)

    # IP allow/deny lists (CIDR blocks)
    ip_whitelist = Column(JSON, default=list)
    ip_blacklist = Column(JSON, default=list)


class IPWhitelist(Base, BaseModel):
    __tablename__ = "ip_whitelists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", foreign_keys="IPWhitelist.user_id")

    cidr_block = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by_user = relationship("User", foreign_keys="IPWhitelist.created_by")


class RequestSignature(Base, BaseModel):
    __tablename__ = "request_signatures"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False)
    integration = relationship("Integration")

    # Signature config (secret stored encrypted)
    webhook_secret = Column(Text, nullable=False)
    signing_algorithm = Column(String(50), default="HMAC-SHA256", nullable=False)

    # Validation
    verify_timestamp = Column(Boolean, default=True, nullable=False)
    timestamp_tolerance_seconds = Column(Integer, default=300, nullable=False)


class OAuthProvider(Base, BaseModel):
    __tablename__ = "oauth_providers"

    id = Column(Integer, primary_key=True, index=True)

    provider_name = Column(String(50), unique=True, nullable=False)  # "github", "google"

    # OAuth credentials
    client_id = Column(String(255), nullable=False)
    client_secret = Column(Text, nullable=False)  # Encrypted

    # Configuration
    authorize_url = Column(String(500), nullable=False)
    token_url = Column(String(500), nullable=False)
    user_info_url = Column(String(500), nullable=False)

    redirect_uri = Column(String(500), nullable=False)
    scopes = Column(JSON, default=list)

    is_enabled = Column(Boolean, default=True, nullable=False)


class OAuthToken(Base, BaseModel):
    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User")

    provider = Column(String(50), nullable=False)
    provider_user_id = Column(String(255), nullable=False)

    # Tokens (encrypted)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class SecurityAuditLog(Base):
    """Append-only audit trail — no BaseModel to avoid updated_at."""

    __tablename__ = "security_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user = relationship("User")

    # Request details
    method = Column(String(10), nullable=True)
    endpoint = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=True)

    # Security context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    api_key_prefix = Column(String(20), nullable=True)

    # Audit trail
    request_headers = Column(JSON, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Security events
    rate_limit_exceeded = Column(Boolean, default=False)
    ip_blocked = Column(Boolean, default=False)
    invalid_signature = Column(Boolean, default=False)

    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class TokenBucket(Base, BaseModel):
    __tablename__ = "token_buckets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User")

    endpoint_pattern = Column(String(200), nullable=False)  # "/api/v1/findings" or "*"

    # Token bucket state
    tokens_available = Column(Float, nullable=False)
    last_refill_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
