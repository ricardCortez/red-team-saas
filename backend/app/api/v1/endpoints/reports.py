"""Report CRUD endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user, require_role
from app.crud.report import crud_report
from app.schemas.report import (
    ReportCreate, ReportUpdate,
    ReportResponse, ReportListResponse,
)
from app.models.user import User
from app.core.audit import log_action

router = APIRouter()


@router.get("/", response_model=ReportListResponse)
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    workspace_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {"status": status, "workspace_id": workspace_id}
    if not current_user.is_superuser:
        filters["author_id"] = current_user.id
    return crud_report.get_multi(db, skip=skip, limit=limit, filters=filters)


@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_in: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    report = crud_report.create(db, obj_in=report_in, author_id=current_user.id)
    await log_action(db, user_id=current_user.id, action="report.create", resource_id=report.id)
    return report


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = crud_report.get(db, id=report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not current_user.is_superuser and report.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return report


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: int,
    report_in: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    report = crud_report.get(db, id=report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not current_user.is_superuser and report.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud_report.update(db, db_obj=report, obj_in=report_in)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    report = crud_report.get(db, id=report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    crud_report.remove(db, id=report_id)
    await log_action(db, user_id=current_user.id, action="report.delete", resource_id=report_id)


@router.post("/{report_id}/finalize", response_model=ReportResponse)
async def finalize_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """Sign and finalize a report (computes SHA-256 hash of content)"""
    report = crud_report.get(db, id=report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report = crud_report.finalize(db, db_obj=report)
    await log_action(db, user_id=current_user.id, action="report.finalize", resource_id=report_id)
    return report
