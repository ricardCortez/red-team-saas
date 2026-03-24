"""Phase 5 - Findings management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRoleEnum
from app.models.finding import Severity, FindingStatus
from app.crud.finding import crud_finding
from app.schemas.finding import FindingResponse, FindingUpdate, FindingFilter, FindingListResponse
from app.core.audit import create_audit_log

router = APIRouter()


@router.get("/", response_model=FindingListResponse)
def list_findings(
    project_id: Optional[int] = Query(None),
    result_id: Optional[int] = Query(None),
    severity: Optional[Severity] = Query(None),
    status: Optional[FindingStatus] = Query(None),
    host: Optional[str] = Query(None),
    tool_name: Optional[str] = Query(None),
    min_risk_score: Optional[float] = Query(None),
    exclude_duplicates: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = FindingFilter(
        project_id=project_id,
        result_id=result_id,
        severity=severity,
        status=status,
        host=host,
        tool_name=tool_name,
        min_risk_score=min_risk_score,
        exclude_duplicates=exclude_duplicates,
    )
    items, total = crud_finding.get_multi_filtered(db, filters=filters, skip=skip, limit=limit)
    return FindingListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/stats/{project_id}")
def findings_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    by_severity = crud_finding.get_stats_by_severity(db, project_id)
    total_open = crud_finding.count_open(db, project_id)
    return {
        "by_severity": by_severity,
        "total_open": total_open,
        "total": sum(by_severity.values()),
    }


@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    finding = crud_finding.get(db, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.patch("/{finding_id}", response_model=FindingResponse)
def update_finding(
    finding_id: int,
    update: FindingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRoleEnum.viewer:
        raise HTTPException(status_code=403, detail="Viewers cannot update findings")

    try:
        finding = crud_finding.update_status(db, finding_id, update, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="finding_updated",
        resource="finding",
        resource_id=finding_id,
        details={"changes": update.model_dump(exclude_none=True)},
    )
    return finding


@router.post("/{finding_id}/false-positive", response_model=FindingResponse)
def mark_false_positive(
    finding_id: int,
    reason: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRoleEnum.viewer:
        raise HTTPException(status_code=403, detail="Viewers cannot update findings")

    try:
        finding = crud_finding.mark_false_positive(db, finding_id, reason, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="finding_false_positive",
        resource="finding",
        resource_id=finding_id,
        details={"reason": reason},
    )
    return finding
