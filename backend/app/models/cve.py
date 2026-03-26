"""CVE cache model - Phase 12 Threat Intelligence"""
from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class CVE(Base):
    __tablename__ = "cves"

    id               = Column(Integer, primary_key=True)
    cve_id           = Column(String(30), unique=True, nullable=False, index=True)
    description      = Column(Text, nullable=True)
    cvss_v3_score    = Column(Float, nullable=True)
    cvss_v3_vector   = Column(String(100), nullable=True)
    cvss_v2_score    = Column(Float, nullable=True)
    severity         = Column(String(20), nullable=True)    # critical/high/medium/low
    cwe_ids          = Column(JSON, default=list)           # ["CWE-79", "CWE-89"]
    affected_products = Column(JSON, default=list)          # CPE strings
    references       = Column(JSON, default=list)           # URLs
    mitre_techniques = Column(JSON, default=list)           # ["T1190", "T1059.001"]
    published_at     = Column(DateTime(timezone=True), nullable=True)
    modified_at      = Column(DateTime(timezone=True), nullable=True)
    fetched_at       = Column(DateTime(timezone=True), server_default=func.now())
    is_kev           = Column(Boolean, default=False)       # CISA Known Exploited Vulnerabilities

    def __repr__(self):
        return f"<CVE(id={self.id}, cve_id={self.cve_id}, severity={self.severity})>"
