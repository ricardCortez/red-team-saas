"""Result (Finding) schemas"""
import json
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class ResultBase(BaseModel):
    title: str = Field(..., max_length=200)
    severity: Severity
    tool: str
    raw_output: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = {}
    cve_ids: Optional[List[str]] = []
    mitre_ids: Optional[List[str]] = []
    affected_host: Optional[str] = None
    affected_port: Optional[int] = None
    remediation: Optional[str] = None
    false_positive: bool = False
    verified: bool = False


class ResultCreate(ResultBase):
    scan_id: int


class ResultUpdate(BaseModel):
    severity: Optional[Severity] = None
    remediation: Optional[str] = None
    false_positive: Optional[bool] = None
    verified: Optional[bool] = None
    verified_by: Optional[int] = None
    notes: Optional[str] = None


class ResultInDB(ResultBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scan_id: int
    risk_score: Optional[float] = 0.0
    verified_by: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("cve_ids", "mitre_ids", mode="before")
    @classmethod
    def _parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return []
        return v if v is not None else []

    @field_validator("parsed_data", mode="before")
    @classmethod
    def _parse_json_dict(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return {}
        return v if v is not None else {}


class ResultResponse(ResultInDB):
    pass


class ResultListResponse(BaseModel):
    items: List[ResultResponse]
    total: int
    skip: int
    limit: int


class ResultSummary(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    total: int = 0
    verified: int = 0
    false_positives: int = 0
