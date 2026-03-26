"""Notifications history API endpoints - Phase 8"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.notification import Notification, NotificationStatus
from app.schemas.notification import NotificationResponse

router = APIRouter()


@router.get("/notifications", response_model=dict)
def list_notifications(
    status: Optional[NotificationStatus] = Query(None),
    channel: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if status:
        q = q.filter(Notification.status == status)
    if channel:
        q = q.filter(Notification.channel == channel)

    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [NotificationResponse.model_validate(n) for n in items],
    }


@router.get("/notifications/stats")
def notification_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    return {
        "total": q.count(),
        "sent": q.filter(Notification.status == NotificationStatus.SENT).count(),
        "failed": q.filter(Notification.status == NotificationStatus.FAILED).count(),
        "skipped": q.filter(Notification.status == NotificationStatus.SKIPPED).count(),
        "pending": q.filter(Notification.status == NotificationStatus.PENDING).count(),
    }


@router.get("/notifications/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi import HTTPException
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(404, "Notification not found")
    return notif
