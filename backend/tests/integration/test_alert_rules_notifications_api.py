"""Integration tests for alert rules and notifications API - Phase 8"""
import pytest
from unittest.mock import patch, MagicMock


# ── Helpers ────────────────────────────────────────────────────────────────────

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def create_email_rule_payload(**overrides):
    payload = {
        "name": "Critical Email Alert",
        "channel": "email",
        "trigger": "severity_threshold",
        "conditions": {"severity": ["critical", "high"]},
        "channel_config": {"to": ["sec@example.com"]},
        "rate_limit_minutes": 60,
    }
    payload.update(overrides)
    return payload


def create_webhook_rule_payload(**overrides):
    payload = {
        "name": "Webhook Alert",
        "channel": "webhook",
        "trigger": "finding_created",
        "conditions": {},
        "channel_config": {"url": "https://hooks.example.com/alert"},
        "rate_limit_minutes": 30,
    }
    payload.update(overrides)
    return payload


def create_slack_rule_payload(**overrides):
    payload = {
        "name": "Slack Alert",
        "channel": "slack",
        "trigger": "scan_failed",
        "conditions": {},
        "channel_config": {"webhook_url": "https://hooks.slack.com/services/T000/B000/xxx"},
        "rate_limit_minutes": 60,
    }
    payload.update(overrides)
    return payload


# ── Alert Rules: Create ────────────────────────────────────────────────────────

class TestCreateAlertRule:
    def test_create_alert_rule_email(self, client, auth_token):
        payload = create_email_rule_payload()
        resp = client.post("/api/v1/alert-rules", json=payload, headers=auth_headers(auth_token))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["channel"] == "email"
        assert data["trigger"] == "severity_threshold"
        assert data["is_active"] is True
        assert data["rate_limit_minutes"] == 60

    def test_create_alert_rule_webhook(self, client, auth_token):
        payload = create_webhook_rule_payload()
        resp = client.post("/api/v1/alert-rules", json=payload, headers=auth_headers(auth_token))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["channel"] == "webhook"

    def test_create_alert_rule_slack(self, client, auth_token):
        payload = create_slack_rule_payload()
        resp = client.post("/api/v1/alert-rules", json=payload, headers=auth_headers(auth_token))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["channel"] == "slack"

    def test_create_alert_rule_invalid_email_config(self, client, auth_token):
        """Email channel with no recipients should fail validation."""
        payload = create_email_rule_payload(channel_config={"to": []})
        resp = client.post("/api/v1/alert-rules", json=payload, headers=auth_headers(auth_token))
        assert resp.status_code == 400

    def test_create_alert_rule_invalid_webhook_config(self, client, auth_token):
        """Webhook channel with invalid URL should fail validation."""
        payload = create_webhook_rule_payload(channel_config={"url": "ftp://bad.url"})
        resp = client.post("/api/v1/alert-rules", json=payload, headers=auth_headers(auth_token))
        assert resp.status_code == 400

    def test_create_alert_rule_requires_auth(self, client):
        payload = create_email_rule_payload()
        resp = client.post("/api/v1/alert-rules", json=payload)
        assert resp.status_code == 401

    def test_create_alert_rule_rate_limit_out_of_range(self, client, auth_token):
        payload = create_email_rule_payload(rate_limit_minutes=9999)
        resp = client.post("/api/v1/alert-rules", json=payload, headers=auth_headers(auth_token))
        assert resp.status_code == 422  # validation error


# ── Alert Rules: List ──────────────────────────────────────────────────────────

class TestListAlertRules:
    def test_list_alert_rules_empty(self, client, auth_token):
        resp = client.get("/api/v1/alert-rules", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_alert_rules_own_only(self, client, auth_token, test_user_data):
        """Creating rules as user A should not be visible to user B."""
        # Create a rule as user A
        payload = create_email_rule_payload()
        resp = client.post("/api/v1/alert-rules", json=payload, headers=auth_headers(auth_token))
        assert resp.status_code == 201

        # Register and login as user B
        user_b_data = {
            "email": "userb@example.com",
            "username": "userbtest",
            "password": "TestPass123!",
            "full_name": "User B",
        }
        client.post("/api/v1/auth/register", json=user_b_data)
        login_resp = client.post(
            "/api/v1/auth/login",
            params={"email": user_b_data["email"], "password": user_b_data["password"]},
        )
        token_b = login_resp.json()["access_token"]

        resp_b = client.get("/api/v1/alert-rules", headers=auth_headers(token_b))
        assert resp_b.status_code == 200
        assert len(resp_b.json()) == 0

    def test_list_shows_own_rules(self, client, auth_token):
        for i in range(3):
            payload = create_email_rule_payload(name=f"Rule {i}")
            client.post("/api/v1/alert-rules", json=payload, headers=auth_headers(auth_token))

        resp = client.get("/api/v1/alert-rules", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        assert len(resp.json()) == 3


# ── Alert Rules: Update ────────────────────────────────────────────────────────

class TestUpdateAlertRule:
    def test_update_alert_rule_deactivate(self, client, auth_token):
        payload = create_email_rule_payload()
        create_resp = client.post("/api/v1/alert-rules", json=payload, headers=auth_headers(auth_token))
        rule_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/alert-rules/{rule_id}",
            json={"is_active": False},
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_update_alert_rule_name(self, client, auth_token):
        create_resp = client.post(
            "/api/v1/alert-rules",
            json=create_email_rule_payload(),
            headers=auth_headers(auth_token),
        )
        rule_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/alert-rules/{rule_id}",
            json={"name": "Updated Name"},
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_update_nonexistent_rule_returns_404(self, client, auth_token):
        resp = client.patch(
            "/api/v1/alert-rules/99999",
            json={"is_active": False},
            headers=auth_headers(auth_token),
        )
        assert resp.status_code == 404


# ── Alert Rules: Delete ────────────────────────────────────────────────────────

class TestDeleteAlertRule:
    def test_delete_alert_rule(self, client, auth_token):
        create_resp = client.post(
            "/api/v1/alert-rules",
            json=create_email_rule_payload(),
            headers=auth_headers(auth_token),
        )
        rule_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/alert-rules/{rule_id}", headers=auth_headers(auth_token))
        assert resp.status_code == 204

        # Verify it's gone
        list_resp = client.get("/api/v1/alert-rules", headers=auth_headers(auth_token))
        assert len(list_resp.json()) == 0

    def test_delete_nonexistent_rule_returns_404(self, client, auth_token):
        resp = client.delete("/api/v1/alert-rules/99999", headers=auth_headers(auth_token))
        assert resp.status_code == 404


# ── Alert Rules: Test Endpoint ─────────────────────────────────────────────────

class TestAlertRuleTestEndpoint:
    def test_test_alert_rule_webhook_success(self, client, auth_token):
        create_resp = client.post(
            "/api/v1/alert-rules",
            json=create_webhook_rule_payload(),
            headers=auth_headers(auth_token),
        )
        rule_id = create_resp.json()["id"]

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch(
            "app.core.notifications.channels.webhook_channel.urllib.request.urlopen",
            return_value=mock_response,
        ):
            resp = client.post(
                f"/api/v1/alert-rules/{rule_id}/test",
                headers=auth_headers(auth_token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert data["success"] is True

    def test_test_alert_rule_email_channel_failure(self, client, auth_token):
        create_resp = client.post(
            "/api/v1/alert-rules",
            json=create_email_rule_payload(),
            headers=auth_headers(auth_token),
        )
        rule_id = create_resp.json()["id"]

        import smtplib
        with patch(
            "app.core.notifications.channels.email_channel.smtplib.SMTP",
            side_effect=smtplib.SMTPException("SMTP error"),
        ):
            resp = client.post(
                f"/api/v1/alert-rules/{rule_id}/test",
                headers=auth_headers(auth_token),
            )

        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_test_alert_rule_nonexistent_returns_404(self, client, auth_token):
        resp = client.post("/api/v1/alert-rules/99999/test", headers=auth_headers(auth_token))
        assert resp.status_code == 404


# ── Notifications: List ────────────────────────────────────────────────────────

class TestListNotifications:
    def _seed_notifications(self, db_session, user_id, count=5, status="sent"):
        from app.models.notification import Notification, NotificationStatus
        for i in range(count):
            n = Notification(
                user_id=user_id,
                channel="webhook",
                trigger="finding_created",
                status=NotificationStatus.SENT if status == "sent" else NotificationStatus.FAILED,
                event_type="finding",
                resource_id=i + 1,
                payload={"finding_title": f"Finding {i}"},
            )
            db_session.add(n)
        db_session.commit()

    def test_list_notifications_empty(self, client, auth_token):
        resp = client.get("/api/v1/notifications", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_notifications_paginated(self, client, auth_token, db_session, registered_user):
        self._seed_notifications(db_session, registered_user["id"], count=10)

        resp = client.get("/api/v1/notifications?limit=5&skip=0", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 10
        assert len(data["items"]) == 5

    def test_list_notifications_filter_status(self, client, auth_token, db_session, registered_user):
        from app.models.notification import Notification, NotificationStatus
        for status in [NotificationStatus.SENT, NotificationStatus.FAILED, NotificationStatus.SKIPPED]:
            n = Notification(
                user_id=registered_user["id"],
                channel="webhook",
                trigger="finding_created",
                status=status,
                event_type="finding",
                resource_id=1,
                payload={},
            )
            db_session.add(n)
        db_session.commit()

        resp = client.get("/api/v1/notifications?status=sent", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert all(item["status"] == "sent" for item in data["items"])

    def test_list_notifications_filter_channel(self, client, auth_token, db_session, registered_user):
        from app.models.notification import Notification, NotificationStatus
        for channel in ["email", "webhook", "slack"]:
            n = Notification(
                user_id=registered_user["id"],
                channel=channel,
                trigger="finding_created",
                status=NotificationStatus.SENT,
                event_type="finding",
                resource_id=1,
                payload={},
            )
            db_session.add(n)
        db_session.commit()

        resp = client.get("/api/v1/notifications?channel=email", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["channel"] == "email"


# ── Notifications: Stats ───────────────────────────────────────────────────────

class TestNotificationStats:
    def test_notification_stats_empty(self, client, auth_token):
        resp = client.get("/api/v1/notifications/stats", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["sent"] == 0
        assert data["failed"] == 0
        assert data["skipped"] == 0

    def test_notification_stats(self, client, auth_token, db_session, registered_user):
        from app.models.notification import Notification, NotificationStatus
        statuses = [
            NotificationStatus.SENT,
            NotificationStatus.SENT,
            NotificationStatus.FAILED,
            NotificationStatus.SKIPPED,
        ]
        for status in statuses:
            n = Notification(
                user_id=registered_user["id"],
                channel="webhook",
                trigger="finding_created",
                status=status,
                event_type="finding",
                resource_id=1,
                payload={},
            )
            db_session.add(n)
        db_session.commit()

        resp = client.get("/api/v1/notifications/stats", headers=auth_headers(auth_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert data["sent"] == 2
        assert data["failed"] == 1
        assert data["skipped"] == 1


# ── Notification created on finding (integration) ─────────────────────────────

class TestNotificationCreatedOnFinding:
    def test_notification_created_on_finding_via_evaluator(self, client, auth_token, db_session, registered_user):
        """
        Verify that AlertEvaluator.evaluate_finding creates a Notification record
        when a matching rule exists.
        """
        from app.models.alert_rule import AlertRule, AlertChannel, AlertTrigger
        from app.models.notification import Notification, NotificationStatus
        from app.core.notifications.evaluator import AlertEvaluator
        from app.models.finding import Finding, Severity
        from app.models.task import Task, TaskStatusEnum
        from datetime import datetime, timezone

        # Create a task
        task = Task(
            user_id=registered_user["id"],
            status=TaskStatusEnum.completed,
            tool_name="nmap",
            target="10.0.0.1",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Create a finding
        finding = Finding(
            task_id=task.id,
            title="SQL Injection",
            severity=Severity.critical,
            risk_score=9.5,
            tool_name="sqlmap",
        )
        db_session.add(finding)
        db_session.commit()
        db_session.refresh(finding)

        # Create a matching alert rule
        rule = AlertRule(
            user_id=registered_user["id"],
            name="Critical Severity Alert",
            channel=AlertChannel.WEBHOOK,
            trigger=AlertTrigger.SEVERITY_THRESHOLD,
            conditions={"severity": ["critical"]},
            channel_config={"url": "https://hooks.example.com"},
            rate_limit_minutes=0,
        )
        db_session.add(rule)
        db_session.commit()

        # Run evaluator with mocked webhook
        evaluator = AlertEvaluator(db_session)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch(
            "app.core.notifications.channels.webhook_channel.urllib.request.urlopen",
            return_value=mock_response,
        ):
            with patch("app.core.notifications.evaluator.is_rate_limited", return_value=False):
                evaluator.evaluate_finding(finding)

        # Verify notification was created
        notif = db_session.query(Notification).filter(
            Notification.user_id == registered_user["id"]
        ).first()
        assert notif is not None
        assert notif.status == NotificationStatus.SENT
        assert notif.channel == "webhook"
        assert notif.resource_id == finding.id
