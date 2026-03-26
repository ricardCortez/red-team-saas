"""Pydantic schemas for Compliance Engine - Phase 13"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Framework ─────────────────────────────────────────────────────────────────

class ComplianceFrameworkResponse(BaseModel):
    id: int
    name: str
    framework_type: str
    version: str
    description: Optional[str]
    total_requirements: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplianceFrameworkCreate(BaseModel):
    name: str
    framework_type: str
    version: str
    description: Optional[str] = None
    total_requirements: int = 0


# ── Requirement ───────────────────────────────────────────────────────────────

class ComplianceRequirementSchema(BaseModel):
    id: int
    framework_id: int
    requirement_id: str
    requirement_text: str
    control_objective: Optional[str]
    severity: str
    related_cve_patterns: Optional[List[str]]
    tool_mappings: Optional[Dict[str, List[str]]]

    model_config = {"from_attributes": True}


# ── Mapping Result ─────────────────────────────────────────────────────────────

class ComplianceMappingResponse(BaseModel):
    id: int
    project_id: int
    framework_id: int
    assessment_date: datetime
    assessment_period: Optional[str]

    total_requirements: int
    met_requirements: int
    non_met_requirements: int
    partial_met_requirements: int
    not_applicable: int

    compliance_score: int
    compliance_status: str
    audit_findings: Any
    evidence_metadata: Optional[Dict[str, Any]]

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Evidence Log ──────────────────────────────────────────────────────────────

class ComplianceEvidenceResponse(BaseModel):
    id: int
    mapping_result_id: int
    requirement_id: str
    finding_id: Optional[int]

    status: str
    evidence_text: Optional[str]
    proof_of_compliance: Optional[Dict[str, Any]]
    reviewer_notes: Optional[str]
    reviewed_at: Optional[datetime]

    created_at: datetime

    model_config = {"from_attributes": True}


class ComplianceEvidenceCreate(BaseModel):
    mapping_result_id: int
    requirement_id: str
    finding_id: Optional[int] = None
    status: str
    evidence_text: Optional[str] = None
    proof_of_compliance: Optional[Dict[str, Any]] = None


# ── Control Matrix ────────────────────────────────────────────────────────────

class ComplianceControlResponse(BaseModel):
    id: int
    project_id: int
    framework_id: int
    requirement_id: str

    control_description: Optional[str]
    control_owner: Optional[str]
    implementation_status: str

    last_tested: Optional[datetime]
    next_test_date: Optional[datetime]
    test_results: Optional[List[Dict[str, Any]]]

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ComplianceControlCreate(BaseModel):
    requirement_id: str
    control_description: Optional[str] = None
    control_owner: Optional[str] = None
    implementation_status: str = "PLANNED"


# ── Request ───────────────────────────────────────────────────────────────────

class ComplianceAssessmentRequest(BaseModel):
    framework_type: str = Field(
        ...,
        description="One of: pci_dss_3.2.1, pci_dss_4.0, hipaa, gdpr, soc2, iso27001",
    )
    assessment_period: Optional[str] = None
