"""Pydantic schemas for analytics / dashboard responses — Phase 7 + Phase 15."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, validator, ConfigDict


class GlobalSummary(BaseModel):
    total_scans: int
    scans_running: int
    scans_completed: int
    scans_failed: int
    total_findings: int
    open_findings: int
    critical_findings: int
    high_findings: int
    total_reports: int
    reports_ready: int


class ProjectSummary(BaseModel):
    findings_by_severity: Dict[str, int]
    findings_by_status: Dict[str, int]
    total_findings: int
    false_positives: int
    avg_risk_score: float
    max_risk_score: float
    avg_scan_duration_s: float
    total_scans: int
    successful_scans: int


class TopTarget(BaseModel):
    host: str
    findings: int
    max_risk: float


class TopTool(BaseModel):
    tool: str
    total_runs: int
    successful: int
    avg_risk: float
    avg_duration: float


class HeatmapRow(BaseModel):
    host: str
    critical: int
    high: int
    medium: int
    low: int
    info: int


class TrendPoint(BaseModel):
    date: str
    total: Optional[int] = None
    critical: Optional[int] = None
    high: Optional[int] = None
    medium: Optional[int] = None
    low: Optional[int] = None
    info: Optional[int] = None


class RiskTrendPoint(BaseModel):
    date: str
    avg_risk: float
    max_risk: float
    scan_count: int


class ActivityPoint(BaseModel):
    date: str
    completed: int
    failed: int
    total: int


class ActivityFeedItem(BaseModel):
    id: int
    action: str
    resource: Optional[str] = None
    details: Optional[Any] = None
    created_at: Optional[datetime] = None

    @validator("details", pre=True)
    def parse_details_json(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {"raw": v}
        return v

    class Config:
        orm_mode = True


# ── Phase 15 Schemas ───────────────────────────────────────────────────────────

class KPIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    project_id:       int
    kpi_type:         str
    current_value:    float
    current_unit:     str
    target_value:     Optional[float] = None
    target_unit:      Optional[str]   = None
    status:           str
    trend:            str
    trend_percentage: float
    calculated_at:    datetime
    calculation_method: Optional[str] = None


class ProjectRiskScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    int
    project_id:            int
    overall_score:         int
    risk_level:            str
    score_component:       Dict[str, int]
    critical_finding_count: int
    days_since_last_remediation: int
    compliance_gap_percentage:   float
    tool_coverage_percentage:    float
    previous_score:        Optional[int] = None
    score_change:          int
    calculated_at:         datetime
    next_calculation_at:   Optional[datetime] = None


class ToolAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                   int
    project_id:           int
    tool_name:            str
    total_invocations:    int
    findings_discovered:  int
    false_positives:      int
    true_positives:       int
    effectiveness_score:  float
    false_positive_rate:  float
    findings_by_severity: Dict[str, int]
    trend_30_days:        str
    last_used:            Optional[datetime] = None


class DashboardConfigCreate(BaseModel):
    project_id:        int
    name:              str
    description:       Optional[str]  = None
    widgets:           Optional[List[Dict[str, Any]]] = None
    default_filters:   Optional[Dict[str, Any]] = None
    date_range_preset: Optional[str]  = "last_30_days"
    is_default:        bool           = False
    is_shared:         bool           = False


class DashboardConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                int
    project_id:        int
    user_id:           int
    name:              str
    widgets:           Optional[List[Dict[str, Any]]] = None
    default_filters:   Optional[Dict[str, Any]] = None
    date_range_preset: Optional[str] = None
    is_default:        bool
    is_shared:         bool
    created_at:        datetime


class AnalyticsSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            int
    project_id:    int
    snapshot_type: str
    snapshot_date: datetime
    metrics_snapshot:         Dict[str, Any]
    kpis_snapshot:            Dict[str, Any]
    risk_snapshot:            Dict[str, Any]
    tool_snapshot:            Dict[str, Any]
    comparison_with_previous: Dict[str, Any]
    created_at:    datetime


class BenchmarkResponse(BaseModel):
    metric_name:   str
    industry:      Optional[str] = None
    company_size:  Optional[str] = None
    average_value: float
    median_value:  Optional[float] = None
    p75_value:     Optional[float] = None
    p90_value:     Optional[float] = None
    sample_size:   Optional[int]   = None


class FullDashboardResponse(BaseModel):
    """Aggregated response for the Phase 15 full dashboard endpoint."""
    project_id:     int
    timestamp:      datetime
    realtime_metrics: Dict[str, int]
    kpis:           List[KPIResponse]
    risk_score:     Optional[ProjectRiskScoreResponse] = None
    tool_analytics: List[ToolAnalyticsResponse]
