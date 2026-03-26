"""IOC (Indicator of Compromise) registry model - Phase 12"""
import enum
from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime, Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func
from app.database import Base


class IOCType(str, enum.Enum):
    IP          = "ip"
    DOMAIN      = "domain"
    URL         = "url"
    HASH_MD5    = "hash_md5"
    HASH_SHA1   = "hash_sha1"
    HASH_SHA256 = "hash_sha256"
    EMAIL       = "email"


class IOCThreatLevel(str, enum.Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class IOC(Base):
    __tablename__ = "iocs"

    id           = Column(Integer, primary_key=True)
    value        = Column(String(500), nullable=False, index=True)
    ioc_type     = Column(SAEnum(IOCType), nullable=False, index=True)
    threat_level = Column(SAEnum(IOCThreatLevel), default=IOCThreatLevel.MEDIUM)
    confidence   = Column(Float, default=0.5)    # 0.0 - 1.0
    source       = Column(String(100), nullable=True)   # "abuseipdb", "urlhaus", "custom"
    description  = Column(Text, nullable=True)
    tags         = Column(JSON, default=list)
    country      = Column(String(10), nullable=True)
    asn          = Column(String(50), nullable=True)
    first_seen   = Column(DateTime(timezone=True), nullable=True)
    last_seen    = Column(DateTime(timezone=True), nullable=True)
    is_active    = Column(Boolean, default=True)
    raw_data     = Column(JSON, default=dict)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<IOC(id={self.id}, value={self.value!r}, type={self.ioc_type})>"
