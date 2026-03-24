"""Celery task for asynchronous report generation - Phase 6"""
import logging
import os
from datetime import datetime

from celery import shared_task

from app.database import SessionLocal
from app.models.report import Report, ReportFormat, ReportStatus
from app.core.reporting.data_aggregator import ReportDataAggregator
from app.core.reporting.html_renderer import HTMLRenderer
from app.core.reporting.pdf_renderer import PDFRenderer
from app.tasks.base_task import BaseRedTeamTask

logger = logging.getLogger(__name__)

STORAGE_DIR = os.environ.get("REPORTS_DIR", "/tmp/reports")


@shared_task(
    bind=True,
    base=BaseRedTeamTask,
    name="app.tasks.report_tasks.generate_report",
    max_retries=1,
    default_retry_delay=30,
)
def generate_report(self, report_id: int):
    """Aggregate findings, render the report file, and persist it."""
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")

        report.status = ReportStatus.generating
        report.celery_task_id = self.request.id
        db.commit()

        # Aggregate project data
        aggregator = ReportDataAggregator(db, report.project_id)
        data = aggregator.aggregate()

        # Snapshot stats into model
        stats = data["stats"]
        report.total_findings = stats["total"]
        report.critical_count = stats["critical"]
        report.high_count = stats["high"]
        report.medium_count = stats["medium"]
        report.low_count = stats["low"]
        report.overall_risk = stats["overall_risk"]

        # Pick renderer
        renderer = PDFRenderer() if report.report_format == ReportFormat.pdf else HTMLRenderer()

        # Render
        content = renderer.render(data, report)

        # Persist file
        os.makedirs(STORAGE_DIR, exist_ok=True)
        filename = f"report_{report_id}_{report.report_type.value}.{renderer.extension()}"
        filepath = os.path.join(STORAGE_DIR, filename)
        with open(filepath, "wb") as fh:
            fh.write(content)

        report.file_path = filepath
        report.file_size_bytes = len(content)
        report.status = ReportStatus.ready
        report.generated_at = datetime.utcnow()
        db.commit()

        return {"report_id": report_id, "file": filename, "size": len(content)}

    except Exception as exc:
        logger.error("Report %s generation failed: %s", report_id, exc)
        try:
            r = db.query(Report).filter(Report.id == report_id).first()
            if r:
                r.status = ReportStatus.failed
                r.error_message = str(exc)
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        db.close()
