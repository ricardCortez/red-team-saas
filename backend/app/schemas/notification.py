"""Schemas for Notification - Phase 8"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.notification import NotificationStatus


class NotificationResponse(BaseModel):
    id: int
    alert_rule_id: Optional[int] = None
    channel: str
    trigger: str
    status: NotificationStatus
    event_type: Optional[str] = None
    resource_id: Optional[int] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
