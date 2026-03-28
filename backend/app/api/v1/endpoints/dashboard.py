"""Dashboard & analytics endpoints — Phase 7 + Phase 15."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog
from app.core.analytics.metrics import MetricsEngine
from app.core.analytics.trends import TrendsEngine
from app.core.analytics.cache import invalidate_cache
from app.schemas.analytics import (
    # Phase 7 schemas
    GlobalSummary,
    ProjectSummary,
    TopTarget,
    TopTool,
    HeatmapRow,
    TrendPoint,
    RiskTrendPoint,
    ActivityPoint,
    ActivityFeedItem,
    # Phase 15 schemas
    KPIResponse,
    ProjectRiskScoreResponse,
    ToolAnalyticsResponse,
    DashboardConfigCreate,
    DashboardConfigResponse,
    AnalyticsSnapshotResponse,
    BenchmarkResponse,
    FullDashboardResponse,
)

router = APIRouter()


# ── Global ────────────────────────────────────────────────────────────────────

@router.get("/dashboard/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregated stats for the frontend dashboard."""
    from app.models.scan import Scan
    from app.models.finding import Finding
    from app.models.project import Project

    total_projects = db.query(Project).count()
    total_scans = db.query(Scan).count()
    active_scans = db.query(Scan).filter(Scan.status == "running").count()
    total_findings = db.query(Finding).count()

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for sev in severity_counts:
        severity_counts[sev] = db.query(Finding).filter(Finding.severity == sev).count()

    recent_scans = db.query(Scan).order_by(Scan.created_at.desc()).limit(5).all()
    recent_findings = db.query(Finding).order_by(Finding.created_at.desc()).limit(5).all()

    return {
        "total_projects": total_projects,
        "total_scans": total_scans,
        "total_findings": total_findings,
        "active_scans": active_scans,
        "findings_by_severity": severity_counts,
        "recent_scans": [
            {"id": s.id, "name": s.name, "scan_type": s.scan_type.value if hasattr(s.scan_type, "value") else s.scan_type, "status": s.status.value if hasattr(s.status, "value") else s.status, "progress": s.progress or 0, "created_at": str(s.created_at)}
            for s in recent_scans
        ],
        "recent_findings": [
            {"id": f.id, "title": f.title, "severity": f.severity.value if hasattr(f.severity, "value") else f.severity, "status": f.status, "created_at": str(f.created_at)}
            for f in recent_findings
        ],
        "compliance_score": 0,
    }


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


# ══════════════════════════════════════════════════════════════════════════════
# Phase 15 — KPIs, Risk Scores, Tool Analytics, Snapshots, Benchmarking
# ══════════════════════════════════════════════════════════════════════════════

def _get_realtime():
    from app.services.realtime_metrics import RealtimeMetricsService
    return RealtimeMetricsService()


# ── Real-time metrics ──────────────────────────────────────────────────────────

@router.get("/analytics/{project_id}/metrics", tags=["Analytics Phase 15"])
def get_realtime_metrics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """Return live Redis counters for a project (Phase 15)."""
    rt = _get_realtime()
    return {
        "project_id": project_id,
        "timestamp":  datetime.utcnow().isoformat(),
        "metrics":    rt.get_current_metrics(str(project_id)),
    }


# ── KPIs ───────────────────────────────────────────────────────────────────────

@router.get("/analytics/{project_id}/kpis", response_model=List[KPIResponse], tags=["Analytics Phase 15"])
def get_kpis(
    project_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Latest KPI records for a project (Phase 15)."""
    from app.crud.analytics import crud_analytics
    return crud_analytics.get_kpis(db, project_id, limit=limit)


@router.get("/analytics/{project_id}/kpis/{kpi_type}", response_model=KPIResponse, tags=["Analytics Phase 15"])
def get_kpi_by_type(
    project_id: int,
    kpi_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch a specific KPI (Phase 15)."""
    from app.crud.analytics import crud_analytics
    kpi = crud_analytics.get_kpi_by_type(db, project_id, kpi_type)
    if not kpi:
        raise HTTPException(status_code=404, detail=f"KPI '{kpi_type}' not found for this project")
    return kpi


@router.post("/analytics/{project_id}/kpis/calculate", response_model=List[KPIResponse], tags=["Analytics Phase 15"])
def calculate_kpis(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger on-demand KPI calculation (Phase 15)."""
    from app.services.analytics_engine import AnalyticsEngine
    engine = AnalyticsEngine(db, _get_realtime())
    return engine.calculate_all_kpis(project_id)


# ── Risk Score ─────────────────────────────────────────────────────────────────

@router.get("/analytics/{project_id}/risk-score", response_model=ProjectRiskScoreResponse, tags=["Analytics Phase 15"])
def get_risk_score(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Latest project risk score (Phase 15). Calculates on-demand if absent."""
    from app.crud.analytics import crud_analytics
    from app.services.analytics_engine import AnalyticsEngine

    rs = crud_analytics.get_latest_risk_score(db, project_id)
    if not rs:
        rs = AnalyticsEngine(db, _get_realtime()).calculate_risk_score(project_id)
    return rs


@router.get("/analytics/{project_id}/risk-score/history", response_model=List[ProjectRiskScoreResponse], tags=["Analytics Phase 15"])
def get_risk_score_history(
    project_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historical risk score trend (Phase 15)."""
    from app.crud.analytics import crud_analytics
    return crud_analytics.get_risk_score_history(db, project_id, days=days)


# ── Tool Analytics ─────────────────────────────────────────────────────────────

@router.get("/analytics/{project_id}/tools", response_model=List[ToolAnalyticsResponse], tags=["Analytics Phase 15"])
def get_tool_analytics(
    project_id: int,
    tool_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tool effectiveness analytics (Phase 15)."""
    from app.crud.analytics import crud_analytics
    return crud_analytics.get_tool_analytics(db, project_id, tool_name=tool_name)


@router.post("/analytics/{project_id}/tools/compute", response_model=List[ToolAnalyticsResponse], tags=["Analytics Phase 15"])
def compute_tool_analytics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recompute tool analytics for all tools in a project (Phase 15)."""
    from app.services.analytics_engine import AnalyticsEngine
    return AnalyticsEngine(db, _get_realtime()).compute_tool_analytics(project_id)


# ── Full Dashboard ─────────────────────────────────────────────────────────────

@router.get("/analytics/{project_id}/dashboard", response_model=FullDashboardResponse, tags=["Analytics Phase 15"])
def full_dashboard(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Combined Phase 15 dashboard: real-time metrics + KPIs + risk + tools."""
    from app.crud.analytics import crud_analytics

    rt = _get_realtime()
    return FullDashboardResponse(
        project_id       = project_id,
        timestamp        = datetime.utcnow(),
        realtime_metrics = rt.get_current_metrics(str(project_id)),
        kpis             = crud_analytics.get_kpis(db, project_id, limit=10),
        risk_score       = crud_analytics.get_latest_risk_score(db, project_id),
        tool_analytics   = crud_analytics.get_tool_analytics(db, project_id),
    )


# ── Snapshots ──────────────────────────────────────────────────────────────────

@router.get("/analytics/{project_id}/snapshots", response_model=List[AnalyticsSnapshotResponse], tags=["Analytics Phase 15"])
def get_snapshots(
    project_id: int,
    days: int = Query(30, ge=1, le=365),
    snapshot_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historical analytics snapshots (Phase 15)."""
    from app.crud.analytics import crud_analytics
    return crud_analytics.get_snapshots(db, project_id, snapshot_type=snapshot_type, days=days)


@router.post("/analytics/{project_id}/snapshots", response_model=AnalyticsSnapshotResponse, status_code=status.HTTP_201_CREATED, tags=["Analytics Phase 15"])
def create_snapshot(
    project_id: int,
    snapshot_type: str = Query("daily"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger an analytics snapshot (Phase 15)."""
    from app.services.analytics_engine import AnalyticsEngine
    return AnalyticsEngine(db, _get_realtime()).create_analytics_snapshot(project_id, snapshot_type)


# ── Benchmarking ───────────────────────────────────────────────────────────────

@router.get("/analytics/benchmarks/{metric_name}", response_model=BenchmarkResponse, tags=["Analytics Phase 15"])
def get_benchmark(
    metric_name: str,
    industry: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Industry benchmark values for a given metric (Phase 15)."""
    from app.crud.analytics import crud_analytics
    bm = crud_analytics.get_benchmark(db, metric_name, industry=industry)
    if not bm:
        raise HTTPException(status_code=404, detail=f"Benchmark '{metric_name}' not found")
    return bm


# ── Dashboard Config ───────────────────────────────────────────────────────────

@router.post("/analytics/dashboard-configs", response_model=DashboardConfigResponse, status_code=status.HTTP_201_CREATED, tags=["Analytics Phase 15"])
def create_dashboard_config(
    payload: DashboardConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a custom dashboard widget configuration (Phase 15)."""
    from app.crud.analytics import crud_analytics
    data = payload.model_dump()
    data["user_id"] = current_user.id
    return crud_analytics.create_dashboard_config(db, data)


@router.get("/analytics/dashboard-configs", response_model=List[DashboardConfigResponse], tags=["Analytics Phase 15"])
def list_dashboard_configs(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List saved dashboard configs for the current user (Phase 15)."""
    from app.crud.analytics import crud_analytics
    return crud_analytics.get_user_dashboards(db, current_user.id, project_id=project_id)


@router.delete("/analytics/dashboard-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Analytics Phase 15"])
def delete_dashboard_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a dashboard config (Phase 15)."""
    from app.crud.analytics import crud_analytics
    if not crud_analytics.delete_dashboard_config(db, config_id):
        raise HTTPException(status_code=404, detail="Config not found")
