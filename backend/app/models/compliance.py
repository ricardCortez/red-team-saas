"""Compliance Engine models - Phase 13
Tables: compliance_frameworks, compliance_requirements,
        compliance_mapping_results, compliance_evidence_logs,
        compliance_control_matrix
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    JSON, DateTime, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ComplianceFrameworkType(str, enum.Enum):
    PCI_DSS_3_2_1 = "pci_dss_3.2.1"
    PCI_DSS_4_0   = "pci_dss_4.0"
    HIPAA         = "hipaa"
    GDPR          = "gdpr"
    SOC2          = "soc2"
    ISO27001      = "iso27001"


class ComplianceStatus(str, enum.Enum):
    COMPLIANT     = "COMPLIANT"
    PARTIAL       = "PARTIAL"
    NON_COMPLIANT = "NON_COMPLIANT"


class ControlImplementationStatus(str, enum.Enum):
    PLANNED     = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    IMPLEMENTED = "IMPLEMENTED"
    TESTED      = "TESTED"


class EvidenceStatus(str, enum.Enum):
    MET            = "MET"
    NON_MET        = "NON_MET"
    PARTIAL        = "PARTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ComplianceFramework(Base):
    """Framework definition (PCI-DSS, HIPAA, GDPR, …)."""
    __tablename__ = "compliance_frameworks"

    id                  = Column(Integer, primary_key=True, index=True)
    name                = Column(String(100), unique=True, nullable=False)
    framework_type      = Column(SAEnum(ComplianceFrameworkType), unique=True, nullable=False, index=True)
    version             = Column(String(20), nullable=False)
    description         = Column(Text, nullable=True)
    total_requirements  = Column(Integer, default=0)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    requirements = relationship("ComplianceRequirement", back_populates="framework", cascade="all, delete-orphan")
    mapping_results = relationship("ComplianceMappingResult", back_populates="framework")

    def __repr__(self):
        return f"<ComplianceFramework(id={self.id}, name={self.name!r})>"


class ComplianceRequirement(Base):
    """Individual control requirement within a framework."""
    __tablename__ = "compliance_requirements"

    id                    = Column(Integer, primary_key=True, index=True)
    framework_id          = Column(Integer, ForeignKey("compliance_frameworks.id"), nullable=False, index=True)
    requirement_id        = Column(String(50), nullable=False)   # "1.1", "164.312(a)(1)", etc.
    requirement_text      = Column(Text, nullable=False)
    control_objective     = Column(Text, nullable=True)
    severity              = Column(String(20), default="HIGH")   # CRITICAL / HIGH / MEDIUM / LOW
    related_cve_patterns  = Column(JSON, default=list)           # ["CWE-200", "CWE-89"]
    tool_mappings         = Column(JSON, default=dict)           # {"nmap": ["open-port"]}
    created_at            = Column(DateTime(timezone=True), server_default=func.now())

    framework = relationship("ComplianceFramework", back_populates="requirements")

    def __repr__(self):
        return f"<ComplianceRequirement(id={self.id}, req_id={self.requirement_id!r})>"


class ComplianceMappingResult(Base):
    """Result of assessing a project against a compliance framework."""
    __tablename__ = "compliance_mapping_results"

    id                      = Column(Integer, primary_key=True, index=True)
    project_id              = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    framework_id            = Column(Integer, ForeignKey("compliance_frameworks.id"), nullable=False, index=True)
    assessment_date         = Column(DateTime(timezone=True), server_default=func.now())
    assessment_period       = Column(String(100), nullable=True)   # "2026-01 to 2026-03"

    # Requirement counts
    total_requirements      = Column(Integer, default=0)
    met_requirements        = Column(Integer, default=0)
    non_met_requirements    = Column(Integer, default=0)
    partial_met_requirements = Column(Integer, default=0)
    not_applicable          = Column(Integer, default=0)

    compliance_score        = Column(Integer, default=0)    # 0-100
    compliance_status       = Column(SAEnum(ComplianceStatus), default=ComplianceStatus.NON_COMPLIANT, nullable=False)

    evidence_metadata       = Column(JSON, default=dict)
    audit_findings          = Column(JSON, default=list)    # [{req_id, finding_id, severity, status}]

    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    framework = relationship("ComplianceFramework", back_populates="mapping_results")
    project   = relationship("Project")
    evidence_logs = relationship("ComplianceEvidenceLog", back_populates="mapping_result", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ComplianceMappingResult(id={self.id}, score={self.compliance_score}, status={self.compliance_status})>"


class ComplianceEvidenceLog(Base):
    """Immutable audit evidence entry for a specific requirement/finding pair."""
    __tablename__ = "compliance_evidence_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    mapping_result_id   = Column(Integer, ForeignKey("compliance_mapping_results.id"), nullable=False, index=True)
    requirement_id      = Column(String(50), nullable=False)
    finding_id          = Column(Integer, ForeignKey("findings.id"), nullable=True, index=True)

    status              = Column(SAEnum(EvidenceStatus), nullable=False, default=EvidenceStatus.NOT_APPLICABLE)
    evidence_text       = Column(Text, nullable=True)
    proof_of_compliance = Column(JSON, default=dict)    # {tool, timestamp, output_snippet}

    reviewer_notes      = Column(Text, nullable=True)
    reviewed_by         = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at         = Column(DateTime(timezone=True), nullable=True)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    mapping_result = relationship("ComplianceMappingResult", back_populates="evidence_logs")
    finding        = relationship("Finding")
    reviewer       = relationship("User")

    def __repr__(self):
        return f"<ComplianceEvidenceLog(id={self.id}, req={self.requirement_id!r}, status={self.status})>"


class ComplianceControlMatrix(Base):
    """Control implementation tracking per project/framework/requirement."""
    __tablename__ = "compliance_control_matrix"

    id                    = Column(Integer, primary_key=True, index=True)
    project_id            = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    framework_id          = Column(Integer, ForeignKey("compliance_frameworks.id"), nullable=False, index=True)
    requirement_id        = Column(String(50), nullable=False)

    control_description   = Column(Text, nullable=True)
    control_owner         = Column(String(100), nullable=True)
    implementation_status = Column(
        SAEnum(ControlImplementationStatus),
        default=ControlImplementationStatus.PLANNED,
        nullable=False,
    )

    last_tested    = Column(DateTime(timezone=True), nullable=True)
    next_test_date = Column(DateTime(timezone=True), nullable=True)
    test_results   = Column(JSON, default=list)   # [{date, result, tester, notes}]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project   = relationship("Project")
    framework = relationship("ComplianceFramework")

    def __repr__(self):
        return f"<ComplianceControlMatrix(id={self.id}, req={self.requirement_id!r}, status={self.implementation_status})>"
