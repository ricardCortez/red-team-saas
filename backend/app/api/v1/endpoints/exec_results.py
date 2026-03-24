"""Phase 5 - Execution Results endpoints (Result model / tool run outputs)"""
import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import EncryptionHandler
from app.crud.exec_result import crud_exec_result
from app.crud.finding import crud_finding
from app.models.result import Result
from app.models.user import User, UserRoleEnum
from app.schemas.result import ResultFilter, ExecutionResultResponse, ExecutionResultListResponse

router = APIRouter()


def _serialize_result(result: Result, include_raw: bool = False) -> dict:
    data = ExecutionResultResponse.model_validate(result).model_dump()
    data["findings_count"] = len(result.findings_rel) if result.findings_rel else len(result.findings or [])
    if include_raw and result.raw_output:
        try:
            data["raw_output"] = EncryptionHandler.decrypt(result.raw_output)
        except Exception:
            data["raw_output"] = result.raw_output
    return data


@router.get("/", response_model=dict)
def list_exec_results(
    tool_name: Optional[str] = Query(None),
    target: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    min_risk_score: Optional[float] = Query(None),
    success: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = ResultFilter(
        tool_name=tool_name,
        target=target,
        project_id=project_id,
        min_risk_score=min_risk_score,
        success=success,
    )
    items, total = crud_exec_result.get_multi_filtered(
        db,
        user_id=current_user.id,
        filters=filters,
        skip=skip,
        limit=limit,
        is_superuser=current_user.is_superuser,
    )
    serialized = [_serialize_result(r) for r in items]
    return {"total": total, "items": serialized, "skip": skip, "limit": limit}


@router.get("/summary/{project_id}")
def project_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {
        "results": crud_exec_result.get_summary_by_project(db, project_id),
        "findings": crud_finding.get_stats_by_severity(db, project_id),
    }


@router.get("/{result_id}")
def get_exec_result(
    result_id: int,
    include_raw: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = crud_exec_result.get(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    if include_raw and current_user.role == UserRoleEnum.viewer:
        raise HTTPException(status_code=403, detail="Viewers cannot access raw output")

    return _serialize_result(result, include_raw=include_raw)


@router.get("/{result_id}/export")
def export_result(
    result_id: int,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = crud_exec_result.get(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    if format == "json":
        payload = {
            "result_id": result.id,
            "tool": result.tool_name,
            "target": result.target,
            "risk_score": result.risk_score,
            "findings": result.findings,
            "parsed_output": result.parsed_output,
        }
        content = json.dumps(payload, indent=2, default=str)
        return StreamingResponse(
            io.StringIO(content),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=result_{result_id}.json"},
        )

    # CSV: findings list
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["severity", "title", "description", "host"]
    )
    writer.writeheader()
    for f in result.findings or []:
        writer.writerow(
            {
                "severity": f.get("severity", ""),
                "title": f.get("title", ""),
                "description": f.get("description", ""),
                "host": f.get("host", result.target or ""),
            }
        )
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=findings_{result_id}.csv"},
    )
