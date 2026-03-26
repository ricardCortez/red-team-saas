"""Security endpoints — Phase 17

Routes:
  POST   /security/api-keys                  create API key
  GET    /security/api-keys                  list API keys
  POST   /security/api-keys/{id}/rotate      rotate API key
  DELETE /security/api-keys/{id}             revoke API key
  POST   /security/ip-whitelist              add IP whitelist entry
  GET    /security/ip-whitelist              list whitelist entries
  DELETE /security/ip-whitelist/{id}         disable whitelist entry
  GET    /security/rate-limit/config         get rate limit config
  PUT    /security/rate-limit/config         upsert rate limit config
  GET    /security/audit-logs                query audit logs
  POST   /security/webhook/verify            verify webhook signature
  GET    /security/oauth/{provider}/authorize OAuth authorize redirect
  POST   /security/oauth/{provider}/callback  OAuth callback
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.api_key_service import APIKeyService
from app.services.ip_validator import IPValidator
from app.services.request_signer import RequestSigner
from app.crud.security import SecurityCRUD
from app.schemas.security import (
    APIKeyCreate,
    APIKeyResponse,
    IPWhitelistCreate,
    IPWhitelistResponse,
    RateLimitConfigCreate,
    RateLimitConfigResponse,
    SecurityAuditLogResponse,
    WebhookVerifyRequest,
    WebhookVerifyResponse,
    OAuthAuthorizeResponse,
)

router = APIRouter(prefix="/security", tags=["Security"])


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a new API key (returned once — store it securely)."""
    return APIKeyService.generate_api_key(
        user_id=current_user.id,
        db=db,
        name=payload.name,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
        description=payload.description,
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all API keys for the current user."""
    return SecurityCRUD.get_api_keys(db, current_user.id)


@router.post("/api-keys/{key_id}/rotate", status_code=status.HTTP_201_CREATED)
async def rotate_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke an existing key and issue a new one with the same scopes."""
    # Ownership check
    existing = SecurityCRUD.get_api_key_by_id(db, key_id, current_user.id)
    if not existing:
        raise HTTPException(status_code=404, detail="API key not found")

    result = APIKeyService.rotate_api_key(key_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke an API key permanently."""
    existing = SecurityCRUD.get_api_key_by_id(db, key_id, current_user.id)
    if not existing:
        raise HTTPException(status_code=404, detail="API key not found")

    APIKeyService.revoke_api_key(key_id, db, reason="Revoked by user")


# ── IP Whitelist ──────────────────────────────────────────────────────────────

@router.post(
    "/ip-whitelist",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def add_ip_whitelist(
    payload: IPWhitelistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a CIDR block to the user's IP whitelist."""
    result = IPValidator.add_whitelist_ip(
        current_user.id, payload.cidr_block, db, payload.description
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/ip-whitelist", response_model=list[IPWhitelistResponse])
async def list_ip_whitelist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active IP whitelist entries."""
    return SecurityCRUD.get_ip_whitelist(db, current_user.id)


@router.delete(
    "/ip-whitelist/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_ip_whitelist_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disable an IP whitelist entry."""
    removed = IPValidator.remove_whitelist_ip(entry_id, current_user.id, db)
    if not removed:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")


# ── Rate Limit Config ─────────────────────────────────────────────────────────

@router.get("/rate-limit/config", response_model=RateLimitConfigResponse)
async def get_rate_limit_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current rate-limit configuration for the user."""
    config = SecurityCRUD.get_rate_limit_config(db, current_user.id)
    if not config:
        raise HTTPException(status_code=404, detail="No rate limit config found")
    return config


@router.put("/rate-limit/config", response_model=RateLimitConfigResponse)
async def upsert_rate_limit_config(
    payload: RateLimitConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update rate-limit configuration."""
    return SecurityCRUD.upsert_rate_limit_config(
        db,
        current_user.id,
        requests_per_minute=payload.requests_per_minute,
        burst_capacity=payload.burst_capacity,
        endpoint_limits=payload.endpoint_limits,
        ip_whitelist=payload.ip_whitelist,
        ip_blacklist=payload.ip_blacklist,
    )


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=list[SecurityAuditLogResponse])
async def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the most recent security audit log entries for the user."""
    return SecurityCRUD.get_security_audit_logs(db, current_user.id, limit)


# ── Webhook Signature Verification ───────────────────────────────────────────

@router.post("/webhook/verify", response_model=WebhookVerifyResponse)
async def verify_webhook(
    payload: WebhookVerifyRequest,
    current_user: User = Depends(get_current_user),
):
    """Verify an HMAC-SHA256 webhook signature."""
    valid, error = RequestSigner.verify_webhook_signature(
        payload=payload.payload,
        signature=payload.signature,
        secret=payload.secret,
        timestamp=payload.timestamp,
    )
    return WebhookVerifyResponse(valid=valid, error=error)


# ── OAuth 2.0 ─────────────────────────────────────────────────────────────────

@router.get(
    "/oauth/{provider}/authorize",
    response_model=OAuthAuthorizeResponse,
)
async def oauth_authorize(
    provider: str,
    db: Session = Depends(get_db),
):
    """Return the OAuth 2.0 authorization URL for a provider."""
    from app.services.oauth_service import OAuth2Service

    svc = OAuth2Service()
    try:
        auth_url = await svc.get_authorization_url(provider, db)
        return OAuthAuthorizeResponse(authorization_url=auth_url, provider=provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle OAuth 2.0 authorization code callback."""
    from app.services.oauth_service import OAuth2Service
    from app.core.security import JWTHandler

    svc = OAuth2Service()
    try:
        user = await svc.create_or_update_user_from_oauth(provider, code, db)
        access_token = JWTHandler.create_access_token({"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
