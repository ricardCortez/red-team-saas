"""
Phase 5 - Findings Processor
Extracts findings from Result.findings JSON, normalizes severity,
detects duplicates by project, and persists Finding rows.
"""
import hashlib
import logging
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.models.finding import Finding, Severity, FindingStatus
from app.models.result import Result

logger = logging.getLogger(__name__)

SEVERITY_MAP: Dict[str, Severity] = {
    "critical": Severity.critical,
    "high": Severity.high,
    "medium": Severity.medium,
    "low": Severity.low,
    "info": Severity.info,
}


def compute_fingerprint(title: str, host: str, port: Any = None) -> str:
    """Stable 16-char hex fingerprint: sha256(title:host:port)[:16]"""
    raw = f"{title.lower().strip()}:{(host or '').lower()}:{port or ''}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _resolve_severity(raw: str) -> Severity:
    return SEVERITY_MAP.get((raw or "info").lower(), Severity.info)


def process_result_findings(db: Session, result: Result) -> List[Finding]:
    """
    Extract findings from result.findings JSON, normalise, deduplicate,
    and persist Finding rows linked to the result/task/project.

    Returns the list of Finding objects created (may include duplicates).
    """
    raw_findings: List[Dict[str, Any]] = result.findings or []
    if not raw_findings:
        return []

    # Resolve project_id from the task relationship
    project_id = None
    if result.task:
        project_id = result.task.project_id

    created: List[Finding] = []

    for raw in raw_findings:
        title = raw.get("title") or "Unknown Finding"
        host = raw.get("host") or result.target or ""
        port = raw.get("port")
        severity = _resolve_severity(raw.get("severity", "info"))
        fp = compute_fingerprint(title, host, port)

        # Duplicate detection: same fingerprint in same project, not itself a dup
        existing: Finding | None = None
        if project_id:
            existing = (
                db.query(Finding)
                .filter(
                    Finding.fingerprint == fp,
                    Finding.project_id == project_id,
                    Finding.is_duplicate == False,  # noqa: E712
                )
                .first()
            )

        finding = Finding(
            result_id=result.id,
            task_id=result.task_id,
            project_id=project_id,
            title=title,
            description=raw.get("description", ""),
            severity=severity,
            status=FindingStatus.open,
            risk_score=float(raw.get("risk_score", 0.0)),
            host=host,
            port=port,
            service=raw.get("service"),
            tool_name=result.tool_name or result.tool,
            fingerprint=fp,
            is_duplicate=bool(existing),
            duplicate_of=existing.id if existing else None,
        )
        db.add(finding)
        created.append(finding)

    try:
        db.commit()
        for f in created:
            db.refresh(f)
    except Exception:
        db.rollback()
        logger.exception("Failed to persist findings for result %s", result.id)
        raise

    return created
