"""Compliance Engine API endpoints - Phase 13"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.crud.compliance import ComplianceCRUD
from app.models.compliance import (
    ComplianceFramework,
    ComplianceMappingResult,
    ComplianceControlMatrix,
)
from app.models.finding import Finding
from app.models.project import Project
from app.models.user import User
from app.schemas.compliance import (
    ComplianceAssessmentRequest,
    ComplianceControlCreate,
    ComplianceControlResponse,
    ComplianceEvidenceResponse,
    ComplianceFrameworkCreate,
    ComplianceFrameworkResponse,
    ComplianceMappingResponse,
)
from app.services.compliance_mapper import ComplianceMapper

router = APIRouter()


# ── Helper ─────────────────────────────────────────────────────────────────────

def _get_project_or_403(db: Session, project_id: int, current_user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, f"Project {project_id} not found")
    if project.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(403, "Access denied")
    return project


def _is_admin_or_superuser(user: User) -> bool:
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    return user.is_superuser or role_val == "admin"


# ── Frameworks ─────────────────────────────────────────────────────────────────

@router.get("/compliance/frameworks", response_model=List[ComplianceFrameworkResponse])
def list_frameworks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all available compliance frameworks."""
    return ComplianceCRUD.list_frameworks(db, skip=skip, limit=limit)


@router.get("/compliance/frameworks/{framework_type}", response_model=ComplianceFrameworkResponse)
def get_framework(
    framework_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific framework."""
    fw = ComplianceCRUD.get_framework_by_type(db, framework_type)
    if not fw:
        raise HTTPException(404, f"Framework '{framework_type}' not found")
    return fw


@router.post("/compliance/frameworks", response_model=ComplianceFrameworkResponse, status_code=201)
def create_framework(
    body: ComplianceFrameworkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new framework definition (admin only)."""
    if not _is_admin_or_superuser(current_user):
        raise HTTPException(403, "Admin only")
    existing = ComplianceCRUD.get_framework_by_type(db, body.framework_type)
    if existing:
        raise HTTPException(409, f"Framework '{body.framework_type}' already exists")
    return ComplianceCRUD.create_framework(db, body)


# ── Assessment ─────────────────────────────────────────────────────────────────

@router.post("/compliance/assess/{project_id}", response_model=ComplianceMappingResponse)
def assess_project_compliance(
    project_id: int,
    body: ComplianceAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run compliance assessment for a project against a framework."""
    _get_project_or_403(db, project_id, current_user)

    findings = db.query(Finding).filter(Finding.project_id == project_id).all()

    mapper = ComplianceMapper(db)
    try:
        result = mapper.assess_project(
            project_id     = project_id,
            framework_type = body.framework_type,
            findings       = findings,
            assessment_period = body.assessment_period,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return result


@router.post("/compliance/assess/{project_id}/async", status_code=202)
def assess_project_async(
    project_id: int,
    body: ComplianceAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Queue async compliance assessment (returns task_id)."""
    _get_project_or_403(db, project_id, current_user)
    from app.tasks.compliance_tasks import assess_project_compliance_task
    job = assess_project_compliance_task.apply_async(
        args=[project_id, body.framework_type],
        queue="compliance",
    )
    return {"project_id": project_id, "task_id": job.id, "status": "queued"}


@router.get("/compliance/assessments/{project_id}", response_model=List[ComplianceMappingResponse])
def get_project_assessments(
    project_id: int,
    framework_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get assessment history for a project."""
    _get_project_or_403(db, project_id, current_user)
    mappings = ComplianceCRUD.get_latest_mappings(db, project_id, limit=limit)
    if framework_type:
        mappings = [
            m for m in mappings
            if (m.framework.framework_type.value
                if hasattr(m.framework.framework_type, "value")
                else m.framework.framework_type) == framework_type
        ]
    return mappings


@router.get("/compliance/mapping/{mapping_id}", response_model=ComplianceMappingResponse)
def get_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific mapping result."""
    mapping = ComplianceCRUD.get_mapping_by_id(db, mapping_id)
    if not mapping:
        raise HTTPException(404, "Mapping not found")
    _get_project_or_403(db, mapping.project_id, current_user)
    return mapping


# ── Evidence ───────────────────────────────────────────────────────────────────

@router.get("/compliance/evidence/{mapping_id}", response_model=List[ComplianceEvidenceResponse])
def get_mapping_evidence(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all evidence logs for an assessment."""
    mapping = ComplianceCRUD.get_mapping_by_id(db, mapping_id)
    if not mapping:
        raise HTTPException(404, "Mapping not found")
    _get_project_or_403(db, mapping.project_id, current_user)
    return ComplianceCRUD.get_evidence_by_mapping(db, mapping_id)


@router.patch("/compliance/evidence/{evidence_id}/status", response_model=ComplianceEvidenceResponse)
def update_evidence_status(
    evidence_id: int,
    status: str = Query(...),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update evidence status (admin/superuser only)."""
    if not _is_admin_or_superuser(current_user):
        raise HTTPException(403, "Requires admin privileges")
    updated = ComplianceCRUD.update_evidence_status(
        db, evidence_id, status, notes, reviewed_by=current_user.id
    )
    if not updated:
        raise HTTPException(404, "Evidence not found")
    return updated


# ── Control Matrix ─────────────────────────────────────────────────────────────

@router.get("/compliance/controls/{project_id}", response_model=List[ComplianceControlResponse])
def get_project_controls(
    project_id: int,
    framework_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get control matrix for a project."""
    _get_project_or_403(db, project_id, current_user)
    framework_id = None
    if framework_type:
        fw = ComplianceCRUD.get_framework_by_type(db, framework_type)
        framework_id = fw.id if fw else None
    return ComplianceCRUD.get_controls_by_project(db, project_id, framework_id)


@router.post("/compliance/controls/{project_id}", response_model=ComplianceControlResponse, status_code=201)
def create_project_control(
    project_id: int,
    framework_type: str = Query(...),
    body: ComplianceControlCreate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new control in the control matrix."""
    _get_project_or_403(db, project_id, current_user)
    fw = ComplianceCRUD.get_framework_by_type(db, framework_type)
    if not fw:
        raise HTTPException(400, f"Framework '{framework_type}' not found")
    return ComplianceCRUD.create_control(db, project_id, fw.id, body)


@router.patch("/compliance/controls/{control_id}/test-result", response_model=ComplianceControlResponse)
def add_control_test_result(
    control_id: int,
    result: str = Query(..., description="PASS or FAIL"),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a test result for a control."""
    if not _is_admin_or_superuser(current_user):
        raise HTTPException(403, "Admin only")
    updated = ComplianceCRUD.update_control_test_result(
        db, control_id, {"result": result, "notes": notes, "tester": current_user.username}
    )
    if not updated:
        raise HTTPException(404, "Control not found")
    return updated


# ── Report (stub — Phase 14 will expand) ──────────────────────────────────────

@router.get("/compliance/report/{mapping_id}")
def get_compliance_report(
    mapping_id: int,
    format: str = Query("json", pattern="^(json|pdf|html)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate compliance report (PDF/HTML export — Phase 14)."""
    mapping = ComplianceCRUD.get_mapping_by_id(db, mapping_id)
    if not mapping:
        raise HTTPException(404, "Mapping not found")
    _get_project_or_403(db, mapping.project_id, current_user)
    return {
        "report_id": mapping_id,
        "format":    format,
        "status":    "generation_queued",
        "score":     mapping.compliance_score,
        "compliance_status": mapping.compliance_status.value
        if hasattr(mapping.compliance_status, "value")
        else mapping.compliance_status,
    }


# ── Seed endpoint (admin only) ─────────────────────────────────────────────────

@router.post("/compliance/seed", status_code=201)
def seed_frameworks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed built-in compliance frameworks (admin only)."""
    if not _is_admin_or_superuser(current_user):
        raise HTTPException(403, "Admin only")
    from app.seeds.compliance_frameworks import seed_compliance_frameworks
    created = seed_compliance_frameworks(db)
    return {"created": created}
