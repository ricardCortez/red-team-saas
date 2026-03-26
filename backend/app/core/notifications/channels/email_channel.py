"""Email notification channel - Phase 8"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.notifications.channels.base_channel import BaseChannel, NotificationPayload
from app.core.config import settings
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

EMAIL_TEMPLATE = """
<html><body>
<h2 style="color:#c0392b;">Red Team Alert: {title}</h2>
<p><strong>Severity:</strong> {severity}</p>
<p>{body}</p>
<hr>
<small>Red Team SaaS - Auto-generated alert. Do not reply.</small>
</body></html>
"""


class EmailChannel(BaseChannel):
    name = "email"

    def send(self, config: Dict[str, Any], payload: NotificationPayload) -> bool:
        recipients = config.get("to", [])
        if not recipients:
            logger.warning("Email channel: no recipients configured")
            return False

        smtp_from = getattr(settings, "SMTP_FROM", None) or "alerts@redteam.local"
        smtp_host = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
        smtp_port = getattr(settings, "SMTP_PORT", 587)
        smtp_tls = getattr(settings, "SMTP_TLS", True)
        smtp_user = getattr(settings, "SMTP_USER", None)
        smtp_password = getattr(settings, "SMTP_PASSWORD", None)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[RedTeam Alert] {payload.title}"
        msg["From"] = smtp_from
        msg["To"] = ", ".join(recipients)

        html = EMAIL_TEMPLATE.format(
            title=payload.title,
            severity=payload.severity.upper(),
            body=payload.body,
        )
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if smtp_tls:
                    server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.sendmail(smtp_from, recipients, msg.as_string())
            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("to") and isinstance(config["to"], list))
