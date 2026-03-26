"""Celery tasks for report generation — Phase 6 + Phase 14"""
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


# ── Phase 14: Scheduled Report Generation ─────────────────────────────────────

@shared_task(
    bind=True,
    base=BaseRedTeamTask,
    name="app.tasks.report_tasks.generate_scheduled_report_v2",
    max_retries=2,
    default_retry_delay=60,
)
def generate_scheduled_report_v2(self, schedule_id: int):
    """
    Generate a ReportV2 triggered by a ReportSchedule (cron-based).
    Renders PDF, HTML, and Excel; stores in S3 or local fallback.
    """
    from app.models.report import ReportSchedule, ReportTypeV2
    from app.models.finding import Finding, FindingStatus
    from app.crud.report import crud_report_v2
    from app.services.report_generator import ReportGenerator

    db = SessionLocal()
    try:
        schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
        if not schedule or not schedule.is_enabled:
            logger.info("Schedule %s is disabled or not found — skipping.", schedule_id)
            return {"status": "skipped", "schedule_id": schedule_id}

        generator = ReportGenerator(db)
        report = generator.generate_report(
            project_id=schedule.project_id,
            report_type=schedule.report_type,
            title=f"{schedule.name} — {datetime.utcnow().date()}",
            generated_by=None,
            template_id=schedule.template_id,
        )

        findings = (
            db.query(Finding)
            .filter(
                Finding.project_id == schedule.project_id,
                Finding.is_duplicate == False,  # noqa: E712
                Finding.status != FindingStatus.false_positive,
            )
            .all()
        )

        from app.core.config import settings
        bucket = getattr(settings, "S3_REPORTS_BUCKET", None)
        version_data: dict = {"version_number": 1, "status": "published"}

        for fmt, render_fn in [
            ("pdf",   lambda: generator.render_pdf(report, findings)),
            ("html",  lambda: generator.render_html(report, findings)),
            ("excel", lambda: generator.render_excel(report, findings)),
        ]:
            try:
                content = render_fn()
                if bucket:
                    from app.services.s3_storage import S3ReportStorage
                    storage = S3ReportStorage(bucket)
                    upload = storage.upload_report(report.id, content, fmt, 1)
                    version_data[f"{fmt}_file_key"] = upload["s3_key"]
                    version_data.setdefault("file_size_bytes", upload["file_size_bytes"])
                    version_data.setdefault("checksum_sha256", upload["checksum_sha256"])
                else:
                    import hashlib
                    out_dir = os.path.join(STORAGE_DIR, "v2", str(report.id))
                    os.makedirs(out_dir, exist_ok=True)
                    path = os.path.join(out_dir, f"report.{fmt}")
                    with open(path, "wb") as fh:
                        fh.write(content)
                    version_data[f"{fmt}_file_key"] = path
                    version_data.setdefault("file_size_bytes", len(content))
                    version_data.setdefault("checksum_sha256", hashlib.sha256(content).hexdigest())
            except Exception as exc:
                logger.error("Scheduled report: error rendering %s for schedule %s: %s", fmt, schedule_id, exc)

        crud_report_v2.create_version(db, report.id, version_data)

        schedule.last_generated_at = datetime.utcnow()
        db.commit()

        logger.info("Scheduled report generated: report_id=%s schedule_id=%s", report.id, schedule_id)
        return {"status": "success", "report_id": report.id, "schedule_id": schedule_id}

    except Exception as exc:
        logger.exception("Scheduled report generation failed (schedule %s): %s", schedule_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


@shared_task(
    bind=True,
    base=BaseRedTeamTask,
    name="app.tasks.report_tasks.dispatch_due_report_schedules",
)
def dispatch_due_report_schedules(self):
    """
    Beat task (every 15 min): find enabled ReportSchedules whose
    next_scheduled_at is due and enqueue generate_scheduled_report_v2.
    """
    from app.models.report import ReportSchedule
    from croniter import croniter

    db = SessionLocal()
    dispatched = []
    try:
        now = datetime.utcnow()
        schedules = (
            db.query(ReportSchedule)
            .filter(ReportSchedule.is_enabled == True)  # noqa: E712
            .all()
        )

        for schedule in schedules:
            try:
                cron = croniter(schedule.cron_expression, schedule.last_generated_at or now)
                next_due = cron.get_next(datetime)

                if next_due <= now:
                    generate_scheduled_report_v2.apply_async(
                        args=[schedule.id], queue="reports"
                    )
                    dispatched.append(schedule.id)
                    logger.info("Dispatched scheduled report for schedule %s", schedule.id)

                # Persist next scheduled time
                schedule.next_scheduled_at = next_due
            except Exception as exc:
                logger.warning("Error processing schedule %s: %s", schedule.id, exc)

        db.commit()
        return {"dispatched": dispatched, "checked": len(schedules)}
    finally:
        db.close()
