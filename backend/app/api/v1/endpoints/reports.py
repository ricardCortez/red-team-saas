"""Report endpoints - Phase 6 Reporting Engine + Phase 14 Professional Reports"""
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db, get_current_user, require_role
from app.core.audit import log_action
from app.crud.report import crud_report, crud_report_v2
from app.models.report import Report, ReportClassification, ReportFormat, ReportStatus
from app.models.user import User
from app.schemas.report import (
    ReportCreate,
    ReportResponse,
    ReportV2Create,
    ReportV2Response,
    ReportTemplateCreate,
    ReportTemplateResponse,
    ReportScheduleCreate,
    ReportScheduleResponse,
    ReportVersionResponse,
    DigitalSignatureResponse,
    ReportAuditLogResponse,
)
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


# ══════════════════════════════════════════════════════════════════════════════
# Phase 14 — Professional Reports (multi-format, signatures, S3, scheduling)
# ══════════════════════════════════════════════════════════════════════════════

# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=List[ReportTemplateResponse], tags=["Report Templates"])
async def list_templates(
    report_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available report templates (Phase 14)."""
    return crud_report_v2.list_templates(db, report_type=report_type)


@router.post("/templates", response_model=ReportTemplateResponse, status_code=status.HTTP_201_CREATED, tags=["Report Templates"])
async def create_template(
    payload: ReportTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """Create a new report template (Phase 14)."""
    data = payload.model_dump()
    return crud_report_v2.create_template(db, data, created_by=current_user.id)


# ── Report V2 Generation ───────────────────────────────────────────────────────

@router.post("/v2", response_model=ReportV2Response, status_code=status.HTTP_202_ACCEPTED, tags=["Reports V2"])
async def create_report_v2(
    payload: ReportV2Create,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester", "api_user"])),
):
    """
    Generate a professional multi-format report (PDF/HTML/Excel) — Phase 14.
    Returns 202 immediately; file generation happens in the background.
    """
    from app.services.report_generator import ReportGenerator

    generator = ReportGenerator(db)
    report = generator.generate_report(
        project_id=payload.project_id,
        report_type=payload.report_type,
        title=payload.title,
        generated_by=current_user.id,
        template_id=payload.template_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        compliance_mapping_id=payload.compliance_mapping_id,
        custom_variables=payload.custom_variables,
    )

    background_tasks.add_task(
        _render_and_store_formats,
        report.id,
        payload.formats,
    )

    crud_report_v2.log_action(db, report.id, "CREATED", current_user.id)
    return report


@router.get("/v2", response_model=dict, tags=["Reports V2"])
async def list_reports_v2(
    project_id: Optional[int] = Query(None),
    report_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Phase 14 reports with optional project/status filters."""
    result = crud_report_v2.list(db, project_id=project_id, status=report_status, skip=skip, limit=limit)
    result["items"] = [ReportV2Response.model_validate(r) for r in result["items"]]
    return result


@router.get("/v2/{report_id}", response_model=ReportV2Response, tags=["Reports V2"])
async def get_report_v2(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a Phase 14 report by ID."""
    report = crud_report_v2.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    crud_report_v2.log_action(db, report_id, "VIEWED", current_user.id)
    return report


# ── Download ───────────────────────────────────────────────────────────────────

@router.get("/v2/{report_id}/download", tags=["Reports V2"])
async def download_report_v2(
    report_id: int,
    fmt: str = Query("pdf", regex="^(pdf|html|excel)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a presigned S3 download URL for a specific report format.
    Falls back to regenerating locally if S3 is not configured.
    """
    import os
    from app.core.config import settings

    report = crud_report_v2.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    version = crud_report_v2.get_latest_version(db, report_id)
    if not version:
        raise HTTPException(status_code=404, detail="No generated version found. Try again shortly.")

    s3_key = getattr(version, f"{fmt}_file_key", None)
    if not s3_key:
        raise HTTPException(status_code=400, detail=f"Format '{fmt}' not yet available for this report.")

    bucket = getattr(settings, "S3_REPORTS_BUCKET", None)
    if not bucket:
        raise HTTPException(status_code=501, detail="S3 storage not configured.")

    from app.services.s3_storage import S3ReportStorage
    storage = S3ReportStorage(bucket)
    download_info = storage.download_url(s3_key)

    crud_report_v2.log_action(db, report_id, "DOWNLOADED", current_user.id, {"format": fmt})
    return download_info


# ── Review & Approval ──────────────────────────────────────────────────────────

@router.patch("/v2/{report_id}/review", response_model=ReportV2Response, tags=["Reports V2"])
async def review_report_v2(
    report_id: int,
    new_status: str = Query(..., alias="status"),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """Approve, reject, or move a report to pending review (Phase 14)."""
    report = crud_report_v2.update_status(
        db, report_id, new_status, reviewer_id=current_user.id, notes=notes
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    crud_report_v2.log_action(
        db, report_id, "REVIEWED", current_user.id, {"status": new_status}
    )
    return report


# ── Digital Signature ──────────────────────────────────────────────────────────

@router.post("/v2/{report_id}/sign", response_model=DigitalSignatureResponse, tags=["Reports V2"])
async def sign_report_v2(
    report_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """
    Digitally sign a report with an X.509 certificate (Phase 14).

    Payload: {certificate_pem: str, private_key_pem: str, password?: str}
    """
    from app.services.digital_signature import DigitalSignatureManager

    cert_pem = payload.get("certificate_pem")
    key_pem = payload.get("private_key_pem")
    if not cert_pem or not key_pem:
        raise HTTPException(
            status_code=400,
            detail="certificate_pem and private_key_pem are required",
        )

    password = payload.get("password")
    password_bytes = password.encode() if password else None

    report = crud_report_v2.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    manager = DigitalSignatureManager(db)
    try:
        sig = manager.sign_report(
            report_id=report_id,
            signer_id=current_user.id,
            certificate_pem=cert_pem.encode() if isinstance(cert_pem, str) else cert_pem,
            private_key_pem=key_pem.encode() if isinstance(key_pem, str) else key_pem,
            private_key_password=password_bytes,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Signing failed: {exc}")

    crud_report_v2.log_action(db, report_id, "SIGNED", current_user.id)
    return sig


@router.get("/v2/{report_id}/verify-signature", tags=["Reports V2"])
async def verify_signature_v2(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify the digital signature of a report (Phase 14)."""
    from app.services.digital_signature import DigitalSignatureManager

    report = crud_report_v2.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    sig = crud_report_v2.get_signature(db, report_id)
    if not sig:
        return {"signed": False, "message": "Report has not been signed"}

    manager = DigitalSignatureManager(db)
    return manager.verify_signature(sig.id)


# ── Audit Trail ────────────────────────────────────────────────────────────────

@router.get("/v2/{report_id}/audit-trail", response_model=List[ReportAuditLogResponse], tags=["Reports V2"])
async def get_audit_trail_v2(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the full immutable audit trail for a report (Phase 14)."""
    report = crud_report_v2.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return crud_report_v2.get_audit_trail(db, report_id)


# ── Versions ───────────────────────────────────────────────────────────────────

@router.get("/v2/{report_id}/versions", response_model=List[ReportVersionResponse], tags=["Reports V2"])
async def list_report_versions(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all stored versions of a report (Phase 14)."""
    report = crud_report_v2.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return crud_report_v2.list_versions(db, report_id)


# ── Schedules ──────────────────────────────────────────────────────────────────

@router.post("/schedules", response_model=ReportScheduleResponse, status_code=status.HTTP_201_CREATED, tags=["Report Schedules"])
async def create_schedule(
    payload: ReportScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
):
    """Create a cron-based report generation schedule (Phase 14)."""
    data = payload.model_dump()
    data["created_by"] = current_user.id
    return crud_report_v2.create_schedule(db, data)


@router.get("/schedules", response_model=List[ReportScheduleResponse], tags=["Report Schedules"])
async def list_schedules(
    project_id: Optional[int] = Query(None),
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List report schedules (Phase 14)."""
    return crud_report_v2.list_schedules(db, project_id=project_id, enabled_only=enabled_only)


# ── Background helper ──────────────────────────────────────────────────────────

async def _render_and_store_formats(report_id: int, formats: List[str]) -> None:
    """
    Background task: render requested formats and store them (S3 or local).
    Runs after the HTTP response has been returned to the client.
    """
    import logging
    from app.core.config import settings
    from app.database import SessionLocal
    from app.models.finding import Finding, FindingStatus
    from app.services.report_generator import ReportGenerator

    log = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        report = crud_report_v2.get(db, report_id)
        if not report:
            log.error("Background render: report %s not found", report_id)
            return

        findings = (
            db.query(Finding)
            .filter(
                Finding.project_id == report.project_id,
                Finding.is_duplicate == False,  # noqa: E712
                Finding.status != FindingStatus.false_positive,
            )
            .all()
        )

        generator = ReportGenerator(db)
        version_data: dict = {"version_number": 1, "status": "published"}

        bucket = getattr(settings, "S3_REPORTS_BUCKET", None)

        for fmt in formats:
            try:
                if fmt == "pdf":
                    content = generator.render_pdf(report, findings)
                    ext = "pdf"
                elif fmt == "html":
                    content = generator.render_html(report, findings)
                    ext = "html"
                elif fmt == "excel":
                    content = generator.render_excel(report, findings)
                    ext = "excel"
                else:
                    continue

                if bucket:
                    from app.services.s3_storage import S3ReportStorage
                    storage = S3ReportStorage(bucket)
                    upload = storage.upload_report(report_id, content, ext, 1)
                    version_data[f"{ext}_file_key"] = upload["s3_key"]
                    version_data["file_size_bytes"] = upload["file_size_bytes"]
                    version_data["checksum_sha256"] = upload["checksum_sha256"]
                else:
                    # Local fallback: write to REPORTS_DIR
                    import os, hashlib
                    reports_dir = os.environ.get("REPORTS_DIR", "/tmp/reports")
                    os.makedirs(f"{reports_dir}/v2/{report_id}", exist_ok=True)
                    path = f"{reports_dir}/v2/{report_id}/report.{ext}"
                    with open(path, "wb") as fh:
                        fh.write(content)
                    version_data[f"{ext}_file_key"] = path
                    version_data["file_size_bytes"] = len(content)
                    version_data["checksum_sha256"] = hashlib.sha256(content).hexdigest()

            except Exception as exc:
                log.error("Error rendering format '%s' for report %s: %s", fmt, report_id, exc)

        crud_report_v2.create_version(db, report_id, version_data)
        log.info("Report %s: formats %s stored successfully.", report_id, formats)

    except Exception as exc:
        log.exception("Background render failed for report %s: %s", report_id, exc)
    finally:
        db.close()
