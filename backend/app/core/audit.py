"""Audit logging helper"""
import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


async def log_action(
    db: Session,
    user_id: int,
    action: str,
    resource_id: Optional[int] = None,
    details: Optional[dict] = None,
) -> None:
    """Append an audit log entry (fire-and-forget, errors are swallowed)"""
    try:
        resource = str(resource_id) if resource_id is not None else None
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            details=json.dumps(details) if details else None,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
