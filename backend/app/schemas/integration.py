"""Pydantic schemas for Integration Hub — Phase 16"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Integration ───────────────────────────────────────────────────────────────

class IntegrationCreate(BaseModel):
    integration_type: str
    name:             str = Field(..., min_length=1, max_length=200)
    description:      Optional[str] = None
    auth_token:       str = Field(..., min_length=1)
    auth_webhook_url: Optional[str] = None
    config:           Dict[str, Any] = Field(default_factory=dict)

    @field_validator("integration_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"slack", "teams", "discord", "github", "gitlab", "gitea", "jira", "webhook"}
        if v.lower() not in allowed:
            raise ValueError(f"integration_type must be one of {allowed}")
        return v.lower()


class IntegrationUpdate(BaseModel):
    name:             Optional[str] = None
    description:      Optional[str] = None
    auth_token:       Optional[str] = None
    auth_webhook_url: Optional[str] = None
    config:           Optional[Dict[str, Any]] = None
    status:           Optional[str] = None


class IntegrationResponse(BaseModel):
    id:                  int
    project_id:          int
    integration_type:    str
    name:                str
    description:         Optional[str]
    auth_webhook_url:    Optional[str]
    config:              Dict[str, Any]
    status:              str
    last_tested_at:      Optional[datetime]
    last_tested_result:  Optional[str]
    created_by:          Optional[int]
    created_at:          datetime
    updated_at:          datetime

    model_config = {"from_attributes": True}

    @field_validator("integration_type", "status", mode="before")
    @classmethod
    def enum_to_str(cls, v):
        return v.value if hasattr(v, "value") else v


class IntegrationTestResponse(BaseModel):
    success:  bool
    message:  Optional[str] = None
    status:   Optional[str] = None


# ── Notification Rules ────────────────────────────────────────────────────────

class NotificationRuleCreate(BaseModel):
    name:               str = Field(..., min_length=1, max_length=200)
    description:        Optional[str] = None
    trigger_type:       str
    trigger_conditions: Dict[str, Any] = Field(default_factory=dict)
    integration_ids:    List[int]
    action_template:    Optional[Dict[str, Any]] = None
    is_enabled:         bool = True

    @field_validator("trigger_type")
    @classmethod
    def validate_trigger(cls, v: str) -> str:
        allowed = {
            "finding_created", "finding_resolved", "critical_finding",
            "risk_score_change", "compliance_breach", "remediation_overdue",
            "scan_completed", "report_generated",
        }
        if v.lower() not in allowed:
            raise ValueError(f"trigger_type must be one of {allowed}")
        return v.lower()


class NotificationRuleUpdate(BaseModel):
    name:               Optional[str] = None
    description:        Optional[str] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    integration_ids:    Optional[List[int]] = None
    action_template:    Optional[Dict[str, Any]] = None
    is_enabled:         Optional[bool] = None


class NotificationRuleResponse(BaseModel):
    id:                 int
    project_id:         int
    name:               str
    description:        Optional[str]
    trigger_type:       str
    trigger_conditions: Dict[str, Any]
    integration_ids:    List[int]
    action_template:    Optional[Dict[str, Any]]
    is_enabled:         bool
    created_by:         Optional[int]
    created_at:         datetime
    updated_at:         datetime

    model_config = {"from_attributes": True}

    @field_validator("trigger_type", mode="before")
    @classmethod
    def enum_to_str(cls, v):
        return v.value if hasattr(v, "value") else v


# ── Audit Logs ────────────────────────────────────────────────────────────────

class IntegrationAuditLogResponse(BaseModel):
    id:              int
    integration_id:  int
    action:          str
    status:          str
    payload_sent:    Optional[Dict[str, Any]]
    payload_received: Optional[Dict[str, Any]]
    error_message:   Optional[str]
    error_code:      Optional[str]
    external_id:     Optional[str]
    external_url:    Optional[str]
    finding_id:      Optional[int]
    report_id:       Optional[int]
    timestamp:       datetime

    model_config = {"from_attributes": True}


# ── Webhook Deliveries ────────────────────────────────────────────────────────

class WebhookDeliveryResponse(BaseModel):
    id:             int
    integration_id: int
    event_type:     str
    attempt_number: int
    status_code:    Optional[int]
    response_body:  Optional[str]
    next_retry_at:  Optional[datetime]
    max_retries:    int
    created_at:     datetime
    delivered_at:   Optional[datetime]

    model_config = {"from_attributes": True}


# ── Templates ─────────────────────────────────────────────────────────────────

class IntegrationTemplateCreate(BaseModel):
    integration_type:   str
    name:               str
    template_text:      str
    template_variables: List[Dict[str, Any]] = Field(default_factory=list)
    is_default:         bool = False


class IntegrationTemplateResponse(BaseModel):
    id:                 int
    integration_type:   str
    name:               str
    template_text:      str
    template_variables: List[Dict[str, Any]]
    is_default:         bool
    created_at:         datetime

    model_config = {"from_attributes": True}

    @field_validator("integration_type", mode="before")
    @classmethod
    def enum_to_str(cls, v):
        return v.value if hasattr(v, "value") else v


# ── Stats ─────────────────────────────────────────────────────────────────────

class IntegrationStatsResponse(BaseModel):
    total:        int
    active:       int
    error:        int
    pending_auth: int
    by_type:      Dict[str, int]
