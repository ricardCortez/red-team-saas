"""ThreatIntel model - CVE and vulnerability database"""
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, DateTime, Enum as SQLEnum
from app.database import Base
from app.models.base import BaseModel


class SeverityLevel(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class ThreatIntel(Base, BaseModel):
    """Threat intelligence entry (CVE / vulnerability)"""

    __tablename__ = "threat_intel"

    id = Column(Integer, primary_key=True, index=True)
    cve_id = Column(String(20), unique=True, nullable=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(SQLEnum(SeverityLevel), nullable=False, index=True)
    cvss_score = Column(Numeric(4, 2), nullable=True)  # 0.0 – 10.0
    affected_products = Column(Text, nullable=True)   # JSON list
    exploit_available = Column(Boolean, default=False, index=True)
    patch_available = Column(Boolean, default=False)
    references = Column(Text, nullable=True)           # JSON list of URLs
    published_date = Column(DateTime(timezone=True), nullable=True)
    last_modified = Column(DateTime(timezone=True), nullable=True)
    tags = Column(Text, nullable=True)                 # JSON list of tags

    def __repr__(self):
        return f"<ThreatIntel(id={self.id}, cve={self.cve_id}, severity={self.severity})>"
