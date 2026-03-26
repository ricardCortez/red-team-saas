"""Pydantic schemas — Phase 17 Security"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class APIKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    scopes: Optional[List[str]] = ["read:*"]
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: List[str]
    expires_at: Optional[datetime] = None
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyRotateResponse(APIKeyResponse):
    key: str
    message: str


class IPWhitelistCreate(BaseModel):
    cidr_block: str = Field(..., examples=["192.168.1.0/24"])
    description: Optional[str] = None


class IPWhitelistResponse(BaseModel):
    id: int
    cidr_block: str
    description: Optional[str] = None
    is_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RateLimitConfigCreate(BaseModel):
    requests_per_minute: int = Field(60, ge=1, le=10000)
    burst_capacity: int = Field(100, ge=1, le=10000)
    endpoint_limits: Optional[dict] = None
    ip_whitelist: Optional[List[str]] = None
    ip_blacklist: Optional[List[str]] = None


class RateLimitConfigResponse(BaseModel):
    id: int
    requests_per_minute: int
    burst_capacity: int
    endpoint_limits: Optional[dict] = None
    ip_whitelist: Optional[List[str]] = None
    ip_blacklist: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class SecurityAuditLogResponse(BaseModel):
    id: int
    method: Optional[str] = None
    endpoint: Optional[str] = None
    status_code: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    api_key_prefix: Optional[str] = None
    response_time_ms: Optional[int] = None
    rate_limit_exceeded: bool
    ip_blocked: bool
    invalid_signature: bool
    error_message: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
    provider: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class WebhookVerifyRequest(BaseModel):
    payload: dict
    signature: str
    timestamp: Optional[int] = None
    secret: str


class WebhookVerifyResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
