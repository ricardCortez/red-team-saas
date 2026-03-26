"""CRUD for Report - Phase 6 + Phase 14"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.report import (
    DigitalSignature,
    Report,
    ReportAuditLog,
    ReportSchedule,
    ReportStatusV2,
    ReportTemplate,
    ReportV2,
    ReportVersion,
    ReportStatus,
)


class CRUDReport:

    def get(self, db: Session, report_id: int) -> Optional[Report]:
        return db.query(Report).filter(Report.id == report_id).first()

    def get_multi(
        self,
        db: Session,
        *,
        user_id: int,
        is_superuser: bool = False,
        project_id: Optional[int] = None,
        status: Optional[ReportStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        q = db.query(Report)
        if not is_superuser:
            q = q.filter(Report.created_by == user_id)
        if project_id is not None:
            q = q.filter(Report.project_id == project_id)
        if status is not None:
            q = q.filter(Report.status == status)
        total = q.with_entities(func.count()).scalar()
        items = q.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "items": items, "skip": skip, "limit": limit}

    def delete(self, db: Session, *, report: Report) -> None:
        db.delete(report)
        db.commit()


crud_report = CRUDReport()


# ── Phase 14 CRUD ──────────────────────────────────────────────────────────────

class CRUDReportV2:
    """CRUD operations for Phase 14 ReportV2 and related models."""

    # ── ReportV2 ────────────────────────────────────────────────────────────

    def get(self, db: Session, report_id: int) -> Optional[ReportV2]:
        return db.query(ReportV2).filter(ReportV2.id == report_id).first()

    def list(
        self,
        db: Session,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict:
        q = db.query(ReportV2)
        if project_id is not None:
            q = q.filter(ReportV2.project_id == project_id)
        if status is not None:
            q = q.filter(ReportV2.status == status)
        total = q.with_entities(func.count()).scalar()
        items = q.order_by(ReportV2.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "items": items, "skip": skip, "limit": limit}

    def update_status(
        self,
        db: Session,
        report_id: int,
        status: str,
        reviewer_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[ReportV2]:
        report = self.get(db, report_id)
        if not report:
            return None
        report.status = status
        if notes:
            report.review_notes = notes
        if reviewer_id and status in (ReportStatusV2.approved, ReportStatusV2.pending_review):
            report.reviewed_by = reviewer_id
            report.reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(report)
        return report

    def publish(self, db: Session, report_id: int) -> Optional[ReportV2]:
        report = self.get(db, report_id)
        if not report:
            return None
        report.is_published = True
        report.published_at = datetime.utcnow()
        report.status = ReportStatusV2.published
        db.commit()
        db.refresh(report)
        return report

    # ── ReportVersion ────────────────────────────────────────────────────────

    def create_version(self, db: Session, report_id: int, version_data: Dict) -> ReportVersion:
        version = ReportVersion(report_id=report_id, **version_data)
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    def get_latest_version(self, db: Session, report_id: int) -> Optional[ReportVersion]:
        return (
            db.query(ReportVersion)
            .filter(ReportVersion.report_id == report_id)
            .order_by(ReportVersion.version_number.desc())
            .first()
        )

    def list_versions(self, db: Session, report_id: int) -> List[ReportVersion]:
        return (
            db.query(ReportVersion)
            .filter(ReportVersion.report_id == report_id)
            .order_by(ReportVersion.version_number.asc())
            .all()
        )

    # ── ReportTemplate ───────────────────────────────────────────────────────

    def create_template(self, db: Session, template_data: Dict, created_by: Optional[int] = None) -> ReportTemplate:
        template = ReportTemplate(**template_data, created_by=created_by)
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    def get_template(self, db: Session, template_id: int) -> Optional[ReportTemplate]:
        return db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()

    def list_templates(self, db: Session, report_type: Optional[str] = None) -> List[ReportTemplate]:
        q = db.query(ReportTemplate)
        if report_type:
            q = q.filter(ReportTemplate.report_type == report_type)
        return q.order_by(ReportTemplate.name).all()

    # ── ReportSchedule ───────────────────────────────────────────────────────

    def create_schedule(self, db: Session, schedule_data: Dict) -> ReportSchedule:
        schedule = ReportSchedule(**schedule_data)
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    def get_schedule(self, db: Session, schedule_id: int) -> Optional[ReportSchedule]:
        return db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()

    def list_schedules(
        self, db: Session, project_id: Optional[int] = None, enabled_only: bool = False
    ) -> List[ReportSchedule]:
        q = db.query(ReportSchedule)
        if project_id is not None:
            q = q.filter(ReportSchedule.project_id == project_id)
        if enabled_only:
            q = q.filter(ReportSchedule.is_enabled == True)  # noqa: E712
        return q.all()

    # ── ReportAuditLog ───────────────────────────────────────────────────────

    def log_action(
        self,
        db: Session,
        report_id: int,
        action: str,
        action_by: Optional[int],
        details: Optional[Dict] = None,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
    ) -> ReportAuditLog:
        entry = ReportAuditLog(
            report_id=report_id,
            action=action,
            action_by=action_by,
            details=details or {},
            previous_state=previous_state,
            new_state=new_state,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def get_audit_trail(self, db: Session, report_id: int) -> List[ReportAuditLog]:
        return (
            db.query(ReportAuditLog)
            .filter(ReportAuditLog.report_id == report_id)
            .order_by(ReportAuditLog.timestamp.asc())
            .all()
        )

    # ── DigitalSignature ─────────────────────────────────────────────────────

    def get_signature(self, db: Session, report_id: int) -> Optional[DigitalSignature]:
        return (
            db.query(DigitalSignature)
            .filter(DigitalSignature.report_id == report_id)
            .order_by(DigitalSignature.timestamp.desc())
            .first()
        )


crud_report_v2 = CRUDReportV2()
