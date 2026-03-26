"""Integration Hub models — Phase 16

Tables:
  integrations, notification_rules, integration_audit_logs,
  webhook_deliveries, integration_templates
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    JSON, DateTime, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.base import BaseModel


# ── Enums ──────────────────────────────────────────────────────────────────────

class IntegrationTypeEnum(str, enum.Enum):
    SLACK   = "slack"
    TEAMS   = "teams"
    DISCORD = "discord"
    GITHUB  = "github"
    GITLAB  = "gitlab"
    GITEA   = "gitea"
    JIRA    = "jira"
    WEBHOOK = "webhook"


class IntegrationStatusEnum(str, enum.Enum):
    ACTIVE       = "active"
    INACTIVE     = "inactive"
    ERROR        = "error"
    PENDING_AUTH = "pending_auth"


class TriggerTypeEnum(str, enum.Enum):
    FINDING_CREATED      = "finding_created"
    FINDING_RESOLVED     = "finding_resolved"
    CRITICAL_FINDING     = "critical_finding"
    RISK_SCORE_CHANGE    = "risk_score_change"
    COMPLIANCE_BREACH    = "compliance_breach"
    REMEDIATION_OVERDUE  = "remediation_overdue"
    SCAN_COMPLETED       = "scan_completed"
    REPORT_GENERATED     = "report_generated"


# ── Models ─────────────────────────────────────────────────────────────────────

class Integration(Base, BaseModel):
    """External service integration (Slack, GitHub, Jira, Webhook, etc.)."""
    __tablename__ = "integrations"

    id               = Column(Integer, primary_key=True, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    project          = relationship("Project")

    integration_type = Column(SAEnum(IntegrationTypeEnum), nullable=False, index=True)
    name             = Column(String(200), nullable=False)
    description      = Column(Text, nullable=True)

    # Authentication — token stored encrypted via EncryptionHandler
    auth_token          = Column(Text, nullable=True)          # Fernet-encrypted
    auth_webhook_url    = Column(String(500), nullable=True)   # Incoming-webhook URL
    auth_refresh_token  = Column(Text, nullable=True)
    auth_expires_at     = Column(DateTime(timezone=True), nullable=True)

    # Configuration per integration type
    config = Column(JSON, default=dict)  # {slack_channel, github_repo, …}

    # Status / health
    status              = Column(
        SAEnum(IntegrationStatusEnum),
        default=IntegrationStatusEnum.PENDING_AUTH,
        nullable=False,
    )
    last_tested_at      = Column(DateTime(timezone=True), nullable=True)
    last_tested_result  = Column(String(50), nullable=True)  # "success" | "failed"

    created_by          = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user     = relationship("User")

    notification_rules  = relationship("NotificationRule", back_populates="integrations",
                                       secondary="notification_rule_integration_link",
                                       viewonly=True)
    audit_logs          = relationship("IntegrationAuditLog", back_populates="integration",
                                       cascade="all, delete-orphan")
    webhook_deliveries  = relationship("WebhookDelivery", back_populates="integration",
                                       cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Integration(id={self.id}, type={self.integration_type!r}, name={self.name!r})>"


# Association table: many-to-many between NotificationRule and Integration
from sqlalchemy import Table
_rule_integration_link = Table(
    "notification_rule_integration_link",
    Base.metadata,
    Column("rule_id",        Integer, ForeignKey("notification_rules.id"),  primary_key=True),
    Column("integration_id", Integer, ForeignKey("integrations.id"), primary_key=True),
)


class NotificationRule(Base, BaseModel):
    """Rule that fires one or more integrations when a trigger condition is met."""
    __tablename__ = "notification_rules"

    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    project     = relationship("Project")

    name        = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Trigger
    trigger_type       = Column(SAEnum(TriggerTypeEnum), nullable=False, index=True)
    trigger_conditions = Column(JSON, default=dict)   # {severity:[CRITICAL], tool:[nmap]}

    # Actions — list of integration IDs (also reflected in M2M)
    integration_ids  = Column(JSON, default=list)     # [1, 2, 3]
    action_template  = Column(JSON, nullable=True)    # {message_format, fields}

    is_enabled   = Column(Boolean, default=True, nullable=False)
    created_by   = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user = relationship("User")

    integrations = relationship("Integration",
                                secondary="notification_rule_integration_link")

    def __repr__(self) -> str:
        return f"<NotificationRule(id={self.id}, trigger={self.trigger_type!r})>"


class IntegrationAuditLog(Base):
    """Full audit trail of every message / issue / event sent by an integration."""
    __tablename__ = "integration_audit_logs"

    id             = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)
    integration    = relationship("Integration", back_populates="audit_logs")

    action  = Column(String(50), nullable=False)   # "message_sent", "issue_created", "error"
    status  = Column(String(20), nullable=False)   # "success", "failed", "pending"

    payload_sent     = Column(JSON, nullable=True)
    payload_received = Column(JSON, nullable=True)

    error_message = Column(Text,    nullable=True)
    error_code    = Column(String(50), nullable=True)

    # Trigger source (optional back-links)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=True)
    report_id  = Column(Integer, ForeignKey("reports.id"),  nullable=True)

    timestamp    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    external_id  = Column(String(200), nullable=True)   # Issue #123, Slack ts, …
    external_url = Column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<IntegrationAuditLog(id={self.id}, action={self.action!r}, status={self.status!r})>"


class WebhookDelivery(Base):
    """Tracks each delivery attempt for generic webhook integrations (with retry)."""
    __tablename__ = "webhook_deliveries"

    id             = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)
    integration    = relationship("Integration", back_populates="webhook_deliveries")

    event_type     = Column(String(50), nullable=False)   # "finding.created", etc.

    attempt_number = Column(Integer, default=1,   nullable=False)
    status_code    = Column(Integer, nullable=True)
    response_body  = Column(Text,    nullable=True)

    next_retry_at  = Column(DateTime(timezone=True), nullable=True)
    max_retries    = Column(Integer, default=3, nullable=False)

    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<WebhookDelivery(id={self.id}, event={self.event_type!r}, attempt={self.attempt_number})>"


class IntegrationTemplate(Base):
    """Reusable Jinja2 message templates for each integration type."""
    __tablename__ = "integration_templates"

    id               = Column(Integer, primary_key=True, index=True)
    integration_type = Column(SAEnum(IntegrationTypeEnum), nullable=False, index=True)
    name             = Column(String(200), nullable=False)

    template_text      = Column(Text, nullable=False)     # Jinja2 template string
    template_variables = Column(JSON, default=list)       # [{name, type, required}]

    is_default = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<IntegrationTemplate(id={self.id}, type={self.integration_type!r}, name={self.name!r})>"
