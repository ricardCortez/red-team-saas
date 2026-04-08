"""Phishing campaign endpoints"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.phishing import PhishingCampaign, PhishingCampaignStatus
from app.crud.phishing import crud_phishing
from app.schemas.phishing import (
    PhishingCampaignCreate,
    PhishingCampaignUpdate,
    PhishingCampaignResponse,
    PhishingCampaignListResponse,
    PhishingTargetCreate,
    PhishingTargetResponse,
    PhishingCampaignResults,
    PhishingTargetResult,
    GoPhishResourcesResponse,
    GoPhishTemplate,
    GoPhishPage,
    GoPhishSMTP,
    GoPhishGroup,
)
from app.core.audit import log_action

router = APIRouter()

_GOPHISH_DOCKER_URL = "https://gophish:3333"


def _normalize_gophish_url(url: str) -> str:
    """Replace localhost/127.0.0.1 GoPhish URLs with the Docker-internal service name.

    Campaigns created before the Docker fix have http://localhost:3333 stored.
    From inside the API container, only https://gophish:3333 is reachable.
    """
    if not url:
        return _GOPHISH_DOCKER_URL
    _localhost_variants = (
        "http://localhost:3333", "https://localhost:3333",
        "http://127.0.0.1:3333", "https://127.0.0.1:3333",
    )
    for variant in _localhost_variants:
        if url.startswith(variant):
            return _GOPHISH_DOCKER_URL
    return url


def _get_campaign_or_404(db: Session, campaign_id: int) -> PhishingCampaign:
    c = crud_phishing.get(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c


# ── Static routes MUST come before /{campaign_id} ─────────────────────────────

@router.post("/resources", response_model=GoPhishResourcesResponse)
async def get_gophish_resources(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """Proxy GoPhish server to return available templates, pages, SMTP profiles, groups."""
    from app.services.gophish_client import GoPhishClient, GoPhishError

    url = payload.get("gophish_url", "")
    key = payload.get("gophish_api_key", "")
    if not url or not key:
        raise HTTPException(status_code=400, detail="gophish_url and gophish_api_key are required")

    client = GoPhishClient(_normalize_gophish_url(url), key)
    try:
        raw_t, raw_p, raw_s, raw_g = await asyncio.gather(
            asyncio.to_thread(client.list_templates),
            asyncio.to_thread(client.list_pages),
            asyncio.to_thread(client.list_smtp_profiles),
            asyncio.to_thread(client.list_groups),
        )
        templates = [GoPhishTemplate(id=t["id"], name=t["name"]) for t in raw_t]
        pages = [GoPhishPage(id=p["id"], name=p["name"]) for p in raw_p]
        smtp = [GoPhishSMTP(id=s["id"], name=s["name"]) for s in raw_s]
        groups = [GoPhishGroup(id=g["id"], name=g["name"]) for g in raw_g]
    except GoPhishError as exc:
        raise HTTPException(status_code=502, detail=f"GoPhish error: {exc}")

    return GoPhishResourcesResponse(templates=templates, pages=pages, smtp_profiles=smtp, groups=groups)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=PhishingCampaignListResponse)
async def list_campaigns(
    project_id: Optional[int] = Query(None),
    campaign_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = crud_phishing.get_multi(
        db, project_id=project_id, status=campaign_status, skip=skip, limit=limit
    )
    result["items"] = [PhishingCampaignResponse.model_validate(i) for i in result["items"]]
    return result


@router.post("/", response_model=PhishingCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: PhishingCampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    data = payload.model_dump()
    data["created_by"] = current_user.id
    campaign = crud_phishing.create(db, data=data)
    await log_action(db, user_id=current_user.id, action="phishing.create", resource_id=campaign.id)
    return campaign


@router.get("/{campaign_id}", response_model=PhishingCampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_campaign_or_404(db, campaign_id)


@router.put("/{campaign_id}", response_model=PhishingCampaignResponse)
async def update_campaign(
    campaign_id: int,
    payload: PhishingCampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    campaign = _get_campaign_or_404(db, campaign_id)
    if campaign.status == PhishingCampaignStatus.active:
        raise HTTPException(status_code=400, detail="Cannot edit an active campaign")
    data = payload.model_dump(exclude_unset=True)
    return crud_phishing.update(db, obj=campaign, data=data)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    campaign = _get_campaign_or_404(db, campaign_id)
    if campaign.status == PhishingCampaignStatus.active:
        raise HTTPException(status_code=400, detail="Stop the campaign before deleting")
    crud_phishing.delete(db, obj=campaign)
    await log_action(db, user_id=current_user.id, action="phishing.delete", resource_id=campaign_id)


# ── Targets ───────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/targets", response_model=List[PhishingTargetResponse], status_code=status.HTTP_201_CREATED)
async def add_targets(
    campaign_id: int,
    targets: List[PhishingTargetCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    _get_campaign_or_404(db, campaign_id)
    objs = crud_phishing.add_targets(db, campaign_id=campaign_id, targets=[t.model_dump() for t in targets])
    return [PhishingTargetResponse.model_validate(o) for o in objs]


@router.get("/{campaign_id}/targets", response_model=List[PhishingTargetResponse])
async def list_targets(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_campaign_or_404(db, campaign_id)
    return [PhishingTargetResponse.model_validate(t) for t in crud_phishing.list_targets(db, campaign_id=campaign_id)]


@router.delete("/{campaign_id}/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    campaign_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    _get_campaign_or_404(db, campaign_id)
    deleted = crud_phishing.delete_target(db, target_id=target_id, campaign_id=campaign_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Target not found")


# ── Launch / Stop ─────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/launch", response_model=PhishingCampaignResponse)
async def launch_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    """Create and start the campaign on GoPhish, then mark it as active."""
    from app.services.gophish_client import GoPhishClient, GoPhishError
    from datetime import datetime, timezone

    campaign = _get_campaign_or_404(db, campaign_id)
    if campaign.status != PhishingCampaignStatus.draft:
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign.status}")

    targets = crud_phishing.list_targets(db, campaign_id=campaign_id)
    if not targets:
        raise HTTPException(status_code=400, detail="Add at least one target before launching")

    client = GoPhishClient(_normalize_gophish_url(campaign.gophish_url), campaign.gophish_api_key)
    payload = {
        "name": campaign.name,
        "template": {"name": campaign.template_name or ""},
        "page": {"name": campaign.landing_page_name or ""},
        "smtp": {"name": campaign.smtp_profile_name or ""},
        "url": campaign.phishing_url or "",
        "launch_date": campaign.launch_date.isoformat() if campaign.launch_date else datetime.now(timezone.utc).isoformat(),
        "groups": [{"name": campaign.target_group_name or campaign.name}],
    }

    try:
        gp_campaign = await asyncio.to_thread(client.create_campaign, payload)
    except GoPhishError as exc:
        raise HTTPException(status_code=502, detail=f"GoPhish error: {exc}")

    updated = crud_phishing.update(db, obj=campaign, data={
        "gophish_campaign_id": gp_campaign.get("id"),
        "status": PhishingCampaignStatus.active,
    })
    await log_action(db, user_id=current_user.id, action="phishing.launch", resource_id=campaign_id)
    return updated


@router.post("/{campaign_id}/stop", response_model=PhishingCampaignResponse)
async def stop_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    """Mark the GoPhish campaign as complete and set status to completed."""
    from app.services.gophish_client import GoPhishClient, GoPhishError

    campaign = _get_campaign_or_404(db, campaign_id)
    if campaign.status != PhishingCampaignStatus.active:
        raise HTTPException(status_code=400, detail="Campaign is not active")

    if campaign.gophish_campaign_id:
        client = GoPhishClient(_normalize_gophish_url(campaign.gophish_url), campaign.gophish_api_key)
        try:
            await asyncio.to_thread(client.complete_campaign, campaign.gophish_campaign_id)
        except GoPhishError:
            pass  # Log but don't fail — still mark locally as completed

    updated = crud_phishing.update(db, obj=campaign, data={"status": PhishingCampaignStatus.completed})
    await log_action(db, user_id=current_user.id, action="phishing.stop", resource_id=campaign_id)
    return updated


# ── Results & Sync ────────────────────────────────────────────────────────────

@router.get("/{campaign_id}/results", response_model=PhishingCampaignResults)
async def get_results(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch per-target results directly from GoPhish."""
    from app.services.gophish_client import GoPhishClient, GoPhishError

    campaign = _get_campaign_or_404(db, campaign_id)
    if not campaign.gophish_campaign_id:
        return PhishingCampaignResults(campaign_id=campaign_id, results=[], stats={})

    client = GoPhishClient(_normalize_gophish_url(campaign.gophish_url), campaign.gophish_api_key)
    try:
        data = await asyncio.to_thread(client.get_campaign_results, campaign.gophish_campaign_id)
    except GoPhishError as exc:
        raise HTTPException(status_code=502, detail=f"GoPhish error: {exc}")

    results = [
        PhishingTargetResult(
            email=r.get("email", ""),
            status=r.get("status", ""),
            ip=r.get("ip"),
            latitude=r.get("latitude"),
            longitude=r.get("longitude"),
            reported=r.get("reported", False),
        )
        for r in data.get("results", [])
    ]
    return PhishingCampaignResults(
        campaign_id=campaign_id,
        gophish_campaign_id=campaign.gophish_campaign_id,
        results=results,
        stats=data.get("stats", {}),
    )


@router.post("/{campaign_id}/sync", response_model=PhishingCampaignResponse)
async def sync_stats(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enqueue a stats sync from GoPhish. Returns current state immediately."""
    campaign = _get_campaign_or_404(db, campaign_id)
    try:
        from app.tasks.phishing_tasks import sync_campaign_stats
        sync_campaign_stats.apply_async(args=[campaign_id], queue="default")
    except Exception:
        pass
    return campaign
