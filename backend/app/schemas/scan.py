"""Scan schemas"""
import json
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ScanStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ScanType(str, Enum):
    recon = "recon"
    vuln_scan = "vuln_scan"
    exploitation = "exploitation"
    post_exploit = "post_exploit"
    brute_force = "brute_force"
    full = "full"


class ScanBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    scan_type: ScanType
    target: str
    options: Optional[Dict[str, Any]] = {}
    tools: Optional[List[str]] = []
    scheduled_at: Optional[datetime] = None


class ScanCreate(ScanBase):
    project_id: int


class ScanUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[ScanStatus] = None
    options: Optional[Dict[str, Any]] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    celery_task_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ScanInDB(ScanBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    created_by: int
    status: ScanStatus = ScanStatus.pending
    progress: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    celery_task_id: Optional[str] = None

    @field_validator("options", mode="before")
    @classmethod
    def _parse_options(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return {}
        return v if v is not None else {}

    @field_validator("tools", mode="before")
    @classmethod
    def _parse_tools(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return []
        return v if v is not None else []


class ScanResponse(ScanInDB):
    pass


class ScanListResponse(BaseModel):
    items: List[ScanResponse]
    total: int
    skip: int
    limit: int
