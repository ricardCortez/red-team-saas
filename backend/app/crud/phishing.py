"""CRUD for PhishingCampaign and PhishingTarget"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.phishing import PhishingCampaign, PhishingTarget, PhishingCampaignStatus


class CRUDPhishingCampaign:

    def create(self, db: Session, *, data: dict) -> PhishingCampaign:
        obj = PhishingCampaign(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get(self, db: Session, campaign_id: int) -> Optional[PhishingCampaign]:
        return db.query(PhishingCampaign).filter(PhishingCampaign.id == campaign_id).first()

    def get_multi(
        self,
        db: Session,
        *,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Dict:
        q = db.query(PhishingCampaign)
        if project_id is not None:
            q = q.filter(PhishingCampaign.project_id == project_id)
        if status:
            q = q.filter(PhishingCampaign.status == status)
        total = q.with_entities(func.count()).scalar()
        items = q.order_by(PhishingCampaign.created_at.desc()).offset(skip).limit(limit).all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    def update(self, db: Session, *, obj: PhishingCampaign, data: dict) -> PhishingCampaign:
        for k, v in data.items():
            setattr(obj, k, v)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, *, obj: PhishingCampaign) -> None:
        db.delete(obj)
        db.commit()

    # ── Targets ───────────────────────────────────────────────────────────────

    def add_targets(self, db: Session, *, campaign_id: int, targets: List[dict]) -> List[PhishingTarget]:
        objs = [PhishingTarget(campaign_id=campaign_id, **t) for t in targets]
        db.add_all(objs)
        db.commit()
        for o in objs:
            db.refresh(o)
        return objs

    def list_targets(self, db: Session, *, campaign_id: int) -> List[PhishingTarget]:
        return (
            db.query(PhishingTarget)
            .filter(PhishingTarget.campaign_id == campaign_id)
            .order_by(PhishingTarget.id)
            .all()
        )

    def delete_target(self, db: Session, *, target_id: int, campaign_id: int) -> bool:
        obj = (
            db.query(PhishingTarget)
            .filter(PhishingTarget.id == target_id, PhishingTarget.campaign_id == campaign_id)
            .first()
        )
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True

    def update_stats(self, db: Session, *, campaign: PhishingCampaign, stats: dict) -> PhishingCampaign:
        from datetime import datetime, timezone
        campaign.stats_total = stats.get("total", 0)
        campaign.stats_sent = stats.get("sent", 0)
        campaign.stats_opened = stats.get("opened", 0)
        campaign.stats_clicked = stats.get("clicked", 0)
        campaign.stats_submitted = stats.get("submitted_data", 0)
        campaign.stats_last_synced = datetime.now(timezone.utc)
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign


crud_phishing = CRUDPhishingCampaign()
