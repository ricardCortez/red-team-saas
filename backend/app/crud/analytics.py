"""CRUD operations for Phase 15 Analytics models."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analytics import (
    AnalyticsSnapshot,
    BenchmarkData,
    DashboardConfig,
    KPI,
    KPITypeEnum,
    ProjectRiskScore,
    ToolAnalytics,
)


class AnalyticsCRUD:
    """Static CRUD helper for Phase 15 analytics models."""

    # ── KPI ───────────────────────────────────────────────────────────────────

    @staticmethod
    def get_kpis(
        db: Session,
        project_id: int,
        limit: int = 20,
    ) -> List[KPI]:
        return (
            db.query(KPI)
            .filter(KPI.project_id == project_id)
            .order_by(KPI.calculated_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_kpi_by_type(
        db: Session, project_id: int, kpi_type: str
    ) -> Optional[KPI]:
        return (
            db.query(KPI)
            .filter(
                KPI.project_id == project_id,
                KPI.kpi_type   == kpi_type,
            )
            .order_by(KPI.calculated_at.desc())
            .first()
        )

    @staticmethod
    def get_kpi_history(
        db: Session,
        project_id: int,
        kpi_type: str,
        days: int = 30,
    ) -> List[KPI]:
        since = datetime.utcnow() - timedelta(days=days)
        return (
            db.query(KPI)
            .filter(
                KPI.project_id   == project_id,
                KPI.kpi_type     == kpi_type,
                KPI.calculated_at >= since,
            )
            .order_by(KPI.calculated_at.asc())
            .all()
        )

    # ── ProjectRiskScore ──────────────────────────────────────────────────────

    @staticmethod
    def get_latest_risk_score(
        db: Session, project_id: int
    ) -> Optional[ProjectRiskScore]:
        return (
            db.query(ProjectRiskScore)
            .filter(ProjectRiskScore.project_id == project_id)
            .order_by(ProjectRiskScore.calculated_at.desc())
            .first()
        )

    @staticmethod
    def get_risk_score_history(
        db: Session, project_id: int, days: int = 30
    ) -> List[ProjectRiskScore]:
        since = datetime.utcnow() - timedelta(days=days)
        return (
            db.query(ProjectRiskScore)
            .filter(
                ProjectRiskScore.project_id   == project_id,
                ProjectRiskScore.calculated_at >= since,
            )
            .order_by(ProjectRiskScore.calculated_at.asc())
            .all()
        )

    # ── ToolAnalytics ─────────────────────────────────────────────────────────

    @staticmethod
    def get_tool_analytics(
        db: Session,
        project_id: int,
        tool_name: Optional[str] = None,
    ) -> List[ToolAnalytics]:
        q = db.query(ToolAnalytics).filter(ToolAnalytics.project_id == project_id)
        if tool_name:
            q = q.filter(ToolAnalytics.tool_name == tool_name)
        return q.order_by(ToolAnalytics.effectiveness_score.desc()).all()

    # ── AnalyticsSnapshot ─────────────────────────────────────────────────────

    @staticmethod
    def get_snapshots(
        db: Session,
        project_id: int,
        snapshot_type: Optional[str] = None,
        days: int = 30,
    ) -> List[AnalyticsSnapshot]:
        since = datetime.utcnow() - timedelta(days=days)
        q = db.query(AnalyticsSnapshot).filter(
            AnalyticsSnapshot.project_id    == project_id,
            AnalyticsSnapshot.snapshot_date >= since,
        )
        if snapshot_type:
            q = q.filter(AnalyticsSnapshot.snapshot_type == snapshot_type)
        return q.order_by(AnalyticsSnapshot.snapshot_date.desc()).all()

    # ── DashboardConfig ───────────────────────────────────────────────────────

    @staticmethod
    def create_dashboard_config(
        db: Session, config_data: Dict
    ) -> DashboardConfig:
        cfg = DashboardConfig(**config_data)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
        return cfg

    @staticmethod
    def get_user_dashboards(
        db: Session, user_id: int, project_id: Optional[int] = None
    ) -> List[DashboardConfig]:
        q = db.query(DashboardConfig).filter(DashboardConfig.user_id == user_id)
        if project_id:
            q = q.filter(DashboardConfig.project_id == project_id)
        return q.all()

    @staticmethod
    def get_dashboard_config(
        db: Session, config_id: int
    ) -> Optional[DashboardConfig]:
        return db.query(DashboardConfig).filter(DashboardConfig.id == config_id).first()

    @staticmethod
    def delete_dashboard_config(db: Session, config_id: int) -> bool:
        cfg = db.query(DashboardConfig).filter(DashboardConfig.id == config_id).first()
        if not cfg:
            return False
        db.delete(cfg)
        db.commit()
        return True

    # ── BenchmarkData ─────────────────────────────────────────────────────────

    @staticmethod
    def get_benchmark(
        db: Session,
        metric_name: str,
        industry: Optional[str] = None,
    ) -> Optional[BenchmarkData]:
        q = db.query(BenchmarkData).filter(BenchmarkData.metric_name == metric_name)
        if industry:
            q = q.filter(BenchmarkData.industry == industry)
        return q.first()

    @staticmethod
    def upsert_benchmark(db: Session, data: Dict) -> BenchmarkData:
        existing = db.query(BenchmarkData).filter(
            BenchmarkData.metric_name == data["metric_name"],
            BenchmarkData.industry    == data.get("industry"),
        ).first()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing
        bm = BenchmarkData(**data)
        db.add(bm)
        db.commit()
        db.refresh(bm)
        return bm

    # ── Aggregate helpers ─────────────────────────────────────────────────────

    @staticmethod
    def get_project_digest(
        db: Session, project_id: int
    ) -> Dict:
        """Return a compact digest dict for email/report generation."""
        latest_risk = AnalyticsCRUD.get_latest_risk_score(db, project_id)
        kpis = AnalyticsCRUD.get_kpis(db, project_id, limit=5)
        tools = AnalyticsCRUD.get_tool_analytics(db, project_id)
        snapshots = AnalyticsCRUD.get_snapshots(db, project_id, days=7)

        return {
            "risk_score":   latest_risk,
            "kpis":         kpis,
            "top_tools":    tools[:5],
            "weekly_snapshots": snapshots,
        }


crud_analytics = AnalyticsCRUD()
