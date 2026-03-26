"""Unit tests for Integration Hub — Phase 16"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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
from app.crud.integration import IntegrationCRUD
from app.schemas.integration import (
    IntegrationCreate,
    IntegrationUpdate,
    NotificationRuleCreate,
    NotificationRuleUpdate,
)


# ─────────────────────────── helpers ──────────────────────────────────────────

def _make_user_and_project(db):
    from app.models.user import User
    from app.models.project import Project, ProjectStatus, ProjectScope
    from app.core.security import PasswordHandler

    user = User(
        email="integ_test@example.com",
        username="integtester",
        hashed_password=PasswordHandler.hash_password("Pass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()

    project = Project(
        name="Integration Test Project",
        status=ProjectStatus.active,
        scope=ProjectScope.external,
        owner_id=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return user, project


def _make_integration(db, project_id: int, user_id: int, int_type: str = "slack") -> Integration:
    return IntegrationCRUD.create_integration(
        db,
        {
            "project_id":       project_id,
            "integration_type": int_type,
            "name":             f"Test {int_type.title()}",
            "auth_token":       "raw_test_token",
            "config":           {"default_channel": "#findings"},
            "created_by":       user_id,
        },
    )


# ═════════════════════════ Model Tests ═════════════════════════════════════════

class TestIntegrationModel:

    def test_create_integration(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)
        assert integ.id is not None
        assert integ.status == IntegrationStatusEnum.PENDING_AUTH

    def test_integration_type_enum_values(self):
        assert IntegrationTypeEnum.SLACK   == "slack"
        assert IntegrationTypeEnum.GITHUB  == "github"
        assert IntegrationTypeEnum.JIRA    == "jira"
        assert IntegrationTypeEnum.WEBHOOK == "webhook"
        assert IntegrationTypeEnum.TEAMS   == "teams"
        assert IntegrationTypeEnum.DISCORD == "discord"

    def test_integration_status_enum_values(self):
        assert IntegrationStatusEnum.ACTIVE       == "active"
        assert IntegrationStatusEnum.INACTIVE     == "inactive"
        assert IntegrationStatusEnum.ERROR        == "error"
        assert IntegrationStatusEnum.PENDING_AUTH == "pending_auth"

    def test_trigger_type_enum_values(self):
        assert TriggerTypeEnum.FINDING_CREATED   == "finding_created"
        assert TriggerTypeEnum.CRITICAL_FINDING  == "critical_finding"
        assert TriggerTypeEnum.RISK_SCORE_CHANGE == "risk_score_change"
        assert TriggerTypeEnum.SCAN_COMPLETED    == "scan_completed"
        assert TriggerTypeEnum.REPORT_GENERATED  == "report_generated"

    def test_integration_repr(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)
        assert "Integration" in repr(integ)
        assert "slack" in repr(integ)

    def test_integration_token_encrypted(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)
        # Stored value should not equal the raw token
        assert integ.auth_token != "raw_test_token"

    def test_integration_config_json(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)
        assert isinstance(integ.config, dict)
        assert integ.config.get("default_channel") == "#findings"


class TestNotificationRuleModel:

    def test_create_rule(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)

        rule = IntegrationCRUD.create_notification_rule(
            db_session,
            {
                "project_id":         project.id,
                "name":               "Critical Alert",
                "trigger_type":       "finding_created",
                "trigger_conditions": {"severity": ["CRITICAL"]},
                "integration_ids":    [integ.id],
                "created_by":         user.id,
            },
        )
        assert rule.id is not None
        assert rule.is_enabled is True
        assert integ.id in rule.integration_ids

    def test_rule_repr(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)
        rule = IntegrationCRUD.create_notification_rule(
            db_session,
            {
                "project_id":         project.id,
                "name":               "Repr Test",
                "trigger_type":       "scan_completed",
                "trigger_conditions": {},
                "integration_ids":    [integ.id],
                "created_by":         user.id,
            },
        )
        assert "NotificationRule" in repr(rule)


class TestIntegrationAuditLogModel:

    def test_create_audit_log(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)

        log = IntegrationCRUD.log_integration_action(
            db_session,
            integration_id=integ.id,
            action="message_sent",
            status="success",
            external_id="ts_12345",
            external_url="https://slack.com/…",
        )
        assert log.id is not None
        assert log.status == "success"
        assert log.external_id == "ts_12345"

    def test_audit_log_repr(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)
        log = IntegrationCRUD.log_integration_action(
            db_session, integ.id, "error", "failed", error_message="timeout"
        )
        assert "IntegrationAuditLog" in repr(log)

    def test_audit_log_with_error(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)
        log = IntegrationCRUD.log_integration_action(
            db_session,
            integ.id,
            "message_sent",
            "failed",
            error_message="Connection refused",
            error_code="503",
        )
        assert log.error_message == "Connection refused"
        assert log.error_code == "503"


class TestWebhookDeliveryModel:

    def test_create_delivery(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id, "webhook")

        delivery = IntegrationCRUD.create_webhook_delivery(
            db_session,
            {
                "integration_id": integ.id,
                "event_type":     "finding.created",
                "max_retries":    3,
            },
        )
        assert delivery.id is not None
        assert delivery.attempt_number == 1
        assert "WebhookDelivery" in repr(delivery)


class TestIntegrationTemplateModel:

    def test_create_template(self, db_session):
        tpl = IntegrationCRUD.create_template(
            db_session,
            {
                "integration_type":   "slack",
                "name":               "Finding Alert",
                "template_text":      ":alert: *{{ title }}* — {{ severity }}",
                "template_variables": [{"name": "title", "type": "str", "required": True}],
                "is_default":         True,
            },
        )
        assert tpl.id is not None
        assert "IntegrationTemplate" in repr(tpl)

    def test_get_default_template(self, db_session):
        IntegrationCRUD.create_template(
            db_session,
            {
                "integration_type": "github",
                "name":             "Default GitHub",
                "template_text":    "## {{ title }}",
                "is_default":       True,
            },
        )
        tpl = IntegrationCRUD.get_default_template(db_session, "github")
        assert tpl is not None
        assert tpl.is_default is True


# ═════════════════════════ CRUD Tests ══════════════════════════════════════════

class TestIntegrationCRUD:

    def test_list_integrations(self, db_session):
        user, project = _make_user_and_project(db_session)
        _make_integration(db_session, project.id, user.id, "slack")
        _make_integration(db_session, project.id, user.id, "github")

        results = IntegrationCRUD.list_integrations(db_session, project.id)
        assert len(results) >= 2

    def test_list_integrations_filter_by_type(self, db_session):
        user, project = _make_user_and_project(db_session)
        _make_integration(db_session, project.id, user.id, "slack")
        _make_integration(db_session, project.id, user.id, "jira")

        slack_only = IntegrationCRUD.list_integrations(db_session, project.id, "slack")
        assert all(
            (i.integration_type.value if hasattr(i.integration_type, "value") else i.integration_type) == "slack"
            for i in slack_only
        )

    def test_update_integration_status(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)

        updated = IntegrationCRUD.update_integration_status(
            db_session, integ.id, "active", "success"
        )
        assert updated is not None
        assert updated.last_tested_result == "success"

    def test_update_integration_fields(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)

        updated = IntegrationCRUD.update_integration(
            db_session, integ.id, {"name": "Updated Name"}
        )
        assert updated.name == "Updated Name"

    def test_delete_integration(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)
        integ_id = integ.id

        result = IntegrationCRUD.delete_integration(db_session, integ_id)
        assert result is True
        assert IntegrationCRUD.get_integration(db_session, integ_id) is None

    def test_delete_nonexistent(self, db_session):
        assert IntegrationCRUD.delete_integration(db_session, 999999) is False

    def test_get_notification_rules_enabled_only(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)

        IntegrationCRUD.create_notification_rule(
            db_session,
            {
                "project_id": project.id, "name": "Enabled Rule",
                "trigger_type": "finding_created", "trigger_conditions": {},
                "integration_ids": [integ.id], "is_enabled": True, "created_by": user.id,
            },
        )
        IntegrationCRUD.create_notification_rule(
            db_session,
            {
                "project_id": project.id, "name": "Disabled Rule",
                "trigger_type": "finding_created", "trigger_conditions": {},
                "integration_ids": [integ.id], "is_enabled": False, "created_by": user.id,
            },
        )

        all_rules = IntegrationCRUD.get_notification_rules(db_session, project.id)
        enabled   = IntegrationCRUD.get_notification_rules(db_session, project.id, enabled_only=True)

        assert len(all_rules) >= 2
        assert len(enabled) < len(all_rules)

    def test_update_notification_rule(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)

        rule = IntegrationCRUD.create_notification_rule(
            db_session,
            {
                "project_id": project.id, "name": "Old Name",
                "trigger_type": "scan_completed", "trigger_conditions": {},
                "integration_ids": [integ.id], "created_by": user.id,
            },
        )

        updated = IntegrationCRUD.update_notification_rule(
            db_session, rule.id, {"name": "New Name", "is_enabled": False}
        )
        assert updated.name == "New Name"
        assert updated.is_enabled is False

    def test_delete_notification_rule(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)

        rule = IntegrationCRUD.create_notification_rule(
            db_session,
            {
                "project_id": project.id, "name": "To Delete",
                "trigger_type": "report_generated", "trigger_conditions": {},
                "integration_ids": [integ.id], "created_by": user.id,
            },
        )
        rule_id = rule.id
        result = IntegrationCRUD.delete_notification_rule(db_session, rule_id)
        assert result is True
        assert IntegrationCRUD.get_notification_rule(db_session, rule_id) is None

    def test_integration_stats(self, db_session):
        user, project = _make_user_and_project(db_session)
        _make_integration(db_session, project.id, user.id, "slack")
        _make_integration(db_session, project.id, user.id, "github")

        s = IntegrationCRUD.integration_stats(db_session, project.id)
        assert s["total"] >= 2
        assert "by_type" in s
        assert "slack" in s["by_type"]

    def test_get_audit_logs_by_project(self, db_session):
        user, project = _make_user_and_project(db_session)
        integ = _make_integration(db_session, project.id, user.id)
        IntegrationCRUD.log_integration_action(
            db_session, integ.id, "message_sent", "success"
        )

        logs = IntegrationCRUD.get_audit_logs(db_session, project_id=project.id)
        assert len(logs) >= 1

    def test_list_templates_by_type(self, db_session):
        IntegrationCRUD.create_template(
            db_session,
            {"integration_type": "slack", "name": "T1", "template_text": "t1", "is_default": False},
        )
        templates = IntegrationCRUD.list_templates(db_session, "slack")
        assert any(t.integration_type.value == "slack" for t in templates)


# ═════════════════════════ Service Tests ═══════════════════════════════════════

class TestNotificationEngine:

    def test_match_conditions_severity(self):
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(None)

        finding = MagicMock()
        finding.severity = MagicMock(value="CRITICAL")
        finding.tool = "nmap"
        finding.cve_id = "CVE-2021-0001"

        assert engine._match_conditions(finding, {"severity": ["CRITICAL", "HIGH"]}) is True
        assert engine._match_conditions(finding, {"severity": ["LOW"]}) is False

    def test_match_conditions_tool(self):
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(None)
        finding = MagicMock()
        finding.severity = MagicMock(value="HIGH")
        finding.tool = "nmap"
        finding.cve_id = None

        assert engine._match_conditions(finding, {"tool": ["nmap"]}) is True
        assert engine._match_conditions(finding, {"tool": ["masscan"]}) is False

    def test_match_conditions_cve_only(self):
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(None)

        finding_with_cve    = MagicMock(); finding_with_cve.cve_id = "CVE-2021-0001"
        finding_without_cve = MagicMock(); finding_without_cve.cve_id = None

        assert engine._match_conditions(finding_with_cve,    {"cve_only": True}) is True
        assert engine._match_conditions(finding_without_cve, {"cve_only": True}) is False

    def test_match_conditions_empty(self):
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(None)
        finding = MagicMock()
        assert engine._match_conditions(finding, {}) is True
        assert engine._match_conditions(finding, None) is True

    def test_format_finding_message_no_template(self):
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(None)
        finding = MagicMock()
        finding.technical_description = "SQL injection in login form"

        msg = engine._format_finding_message(finding, None)
        assert "SQL injection" in msg

    def test_format_finding_message_with_template(self):
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(None)
        finding = MagicMock()
        finding.title              = "SQL Injection"
        finding.severity           = MagicMock(value="CRITICAL")
        finding.cve_id             = "CVE-2021-0001"
        finding.technical_description = "Details here"
        finding.remediation        = "Fix it"
        finding.tool               = "sqlmap"

        template = {"message_format": "{{ title }} — {{ severity }}"}
        msg = engine._format_finding_message(finding, template)
        assert "SQL Injection" in msg
        assert "CRITICAL" in msg

    def test_get_severity_string(self):
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(None)

        f1 = MagicMock(); f1.severity = MagicMock(value="high")
        f2 = MagicMock(); f2.severity = "CRITICAL"
        f3 = MagicMock(); f3.severity = None

        assert engine._get_severity(f1) == "HIGH"
        assert engine._get_severity(f2) == "CRITICAL"
        assert engine._get_severity(f3) == "UNKNOWN"

    def test_format_message_dict(self):
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(None)
        msg = engine._format_message({"risk_score": 85, "previous_score": 60}, None, "risk_score")
        assert "risk_score" in msg
        assert "85" in msg


# ═════════════════════════ Schema Tests ════════════════════════════════════════

class TestIntegrationSchemas:

    def test_integration_create_valid(self):
        schema = IntegrationCreate(
            integration_type="slack",
            name="My Slack",
            auth_token="xoxb-token",
            config={"default_channel": "#sec"},
        )
        assert schema.integration_type == "slack"

    def test_integration_create_invalid_type(self):
        with pytest.raises(Exception):
            IntegrationCreate(
                integration_type="unknown_type",
                name="Bad",
                auth_token="tok",
            )

    def test_notification_rule_create_valid(self):
        schema = NotificationRuleCreate(
            name="Critical Alerts",
            trigger_type="finding_created",
            trigger_conditions={"severity": ["CRITICAL"]},
            integration_ids=[1, 2],
        )
        assert schema.trigger_type == "finding_created"

    def test_notification_rule_create_invalid_trigger(self):
        with pytest.raises(Exception):
            NotificationRuleCreate(
                name="Bad Rule",
                trigger_type="not_a_trigger",
                trigger_conditions={},
                integration_ids=[1],
            )


# ═════════════════════════ Service Unit Tests ══════════════════════════════════

class TestSlackIntegration:

    def test_test_connection_success(self):
        import asyncio
        from app.services.integrations.slack_integration import SlackIntegration

        slack = SlackIntegration("xoxb-test", {"default_channel": "#findings"})

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value={"ok": True, "team": "TestTeam"})

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post.return_value.__aexit__  = AsyncMock(return_value=False)
            result = asyncio.run(slack.test_connection())

        assert result is True

    def test_test_connection_failure(self):
        import asyncio
        from app.services.integrations.slack_integration import SlackIntegration

        slack = SlackIntegration("bad-token", {})

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value={"ok": False, "error": "invalid_auth"})

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post.return_value.__aexit__  = AsyncMock(return_value=False)
            result = asyncio.run(slack.test_connection())

        assert result is False

    def test_send_message(self):
        import asyncio
        from app.services.integrations.slack_integration import SlackIntegration

        slack = SlackIntegration("xoxb-test", {"default_channel": "#findings"})

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value={"ok": True, "ts": "1234567890.000100"})

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post.return_value.__aexit__  = AsyncMock(return_value=False)
            result = asyncio.run(slack.send_message("Test message", severity="CRITICAL"))

        assert result["success"] is True
        assert result["external_id"] == "1234567890.000100"

    def test_create_issue(self):
        import asyncio
        from app.services.integrations.slack_integration import SlackIntegration

        slack = SlackIntegration("xoxb-test", {})
        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value={"ok": True, "ts": "111.222"})

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post.return_value.__aexit__  = AsyncMock(return_value=False)
            result = asyncio.run(slack.create_issue(
                "SQL Injection", "Description", severity="HIGH", cve_id="CVE-2021-0001"
            ))

        assert result["success"] is True

    def test_get_auth_url(self):
        import asyncio
        from app.services.integrations.slack_integration import SlackIntegration

        slack = SlackIntegration("", {"client_id": "MYID"})
        url = asyncio.run(slack.get_auth_url())
        assert "MYID" in url
        assert "slack.com" in url


class TestGitHubIntegration:

    def test_create_issue_success(self):
        import asyncio
        from app.services.integrations.github_integration import GitHubIntegration

        gh = GitHubIntegration("ghp_test", {"repository": "org/repo"})

        mock_resp = AsyncMock()
        mock_resp.status = 201
        mock_resp.json   = AsyncMock(return_value={"number": 42, "html_url": "https://github.com/org/repo/issues/42"})

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post.return_value.__aexit__  = AsyncMock(return_value=False)
            result = asyncio.run(gh.create_issue(
                "Critical Vuln", "Description", severity="CRITICAL", cve_id="CVE-2021-0001"
            ))

        assert result["success"] is True
        assert result["external_id"] == "42"

    def test_send_message_not_supported(self):
        import asyncio
        from app.services.integrations.github_integration import GitHubIntegration

        gh = GitHubIntegration("token", {})
        result = asyncio.run(gh.send_message("hello"))
        assert result["success"] is False
        assert "NOT_SUPPORTED" in result.get("error_code", "NOT_SUPPORTED")

    def test_create_issue_no_repo(self):
        import asyncio
        from app.services.integrations.github_integration import GitHubIntegration

        gh = GitHubIntegration("token", {})
        result = asyncio.run(gh.create_issue("Title", "Desc"))
        assert result["success"] is False


class TestJiraIntegration:

    def test_create_issue_success(self):
        import asyncio
        from app.services.integrations.jira_integration import JiraIntegration

        jira = JiraIntegration(
            "api_token",
            {"jira_url": "https://company.atlassian.net", "project_key": "SEC", "email": "user@co.com"},
        )

        mock_resp = AsyncMock()
        mock_resp.status = 201
        mock_resp.json   = AsyncMock(return_value={"key": "SEC-42", "id": "10001"})

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post.return_value.__aexit__  = AsyncMock(return_value=False)
            result = asyncio.run(jira.create_issue(
                "SQL Injection", "Details", severity="HIGH", cve_id="CVE-2022-0001"
            ))

        assert result["success"] is True
        assert result["external_id"] == "SEC-42"

    def test_no_config_returns_error(self):
        import asyncio
        from app.services.integrations.jira_integration import JiraIntegration

        jira = JiraIntegration("token", {})
        result = asyncio.run(jira.create_issue("Title", "Desc"))
        assert result["success"] is False

    def test_send_message_not_supported(self):
        import asyncio
        from app.services.integrations.jira_integration import JiraIntegration

        jira = JiraIntegration("token", {})
        result = asyncio.run(jira.send_message("hello"))
        assert result["success"] is False


class TestWebhookIntegration:

    def test_test_connection_success(self):
        import asyncio
        from app.services.integrations.webhook_integration import WebhookIntegration

        wh = WebhookIntegration("secret", {"webhook_url": "https://hooks.example.com/test"})

        mock_resp = AsyncMock()
        mock_resp.status = 200

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post.return_value.__aexit__  = AsyncMock(return_value=False)
            result = asyncio.run(wh.test_connection())

        assert result is True

    def test_test_connection_no_url(self):
        import asyncio
        from app.services.integrations.webhook_integration import WebhookIntegration

        wh = WebhookIntegration("", {})
        result = asyncio.run(wh.test_connection())
        assert result is False

    def test_send_message(self):
        import asyncio
        from app.services.integrations.webhook_integration import WebhookIntegration

        wh = WebhookIntegration("", {"webhook_url": "https://hooks.example.com/events"})

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.text   = AsyncMock(return_value="ok")

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post.return_value.__aexit__  = AsyncMock(return_value=False)
            result = asyncio.run(wh.send_message("alert", severity="HIGH"))

        assert result["success"] is True

    def test_create_issue_delegates_to_send_message(self):
        import asyncio
        from app.services.integrations.webhook_integration import WebhookIntegration

        wh = WebhookIntegration("", {"webhook_url": "https://hooks.example.com"})

        mock_resp = AsyncMock()
        mock_resp.status = 204
        mock_resp.text   = AsyncMock(return_value="")

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post.return_value.__aexit__  = AsyncMock(return_value=False)
            result = asyncio.run(wh.create_issue("Title", "Desc"))

        assert result["success"] is True
