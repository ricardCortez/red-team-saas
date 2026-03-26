"""Celery tasks for Integration Hub — Phase 16"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── Finding notification ───────────────────────────────────────────────────────

@celery_app.task(
    name="app.tasks.integration_tasks.process_finding_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_finding_notification(self, finding_id: int) -> dict:
    """Dispatch integration notifications when a finding is created."""
    db = SessionLocal()
    try:
        from app.models.finding import Finding
        from app.services.notification_engine import NotificationEngine

        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            logger.warning("Finding %d not found for notification", finding_id)
            return {"status": "not_found"}

        engine = NotificationEngine(db)
        results = _run_async(engine.notify_on_finding(finding, finding.project_id))

        severity = (
            finding.severity.value if hasattr(finding.severity, "value") else finding.severity
        )
        if str(severity).upper() == "CRITICAL":
            critical_results = _run_async(
                engine.notify_on_critical_finding(finding, finding.project_id)
            )
            results.extend(critical_results)

        success_count = sum(1 for r in results if r.get("success"))
        logger.info(
            "Finding %d notifications: %d/%d successful",
            finding_id, success_count, len(results),
        )
        return {
            "status":        "success",
            "finding_id":    finding_id,
            "total":         len(results),
            "success_count": success_count,
        }

    except Exception as exc:
        logger.exception("Error processing finding notification %d: %s", finding_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ── Risk score notification ────────────────────────────────────────────────────

@celery_app.task(
    name="app.tasks.integration_tasks.process_risk_score_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_risk_score_notification(
    self,
    project_id: int,
    risk_score: int,
    previous_score: int,
) -> dict:
    """Dispatch notifications when a project's risk score changes."""
    db = SessionLocal()
    try:
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(db)
        results = _run_async(
            engine.notify_on_risk_score(project_id, risk_score, previous_score)
        )

        return {
            "status":        "success",
            "project_id":    project_id,
            "risk_score":    risk_score,
            "previous":      previous_score,
            "notified":      len(results),
        }
    except Exception as exc:
        logger.exception("Error processing risk score notification for project %d: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ── Scan completed notification ────────────────────────────────────────────────

@celery_app.task(
    name="app.tasks.integration_tasks.process_scan_completed_notification",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def process_scan_completed_notification(
    self,
    project_id: int,
    scan_id: int,
    finding_count: int = 0,
) -> dict:
    """Notify integrations when a scan finishes."""
    db = SessionLocal()
    try:
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(db)
        results = _run_async(
            engine.notify_on_scan_completed(project_id, scan_id, finding_count)
        )
        return {"status": "success", "scan_id": scan_id, "notified": len(results)}
    except Exception as exc:
        logger.exception("Error processing scan notification for scan %d: %s", scan_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ── Report generated notification ─────────────────────────────────────────────

@celery_app.task(
    name="app.tasks.integration_tasks.process_report_generated_notification",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def process_report_generated_notification(
    self,
    project_id: int,
    report_id: int,
    report_url: str = "",
) -> dict:
    """Notify integrations when a report is generated."""
    db = SessionLocal()
    try:
        from app.services.notification_engine import NotificationEngine

        engine = NotificationEngine(db)
        results = _run_async(
            engine.notify_on_report_generated(project_id, report_id, report_url)
        )
        return {"status": "success", "report_id": report_id, "notified": len(results)}
    except Exception as exc:
        logger.exception("Error processing report notification for report %d: %s", report_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ── Retry failed webhook deliveries ───────────────────────────────────────────

@celery_app.task(name="app.tasks.integration_tasks.retry_failed_webhook_deliveries")
def retry_failed_webhook_deliveries() -> dict:
    """Retry webhook deliveries that failed and are due for retry (every 15 min)."""
    db = SessionLocal()
    retried = 0
    try:
        from app.crud.integration import IntegrationCRUD
        from app.core.security import EncryptionHandler
        from app.services.integrations import INTEGRATION_CLASSES

        pending = IntegrationCRUD.get_pending_retries(db)

        for delivery in pending:
            integration = IntegrationCRUD.get_integration(db, delivery.integration_id)
            if not integration:
                continue
            try:
                int_type = (
                    integration.integration_type.value
                    if hasattr(integration.integration_type, "value")
                    else integration.integration_type
                )
                int_class = INTEGRATION_CLASSES.get(int_type.lower())
                if not int_class:
                    continue

                token = EncryptionHandler.decrypt(integration.auth_token or "")
                instance = int_class(token, integration.config or {})
                result = _run_async(
                    instance.send_message(f"Retry delivery for event: {delivery.event_type}")
                )

                delivery.attempt_number += 1
                if result.get("success"):
                    IntegrationCRUD.mark_delivery_success(
                        db, delivery.id,
                        int(result.get("status_code", 200)),
                        str(result),
                    )
                else:
                    delivery.next_retry_at = datetime.utcnow() + timedelta(minutes=15 * delivery.attempt_number)
                    db.commit()

                retried += 1
            except Exception as exc:
                logger.warning("Retry failed for delivery %d: %s", delivery.id, exc)

        logger.info("Retried %d failed webhook deliveries", retried)
        return {"status": "success", "retried": retried}

    except Exception as exc:
        logger.exception("Error in retry_failed_webhook_deliveries: %s", exc)
        return {"status": "error", "message": str(exc)}
    finally:
        db.close()


# ── Integration health check ───────────────────────────────────────────────────

@celery_app.task(name="app.tasks.integration_tasks.health_check_integrations")
def health_check_integrations() -> dict:
    """Periodically test all active integrations (every 6 hours)."""
    db = SessionLocal()
    checked = 0
    errors = 0
    try:
        from app.models.integration import Integration, IntegrationStatusEnum
        from app.crud.integration import IntegrationCRUD
        from app.core.security import EncryptionHandler
        from app.services.integrations import INTEGRATION_CLASSES

        integrations = (
            db.query(Integration)
            .filter(Integration.status == IntegrationStatusEnum.ACTIVE)
            .all()
        )

        for integration in integrations:
            try:
                int_type = (
                    integration.integration_type.value
                    if hasattr(integration.integration_type, "value")
                    else integration.integration_type
                )
                int_class = INTEGRATION_CLASSES.get(int_type.lower())
                if not int_class:
                    continue

                token = EncryptionHandler.decrypt(integration.auth_token or "")
                instance = int_class(token, integration.config or {})
                success = _run_async(instance.test_connection())

                IntegrationCRUD.update_integration_status(
                    db,
                    integration.id,
                    "active" if success else "error",
                    "success" if success else "failed",
                )
                checked += 1
                if not success:
                    errors += 1
            except Exception as exc:
                logger.warning("Health check failed for integration %d: %s", integration.id, exc)
                errors += 1

        logger.info("Integration health check: %d checked, %d errors", checked, errors)
        return {"status": "success", "checked": checked, "errors": errors}

    except Exception as exc:
        logger.exception("Health check task failed: %s", exc)
        return {"status": "error", "message": str(exc)}
    finally:
        db.close()
