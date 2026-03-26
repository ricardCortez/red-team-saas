"""Notification history model - Phase 8"""
import enum
from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.database import Base
from app.models.base import BaseModel


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"  # rate limited


class Notification(Base, BaseModel):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    alert_rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    channel = Column(String(50), nullable=False)
    trigger = Column(String(100), nullable=False)
    status = Column(SAEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)

    # Context of the event that triggered the alert
    event_type = Column(String(100), nullable=True)   # "finding", "scan"
    resource_id = Column(Integer, nullable=True)       # finding_id or task_id
    payload = Column(JSON, default=dict)               # data sent to the channel

    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    alert_rule = relationship("AlertRule", foreign_keys=[alert_rule_id])
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<Notification(id={self.id}, channel={self.channel}, status={self.status})>"
