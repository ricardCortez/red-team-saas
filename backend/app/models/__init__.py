"""Models package"""
from app.models.base import BaseModel
from app.models.user import User
# Workspace must be imported before Task (Task has workspace FK)
from app.models.workspace import Workspace
from app.models.task import Task
from app.models.result import Result
from app.models.audit_log import AuditLog
# Phase 3 models
from app.models.project import Project, ProjectStatus, ProjectScope, ProjectType
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.finding import Finding, Severity
# Phase 9 models (must come after Project)
from app.models.project_member import ProjectMember, ProjectRole
from app.models.target import Target, TargetType, TargetStatus
from app.models.brute_force_config import BruteForceConfig, BruteForceResult
from app.models.generic_tool import GenericToolConfig, ToolExecution
from app.models.plugin import Plugin, PluginExecution
# Phase 2 models
from app.models.template import Template, TemplateCategory
from app.models.threat_intel import ThreatIntel, SeverityLevel
from app.models.risk_score import RiskScore
from app.models.compliance_mapping import ComplianceMapping, ComplianceFramework as ComplianceFrameworkEnum, ComplianceStatus as ComplianceStatusEnum
from app.models.report import (
    Report, ReportStatus,
    # Phase 14
    ReportV2, ReportTemplate, ReportVersion, ReportSchedule, ReportAuditLog,
    DigitalSignature, ReportTypeV2, ReportFormatV2, ReportStatusV2,
)
# Phase 8 models
from app.models.alert_rule import AlertRule, AlertChannel, AlertTrigger
from app.models.notification import Notification, NotificationStatus
# Phase 12 models
from app.models.cve import CVE
from app.models.mitre_technique import MitreTechnique
from app.models.ioc import IOC, IOCType, IOCThreatLevel
# Phase 15 models
from app.models.analytics import (
    KPI,
    ProjectRiskScore,
    ToolAnalytics,
    DashboardConfig,
    AnalyticsSnapshot,
    BenchmarkData,
    KPITypeEnum,
    KPIStatusEnum,
    MetricTypeEnum,
    RiskLevelEnum,
    TrendEnum,
)
# Phase 13 models
from app.models.compliance import (
    ComplianceFramework,
    ComplianceRequirement,
    ComplianceMappingResult,
    ComplianceEvidenceLog,
    ComplianceControlMatrix,
    ComplianceFrameworkType,
    ComplianceStatus,
    EvidenceStatus,
    ControlImplementationStatus,
)

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
    "ComplianceFrameworkEnum",
    "ComplianceStatusEnum",
    "Report",
    "ReportStatus",
    # Phase 15
    "KPI",
    "ProjectRiskScore",
    "ToolAnalytics",
    "DashboardConfig",
    "AnalyticsSnapshot",
    "BenchmarkData",
    "KPITypeEnum",
    "KPIStatusEnum",
    "MetricTypeEnum",
    "RiskLevelEnum",
    "TrendEnum",
    # Phase 14
    "ReportV2",
    "ReportTemplate",
    "ReportVersion",
    "ReportSchedule",
    "ReportAuditLog",
    "DigitalSignature",
    "ReportTypeV2",
    "ReportFormatV2",
    "ReportStatusV2",
    # Phase 3 models
    "Project",
    "ProjectStatus",
    "ProjectScope",
    "ProjectType",
    "Scan",
    "ScanStatus",
    "ScanType",
    "Finding",
    "Severity",
    # Phase 9 models
    "ProjectMember",
    "ProjectRole",
    "Target",
    "TargetType",
    "TargetStatus",
    # Phase 8 models
    "AlertRule",
    "AlertChannel",
    "AlertTrigger",
    "Notification",
    "NotificationStatus",
    # Phase 12 models
    "CVE",
    "MitreTechnique",
    "IOC",
    "IOCType",
    "IOCThreatLevel",
    # Phase 13 models
    "ComplianceFramework",
    "ComplianceRequirement",
    "ComplianceMappingResult",
    "ComplianceEvidenceLog",
    "ComplianceControlMatrix",
    "ComplianceFrameworkType",
    "ComplianceStatus",
    "EvidenceStatus",
    "ControlImplementationStatus",
]
