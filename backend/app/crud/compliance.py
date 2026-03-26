"""CRUD operations for Compliance Engine - Phase 13"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.compliance import (
    ComplianceFramework,
    ComplianceRequirement,
    ComplianceMappingResult,
    ComplianceEvidenceLog,
    ComplianceControlMatrix,
    ComplianceFrameworkType,
    EvidenceStatus,
    ControlImplementationStatus,
)
from app.schemas.compliance import (
    ComplianceFrameworkCreate,
    ComplianceEvidenceCreate,
    ComplianceControlCreate,
)


class ComplianceCRUD:

    # ── Framework ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_framework(db: Session, framework: ComplianceFrameworkCreate) -> ComplianceFramework:
        db_obj = ComplianceFramework(**framework.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def get_framework_by_type(db: Session, framework_type: str) -> Optional[ComplianceFramework]:
        return db.query(ComplianceFramework).filter(
            ComplianceFramework.framework_type == framework_type
        ).first()

    @staticmethod
    def get_framework_by_id(db: Session, framework_id: int) -> Optional[ComplianceFramework]:
        return db.query(ComplianceFramework).filter(
            ComplianceFramework.id == framework_id
        ).first()

    @staticmethod
    def list_frameworks(db: Session, skip: int = 0, limit: int = 100) -> List[ComplianceFramework]:
        return db.query(ComplianceFramework).offset(skip).limit(limit).all()

    # ── Requirement ────────────────────────────────────────────────────────────

    @staticmethod
    def get_requirements_by_framework(db: Session, framework_id: int) -> List[ComplianceRequirement]:
        return db.query(ComplianceRequirement).filter(
            ComplianceRequirement.framework_id == framework_id
        ).all()

    @staticmethod
    def get_requirement(db: Session, framework_id: int, requirement_id: str) -> Optional[ComplianceRequirement]:
        return db.query(ComplianceRequirement).filter(
            ComplianceRequirement.framework_id == framework_id,
            ComplianceRequirement.requirement_id == requirement_id,
        ).first()

    # ── Mapping Result ─────────────────────────────────────────────────────────

    @staticmethod
    def create_mapping_result(db: Session, obj: ComplianceMappingResult) -> ComplianceMappingResult:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def get_mapping_by_project_framework(
        db: Session, project_id: int, framework_id: int
    ) -> Optional[ComplianceMappingResult]:
        return db.query(ComplianceMappingResult).filter(
            ComplianceMappingResult.project_id == project_id,
            ComplianceMappingResult.framework_id == framework_id,
        ).order_by(ComplianceMappingResult.created_at.desc()).first()

    @staticmethod
    def get_latest_mappings(
        db: Session, project_id: int, limit: int = 5
    ) -> List[ComplianceMappingResult]:
        return (
            db.query(ComplianceMappingResult)
            .filter(ComplianceMappingResult.project_id == project_id)
            .order_by(ComplianceMappingResult.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_mapping_by_id(db: Session, mapping_id: int) -> Optional[ComplianceMappingResult]:
        return db.query(ComplianceMappingResult).filter(
            ComplianceMappingResult.id == mapping_id
        ).first()

    # ── Evidence Log ───────────────────────────────────────────────────────────

    @staticmethod
    def create_evidence_log(db: Session, evidence: ComplianceEvidenceCreate) -> ComplianceEvidenceLog:
        db_obj = ComplianceEvidenceLog(**evidence.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def get_evidence_by_mapping(db: Session, mapping_result_id: int) -> List[ComplianceEvidenceLog]:
        return db.query(ComplianceEvidenceLog).filter(
            ComplianceEvidenceLog.mapping_result_id == mapping_result_id
        ).all()

    @staticmethod
    def update_evidence_status(
        db: Session,
        evidence_id: int,
        status: str,
        notes: Optional[str] = None,
        reviewed_by: Optional[int] = None,
    ) -> Optional[ComplianceEvidenceLog]:
        db_obj = db.query(ComplianceEvidenceLog).filter(
            ComplianceEvidenceLog.id == evidence_id
        ).first()
        if db_obj:
            db_obj.status = status
            db_obj.reviewer_notes = notes
            db_obj.reviewed_at = datetime.utcnow()
            db_obj.reviewed_by = reviewed_by
            db.commit()
            db.refresh(db_obj)
        return db_obj

    # ── Control Matrix ─────────────────────────────────────────────────────────

    @staticmethod
    def create_control(
        db: Session,
        project_id: int,
        framework_id: int,
        control_data: ComplianceControlCreate,
    ) -> ComplianceControlMatrix:
        db_obj = ComplianceControlMatrix(
            project_id=project_id,
            framework_id=framework_id,
            **control_data.model_dump(),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def get_controls_by_project(
        db: Session,
        project_id: int,
        framework_id: Optional[int] = None,
    ) -> List[ComplianceControlMatrix]:
        q = db.query(ComplianceControlMatrix).filter(
            ComplianceControlMatrix.project_id == project_id
        )
        if framework_id:
            q = q.filter(ComplianceControlMatrix.framework_id == framework_id)
        return q.all()

    @staticmethod
    def get_control_by_id(db: Session, control_id: int) -> Optional[ComplianceControlMatrix]:
        return db.query(ComplianceControlMatrix).filter(
            ComplianceControlMatrix.id == control_id
        ).first()

    @staticmethod
    def update_control_test_result(
        db: Session, control_id: int, test_result: dict
    ) -> Optional[ComplianceControlMatrix]:
        db_obj = db.query(ComplianceControlMatrix).filter(
            ComplianceControlMatrix.id == control_id
        ).first()
        if db_obj:
            existing = list(db_obj.test_results or [])
            existing.append({
                "date": datetime.utcnow().isoformat(),
                **test_result,
            })
            db_obj.test_results = existing
            db_obj.last_tested = datetime.utcnow()
            db.commit()
            db.refresh(db_obj)
        return db_obj
