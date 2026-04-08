"""Periodic Celery tasks for analytics — Phase 7 + Phase 15."""
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.analytics_tasks.precompute_global_metrics")
def precompute_global_metrics():
    """
    Pre-compute global metrics for all active users and warm the Redis cache.
    Scheduled every 10 minutes via Celery beat (Phase 7).
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


# ── Phase 15 Celery Tasks ──────────────────────────────────────────────────────

@celery_app.task(
    name="app.tasks.analytics_tasks.calculate_kpis_for_project",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def calculate_kpis_for_project(self, project_id: int):
    """Calculate and persist all KPIs for a single project (Phase 15)."""
    from app.database import SessionLocal
    from app.services.analytics_engine import AnalyticsEngine
    from app.services.realtime_metrics import RealtimeMetricsService

    db = SessionLocal()
    try:
        engine = AnalyticsEngine(db, RealtimeMetricsService())
        kpis = engine.calculate_all_kpis(project_id)
        logger.info("KPIs calculated for project %s: %d KPIs", project_id, len(kpis))
        return {"status": "success", "project_id": project_id, "kpis_count": len(kpis)}
    except Exception as exc:
        logger.exception("Error calculating KPIs for project %s: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.analytics_tasks.calculate_risk_score_for_project",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def calculate_risk_score_for_project(self, project_id: int):
    """Calculate and persist project risk score (Phase 15)."""
    from app.database import SessionLocal
    from app.services.analytics_engine import AnalyticsEngine
    from app.services.realtime_metrics import RealtimeMetricsService

    db = SessionLocal()
    try:
        engine = AnalyticsEngine(db, RealtimeMetricsService())
        rs = engine.calculate_risk_score(project_id)
        logger.info("Risk score for project %s: %d (%s)", project_id, rs.overall_score, rs.risk_level)
        return {"status": "success", "project_id": project_id, "score": rs.overall_score, "level": str(rs.risk_level)}
    except Exception as exc:
        logger.exception("Error calculating risk score for project %s: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.analytics_tasks.create_daily_snapshot",
    bind=True,
    max_retries=1,
)
def create_daily_snapshot(self, project_id: int, snapshot_type: str = "daily"):
    """Create analytics snapshot for a project (Phase 15)."""
    from app.database import SessionLocal
    from app.services.analytics_engine import AnalyticsEngine
    from app.services.realtime_metrics import RealtimeMetricsService

    db = SessionLocal()
    try:
        engine = AnalyticsEngine(db, RealtimeMetricsService())
        snapshot = engine.create_analytics_snapshot(project_id, snapshot_type)
        logger.info("Snapshot created for project %s (type=%s): id=%s", project_id, snapshot_type, snapshot.id)
        return {"status": "success", "snapshot_id": snapshot.id}
    except Exception as exc:
        logger.exception("Error creating snapshot for project %s: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.analytics_tasks.send_analytics_digest",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def send_analytics_digest(self, project_id: int, recipient_email: str):
    """Send weekly analytics digest email (Phase 15)."""
    from app.database import SessionLocal
    from app.crud.analytics import crud_analytics

    db = SessionLocal()
    try:
        digest = crud_analytics.get_project_digest(db, project_id)
        risk = digest["risk_score"]
        kpis = digest["kpis"]

        risk_line = f"{risk.overall_score}/100 ({risk.risk_level})" if risk else "N/A"

        kpi_items = "".join(
            f"<li><strong>{k.kpi_type}</strong>: {k.current_value} {k.current_unit} "
            f"(Trend: {k.trend})</li>"
            for k in kpis
        )

        html_content = f"""
        <h2>Weekly Red Team Analytics Digest</h2>
        <p><strong>Project:</strong> {project_id}</p>
        <p><strong>Risk Score:</strong> {risk_line}</p>
        <h3>Key KPIs</h3>
        <ul>{kpi_items or "<li>No KPI data yet</li>"}</ul>
        <p>View full dashboard in the Red Team SaaS platform.</p>
        """

        try:
            from app.core.notifications.channels.email_channel import EmailChannel
            EmailChannel.send_html(
                to=recipient_email,
                subject="Red Team Weekly Analytics Digest",
                html=html_content,
            )
        except Exception as email_exc:
            logger.warning("Email send failed (digest for project %s): %s", project_id, email_exc)

        logger.info("Analytics digest sent to %s for project %s", recipient_email, project_id)
        return {"status": "success", "recipient": recipient_email}

    except Exception as exc:
        logger.exception("Error sending digest for project %s: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(name="app.tasks.analytics_tasks.dispatch_project_analytics")
def dispatch_project_analytics():
    """
    Hourly beat task: dispatch KPI + risk-score calculation for all active projects.
    Phase 15 replacement for project-by-project ad-hoc calls.
    """
    from app.database import SessionLocal
    from app.models.project import Project

    db = SessionLocal()
    dispatched = []
    try:
        project_ids = [
            row[0]
            for row in db.query(Project.id).filter(Project.status != "archived").all()
        ]
        for pid in project_ids:
            calculate_kpis_for_project.apply_async(args=[pid], queue="analytics")
            calculate_risk_score_for_project.apply_async(args=[pid], queue="analytics")
            dispatched.append(pid)
        logger.info("Dispatched analytics for %d projects", len(dispatched))
        return {"dispatched": len(dispatched)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.analytics_tasks.dispatch_daily_snapshots")
def dispatch_daily_snapshots():
    """Midnight beat task: create daily snapshot for all active projects (Phase 15)."""
    from app.database import SessionLocal
    from app.models.project import Project

    db = SessionLocal()
    try:
        project_ids = [
            row[0]
            for row in db.query(Project.id).filter(Project.status != "archived").all()
        ]
        for pid in project_ids:
            create_daily_snapshot.apply_async(args=[pid, "daily"], queue="analytics")
        logger.info("Dispatched daily snapshots for %d projects", len(project_ids))
        return {"dispatched": len(project_ids)}
    finally:
        db.close()
