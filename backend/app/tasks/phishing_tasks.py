"""Celery tasks for phishing campaign stats synchronisation."""
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.tasks.base_task import BaseRedTeamTask

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    base=BaseRedTeamTask,
    name="app.tasks.phishing_tasks.sync_campaign_stats",
    max_retries=2,
    default_retry_delay=30,
)
def sync_campaign_stats(self, campaign_id: int):
    """Fetch latest stats from GoPhish and update the PhishingCampaign row."""
    from app.database import SessionLocal
    from app.models.phishing import PhishingCampaign, PhishingTarget, PhishingTargetStatus
    from app.services.gophish_client import GoPhishClient, GoPhishError
    from app.crud.phishing import crud_phishing

    db = SessionLocal()
    try:
        campaign = db.query(PhishingCampaign).filter(PhishingCampaign.id == campaign_id).first()
        if not campaign or not campaign.gophish_campaign_id:
            logger.info("sync_campaign_stats: campaign %s not found or not launched", campaign_id)
            return {"status": "skipped", "campaign_id": campaign_id}

        client = GoPhishClient(campaign.gophish_url, campaign.gophish_api_key)
        summary = client.get_campaign_summary(campaign.gophish_campaign_id)

        gp_stats = summary.get("stats", {})
        stats = {
            "total": gp_stats.get("total", 0),
            "sent": gp_stats.get("sent", 0),
            "opened": gp_stats.get("opened", 0),
            "clicked": gp_stats.get("clicked", 0),
            "submitted_data": gp_stats.get("submitted_data", 0),
        }
        crud_phishing.update_stats(db, campaign=campaign, stats=stats)

        # Sync per-target statuses
        try:
            results_data = client.get_campaign_results(campaign.gophish_campaign_id)
            STATUS_MAP = {
                "Email Sent": PhishingTargetStatus.sent,
                "Email Opened": PhishingTargetStatus.opened,
                "Clicked Link": PhishingTargetStatus.clicked,
                "Submitted Data": PhishingTargetStatus.submitted_data,
                "Email Reported": PhishingTargetStatus.reported,
            }
            for r in results_data.get("results", []):
                email = r.get("email", "")
                raw_status = r.get("status", "")
                new_status = STATUS_MAP.get(raw_status)
                if new_status and email:
                    target = (
                        db.query(PhishingTarget)
                        .filter(
                            PhishingTarget.campaign_id == campaign_id,
                            PhishingTarget.email == email,
                        )
                        .first()
                    )
                    if target:
                        target.status = new_status
            db.commit()
        except Exception as exc:
            logger.warning("sync_campaign_stats: could not sync per-target results: %s", exc)

        logger.info("sync_campaign_stats: campaign %s synced — %s", campaign_id, stats)
        return {"status": "ok", "campaign_id": campaign_id, "stats": stats}

    except GoPhishError as exc:
        # Transient GoPhish errors (network, 5xx) → retry
        logger.error("sync_campaign_stats: GoPhish error for campaign %s: %s", campaign_id, exc)
        raise self.retry(exc=exc)
    except Exception as exc:
        # Non-transient errors (missing model, programming error) → fail fast, do not retry
        logger.exception("sync_campaign_stats: unexpected error for campaign %s: %s", campaign_id, exc)
        raise
    finally:
        db.close()
