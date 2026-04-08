"""Phishing campaign schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PhishingCampaignStatus(str, Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class PhishingTargetStatus(str, Enum):
    queued = "queued"
    sent = "sent"
    opened = "opened"
    clicked = "clicked"
    submitted_data = "submitted_data"
    reported = "reported"


# ── Target ────────────────────────────────────────────────────────────────────

class PhishingTargetCreate(BaseModel):
    email: str = Field(..., max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)


class PhishingTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    status: PhishingTargetStatus
    created_at: datetime


# ── Campaign ──────────────────────────────────────────────────────────────────

class PhishingCampaignCreate(BaseModel):
    project_id: int
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    gophish_url: str = Field(..., max_length=500)
    gophish_api_key: str = Field(...)
    template_name: Optional[str] = Field(None, max_length=200)
    landing_page_name: Optional[str] = Field(None, max_length=200)
    smtp_profile_name: Optional[str] = Field(None, max_length=200)
    target_group_name: Optional[str] = Field(None, max_length=200)
    phishing_url: Optional[str] = Field(None, max_length=500)
    launch_date: Optional[datetime] = None


class PhishingCampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    template_name: Optional[str] = None
    landing_page_name: Optional[str] = None
    smtp_profile_name: Optional[str] = None
    target_group_name: Optional[str] = None
    phishing_url: Optional[str] = None
    launch_date: Optional[datetime] = None


class PhishingCampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_by: int
    name: str
    description: Optional[str] = None
    status: PhishingCampaignStatus
    gophish_url: str
    gophish_campaign_id: Optional[int] = None
    template_name: Optional[str] = None
    landing_page_name: Optional[str] = None
    smtp_profile_name: Optional[str] = None
    target_group_name: Optional[str] = None
    phishing_url: Optional[str] = None
    launch_date: Optional[datetime] = None
    stats_total: int = 0
    stats_sent: int = 0
    stats_opened: int = 0
    stats_clicked: int = 0
    stats_submitted: int = 0
    stats_last_synced: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PhishingCampaignListResponse(BaseModel):
    items: List[PhishingCampaignResponse]
    total: int
    skip: int
    limit: int


class GoPhishTemplate(BaseModel):
    id: int
    name: str


class GoPhishPage(BaseModel):
    id: int
    name: str


class GoPhishSMTP(BaseModel):
    id: int
    name: str


class GoPhishGroup(BaseModel):
    id: int
    name: str


class GoPhishResourcesResponse(BaseModel):
    templates: List[GoPhishTemplate] = []
    pages: List[GoPhishPage] = []
    smtp_profiles: List[GoPhishSMTP] = []
    groups: List[GoPhishGroup] = []


class PhishingTargetResult(BaseModel):
    email: str
    status: str
    ip: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reported: bool = False


class PhishingCampaignResults(BaseModel):
    campaign_id: int
    gophish_campaign_id: Optional[int] = None
    results: List[PhishingTargetResult] = []
    stats: dict = {}
