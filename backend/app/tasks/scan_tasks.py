"""Celery tasks for scan execution (stub — full implementation in Fase 4)"""
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.execute_scan")
def execute_scan(self, scan_id: int):
    """Execute a scan asynchronously.

    Stub implementation: marks the scan as running then completed.
    Fase 4 will plug in the actual tool execution engine here.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"execute_scan called for scan_id={scan_id} (stub)")
    return {"scan_id": scan_id, "status": "queued"}
