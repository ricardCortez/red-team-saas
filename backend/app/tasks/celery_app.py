"""Celery application instance for Phase 4 tool execution"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "redteam_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.tool_executor",
        "app.tasks.cleanup_tasks",
        "app.tasks.report_tasks",
        "app.tasks.analytics_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.threat_intel_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=3300,   # 55 min soft limit
    task_time_limit=3600,        # 60 min hard limit
    result_expires=86400,        # 24 h
    beat_schedule={
        "cleanup-old-results": {
            "task": "app.tasks.cleanup_tasks.cleanup_expired_results",
            "schedule": 3600.0,
        },
        "health-check-workers": {
            "task": "app.tasks.cleanup_tasks.health_check",
            "schedule": 300.0,
        },
        "precompute-metrics": {
            "task": "app.tasks.analytics_tasks.precompute_global_metrics",
            "schedule": 600.0,  # every 10 min
        },
        "sync-mitre-weekly": {
            "task": "app.tasks.threat_intel_tasks.sync_mitre_techniques",
            "schedule": 604800.0,  # 1 week
        },
        "sync-ioc-feeds": {
            "task": "app.tasks.threat_intel_tasks.sync_ioc_feeds",
            "schedule": 21600.0,   # 6 hours
        },
    },
)
