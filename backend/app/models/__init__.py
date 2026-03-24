"""Models package"""
from app.models.base import BaseModel
from app.models.user import User
# Workspace must be imported before Task (Task has workspace FK)
from app.models.workspace import Workspace
from app.models.task import Task
from app.models.result import Result
from app.models.audit_log import AuditLog
# Phase 3 models
from app.models.project import Project, ProjectStatus, ProjectScope
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.finding import Finding, Severity
from app.models.brute_force_config import BruteForceConfig, BruteForceResult
from app.models.generic_tool import GenericToolConfig, ToolExecution
from app.models.plugin import Plugin, PluginExecution
# Phase 2 models
from app.models.template import Template, TemplateCategory
from app.models.threat_intel import ThreatIntel, SeverityLevel
from app.models.risk_score import RiskScore
from app.models.compliance_mapping import ComplianceMapping, ComplianceFramework, ComplianceStatus
from app.models.report import Report, ReportStatus

__all__ = [
    # Base
    "BaseModel",
    # Phase 1 models
    "User",
    "Workspace",
    "Task",
    "Result",
    "AuditLog",
    "BruteForceConfig",
    "BruteForceResult",
    "GenericToolConfig",
    "ToolExecution",
    "Plugin",
    "PluginExecution",
    # Phase 2 models
    "Template",
    "TemplateCategory",
    "ThreatIntel",
    "SeverityLevel",
    "RiskScore",
    "ComplianceMapping",
    "ComplianceFramework",
    "ComplianceStatus",
    "Report",
    "ReportStatus",
    # Phase 3 models
    "Project",
    "ProjectStatus",
    "ProjectScope",
    "Scan",
    "ScanStatus",
    "ScanType",
    "Finding",
    "Severity",
]
