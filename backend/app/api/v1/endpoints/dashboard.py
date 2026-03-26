"""Dashboard & analytics endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog
from app.core.analytics.metrics import MetricsEngine
from app.core.analytics.trends import TrendsEngine
from app.core.analytics.cache import invalidate_cache
from app.schemas.analytics import (
    GlobalSummary,
    ProjectSummary,
    TopTarget,
    TopTool,
    HeatmapRow,
    TrendPoint,
    RiskTrendPoint,
    ActivityPoint,
    ActivityFeedItem,
)

router = APIRouter()


# ── Global ────────────────────────────────────────────────────────────────────

@router.get("/dashboard/summary", response_model=GlobalSummary)
def global_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MetricsEngine.global_summary(db, current_user.id)


@router.get("/dashboard/top-targets", response_model=List[TopTarget])
def top_targets(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MetricsEngine.top_targets(db, current_user.id, limit=limit)


@router.get("/dashboard/top-tools", response_model=List[TopTool])
def top_tools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MetricsEngine.top_tools(db, current_user.id)


@router.get("/dashboard/activity-feed", response_model=List[ActivityFeedItem])
def activity_feed(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )


# ── Trends ────────────────────────────────────────────────────────────────────

@router.get("/dashboard/trends/findings", response_model=List[TrendPoint])
def findings_trend(
    days: int = Query(30, ge=7, le=90),
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return TrendsEngine.findings_over_time(db, current_user.id, days=days, project_id=project_id)


@router.get("/dashboard/trends/risk", response_model=List[RiskTrendPoint])
def risk_trend(
    days: int = Query(30, ge=7, le=90),
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return TrendsEngine.risk_score_trend(db, current_user.id, days=days, project_id=project_id)


@router.get("/dashboard/trends/activity", response_model=List[ActivityPoint])
def scan_activity(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return TrendsEngine.scan_activity(db, current_user.id, days=days)


# ── Per-project ────────────────────────────────────────────────────────────────

@router.get("/dashboard/projects/{project_id}/summary", response_model=ProjectSummary)
def project_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MetricsEngine.project_summary(db, project_id)


@router.get("/dashboard/projects/{project_id}/heatmap", response_model=List[HeatmapRow])
def severity_heatmap(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MetricsEngine.severity_heatmap(db, project_id)


# ── Cache management ──────────────────────────────────────────────────────────

@router.post("/dashboard/cache/invalidate", status_code=204)
def invalidate_analytics_cache(
    current_user: User = Depends(get_current_user),
):
    """Force-refresh the analytics cache (useful after a bulk scan)."""
    invalidate_cache("analytics")
    invalidate_cache("trends")
