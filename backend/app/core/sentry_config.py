"""Sentry error tracking configuration"""
import os
import logging

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry SDK with FastAPI, SQLAlchemy, and Celery integrations."""
    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        logger.info("SENTRY_DSN not set — Sentry error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        logging_integration = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                CeleryIntegration(),
                logging_integration,
            ],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
            environment=os.getenv("ENVIRONMENT", "development"),
            release=os.getenv("VERSION", "unknown"),
            send_default_pii=False,
            before_send=_before_send,
        )
        logger.info(
            "Sentry initialized — env=%s release=%s",
            os.getenv("ENVIRONMENT", "development"),
            os.getenv("VERSION", "unknown"),
        )
    except ImportError:
        logger.warning("sentry-sdk not installed — Sentry integration skipped")


def _before_send(event, hint):
    """Filter out low-signal events before sending to Sentry."""
    # Drop 404s
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        if exc_type and exc_type.__name__ in ("HTTPException",):
            status_code = getattr(exc_value, "status_code", None)
            if status_code in (404, 401, 403):
                return None
    return event
