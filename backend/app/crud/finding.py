"""Phase 5 Finding CRUD - filtered queries, status management, stats"""
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.finding import Finding, Severity, FindingStatus
from app.schemas.finding import FindingFilter, FindingUpdate


class CRUDFinding:

    def get(self, db: Session, finding_id: int) -> Optional[Finding]:
        return db.query(Finding).filter(Finding.id == finding_id).first()

    def get_multi_filtered(
        self,
        db: Session,
        filters: FindingFilter,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Finding], int]:
        q = db.query(Finding)

        if filters.project_id is not None:
            q = q.filter(Finding.project_id == filters.project_id)
        if filters.result_id is not None:
            q = q.filter(Finding.result_id == filters.result_id)
        if filters.severity is not None:
            q = q.filter(Finding.severity == filters.severity)
        if filters.status is not None:
            q = q.filter(Finding.status == filters.status)
        if filters.host:
            q = q.filter(Finding.host.ilike(f"%{filters.host}%"))
        if filters.tool_name:
            q = q.filter(Finding.tool_name == filters.tool_name)
        if filters.min_risk_score is not None:
            q = q.filter(Finding.risk_score >= filters.min_risk_score)
        if filters.exclude_duplicates:
            q = q.filter(Finding.is_duplicate == False)  # noqa: E712

        total = q.count()
        # Order: critical first (alphabetical happens to work for these 5 values),
        # then descending risk score
        items = (
            q.order_by(Finding.severity, desc(Finding.risk_score))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def update_status(
        self,
        db: Session,
        finding_id: int,
        update: FindingUpdate,
        user_id: int,
    ) -> Finding:
        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            raise ValueError(f"Finding {finding_id} not found")

        if update.status is not None:
            finding.status = update.status
        if update.severity is not None:
            finding.severity = update.severity
        if update.notes is not None:
            finding.notes = update.notes
        if update.assigned_to is not None:
            finding.assigned_to = update.assigned_to
        if update.false_positive_reason is not None:
            finding.false_positive_reason = update.false_positive_reason
            finding.false_positive = True
            finding.status = FindingStatus.false_positive

        db.add(finding)
        db.commit()
        db.refresh(finding)
        return finding

    def mark_false_positive(
        self,
        db: Session,
        finding_id: int,
        reason: str,
        user_id: int,
    ) -> Finding:
        update = FindingUpdate(
            status=FindingStatus.false_positive,
            false_positive_reason=reason,
        )
        return self.update_status(db, finding_id, update, user_id)

    def get_stats_by_severity(self, db: Session, project_id: int) -> dict:
        rows = (
            db.query(Finding.severity, func.count(Finding.id))
            .filter(
                Finding.project_id == project_id,
                Finding.is_duplicate == False,  # noqa: E712
                Finding.status != FindingStatus.false_positive,
            )
            .group_by(Finding.severity)
            .all()
        )
        return {sev.value: count for sev, count in rows}

    def count_open(self, db: Session, project_id: int) -> int:
        return (
            db.query(Finding)
            .filter(
                Finding.project_id == project_id,
                Finding.status == FindingStatus.open,
                Finding.is_duplicate == False,  # noqa: E712
            )
            .count()
        )


crud_finding = CRUDFinding()
