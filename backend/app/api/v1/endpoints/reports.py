"""Report endpoints - Phase 6 Reporting Engine"""
import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user, require_role
from app.core.audit import log_action
from app.crud.report import crud_report
from app.models.report import Report, ReportClassification, ReportFormat, ReportStatus
from app.models.user import User
from app.schemas.report import ReportCreate, ReportResponse
from app.tasks.report_tasks import generate_report

router = APIRouter()


# ── Create ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester", "api_user"])),
):
    """Enqueue asynchronous report generation. Returns 202 with initial record."""
    report = Report(
        project_id=payload.project_id,
        created_by=current_user.id,
        title=payload.title,
        report_type=payload.report_type,
        report_format=payload.report_format or ReportFormat.pdf,
        classification=payload.classification or ReportClassification.confidential,
        scope_description=payload.scope_description,
        executive_summary=payload.executive_summary,
        recommendations=payload.recommendations,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    job = generate_report.apply_async(args=[report.id], queue="reports")
    report.celery_task_id = job.id
    db.commit()

    await log_action(
        db,
        user_id=current_user.id,
        action="report.create",
        resource_id=report.id,
        details={"type": payload.report_type, "format": payload.report_format},
    )
    return report


# ── List ───────────────────────────────────────────────────────────────────────

@router.get("/", response_model=dict)
async def list_reports(
    project_id: Optional[int] = Query(None),
    report_status: Optional[ReportStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = crud_report.get_multi(
        db,
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
        project_id=project_id,
        status=report_status,
        skip=skip,
        limit=limit,
    )
    result["items"] = [ReportResponse.model_validate(r) for r in result["items"]]
    return result


# ── Detail ─────────────────────────────────────────────────────────────────────

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = crud_report.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    return report


# ── Download ───────────────────────────────────────────────────────────────────

@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = crud_report.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    if report.status != ReportStatus.ready:
        raise HTTPException(status_code=400, detail=f"Report not ready. Status: {report.status.value}")
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    media_type = "application/pdf" if report.report_format == ReportFormat.pdf else "text/html"
    ext = "pdf" if report.report_format == ReportFormat.pdf else "html"
    filename = f"{report.title.replace(' ', '_')}_{report.id}.{ext}"

    await log_action(
        db,
        user_id=current_user.id,
        action="report.download",
        resource_id=report_id,
        details={"filename": filename},
    )
    return FileResponse(path=report.file_path, media_type=media_type, filename=filename)


# ── Delete ─────────────────────────────────────────────────────────────────────

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = crud_report.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    if report.file_path and os.path.exists(report.file_path):
        os.remove(report.file_path)

    crud_report.delete(db, report=report)
