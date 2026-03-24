"""Periodic Celery beat tasks: cleanup and health checks"""
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

from app.database import SessionLocal
from app.models.result import Result
from app.models.task import Task, TaskStatusEnum

logger = logging.getLogger(__name__)


@shared_task(name="app.tasks.cleanup_tasks.cleanup_expired_results")
def cleanup_expired_results(days: int = 30) -> dict:
    """Delete results older than `days` days."""
    db = SessionLocal()
    deleted = 0
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        results = db.query(Result).filter(Result.created_at < cutoff).all()
        deleted = len(results)
        for r in results:
            db.delete(r)
        db.commit()
        logger.info(f"cleanup_expired_results: deleted {deleted} results older than {days} days")
    except Exception as exc:
        logger.error(f"cleanup_expired_results failed: {exc}")
        db.rollback()
    finally:
        db.close()
    return {"deleted": deleted}


@shared_task(name="app.tasks.cleanup_tasks.health_check")
def health_check() -> dict:
    """Verify DB connectivity and report stuck running tasks."""
    db = SessionLocal()
    stuck = 0
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))

        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        stuck_tasks = (
            db.query(Task)
            .filter(
                Task.status == TaskStatusEnum.running,
                Task.updated_at < cutoff,
            )
            .all()
        )
        stuck = len(stuck_tasks)
        for t in stuck_tasks:
            t.status = TaskStatusEnum.failed
            t.error_message = "Task marked as failed by health check (stuck running > 2h)"
        if stuck_tasks:
            db.commit()
    except Exception as exc:
        logger.error(f"health_check failed: {exc}")
    finally:
        db.close()
    return {"db": "ok", "stuck_tasks_recovered": stuck}
