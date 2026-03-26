"""Alert rules API endpoints - Phase 8"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.alert_rule import AlertRule, AlertChannel
from app.core.notifications.channels.email_channel import EmailChannel
from app.core.notifications.channels.webhook_channel import WebhookChannel
from app.core.notifications.channels.slack_channel import SlackChannel
from app.core.notifications.channels.base_channel import NotificationPayload
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleResponse, AlertRuleUpdate
from app.core.audit import create_audit_log

router = APIRouter()

CHANNEL_VALIDATORS = {
    AlertChannel.EMAIL: EmailChannel(),
    AlertChannel.WEBHOOK: WebhookChannel(),
    AlertChannel.SLACK: SlackChannel(),
}


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=201)
def create_alert_rule(
    payload: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validator = CHANNEL_VALIDATORS.get(payload.channel)
    if validator and not validator.validate_config(payload.channel_config):
        raise HTTPException(400, f"Invalid config for channel '{payload.channel}'")

    rule = AlertRule(
        user_id=current_user.id,
        project_id=payload.project_id,
        name=payload.name,
        channel=payload.channel,
        trigger=payload.trigger,
        conditions=payload.conditions or {},
        channel_config=payload.channel_config,
        rate_limit_minutes=payload.rate_limit_minutes if payload.rate_limit_minutes is not None else 60,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="alert_rule_created",
        resource="alert_rule",
        resource_id=rule.id,
        details={"channel": payload.channel, "trigger": payload.trigger},
    )
    return rule


@router.get("/alert-rules", response_model=List[AlertRuleResponse])
def list_alert_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(AlertRule).filter(AlertRule.user_id == current_user.id).all()


@router.get("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
def get_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id,
        AlertRule.user_id == current_user.id,
    ).first()
    if not rule:
        raise HTTPException(404, "Alert rule not found")
    return rule


@router.patch("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(
    rule_id: int,
    payload: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id,
        AlertRule.user_id == current_user.id,
    ).first()
    if not rule:
        raise HTTPException(404, "Alert rule not found")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/alert-rules/{rule_id}", status_code=204)
def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id,
        AlertRule.user_id == current_user.id,
    ).first()
    if not rule:
        raise HTTPException(404, "Alert rule not found")

    db.delete(rule)
    db.commit()
    return None


@router.post("/alert-rules/{rule_id}/test", status_code=200)
def test_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a test notification to verify channel config (does not persist notification)."""
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id,
        AlertRule.user_id == current_user.id,
    ).first()
    if not rule:
        raise HTTPException(404, "Alert rule not found")

    channel = CHANNEL_VALIDATORS.get(rule.channel)
    if not channel:
        raise HTTPException(400, f"Unsupported channel: {rule.channel}")

    test_payload = NotificationPayload(
        title="[TEST] Red Team Alert Rule Test",
        body=f"This is a test notification for rule: {rule.name}",
        severity="info",
    )
    success = channel.send(rule.channel_config, test_payload)
    return {"success": success, "channel": rule.channel}
