"""Integration CRUD operations — Phase 16"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.integration import (
    Integration,
    IntegrationAuditLog,
    IntegrationStatusEnum,
    IntegrationTemplate,
    IntegrationTypeEnum,
    NotificationRule,
    TriggerTypeEnum,
    WebhookDelivery,
)

logger = logging.getLogger(__name__)


class IntegrationCRUD:

    # ── Integrations ──────────────────────────────────────────────────────────

    @staticmethod
    def create_integration(db: Session, data: Dict[str, Any]) -> Integration:
        """Create an integration, encrypting the auth_token if present."""
        if "auth_token" in data and data["auth_token"]:
            from app.core.security import EncryptionHandler
            data = dict(data)
            data["auth_token"] = EncryptionHandler.encrypt(data["auth_token"])

        integration = Integration(**data)
        db.add(integration)
        db.commit()
        db.refresh(integration)
        return integration

    @staticmethod
    def get_integration(db: Session, integration_id: int) -> Optional[Integration]:
        return db.query(Integration).filter(Integration.id == integration_id).first()

    @staticmethod
    def list_integrations(
        db: Session,
        project_id: int,
        integration_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Integration]:
        query = db.query(Integration).filter(Integration.project_id == project_id)
        if integration_type:
            query = query.filter(Integration.integration_type == integration_type)
        if status:
            query = query.filter(Integration.status == status)
        return query.order_by(Integration.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_integration(
        db: Session,
        integration_id: int,
        updates: Dict[str, Any],
    ) -> Optional[Integration]:
        integration = db.query(Integration).filter(Integration.id == integration_id).first()
        if not integration:
            return None

        if "auth_token" in updates and updates["auth_token"]:
            from app.core.security import EncryptionHandler
            updates = dict(updates)
            updates["auth_token"] = EncryptionHandler.encrypt(updates["auth_token"])

        for key, value in updates.items():
            if hasattr(integration, key):
                setattr(integration, key, value)

        db.commit()
        db.refresh(integration)
        return integration

    @staticmethod
    def update_integration_status(
        db: Session,
        integration_id: int,
        status: str,
        test_result: Optional[str] = None,
    ) -> Optional[Integration]:
        integration = db.query(Integration).filter(Integration.id == integration_id).first()
        if not integration:
            return None

        integration.status = status
        if test_result is not None:
            integration.last_tested_result = test_result
            integration.last_tested_at = datetime.utcnow()

        db.commit()
        db.refresh(integration)
        return integration

    @staticmethod
    def delete_integration(db: Session, integration_id: int) -> bool:
        integration = db.query(Integration).filter(Integration.id == integration_id).first()
        if not integration:
            return False
        db.delete(integration)
        db.commit()
        return True

    # ── Notification Rules ────────────────────────────────────────────────────

    @staticmethod
    def create_notification_rule(db: Session, data: Dict[str, Any]) -> NotificationRule:
        rule = NotificationRule(**data)
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def get_notification_rule(db: Session, rule_id: int) -> Optional[NotificationRule]:
        return db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()

    @staticmethod
    def get_notification_rules(
        db: Session,
        project_id: int,
        trigger_type: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[NotificationRule]:
        query = db.query(NotificationRule).filter(NotificationRule.project_id == project_id)
        if trigger_type:
            query = query.filter(NotificationRule.trigger_type == trigger_type)
        if enabled_only:
            query = query.filter(NotificationRule.is_enabled.is_(True))
        return query.order_by(NotificationRule.id).all()

    @staticmethod
    def update_notification_rule(
        db: Session,
        rule_id: int,
        updates: Dict[str, Any],
    ) -> Optional[NotificationRule]:
        rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
        if not rule:
            return None
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def delete_notification_rule(db: Session, rule_id: int) -> bool:
        rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
        if not rule:
            return False
        db.delete(rule)
        db.commit()
        return True

    # ── Audit Logs ────────────────────────────────────────────────────────────

    @staticmethod
    def log_integration_action(
        db: Session,
        integration_id: int,
        action: str,
        status: str,
        payload_sent: Optional[Dict] = None,
        payload_received: Optional[Dict] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        external_id: Optional[str] = None,
        external_url: Optional[str] = None,
        finding_id: Optional[int] = None,
        report_id: Optional[int] = None,
    ) -> IntegrationAuditLog:
        log = IntegrationAuditLog(
            integration_id=integration_id,
            action=action,
            status=status,
            payload_sent=payload_sent,
            payload_received=payload_received,
            error_message=error_message,
            error_code=error_code,
            external_id=external_id,
            external_url=external_url,
            finding_id=finding_id,
            report_id=report_id,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def get_audit_logs(
        db: Session,
        integration_id: Optional[int] = None,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[IntegrationAuditLog]:
        query = db.query(IntegrationAuditLog)

        if integration_id:
            query = query.filter(IntegrationAuditLog.integration_id == integration_id)
        elif project_id:
            # Join through Integration to filter by project
            query = (
                query.join(Integration, IntegrationAuditLog.integration_id == Integration.id)
                .filter(Integration.project_id == project_id)
            )

        if status:
            query = query.filter(IntegrationAuditLog.status == status)

        return (
            query.order_by(IntegrationAuditLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ── Webhook Deliveries ────────────────────────────────────────────────────

    @staticmethod
    def create_webhook_delivery(db: Session, data: Dict[str, Any]) -> WebhookDelivery:
        delivery = WebhookDelivery(**data)
        db.add(delivery)
        db.commit()
        db.refresh(delivery)
        return delivery

    @staticmethod
    def get_pending_retries(db: Session) -> List[WebhookDelivery]:
        """Return webhook deliveries that are due for retry."""
        return (
            db.query(WebhookDelivery)
            .filter(
                WebhookDelivery.next_retry_at <= func.now(),
                WebhookDelivery.attempt_number < WebhookDelivery.max_retries,
                WebhookDelivery.delivered_at.is_(None),
            )
            .all()
        )

    @staticmethod
    def mark_delivery_success(db: Session, delivery_id: int, status_code: int, response_body: str) -> Optional[WebhookDelivery]:
        delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
        if not delivery:
            return None
        delivery.status_code = status_code
        delivery.response_body = response_body[:4000] if response_body else None
        delivery.delivered_at = datetime.utcnow()
        db.commit()
        db.refresh(delivery)
        return delivery

    # ── Templates ─────────────────────────────────────────────────────────────

    @staticmethod
    def create_template(db: Session, data: Dict[str, Any]) -> IntegrationTemplate:
        template = IntegrationTemplate(**data)
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def list_templates(
        db: Session,
        integration_type: Optional[str] = None,
    ) -> List[IntegrationTemplate]:
        query = db.query(IntegrationTemplate)
        if integration_type:
            query = query.filter(IntegrationTemplate.integration_type == integration_type)
        return query.order_by(IntegrationTemplate.integration_type, IntegrationTemplate.name).all()

    @staticmethod
    def get_default_template(
        db: Session,
        integration_type: str,
    ) -> Optional[IntegrationTemplate]:
        return (
            db.query(IntegrationTemplate)
            .filter(
                IntegrationTemplate.integration_type == integration_type,
                IntegrationTemplate.is_default.is_(True),
            )
            .first()
        )

    # ── Stats ─────────────────────────────────────────────────────────────────

    @staticmethod
    def integration_stats(db: Session, project_id: int) -> Dict[str, Any]:
        """Return a summary of integration health for a project."""
        integrations = (
            db.query(Integration).filter(Integration.project_id == project_id).all()
        )
        stats: Dict[str, Any] = {
            "total":        len(integrations),
            "active":       sum(1 for i in integrations if i.status == IntegrationStatusEnum.ACTIVE),
            "error":        sum(1 for i in integrations if i.status == IntegrationStatusEnum.ERROR),
            "pending_auth": sum(1 for i in integrations if i.status == IntegrationStatusEnum.PENDING_AUTH),
            "by_type":      {},
        }
        for i in integrations:
            t = i.integration_type.value if hasattr(i.integration_type, "value") else str(i.integration_type)
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
        return stats
