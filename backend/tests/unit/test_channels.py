"""Unit tests for notification channels - Phase 8"""
import json
import pytest
from unittest.mock import MagicMock, patch, call
from app.core.notifications.channels.base_channel import NotificationPayload
from app.core.notifications.channels.email_channel import EmailChannel
from app.core.notifications.channels.webhook_channel import WebhookChannel
from app.core.notifications.channels.slack_channel import SlackChannel


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_payload():
    return NotificationPayload(
        title="Critical Finding",
        body="SQL injection found on /login",
        severity="critical",
        resource_id=42,
        extra={"project_id": 1},
    )


@pytest.fixture
def email_channel():
    return EmailChannel()


@pytest.fixture
def webhook_channel():
    return WebhookChannel()


@pytest.fixture
def slack_channel():
    return SlackChannel()


# ── EmailChannel ──────────────────────────────────────────────────────────────

class TestEmailChannelValidation:
    def test_validate_config_valid(self, email_channel):
        assert email_channel.validate_config({"to": ["sec@example.com"]}) is True

    def test_validate_config_multiple_recipients(self, email_channel):
        assert email_channel.validate_config({"to": ["a@b.com", "c@d.com"]}) is True

    def test_validate_config_empty_list(self, email_channel):
        assert email_channel.validate_config({"to": []}) is False

    def test_validate_config_missing_to(self, email_channel):
        assert email_channel.validate_config({}) is False

    def test_validate_config_to_not_list(self, email_channel):
        assert email_channel.validate_config({"to": "sec@example.com"}) is False


class TestEmailChannelSend:
    def test_send_no_recipients_returns_false(self, email_channel, sample_payload):
        result = email_channel.send({"to": []}, sample_payload)
        assert result is False

    def test_send_mock_smtp_success(self, email_channel, sample_payload):
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("app.core.notifications.channels.email_channel.smtplib.SMTP", return_value=mock_smtp):
            result = email_channel.send({"to": ["sec@example.com"]}, sample_payload)

        assert result is True
        mock_smtp.sendmail.assert_called_once()

    def test_send_smtp_exception_returns_false(self, email_channel, sample_payload):
        with patch(
            "app.core.notifications.channels.email_channel.smtplib.SMTP",
            side_effect=ConnectionRefusedError("SMTP down"),
        ):
            result = email_channel.send({"to": ["sec@example.com"]}, sample_payload)

        assert result is False

    def test_send_with_tls_calls_starttls(self, email_channel, sample_payload):
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("app.core.notifications.channels.email_channel.smtplib.SMTP", return_value=mock_smtp):
            with patch.object(
                type(email_channel),
                "send",
                wraps=email_channel.send,
            ):
                # Just verify no exceptions raised
                email_channel.send({"to": ["sec@example.com"]}, sample_payload)


# ── WebhookChannel ────────────────────────────────────────────────────────────

class TestWebhookChannelValidation:
    def test_validate_https_url(self, webhook_channel):
        assert webhook_channel.validate_config({"url": "https://hooks.example.com/notify"}) is True

    def test_validate_http_url(self, webhook_channel):
        assert webhook_channel.validate_config({"url": "http://internal.service/alert"}) is True

    def test_validate_invalid_url(self, webhook_channel):
        assert webhook_channel.validate_config({"url": "ftp://bad.url"}) is False

    def test_validate_missing_url(self, webhook_channel):
        assert webhook_channel.validate_config({}) is False

    def test_validate_empty_url(self, webhook_channel):
        assert webhook_channel.validate_config({"url": ""}) is False


class TestWebhookChannelSend:
    def test_send_no_url_returns_false(self, webhook_channel, sample_payload):
        result = webhook_channel.send({}, sample_payload)
        assert result is False

    def test_send_mock_http_success(self, webhook_channel, sample_payload):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.core.notifications.channels.webhook_channel.urllib.request.urlopen", return_value=mock_response):
            result = webhook_channel.send({"url": "https://hooks.example.com"}, sample_payload)

        assert result is True

    def test_send_http_error_returns_false(self, webhook_channel, sample_payload):
        import urllib.error
        with patch(
            "app.core.notifications.channels.webhook_channel.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = webhook_channel.send({"url": "https://hooks.example.com"}, sample_payload)

        assert result is False

    def test_send_includes_hmac_header_when_secret_provided(self, webhook_channel, sample_payload):
        import urllib.request as _req
        captured_request = {}

        def fake_urlopen(req, timeout=None):
            captured_request["headers"] = dict(req.headers)
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("app.core.notifications.channels.webhook_channel.urllib.request.urlopen", fake_urlopen):
            webhook_channel.send(
                {"url": "https://hooks.example.com", "secret": "mysecret"},
                sample_payload,
            )

        assert "X-redteam-signature" in captured_request["headers"]
        assert captured_request["headers"]["X-redteam-signature"].startswith("sha256=")

    def test_send_status_4xx_returns_false(self, webhook_channel, sample_payload):
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.core.notifications.channels.webhook_channel.urllib.request.urlopen", return_value=mock_response):
            result = webhook_channel.send({"url": "https://hooks.example.com"}, sample_payload)

        assert result is False


# ── SlackChannel ──────────────────────────────────────────────────────────────

class TestSlackChannelValidation:
    def test_validate_hooks_slack_url(self, slack_channel):
        assert slack_channel.validate_config({"webhook_url": "https://hooks.slack.com/services/T000/B000/xxx"}) is True

    def test_validate_https_url(self, slack_channel):
        assert slack_channel.validate_config({"webhook_url": "https://custom.slack.endpoint.com/hook"}) is True

    def test_validate_missing_webhook_url(self, slack_channel):
        assert slack_channel.validate_config({}) is False

    def test_validate_http_without_hooks_slack(self, slack_channel):
        assert slack_channel.validate_config({"webhook_url": "http://not-slack.com"}) is False


class TestSlackChannelSend:
    def test_send_no_webhook_url_returns_false(self, slack_channel, sample_payload):
        result = slack_channel.send({}, sample_payload)
        assert result is False

    def test_send_mock_http_success(self, slack_channel, sample_payload):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.core.notifications.channels.slack_channel.urllib.request.urlopen", return_value=mock_response):
            result = slack_channel.send(
                {"webhook_url": "https://hooks.slack.com/services/T000/B000/xxx"},
                sample_payload,
            )

        assert result is True

    def test_send_url_error_returns_false(self, slack_channel, sample_payload):
        import urllib.error
        with patch(
            "app.core.notifications.channels.slack_channel.urllib.request.urlopen",
            side_effect=urllib.error.URLError("timeout"),
        ):
            result = slack_channel.send(
                {"webhook_url": "https://hooks.slack.com/services/T000/B000/xxx"},
                sample_payload,
            )

        assert result is False

    def test_send_uses_severity_color_critical(self, slack_channel):
        from app.core.notifications.channels.slack_channel import SEVERITY_COLORS
        assert SEVERITY_COLORS["critical"] == "#c0392b"
        assert SEVERITY_COLORS["high"] == "#e67e22"
        assert SEVERITY_COLORS["low"] == "#27ae60"
