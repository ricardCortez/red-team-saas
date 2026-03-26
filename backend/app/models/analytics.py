"""Analytics models — Phase 15 Dashboard Analytics Engine

Tables:
  kpis                  — Project-level KPI records
  project_risk_scores   — 0-100 risk score per project (not task-based)
  tool_analytics        — Effectiveness metrics per tool per project
  dashboard_configs     — Per-user widget/filter config
  analytics_snapshots   — Point-in-time metric snapshots
  benchmark_data        — Industry benchmark reference values
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, Enum as SAEnum, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.base import BaseModel


# ── Enums ──────────────────────────────────────────────────────────────────────

class MetricTypeEnum(str, enum.Enum):
    FINDINGS_CREATED    = "findings_created"
    FINDINGS_RESOLVED   = "findings_resolved"
    SCAN_EXECUTED       = "scan_executed"
    TOOL_INVOCATION     = "tool_invocation"
    REMEDIATION_ATTEMPT = "remediation_attempt"
    COMPLIANCE_CHECK    = "compliance_check"


class KPITypeEnum(str, enum.Enum):
    MTTR                = "mttr"
    REMEDIATION_RATE    = "remediation_rate"
    CRITICAL_FINDINGS   = "critical_findings"
    COMPLIANCE_SCORE    = "compliance_score"
    TOOL_EFFECTIVENESS  = "tool_effectiveness"
    FALSE_POSITIVE_RATE = "false_positive_rate"


class KPIStatusEnum(str, enum.Enum):
    ON_TRACK = "ON_TRACK"
    AT_RISK  = "AT_RISK"
    FAILED   = "FAILED"
    UNKNOWN  = "UNKNOWN"


class TrendEnum(str, enum.Enum):
    IMPROVING  = "IMPROVING"
    STABLE     = "STABLE"
    DEGRADING  = "DEGRADING"


class RiskLevelEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
    MINIMAL  = "MINIMAL"


# ── Models ─────────────────────────────────────────────────────────────────────

class KPI(Base, BaseModel):
    """Project-level Key Performance Indicator — Phase 15"""

    __tablename__ = "kpis"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    project = relationship("Project")

    kpi_type = Column(SAEnum(KPITypeEnum, name="kpitypeenum"), nullable=False, index=True)

    # Current value
    current_value = Column(Float, nullable=False)
    current_unit  = Column(String(50), nullable=False)   # "hours", "days", "%", "score"

    # Target
    target_value = Column(Float, nullable=True)
    target_unit  = Column(String(50), nullable=True)

    # Status & trend
    status           = Column(SAEnum(KPIStatusEnum, name="kpistatusenum"), default=KPIStatusEnum.UNKNOWN)
    threshold_alert  = Column(Boolean, default=False)
    trend            = Column(SAEnum(TrendEnum, name="kpitrendenum"), default=TrendEnum.STABLE)
    trend_percentage = Column(Float, default=0.0)   # % change from previous period

    # Metadata
    calculated_at       = Column(DateTime(timezone=True), server_default=func.now())
    calculation_method  = Column(Text, nullable=True)

    def __repr__(self):
        return f"<KPI(id={self.id}, type={self.kpi_type}, value={self.current_value})>"


class ProjectRiskScore(Base):
    """Project-level risk score (0-100 composite) — Phase 15.

    Distinct from models/risk_score.py (RiskScore) which is task-level 0-10.
    """

    __tablename__ = "project_risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    project = relationship("Project")

    overall_score   = Column(Integer, nullable=False)   # 0-100
    score_component = Column(JSON, default=dict)        # {critical_findings: 40, compliance: 30, ...}

    risk_level = Column(SAEnum(RiskLevelEnum, name="risklevelenum"), nullable=False)

    # Input factors
    critical_finding_count        = Column(Integer, default=0)
    days_since_last_remediation   = Column(Integer, default=0)
    compliance_gap_percentage     = Column(Float, default=50.0)
    tool_coverage_percentage      = Column(Float, default=50.0)

    # Trend
    previous_score = Column(Integer, nullable=True)
    score_change   = Column(Integer, default=0)   # positive = worsening

    calculated_at      = Column(DateTime(timezone=True), server_default=func.now())
    next_calculation_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ProjectRiskScore(project={self.project_id}, score={self.overall_score}, level={self.risk_level})>"


class ToolAnalytics(Base, BaseModel):
    """Per-tool effectiveness analytics per project — Phase 15"""

    __tablename__ = "tool_analytics"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    project = relationship("Project")

    tool_name = Column(String(100), nullable=False, index=True)

    # Counts
    total_invocations   = Column(Integer, default=0)
    findings_discovered = Column(Integer, default=0)
    false_positives     = Column(Integer, default=0)
    true_positives      = Column(Integer, default=0)

    # Rates
    effectiveness_score  = Column(Float, default=0.0)   # 0-100
    false_positive_rate  = Column(Float, default=0.0)   # %

    # Performance
    avg_execution_time_seconds = Column(Float, default=0.0)
    avg_findings_per_execution = Column(Float, default=0.0)

    # Breakdown
    findings_by_severity = Column(JSON, default=dict)   # {critical: 5, high: 12, ...}

    trend_30_days = Column(SAEnum(TrendEnum, name="tooltrendenum"), default=TrendEnum.STABLE)
    last_used = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ToolAnalytics(tool={self.tool_name!r}, project={self.project_id}, score={self.effectiveness_score})>"


class DashboardConfig(Base, BaseModel):
    """Saved per-user dashboard widget/filter configuration — Phase 15"""

    __tablename__ = "dashboard_configs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    project = relationship("Project")

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User")

    name        = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Widget layout
    widgets = Column(JSON, default=list)            # [{type, kpi_type, position}, ...]
    default_filters = Column(JSON, default=dict)    # {severity: [...], tool: [...]}
    date_range_preset = Column(String(50), default="last_30_days")

    is_default = Column(Boolean, default=False)
    is_shared  = Column(Boolean, default=False)

    def __repr__(self):
        return f"<DashboardConfig(id={self.id}, name={self.name!r}, user={self.user_id})>"


class AnalyticsSnapshot(Base):
    """Point-in-time snapshot of all project analytics — Phase 15"""

    __tablename__ = "analytics_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    project = relationship("Project")

    snapshot_type = Column(String(50), nullable=False)      # "daily", "weekly", "monthly"
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)

    metrics_snapshot = Column(JSON, default=dict)   # {findings_created: 15, ...}
    kpis_snapshot    = Column(JSON, default=dict)   # {mttr: 2.5, remediation_rate: 53, ...}
    risk_snapshot    = Column(JSON, default=dict)   # {overall_score: 72, risk_level: MEDIUM}
    tool_snapshot    = Column(JSON, default=dict)   # {nmap: {effectiveness: 85}, ...}

    comparison_with_previous = Column(JSON, default=dict)   # {metric: change_pct}

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AnalyticsSnapshot(project={self.project_id}, type={self.snapshot_type!r}, date={self.snapshot_date})>"


class BenchmarkData(Base):
    """Industry benchmark reference values for KPI comparison — Phase 15"""

    __tablename__ = "benchmark_data"

    id = Column(Integer, primary_key=True, index=True)

    metric_name  = Column(String(100), nullable=False, index=True)
    industry     = Column(String(100), nullable=True, index=True)   # "finance", "healthcare"
    company_size = Column(String(50),  nullable=True)               # "small", "medium", "enterprise"

    # Statistics
    average_value = Column(Float, nullable=False)
    median_value  = Column(Float, nullable=True)
    p75_value     = Column(Float, nullable=True)
    p90_value     = Column(Float, nullable=True)

    sample_size  = Column(Integer, nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<BenchmarkData(metric={self.metric_name!r}, industry={self.industry!r}, avg={self.average_value})>"
