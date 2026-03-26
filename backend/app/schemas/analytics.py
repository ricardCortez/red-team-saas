"""Pydantic schemas for analytics / dashboard responses."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, validator


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
