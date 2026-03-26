"""CRUD operations — Phase 17 Security"""
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.security import (
    APIKey, SecurityAuditLog, IPWhitelist, RateLimitConfig, TokenBucket
)


class SecurityCRUD:

    @staticmethod
    def get_api_keys(db: Session, user_id: int):
        return (
            db.query(APIKey)
            .filter(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
            .all()
        )

    @staticmethod
    def get_api_key_by_id(db: Session, key_id: int, user_id: int):
        return (
            db.query(APIKey)
            .filter(APIKey.id == key_id, APIKey.user_id == user_id)
            .first()
        )

    @staticmethod
    def log_security_event(
        db: Session,
        user_id: int = None,
        method: str = None,
        endpoint: str = None,
        status_code: int = None,
        ip_address: str = None,
        user_agent: str = None,
        api_key_prefix: str = None,
        request_headers: dict = None,
        response_time_ms: int = None,
        rate_limit_exceeded: bool = False,
        ip_blocked: bool = False,
        invalid_signature: bool = False,
        error_message: str = None,
    ):
        log = SecurityAuditLog(
            user_id=user_id,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            ip_address=ip_address,
            user_agent=user_agent,
            api_key_prefix=api_key_prefix,
            request_headers=request_headers,
            response_time_ms=response_time_ms,
            rate_limit_exceeded=rate_limit_exceeded,
            ip_blocked=ip_blocked,
            invalid_signature=invalid_signature,
            error_message=error_message,
        )
        db.add(log)
        try:
            db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def get_security_audit_logs(db: Session, user_id: int, limit: int = 100):
        return (
            db.query(SecurityAuditLog)
            .filter(SecurityAuditLog.user_id == user_id)
            .order_by(SecurityAuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_ip_whitelist(db: Session, user_id: int):
        return (
            db.query(IPWhitelist)
            .filter(IPWhitelist.user_id == user_id, IPWhitelist.is_enabled == True)
            .all()
        )

    @staticmethod
    def get_rate_limit_config(db: Session, user_id: int):
        return (
            db.query(RateLimitConfig)
            .filter(RateLimitConfig.user_id == user_id)
            .first()
        )

    @staticmethod
    def upsert_rate_limit_config(
        db: Session,
        user_id: int,
        requests_per_minute: int = 60,
        burst_capacity: int = 100,
        endpoint_limits: dict = None,
        ip_whitelist: list = None,
        ip_blacklist: list = None,
    ) -> RateLimitConfig:
        config = SecurityCRUD.get_rate_limit_config(db, user_id)
        if config:
            config.requests_per_minute = requests_per_minute
            config.burst_capacity = burst_capacity
            if endpoint_limits is not None:
                config.endpoint_limits = endpoint_limits
            if ip_whitelist is not None:
                config.ip_whitelist = ip_whitelist
            if ip_blacklist is not None:
                config.ip_blacklist = ip_blacklist
        else:
            config = RateLimitConfig(
                user_id=user_id,
                requests_per_minute=requests_per_minute,
                burst_capacity=burst_capacity,
                endpoint_limits=endpoint_limits or {},
                ip_whitelist=ip_whitelist or [],
                ip_blacklist=ip_blacklist or [],
            )
            db.add(config)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def get_token_bucket(db: Session, user_id: int, endpoint: str):
        return (
            db.query(TokenBucket)
            .filter(
                TokenBucket.user_id == user_id,
                TokenBucket.endpoint_pattern == endpoint,
            )
            .first()
        )
