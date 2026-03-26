"""Celery tasks for Compliance Engine - Phase 13"""
from __future__ import annotations

import logging

from app.tasks.celery_app import celery_app
from app.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.compliance_tasks.assess_project_compliance")
def assess_project_compliance_task(project_id: int, framework_type: str) -> dict:
    """
    Async compliance assessment for a project.
    Useful when a project has many findings.
    """
    db = SessionLocal()
    try:
        from app.models.project import Project
        from app.models.finding import Finding
        from app.services.compliance_mapper import ComplianceMapper

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"Project {project_id} not found")
            return {"status": "error", "message": f"Project {project_id} not found"}

        findings = db.query(Finding).filter(
            Finding.project_id == project_id
        ).all()

        mapper = ComplianceMapper(db)
        mapping_result = mapper.assess_project(project_id, framework_type, findings)

        logger.info(
            f"Compliance assessment done for project {project_id}: "
            f"score={mapping_result.compliance_score}, "
            f"status={mapping_result.compliance_status}"
        )
        return {
            "status":            "success",
            "mapping_id":        mapping_result.id,
            "compliance_score":  mapping_result.compliance_score,
            "compliance_status": mapping_result.compliance_status.value
            if hasattr(mapping_result.compliance_status, "value")
            else mapping_result.compliance_status,
        }
    except Exception as e:
        logger.exception(f"Compliance assessment failed for project {project_id}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
