"""Schemas for AlertRule - Phase 8"""
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.alert_rule import AlertChannel, AlertTrigger


class AlertRuleCreate(BaseModel):
    name: str
    channel: AlertChannel
    trigger: AlertTrigger
    conditions: Optional[Dict[str, Any]] = {}
    channel_config: Dict[str, Any]
    project_id: Optional[int] = None
    rate_limit_minutes: Optional[int] = 60

    @field_validator("rate_limit_minutes")
    @classmethod
    def validate_rate(cls, v):
        if v is None:
            return 60
        if not 0 <= v <= 1440:
            raise ValueError("rate_limit_minutes must be 0-1440")
        return v


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    conditions: Optional[Dict[str, Any]] = None
    channel_config: Optional[Dict[str, Any]] = None
    rate_limit_minutes: Optional[int] = None


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    channel: AlertChannel
    trigger: AlertTrigger
    is_active: bool
    conditions: Dict[str, Any]
    project_id: Optional[int] = None
    rate_limit_minutes: int
    created_at: datetime

    model_config = {"from_attributes": True}
