"""Schemas for the execution engine (Phase 4)"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator, ConfigDict

from app.models.task import TaskStatusEnum


class ExecutionCreate(BaseModel):
    tool_name: str
    target: str
    options: Optional[Dict[str, Any]] = {}
    project_id: Optional[int] = None
    priority: Optional[int] = 5  # 1-9, higher = more priority

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if not 1 <= v <= 9:
            raise ValueError("Priority must be between 1 and 9")
        return v


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str]
    tool_name: Optional[str]
    target: Optional[str]
    status: TaskStatusEnum
    celery_task_id: Optional[str]
    created_at: datetime


class ExecutionStatus(BaseModel):
    task_id: int
    status: TaskStatusEnum
    celery_state: Optional[str]
    celery_task_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
