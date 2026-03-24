"""Finding model (scan results/vulnerabilities)"""
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel
from app.core.security import EncryptedString


class Severity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class Finding(Base, BaseModel):
    """Finding/vulnerability discovered during a scan"""

    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    severity = Column(SQLEnum(Severity), nullable=False, index=True)
    tool = Column(String(100), nullable=False, index=True)
    raw_output = Column(EncryptedString(65535), nullable=True)   # AES-256 encrypted
    parsed_data = Column(EncryptedString(65535), nullable=True)  # AES-256 encrypted JSON
    cve_ids = Column(Text, nullable=True)    # JSON array ["CVE-2021-1234"]
    mitre_ids = Column(Text, nullable=True)  # JSON array ["T1190", "T1059"]
    affected_host = Column(String(255), nullable=True, index=True)
    affected_port = Column(Integer, nullable=True)
    remediation = Column(Text, nullable=True)
    false_positive = Column(Boolean, default=False, index=True)
    verified = Column(Boolean, default=False, index=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    risk_score = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="findings")
    verifier = relationship("User", foreign_keys=[verified_by])

    def __repr__(self):
        return f"<Finding(id={self.id}, severity={self.severity}, title={self.title!r})>"
