"""MITRE ATT&CK technique cache model - Phase 12"""
from sqlalchemy import Column, Integer, String, Text, JSON, Boolean
from app.database import Base


class MitreTechnique(Base):
    __tablename__ = "mitre_techniques"

    id              = Column(Integer, primary_key=True)
    technique_id    = Column(String(20), unique=True, nullable=False, index=True)  # T1190
    name            = Column(String(200), nullable=False)
    tactic          = Column(String(50), nullable=True, index=True)    # initial-access
    tactic_name     = Column(String(100), nullable=True)               # Initial Access
    description     = Column(Text, nullable=True)
    is_subtechnique = Column(Boolean, default=False)
    parent_id       = Column(String(20), nullable=True)                # T1059 para T1059.001
    platforms       = Column(JSON, default=list)                       # ["Windows", "Linux"]
    detection       = Column(Text, nullable=True)
    mitigations     = Column(JSON, default=list)
    url             = Column(String(300), nullable=True)

    def __repr__(self):
        return f"<MitreTechnique(id={self.id}, technique_id={self.technique_id}, name={self.name!r})>"
