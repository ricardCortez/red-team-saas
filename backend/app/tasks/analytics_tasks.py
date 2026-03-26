"""Periodic Celery tasks for pre-computing analytics metrics."""
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.analytics_tasks.precompute_global_metrics")
def precompute_global_metrics():
    """
    Pre-compute global metrics for all active users and warm the Redis cache.
    Scheduled every 10 minutes via Celery beat.
    """
    from app.database import SessionLocal
    from app.models.user import User
    from app.core.analytics.metrics import MetricsEngine

    db = SessionLocal()
    try:
        users = db.query(User.id).filter(User.is_active == True).all()
        for (user_id,) in users:
            try:
                MetricsEngine.global_summary(db, user_id)
                MetricsEngine.top_targets(db, user_id)
                MetricsEngine.top_tools(db, user_id)
            except Exception as e:
                logger.warning(f"Precompute failed for user {user_id}: {e}")
    finally:
        db.close()
