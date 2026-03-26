"""Alert evaluator - matches findings/scans against alert rules - Phase 8"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.alert_rule import AlertRule, AlertChannel, AlertTrigger
from app.models.finding import Finding
from app.models.task import Task, TaskStatusEnum
from app.core.notifications.channels.email_channel import EmailChannel
from app.core.notifications.channels.webhook_channel import WebhookChannel
from app.core.notifications.channels.slack_channel import SlackChannel
from app.core.notifications.channels.base_channel import NotificationPayload
from app.core.notifications.rate_limiter import is_rate_limited
from app.models.notification import Notification, NotificationStatus
from typing import List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

CHANNELS = {
    AlertChannel.EMAIL: EmailChannel(),
    AlertChannel.WEBHOOK: WebhookChannel(),
    AlertChannel.SLACK: SlackChannel(),
}


class AlertEvaluator:

    def __init__(self, db: Session):
        self.db = db

    def evaluate_finding(self, finding: Finding) -> None:
        """Evaluate all active rules for a newly created finding."""
        # Finding may not have a task (scan-based), use user from task or project owner
        user_id = None
        if finding.task_id:
            task = self.db.query(Task).filter(Task.id == finding.task_id).first()
            if task:
                user_id = task.user_id

        if user_id is None:
            logger.debug(f"Finding {finding.id} has no associated user_id, skipping alert evaluation")
            return

        rules = self._get_applicable_rules(user_id, finding.project_id)
        for rule in rules:
            if self._matches_finding(rule, finding):
                self._dispatch(rule, finding=finding)

    def evaluate_scan(self, task: Task) -> None:
        """Evaluate scan_completed / scan_failed rules for a task."""
        rules = self._get_applicable_rules(task.user_id, task.project_id)
        for rule in rules:
            if rule.trigger == AlertTrigger.SCAN_COMPLETED and task.status == TaskStatusEnum.completed:
                self._dispatch(rule, task=task)
            elif rule.trigger == AlertTrigger.SCAN_FAILED and task.status == TaskStatusEnum.failed:
                self._dispatch(rule, task=task)

    def _get_applicable_rules(self, user_id: int, project_id: Optional[int]) -> List[AlertRule]:
        """Get active rules for the user: global (project_id=None) + project-specific."""
        q = self.db.query(AlertRule).filter(
            AlertRule.user_id == user_id,
            AlertRule.is_active == True,
        )
        q = q.filter(
            or_(AlertRule.project_id == None, AlertRule.project_id == project_id)
        )
        return q.all()

    def _matches_finding(self, rule: AlertRule, finding: Finding) -> bool:
        """Check if a rule's conditions match the given finding."""
        conds = rule.conditions or {}

        if rule.trigger == AlertTrigger.SEVERITY_THRESHOLD:
            allowed = conds.get("severity", [])
            return finding.severity.value in allowed

        elif rule.trigger == AlertTrigger.RISK_SCORE_THRESHOLD:
            min_risk = conds.get("min_risk_score", 0.0)
            score = finding.risk_score or 0.0
            return score >= min_risk

        elif rule.trigger == AlertTrigger.FINDING_CREATED:
            severity_filter = conds.get("severity", [])
            tool_filter = conds.get("tool_name")
            ok_severity = (not severity_filter) or (finding.severity.value in severity_filter)
            ok_tool = (not tool_filter) or (finding.tool_name == tool_filter)
            return ok_severity and ok_tool

        return False

    def _dispatch(
        self,
        rule: AlertRule,
        finding: Optional[Finding] = None,
        task: Optional[Task] = None,
    ) -> None:
        """Rate-check then send via the appropriate channel."""
        if is_rate_limited(rule.id, rule.rate_limit_minutes):
            logger.info(f"Rule {rule.id} is rate limited, saving SKIPPED notification")
            self._save_notification(rule, NotificationStatus.SKIPPED, finding=finding, task=task)
            return

        payload = self._build_payload(rule, finding=finding, task=task)
        channel = CHANNELS.get(rule.channel)

        if not channel:
            logger.error(f"Unknown channel: {rule.channel}")
            return

        success = False
        error = None
        try:
            success = channel.send(rule.channel_config, payload)
        except Exception as e:
            error = str(e)
            logger.error(f"Channel send error rule={rule.id}: {e}")

        status = NotificationStatus.SENT if success else NotificationStatus.FAILED
        self._save_notification(rule, status, finding=finding, task=task, error=error)

    def _build_payload(
        self,
        rule: AlertRule,
        finding: Optional[Finding] = None,
        task: Optional[Task] = None,
    ) -> NotificationPayload:
        if finding:
            return NotificationPayload(
                title=f"[{finding.severity.value.upper()}] {finding.title}",
                body=(
                    f"Host: {finding.host or 'N/A'} | "
                    f"Tool: {finding.tool_name or 'N/A'} | "
                    f"Risk: {finding.risk_score or 0}/10\n"
                    f"{finding.description or ''}"
                ),
                severity=finding.severity.value,
                resource_id=finding.id,
                extra={"project_id": finding.project_id},
            )
        elif task:
            return NotificationPayload(
                title=f"Scan {task.status.value}: {task.name or task.tool_name}",
                body=(
                    f"Tool: {task.tool_name or 'N/A'} | "
                    f"Target: {task.target or 'N/A'}\n"
                    f"{task.error_message or ''}"
                ),
                severity="high" if task.status == TaskStatusEnum.failed else "info",
                resource_id=task.id,
            )
        # Fallback
        return NotificationPayload(title="Alert", body="Alert triggered", severity="info")

    def _save_notification(
        self,
        rule: AlertRule,
        status: NotificationStatus,
        finding: Optional[Finding] = None,
        task: Optional[Task] = None,
        error: Optional[str] = None,
    ) -> None:
        notif = Notification(
            alert_rule_id=rule.id,
            user_id=rule.user_id,
            channel=rule.channel.value,
            trigger=rule.trigger.value,
            status=status,
            event_type="finding" if finding else "scan",
            resource_id=finding.id if finding else (task.id if task else None),
            payload={
                "finding_title": finding.title if finding else None,
                "task_name": task.name if task else None,
            },
            error_message=error,
            sent_at=datetime.now(timezone.utc) if status == NotificationStatus.SENT else None,
        )
        self.db.add(notif)
        self.db.commit()
