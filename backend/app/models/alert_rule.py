"""AlertRule model - Phase 8"""
import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.database import Base
from app.models.base import BaseModel


class AlertChannel(str, enum.Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"


class AlertTrigger(str, enum.Enum):
    FINDING_CREATED = "finding_created"
    SEVERITY_THRESHOLD = "severity_threshold"
    RISK_SCORE_THRESHOLD = "risk_score_threshold"
    SCAN_FAILED = "scan_failed"
    SCAN_COMPLETED = "scan_completed"


class AlertRule(Base, BaseModel):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    channel = Column(SAEnum(AlertChannel), nullable=False)
    trigger = Column(SAEnum(AlertTrigger), nullable=False)

    # Flexible conditions JSON
    # severity_threshold:   {"severity": ["critical", "high"]}
    # risk_score_threshold: {"min_risk_score": 7.5}
    # finding_created:      {"tool_name": "nmap", "severity": ["critical"]}
    conditions = Column(JSON, default=dict)

    # Channel config (stored as JSON)
    # email:   {"to": ["sec@co.com"]}
    # webhook: {"url": "https://...", "secret": "...", "method": "POST"}
    # slack:   {"webhook_url": "https://hooks.slack.com/..."}
    channel_config = Column(JSON, nullable=False)

    # Rate limiting: min between alerts of the same rule
    rate_limit_minutes = Column(Integer, default=60, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    project = relationship("Project", foreign_keys=[project_id])

    def __repr__(self):
        return f"<AlertRule(id={self.id}, name={self.name!r}, channel={self.channel}, trigger={self.trigger})>"
