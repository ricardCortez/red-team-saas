"""Notification Rule Engine — Phase 16

Evaluates NotificationRules on events (finding created, risk-score change, …)
and dispatches messages/issues to the configured integrations.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.integration import Integration, IntegrationAuditLog, NotificationRule
from app.services.integrations import INTEGRATION_CLASSES

logger = logging.getLogger(__name__)


class NotificationEngine:
    """Evaluate notification rules and dispatch to external integrations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Public API ─────────────────────────────────────────────────────────────

    async def notify_on_finding(self, finding, project_id: int) -> List[Dict[str, Any]]:
        """Process FINDING_CREATED rules for the given finding."""
        rules = self._active_rules(project_id, "finding_created")
        results: List[Dict[str, Any]] = []
        for rule in rules:
            if not self._match_conditions(finding, rule.trigger_conditions):
                continue
            for integration_id in (rule.integration_ids or []):
                result = await self._execute_integration(
                    integration_id, rule, finding, context="finding"
                )
                results.append(result)
        return results

    async def notify_on_critical_finding(self, finding, project_id: int) -> List[Dict[str, Any]]:
        """Process CRITICAL_FINDING rules (severity == CRITICAL)."""
        rules = self._active_rules(project_id, "critical_finding")
        results: List[Dict[str, Any]] = []
        for rule in rules:
            if not self._match_conditions(finding, rule.trigger_conditions):
                continue
            for integration_id in (rule.integration_ids or []):
                result = await self._execute_integration(
                    integration_id, rule, finding, context="finding"
                )
                results.append(result)
        return results

    async def notify_on_risk_score(
        self,
        project_id: int,
        risk_score: int,
        previous_score: int,
    ) -> List[Dict[str, Any]]:
        """Process RISK_SCORE_CHANGE rules when the score shifts beyond a threshold."""
        rules = self._active_rules(project_id, "risk_score_change")
        results: List[Dict[str, Any]] = []
        for rule in rules:
            threshold = int((rule.trigger_conditions or {}).get("threshold", 10))
            if abs(risk_score - previous_score) < threshold:
                continue
            data = {
                "risk_score":     risk_score,
                "previous_score": previous_score,
                "delta":          risk_score - previous_score,
            }
            for integration_id in (rule.integration_ids or []):
                result = await self._execute_integration(
                    integration_id, rule, data, context="risk_score"
                )
                results.append(result)
        return results

    async def notify_on_scan_completed(
        self,
        project_id: int,
        scan_id: int,
        finding_count: int,
    ) -> List[Dict[str, Any]]:
        """Process SCAN_COMPLETED rules."""
        rules = self._active_rules(project_id, "scan_completed")
        data = {"scan_id": scan_id, "finding_count": finding_count}
        results: List[Dict[str, Any]] = []
        for rule in rules:
            for integration_id in (rule.integration_ids or []):
                result = await self._execute_integration(
                    integration_id, rule, data, context="scan"
                )
                results.append(result)
        return results

    async def notify_on_report_generated(
        self,
        project_id: int,
        report_id: int,
        report_url: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Process REPORT_GENERATED rules."""
        rules = self._active_rules(project_id, "report_generated")
        data = {"report_id": report_id, "report_url": report_url or ""}
        results: List[Dict[str, Any]] = []
        for rule in rules:
            for integration_id in (rule.integration_ids or []):
                result = await self._execute_integration(
                    integration_id, rule, data, context="report"
                )
                results.append(result)
        return results

    # ── Condition Matching ─────────────────────────────────────────────────────

    def _match_conditions(self, finding, conditions: Dict[str, Any]) -> bool:
        """Return True if the finding satisfies all rule conditions."""
        if not conditions:
            return True

        if "severity" in conditions:
            finding_sev = getattr(finding, "severity", None)
            if hasattr(finding_sev, "value"):
                finding_sev = finding_sev.value
            if finding_sev not in conditions["severity"]:
                return False

        if "tool" in conditions:
            if getattr(finding, "tool", None) not in conditions["tool"]:
                return False

        if conditions.get("cve_only"):
            if not getattr(finding, "cve_id", None):
                return False

        return True

    # ── Execution ──────────────────────────────────────────────────────────────

    async def _execute_integration(
        self,
        integration_id: int,
        rule: NotificationRule,
        data: Any,
        context: str = "generic",
    ) -> Dict[str, Any]:
        integration = self.db.query(Integration).filter(
            Integration.id == integration_id
        ).first()

        if not integration:
            return {"success": False, "error": f"Integration {integration_id} not found"}

        try:
            int_type = (
                integration.integration_type.value
                if hasattr(integration.integration_type, "value")
                else integration.integration_type
            )
            int_class = INTEGRATION_CLASSES.get(int_type.lower())
            if not int_class:
                raise ValueError(f"Unknown integration type: {int_type}")

            token = self._decrypt_token(integration.auth_token)
            instance = int_class(token, integration.config or {})

            if context == "finding":
                result = await instance.create_issue(
                    title=getattr(data, "title", str(data)),
                    description=self._format_finding_message(data, rule.action_template),
                    severity=self._get_severity(data),
                    cve_id=getattr(data, "cve_id", None),
                )
            else:
                message = self._format_message(data, rule.action_template, context)
                result = await instance.send_message(message)

            self._write_audit_log(
                integration_id=integration_id,
                action="message_sent" if context != "finding" else "issue_created",
                status="success" if result.get("success") else "failed",
                payload_sent={"context": context, "rule_id": rule.id},
                payload_received=result,
                external_id=result.get("external_id"),
                external_url=result.get("external_url"),
                finding_id=getattr(data, "id", None) if context == "finding" else None,
            )
            return result

        except Exception as exc:
            logger.exception("Integration %d execution failed: %s", integration_id, exc)
            self._write_audit_log(
                integration_id=integration_id,
                action="message_sent",
                status="failed",
                payload_sent={"context": context},
                error_message=str(exc),
            )
            return {"success": False, "error": str(exc)}

    # ── Formatting ─────────────────────────────────────────────────────────────

    def _format_finding_message(self, finding, template: Optional[Dict] = None) -> str:
        if not template or not template.get("message_format"):
            desc = getattr(finding, "technical_description", None) or getattr(finding, "description", "")
            return str(desc)
        try:
            from jinja2 import Template
            tmpl = Template(template["message_format"])
            return tmpl.render(
                title=getattr(finding, "title", ""),
                severity=self._get_severity(finding),
                cve_id=getattr(finding, "cve_id", "N/A"),
                description=getattr(finding, "technical_description", ""),
                remediation=getattr(finding, "remediation", ""),
                tool=getattr(finding, "tool", ""),
            )
        except Exception:
            return getattr(finding, "technical_description", str(finding))

    def _format_message(self, data: Any, template: Optional[Dict], context: str) -> str:
        if not template or not template.get("message_format"):
            if isinstance(data, dict):
                return "\n".join(f"**{k}**: {v}" for k, v in data.items())
            return str(data)
        try:
            from jinja2 import Template
            tmpl = Template(template["message_format"])
            payload = data if isinstance(data, dict) else {"data": str(data)}
            return tmpl.render(**payload)
        except Exception:
            return str(data)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _active_rules(self, project_id: int, trigger_type: str) -> List[NotificationRule]:
        return (
            self.db.query(NotificationRule)
            .filter(
                NotificationRule.project_id == project_id,
                NotificationRule.trigger_type == trigger_type,
                NotificationRule.is_enabled.is_(True),
            )
            .all()
        )

    def _get_severity(self, finding) -> str:
        sev = getattr(finding, "severity", None)
        if sev is None:
            return "UNKNOWN"
        if hasattr(sev, "value"):
            return sev.value.upper()
        return str(sev).upper()

    def _decrypt_token(self, token: Optional[str]) -> str:
        if not token:
            return ""
        try:
            from app.core.security import EncryptionHandler
            return EncryptionHandler.decrypt(token)
        except Exception:
            return token or ""

    def _write_audit_log(
        self,
        integration_id: int,
        action: str,
        status: str,
        payload_sent: Optional[Dict] = None,
        payload_received: Optional[Dict] = None,
        error_message: Optional[str] = None,
        external_id: Optional[str] = None,
        external_url: Optional[str] = None,
        finding_id: Optional[int] = None,
    ) -> None:
        try:
            log = IntegrationAuditLog(
                integration_id=integration_id,
                action=action,
                status=status,
                payload_sent=payload_sent,
                payload_received=payload_received,
                error_message=error_message,
                external_id=external_id,
                external_url=external_url,
                finding_id=finding_id,
            )
            self.db.add(log)
            self.db.commit()
        except Exception:
            self.db.rollback()
