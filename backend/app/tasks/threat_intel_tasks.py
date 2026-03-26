"""Celery tasks for Threat Intelligence - Phase 12"""
import logging

from app.tasks.celery_app import celery_app
from app.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.threat_intel_tasks.sync_mitre_techniques")
def sync_mitre_techniques():
    """Download and sync all ATT&CK techniques. Run weekly."""
    db = SessionLocal()
    try:
        from app.core.threat_intel.mitre_client import MITREClient
        from app.models.mitre_technique import MitreTechnique

        client = MITREClient()
        techniques = client.fetch_techniques()
        if not techniques:
            logger.warning("No MITRE techniques fetched")
            return {"synced": 0}

        synced = 0
        for t in techniques:
            existing = db.query(MitreTechnique).filter(
                MitreTechnique.technique_id == t["technique_id"]
            ).first()
            if existing:
                for k, v in t.items():
                    setattr(existing, k, v)
            else:
                db.add(MitreTechnique(**t))
            synced += 1

        db.commit()
        logger.info(f"MITRE sync: {synced} techniques")
        return {"synced": synced}
    except Exception as e:
        logger.error(f"MITRE sync failed: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.threat_intel_tasks.sync_ioc_feeds")
def sync_ioc_feeds():
    """Sync IOC feeds. Run every 6h."""
    db = SessionLocal()
    try:
        from app.core.threat_intel.ioc_feeds import IOCFeedClient
        from app.models.ioc import IOC, IOCType, IOCThreatLevel

        client = IOCFeedClient()
        iocs = client.fetch_all()
        added = 0

        for ioc_data in iocs:
            if not ioc_data.get("value"):
                continue
            existing = db.query(IOC).filter(IOC.value == ioc_data["value"]).first()
            if existing:
                continue

            # Validate enum values
            try:
                ioc_type = IOCType(ioc_data["ioc_type"])
            except (ValueError, KeyError):
                continue

            try:
                threat_level = IOCThreatLevel(ioc_data.get("threat_level", "medium"))
            except ValueError:
                threat_level = IOCThreatLevel.MEDIUM

            ioc = IOC(
                value=ioc_data["value"],
                ioc_type=ioc_type,
                threat_level=threat_level,
                confidence=ioc_data.get("confidence", 0.7),
                source=ioc_data.get("source"),
                description=ioc_data.get("description"),
                tags=ioc_data.get("tags", []),
            )
            db.add(ioc)
            added += 1

        db.commit()
        logger.info(f"IOC sync: {added} new IOCs")
        return {"added": added, "total_processed": len(iocs)}
    except Exception as e:
        logger.error(f"IOC sync failed: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.threat_intel_tasks.enrich_finding")
def enrich_finding_task(finding_id: int):
    """Enrich a specific finding. Queued after creation."""
    db = SessionLocal()
    try:
        from app.models.finding import Finding
        from app.core.threat_intel.enricher import FindingEnricher

        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            return {"error": f"Finding {finding_id} not found"}

        enricher = FindingEnricher(db)
        intel = enricher.enrich_finding(finding)

        if intel["risk_adjustment"] > 0:
            finding.risk_score = min((finding.risk_score or 0.0) + intel["risk_adjustment"], 10.0)
            db.commit()

        return intel
    except Exception as e:
        logger.error(f"Enrich finding {finding_id} failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()
