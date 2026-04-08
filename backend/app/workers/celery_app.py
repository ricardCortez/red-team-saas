# Re-export the canonical Celery application so that any legacy code
# that imports from app.workers.celery_app still works correctly.
from app.tasks.celery_app import celery_app  # noqa: F401

__all__ = ["celery_app"]
