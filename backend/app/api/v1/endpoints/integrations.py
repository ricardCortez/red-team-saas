"""Integration Hub API endpoints — Phase 16"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.integration import IntegrationCRUD
from app.models.integration import Integration
from app.models.project import Project
from app.models.user import User
from app.schemas.integration import (
    IntegrationAuditLogResponse,
    IntegrationCreate,
    IntegrationResponse,
    IntegrationStatsResponse,
    IntegrationTemplateCreate,
    IntegrationTemplateResponse,
    IntegrationTestResponse,
    IntegrationUpdate,
    NotificationRuleCreate,
    NotificationRuleResponse,
    NotificationRuleUpdate,
    WebhookDeliveryResponse,
)

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_project_or_raise(db: Session, project_id: int, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {project_id} not found")
    if project.owner_id != user.id and not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    return project


def _verify_integration_belongs(integration: Optional[Integration], project_id: int) -> Integration:
    if not integration or integration.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
    return integration


async def _bg_test_integration(integration_id: int, db: Session) -> None:
    """Background task: test connection and update integration status."""
    from app.core.security import EncryptionHandler
    from app.services.integrations import INTEGRATION_CLASSES

    integration = IntegrationCRUD.get_integration(db, integration_id)
    if not integration:
        return
    try:
        int_type = (
            integration.integration_type.value
            if hasattr(integration.integration_type, "value")
            else integration.integration_type
        )
        int_class = INTEGRATION_CLASSES.get(int_type.lower())
        if not int_class:
            IntegrationCRUD.update_integration_status(db, integration_id, "error", "failed")
            return

        token = EncryptionHandler.decrypt(integration.auth_token or "")
        instance = int_class(token, integration.config or {})
        success = await instance.test_connection()

        IntegrationCRUD.update_integration_status(
            db,
            integration_id,
            "active" if success else "error",
            "success" if success else "failed",
        )
    except Exception:
        IntegrationCRUD.update_integration_status(db, integration_id, "error", "failed")


# ── Integrations ───────────────────────────────────────────────────────────────

@router.post(
    "/integrations/projects/{project_id}/integrations",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Integrations"],
)
async def create_integration(
    project_id: int,
    request: IntegrationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new external integration for a project."""
    _get_project_or_raise(db, project_id, current_user)

    integration = IntegrationCRUD.create_integration(
        db,
        {
            **request.model_dump(),
            "project_id": project_id,
            "created_by": current_user.id,
        },
    )
    # Test connectivity asynchronously
    background_tasks.add_task(_bg_test_integration, integration.id, db)
    return integration


@router.get(
    "/integrations/projects/{project_id}/integrations",
    response_model=List[IntegrationResponse],
    tags=["Integrations"],
)
def list_integrations(
    project_id: int,
    integration_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all integrations for a project."""
    _get_project_or_raise(db, project_id, current_user)
    return IntegrationCRUD.list_integrations(db, project_id, integration_type, status_filter, skip, limit)


@router.get(
    "/integrations/projects/{project_id}/integrations/{integration_id}",
    response_model=IntegrationResponse,
    tags=["Integrations"],
)
def get_integration(
    project_id: int,
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific integration."""
    _get_project_or_raise(db, project_id, current_user)
    integration = IntegrationCRUD.get_integration(db, integration_id)
    return _verify_integration_belongs(integration, project_id)


@router.patch(
    "/integrations/projects/{project_id}/integrations/{integration_id}",
    response_model=IntegrationResponse,
    tags=["Integrations"],
)
def update_integration(
    project_id: int,
    integration_id: int,
    request: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an integration."""
    _get_project_or_raise(db, project_id, current_user)
    integration = IntegrationCRUD.get_integration(db, integration_id)
    _verify_integration_belongs(integration, project_id)

    updated = IntegrationCRUD.update_integration(
        db, integration_id, request.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found")
    return updated


@router.delete(
    "/integrations/projects/{project_id}/integrations/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Integrations"],
)
def delete_integration(
    project_id: int,
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an integration."""
    _get_project_or_raise(db, project_id, current_user)
    integration = IntegrationCRUD.get_integration(db, integration_id)
    _verify_integration_belongs(integration, project_id)
    IntegrationCRUD.delete_integration(db, integration_id)


@router.post(
    "/integrations/projects/{project_id}/integrations/{integration_id}/test",
    response_model=IntegrationTestResponse,
    tags=["Integrations"],
)
async def test_integration(
    project_id: int,
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test the connection of an integration synchronously."""
    _get_project_or_raise(db, project_id, current_user)
    integration = IntegrationCRUD.get_integration(db, integration_id)
    _verify_integration_belongs(integration, project_id)

    from app.core.security import EncryptionHandler
    from app.services.integrations import INTEGRATION_CLASSES

    int_type = (
        integration.integration_type.value
        if hasattr(integration.integration_type, "value")
        else integration.integration_type
    )
    int_class = INTEGRATION_CLASSES.get(int_type.lower())
    if not int_class:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown integration type: {int_type}")

    try:
        token = EncryptionHandler.decrypt(integration.auth_token or "")
        instance = int_class(token, integration.config or {})
        success = await instance.test_connection()

        new_status = "active" if success else "error"
        IntegrationCRUD.update_integration_status(
            db, integration_id, new_status, "success" if success else "failed"
        )
        return IntegrationTestResponse(
            success=success,
            status=new_status,
            message="Connection successful" if success else "Connection failed",
        )
    except Exception as exc:
        IntegrationCRUD.update_integration_status(db, integration_id, "error", "failed")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.get(
    "/integrations/projects/{project_id}/stats",
    response_model=IntegrationStatsResponse,
    tags=["Integrations"],
)
def integration_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get integration health statistics for a project."""
    _get_project_or_raise(db, project_id, current_user)
    return IntegrationCRUD.integration_stats(db, project_id)


# ── Notification Rules ─────────────────────────────────────────────────────────

@router.post(
    "/integrations/projects/{project_id}/rules",
    response_model=NotificationRuleResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Notification Rules"],
)
def create_notification_rule(
    project_id: int,
    request: NotificationRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a notification rule for a project."""
    _get_project_or_raise(db, project_id, current_user)
    rule = IntegrationCRUD.create_notification_rule(
        db,
        {
            **request.model_dump(),
            "project_id": project_id,
            "created_by": current_user.id,
        },
    )
    return rule


@router.get(
    "/integrations/projects/{project_id}/rules",
    response_model=List[NotificationRuleResponse],
    tags=["Notification Rules"],
)
def list_notification_rules(
    project_id: int,
    trigger_type: Optional[str] = Query(None),
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List notification rules for a project."""
    _get_project_or_raise(db, project_id, current_user)
    return IntegrationCRUD.get_notification_rules(db, project_id, trigger_type, enabled_only)


@router.get(
    "/integrations/projects/{project_id}/rules/{rule_id}",
    response_model=NotificationRuleResponse,
    tags=["Notification Rules"],
)
def get_notification_rule(
    project_id: int,
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific notification rule."""
    _get_project_or_raise(db, project_id, current_user)
    rule = IntegrationCRUD.get_notification_rule(db, rule_id)
    if not rule or rule.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return rule


@router.patch(
    "/integrations/projects/{project_id}/rules/{rule_id}",
    response_model=NotificationRuleResponse,
    tags=["Notification Rules"],
)
def update_notification_rule(
    project_id: int,
    rule_id: int,
    request: NotificationRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a notification rule."""
    _get_project_or_raise(db, project_id, current_user)
    rule = IntegrationCRUD.get_notification_rule(db, rule_id)
    if not rule or rule.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")

    updated = IntegrationCRUD.update_notification_rule(
        db, rule_id, request.model_dump(exclude_unset=True)
    )
    return updated


@router.delete(
    "/integrations/projects/{project_id}/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Notification Rules"],
)
def delete_notification_rule(
    project_id: int,
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification rule."""
    _get_project_or_raise(db, project_id, current_user)
    rule = IntegrationCRUD.get_notification_rule(db, rule_id)
    if not rule or rule.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    IntegrationCRUD.delete_notification_rule(db, rule_id)


# ── Audit Logs ─────────────────────────────────────────────────────────────────

@router.get(
    "/integrations/projects/{project_id}/audit-logs",
    response_model=List[IntegrationAuditLogResponse],
    tags=["Integration Audit"],
)
def get_audit_logs(
    project_id: int,
    integration_id: Optional[int] = Query(None),
    log_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get audit logs for integrations in a project."""
    _get_project_or_raise(db, project_id, current_user)

    if integration_id:
        integration = IntegrationCRUD.get_integration(db, integration_id)
        _verify_integration_belongs(integration, project_id)

    return IntegrationCRUD.get_audit_logs(
        db,
        integration_id=integration_id,
        project_id=project_id if not integration_id else None,
        status=log_status,
        skip=skip,
        limit=limit,
    )


# ── Templates ──────────────────────────────────────────────────────────────────

@router.post(
    "/integrations/templates",
    response_model=IntegrationTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Integration Templates"],
)
def create_template(
    request: IntegrationTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a reusable message template."""
    if not current_user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Superuser required")
    return IntegrationCRUD.create_template(db, request.model_dump())


@router.get(
    "/integrations/templates",
    response_model=List[IntegrationTemplateResponse],
    tags=["Integration Templates"],
)
def list_templates(
    integration_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available message templates."""
    return IntegrationCRUD.list_templates(db, integration_type)
