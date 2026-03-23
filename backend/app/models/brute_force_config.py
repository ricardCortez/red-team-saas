"""Brute Force Tools Configuration and Results"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel


class BruteForceConfig(Base, BaseModel):
    """Configuration for brute force tools"""

    __tablename__ = "brute_force_configs"

    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String(50), nullable=False, index=True)  # hydra, john, medusa, cewl, wpscan
    target = Column(String(255), nullable=False, index=True)
    username_list = Column(Text, nullable=True)
    wordlist_path = Column(String(500), nullable=True)
    wordlist_size = Column(Integer, nullable=True)
    attack_type = Column(String(50), nullable=True)  # ssh, rdp, ftp, http, smb, wordpress
    timeout_seconds = Column(Integer, default=300)
    max_attempts = Column(Integer, nullable=True)
    rate_limit = Column(Integer, nullable=True)  # attempts per second

    results = relationship("BruteForceResult", back_populates="config", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BruteForceConfig(tool={self.tool_name}, target={self.target})>"


class BruteForceResult(Base, BaseModel):
    """Results from brute force attacks"""

    __tablename__ = "brute_force_results"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("brute_force_configs.id"), nullable=False, index=True)
    credential = Column(String(500), nullable=True)  # username:password
    is_valid = Column(Boolean, default=False)
    attempts_count = Column(Integer, default=0)
    duration_seconds = Column(Integer, nullable=True)

    config = relationship("BruteForceConfig", back_populates="results")

    def __repr__(self):
        return f"<BruteForceResult(credential={self.credential}, valid={self.is_valid})>"
