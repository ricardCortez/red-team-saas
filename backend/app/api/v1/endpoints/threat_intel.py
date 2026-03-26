"""Threat Intelligence API endpoints - Phase 12"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.cve import CVE
from app.models.mitre_technique import MitreTechnique
from app.models.ioc import IOC, IOCType, IOCThreatLevel
from app.core.threat_intel.enricher import FindingEnricher
from app.core.threat_intel.correlator import ThreatCorrelator

router = APIRouter()


# ── CVE ───────────────────────────────────────────────────────────────────────

@router.get("/threat-intel/cve/{cve_id}")
def get_cve(
    cve_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get CVE details (from local cache or NVD)."""
    enricher = FindingEnricher(db)
    cve = enricher._get_or_fetch_cve(cve_id.upper())
    if not cve:
        raise HTTPException(404, f"CVE {cve_id} not found")
    return cve


@router.get("/threat-intel/cve")
def search_cves(
    keyword: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search CVEs by keyword."""
    local = db.query(CVE).filter(
        CVE.description.ilike(f"%{keyword}%")
    ).limit(limit).all()
    if local:
        return local

    from app.core.threat_intel.nvd_client import NVDClient
    from app.core.config import settings
    client = NVDClient(api_key=getattr(settings, "NVD_API_KEY", None))
    return client.search_by_keyword(keyword, limit=limit)


# ── MITRE ─────────────────────────────────────────────────────────────────────

@router.get("/threat-intel/mitre/techniques")
def list_techniques(
    tactic: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List MITRE ATT&CK techniques with optional filters."""
    q = db.query(MitreTechnique)
    if tactic:
        q = q.filter(MitreTechnique.tactic == tactic)
    if search:
        q = q.filter(MitreTechnique.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.get("/threat-intel/mitre/{technique_id}")
def get_technique(
    technique_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get technique details with related CVEs."""
    tech = db.query(MitreTechnique).filter(
        MitreTechnique.technique_id == technique_id.upper()
    ).first()
    if not tech:
        raise HTTPException(404, f"Technique {technique_id} not found")
    correlator = ThreatCorrelator(db)
    return {
        "technique_id":  tech.technique_id,
        "name":          tech.name,
        "tactic":        tech.tactic,
        "tactic_name":   tech.tactic_name,
        "description":   tech.description,
        "is_subtechnique": tech.is_subtechnique,
        "parent_id":     tech.parent_id,
        "platforms":     tech.platforms,
        "detection":     tech.detection,
        "url":           tech.url,
        "related_cves":  correlator.mitre_to_cves(technique_id.upper()),
    }


# ── IOC ───────────────────────────────────────────────────────────────────────

@router.get("/threat-intel/ioc/check")
def check_ioc(
    value: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if a value is a known IOC."""
    correlator = ThreatCorrelator(db)
    result = correlator.check_ioc(value)
    return {"value": value, "is_ioc": bool(result), "intel": result}


@router.get("/threat-intel/ioc")
def list_iocs(
    ioc_type: Optional[str] = Query(None),
    threat_level: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active IOCs with optional filters."""
    q = db.query(IOC).filter(IOC.is_active == True)  # noqa: E712
    if ioc_type:
        try:
            q = q.filter(IOC.ioc_type == IOCType(ioc_type))
        except ValueError:
            raise HTTPException(400, f"Invalid ioc_type: {ioc_type}")
    if threat_level:
        try:
            q = q.filter(IOC.threat_level == IOCThreatLevel(threat_level))
        except ValueError:
            raise HTTPException(400, f"Invalid threat_level: {threat_level}")
    if source:
        q = q.filter(IOC.source == source)
    total = q.count()
    items = q.order_by(IOC.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.post("/threat-intel/ioc")
def add_custom_ioc(
    value: str = Query(...),
    ioc_type: str = Query(...),
    threat_level: str = Query("medium"),
    description: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a custom IOC manually."""
    try:
        ioc_type_enum = IOCType(ioc_type)
    except ValueError:
        raise HTTPException(400, f"Invalid ioc_type: {ioc_type}")
    try:
        threat_level_enum = IOCThreatLevel(threat_level)
    except ValueError:
        raise HTTPException(400, f"Invalid threat_level: {threat_level}")

    ioc = IOC(
        value=value,
        ioc_type=ioc_type_enum,
        threat_level=threat_level_enum,
        source="custom",
        description=description,
        confidence=1.0,
        tags=[],
    )
    db.add(ioc)
    db.commit()
    db.refresh(ioc)
    return ioc


# ── Enrichment ────────────────────────────────────────────────────────────────

@router.post("/threat-intel/enrich/finding/{finding_id}")
def enrich_finding_endpoint(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Queue manual enrichment of a finding."""
    from app.tasks.threat_intel_tasks import enrich_finding_task
    job = enrich_finding_task.apply_async(args=[finding_id], queue="threat_intel")
    return {"finding_id": finding_id, "task_id": job.id, "status": "queued"}


@router.get("/threat-intel/project/{project_id}/profile")
def project_threat_profile(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full threat profile for a project."""
    correlator = ThreatCorrelator(db)
    return correlator.project_threat_profile(project_id)


# ── Manual sync (admin only) ──────────────────────────────────────────────────

@router.post("/threat-intel/sync/mitre", status_code=202)
def trigger_mitre_sync(current_user: User = Depends(get_current_user)):
    """Trigger MITRE ATT&CK sync (admin only)."""
    if not current_user.is_superuser and (
        not hasattr(current_user.role, "value")
        or current_user.role.value != "admin"
    ):
        raise HTTPException(403, "Admin only")
    from app.tasks.threat_intel_tasks import sync_mitre_techniques
    job = sync_mitre_techniques.apply_async(queue="threat_intel")
    return {"task_id": job.id, "status": "queued"}


@router.post("/threat-intel/sync/iocs", status_code=202)
def trigger_ioc_sync(current_user: User = Depends(get_current_user)):
    """Trigger IOC feeds sync (admin only)."""
    if not current_user.is_superuser and (
        not hasattr(current_user.role, "value")
        or current_user.role.value != "admin"
    ):
        raise HTTPException(403, "Admin only")
    from app.tasks.threat_intel_tasks import sync_ioc_feeds
    job = sync_ioc_feeds.apply_async(queue="threat_intel")
    return {"task_id": job.id, "status": "queued"}
