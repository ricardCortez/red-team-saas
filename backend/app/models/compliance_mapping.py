"""ComplianceMapping model - maps findings to compliance frameworks"""
import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel


class ComplianceFramework(str, enum.Enum):
    pci_dss = "PCI-DSS"
    hipaa = "HIPAA"
    gdpr = "GDPR"
    iso27001 = "ISO27001"
    soc2 = "SOC2"
    nist = "NIST"


class ComplianceStatus(str, enum.Enum):
    compliant = "compliant"
    non_compliant = "non_compliant"
    not_assessed = "not_assessed"
    in_remediation = "in_remediation"


class ComplianceMapping(Base, BaseModel):
    """Maps a task or threat to a specific compliance control"""

    __tablename__ = "compliance_mappings"

    id = Column(Integer, primary_key=True, index=True)
    framework = Column(SQLEnum(ComplianceFramework), nullable=False, index=True)
    control_id = Column(String(50), nullable=False, index=True)   # e.g. "PCI-DSS 6.5.1"
    control_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(ComplianceStatus),
        default=ComplianceStatus.not_assessed,
        nullable=False,
        index=True,
    )
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    threat_intel_id = Column(Integer, ForeignKey("threat_intel.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    task = relationship("Task")
    threat = relationship("ThreatIntel")

    def __repr__(self):
        fw = self.framework.value if hasattr(self.framework, "value") else self.framework
        return f"<ComplianceMapping(id={self.id}, framework={fw}, control={self.control_id})>"
