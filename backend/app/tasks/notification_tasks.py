"""Celery tasks for alert evaluation and notification sending - Phase 8"""
import logging

from app.tasks.celery_app import celery_app
from app.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.notification_tasks.evaluate_finding_alerts")
def evaluate_finding_alerts(finding_id: int) -> dict:
    """
    Evaluate alert rules for a newly created finding.
    Should be called after process_result_findings in tool_executor.
    """
    db = SessionLocal()
    try:
        from app.models.finding import Finding
        from app.core.notifications.evaluator import AlertEvaluator

        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            logger.warning(f"evaluate_finding_alerts: finding {finding_id} not found")
            return {"status": "skipped", "reason": "finding_not_found"}

        evaluator = AlertEvaluator(db)
        evaluator.evaluate_finding(finding)
        return {"status": "ok", "finding_id": finding_id}
    except Exception as e:
        logger.error(f"evaluate_finding_alerts failed for finding={finding_id}: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.notification_tasks.evaluate_scan_alerts")
def evaluate_scan_alerts(task_id: int) -> dict:
    """
    Evaluate scan_completed / scan_failed alert rules for a task.
    Should be called after a task completes or fails in tool_executor.
    """
    db = SessionLocal()
    try:
        from app.models.task import Task
        from app.core.notifications.evaluator import AlertEvaluator

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"evaluate_scan_alerts: task {task_id} not found")
            return {"status": "skipped", "reason": "task_not_found"}

        evaluator = AlertEvaluator(db)
        evaluator.evaluate_scan(task)
        return {"status": "ok", "task_id": task_id}
    except Exception as e:
        logger.error(f"evaluate_scan_alerts failed for task={task_id}: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
