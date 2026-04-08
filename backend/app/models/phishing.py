"""Phishing campaign models"""
import enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Enum as SQLEnum, Boolean,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel
from app.core.security import EncryptedString


class PhishingCampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class PhishingTargetStatus(str, enum.Enum):
    queued = "queued"
    sent = "sent"
    opened = "opened"
    clicked = "clicked"
    submitted_data = "submitted_data"
    reported = "reported"


class PhishingCampaign(Base, BaseModel):
    """A phishing simulation campaign backed by a GoPhish server."""

    __tablename__ = "phishing_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(PhishingCampaignStatus),
        default=PhishingCampaignStatus.draft,
        nullable=False,
        index=True,
    )

    # GoPhish server config (per-campaign so teams can use different servers)
    gophish_url = Column(String(500), nullable=False)
    gophish_api_key = Column(EncryptedString(500), nullable=False)
    gophish_campaign_id = Column(Integer, nullable=True)

    # Campaign content references (names of resources on GoPhish)
    template_name = Column(String(200), nullable=True)
    landing_page_name = Column(String(200), nullable=True)
    smtp_profile_name = Column(String(200), nullable=True)
    target_group_name = Column(String(200), nullable=True)
    phishing_url = Column(String(500), nullable=True)
    launch_date = Column(DateTime(timezone=True), nullable=True)

    # Stats cached from GoPhish (refreshed by sync task)
    stats_total = Column(Integer, default=0)
    stats_sent = Column(Integer, default=0)
    stats_opened = Column(Integer, default=0)
    stats_clicked = Column(Integer, default=0)
    stats_submitted = Column(Integer, default=0)
    stats_last_synced = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project")
    creator = relationship("User", foreign_keys=[created_by])
    targets = relationship(
        "PhishingTarget",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


class PhishingTarget(Base, BaseModel):
    """An individual email target within a phishing campaign."""

    __tablename__ = "phishing_targets"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer,
        ForeignKey("phishing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    status = Column(
        SQLEnum(PhishingTargetStatus),
        default=PhishingTargetStatus.queued,
        nullable=False,
    )

    campaign = relationship("PhishingCampaign", back_populates="targets")
