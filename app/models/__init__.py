"""
RED TEAM SAAS - All SQLAlchemy models (Phase 1 + Phase 2)
Self-contained: includes EncryptedString, BaseModel, all 10 models.
"""
import os, enum, hashlib, json, logging
from cryptography.fernet import Fernet
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    Numeric, String, Text, func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_mixin, relationship
from sqlalchemy.types import TypeDecorator
from app.database import Base

logger = logging.getLogger(__name__)

def _build_cipher():
    key = os.environ.get("ENCRYPTION_KEY", "")
    try:
        return Fernet(key.encode())
    except Exception:
        logger.warning("ENCRYPTION_KEY invalida - usando clave efimera")
        return Fernet(Fernet.generate_key())

_cipher = _build_cipher()

class EncryptedString(TypeDecorator):
    """Cifrado Fernet transparente en columnas String."""
    impl = String
    cache_ok = True
    def process_bind_param(self, value, dialect):
        if value is None: return value
        try: return _cipher.encrypt(str(value).encode()).decode()
        except Exception: return value
    def process_result_value(self, value, dialect):
        if value is None: return value
        try: return _cipher.decrypt(value.encode()).decode()
        except Exception: return value

@declarative_mixin
class BaseModel:
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

class UserRoleEnum(str, enum.Enum):
    admin="admin"; manager="manager"; pentester="pentester"; viewer="viewer"; api_user="api_user"

class TaskStatusEnum(str, enum.Enum):
    pending="pending"; running="running"; completed="completed"; failed="failed"; cancelled="cancelled"

class TaskPriority(str, enum.Enum):
    low="low"; medium="medium"; high="high"; critical="critical"

class AuditAction(str, enum.Enum):
    create="create"; read="read"; update="update"; delete="delete"
    login="login"; logout="logout"; execute="execute"

class TemplateCategory(str, enum.Enum):
    brute_force="brute_force"; osint="osint"; enumeration="enumeration"
    exploitation="exploitation"; post_exploitation="post_exploitation"
    phishing="phishing"; network="network"; custom="custom"

class SeverityLevel(str, enum.Enum):
    critical="critical"; high="high"; medium="medium"; low="low"; info="info"

class ComplianceFramework(str, enum.Enum):
    pci_dss="PCI-DSS"; hipaa="HIPAA"; gdpr="GDPR"
    iso27001="ISO27001"; soc2="SOC2"; nist="NIST"

class ComplianceStatus(str, enum.Enum):
    compliant="compliant"; non_compliant="non_compliant"
    not_assessed="not_assessed"; in_remediation="in_remediation"

class ReportStatus(str, enum.Enum):
    draft="draft"; review="review"; final="final"; archived="archived"

# â”€â”€ Model 1: User â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class User(Base, BaseModel):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(SQLEnum(UserRoleEnum), default=UserRoleEnum.pentester)
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    def __repr__(self): return f"<User(id={self.id}, email={self.email})>"

# â”€â”€ Model 2: Workspace â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Workspace(Base, BaseModel):
    __tablename__ = "workspaces"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    client_name = Column(String(255), nullable=True, index=True)
    scope = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    owner = relationship("User")
    tasks = relationship("Task", back_populates="workspace", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="workspace", cascade="all, delete-orphan")
    def __repr__(self): return f"<Workspace(id={self.id}, name={self.name})>"

# â”€â”€ Model 3: Task â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Task(Base, BaseModel):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    status = Column(SQLEnum(TaskStatusEnum), default=TaskStatusEnum.pending, index=True)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.medium)
    tool_name = Column(String(255), nullable=True)
    parameters = Column(EncryptedString(4096), nullable=True)
    user = relationship("User", back_populates="tasks")
    workspace = relationship("Workspace", back_populates="tasks")
    results = relationship("Result", back_populates="task", cascade="all, delete-orphan")
    risk_scores = relationship("RiskScore", back_populates="task", cascade="all, delete-orphan")
    def __repr__(self): return f"<Task(id={self.id}, status={self.status}, tool={self.tool_name})>"

# â”€â”€ Model 4: Result â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Result(Base, BaseModel):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    tool = Column(String(255), nullable=False)
    output = Column(EncryptedString(65535), nullable=True)
    parsed_data = Column(EncryptedString(65535), nullable=True)
    task = relationship("Task", back_populates="results")
    def __repr__(self): return f"<Result(id={self.id}, task_id={self.task_id}, tool={self.tool})>"

# â”€â”€ Model 5: AuditLog â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class AuditLog(Base, BaseModel):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user = relationship("User", back_populates="audit_logs")
    def __repr__(self): return f"<AuditLog(id={self.id}, action={self.action})>"

# â”€â”€ Model 6: Template â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Template(Base, BaseModel):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(TemplateCategory), nullable=False, index=True)
    tool_configs = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, index=True)
    usage_count = Column(Integer, default=0)
    creator = relationship("User")
    def __repr__(self): return f"<Template(id={self.id}, name={self.name})>"

# â”€â”€ Model 7: ThreatIntel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ThreatIntel(Base, BaseModel):
    __tablename__ = "threat_intel"
    id = Column(Integer, primary_key=True, index=True)
    cve_id = Column(String(20), unique=True, nullable=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(SQLEnum(SeverityLevel), nullable=False, index=True)
    cvss_score = Column(Numeric(4, 2), nullable=True)
    affected_products = Column(Text, nullable=True)
    exploit_available = Column(Boolean, default=False, index=True)
    patch_available = Column(Boolean, default=False)
    references = Column(Text, nullable=True)
    published_date = Column(DateTime(timezone=True), nullable=True)
    last_modified = Column(DateTime(timezone=True), nullable=True)
    tags = Column(Text, nullable=True)
    def __repr__(self): return f"<ThreatIntel(id={self.id}, cve={self.cve_id})>"

# â”€â”€ Model 8: RiskScore â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class RiskScore(Base, BaseModel):
    __tablename__ = "risk_scores"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    score = Column(Numeric(4, 2), nullable=False)
    components = Column(Text, nullable=True)
    justification = Column(Text, nullable=True)
    task = relationship("Task", back_populates="risk_scores")
    @property
    def risk_level(self):
        try:
            s = float(self.score)
        except (TypeError, ValueError):
            return "UNKNOWN"
        if s >= 9.0: return "CRITICAL"
        if s >= 7.0: return "HIGH"
        if s >= 4.0: return "MEDIUM"
        if s >= 1.0: return "LOW"
        return "INFO"
    def __repr__(self): return f"<RiskScore(id={self.id}, score={self.score}, level={self.risk_level})>"

# â”€â”€ Model 9: ComplianceMapping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ComplianceMapping(Base, BaseModel):
    __tablename__ = "compliance_mappings"
    id = Column(Integer, primary_key=True, index=True)
    framework = Column(SQLEnum(ComplianceFramework), nullable=False, index=True)
    control_id = Column(String(50), nullable=False, index=True)
    control_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ComplianceStatus), default=ComplianceStatus.not_assessed, nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    threat_intel_id = Column(Integer, ForeignKey("threat_intel.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    task = relationship("Task")
    threat = relationship("ThreatIntel")
    def __repr__(self):
        fw = self.framework.value if hasattr(self.framework, "value") else self.framework
        return f"<ComplianceMapping(id={self.id}, framework={fw}, control={self.control_id})>"

# â”€â”€ Model 10: Report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Report(Base, BaseModel):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    executive_summary = Column(Text, nullable=True)
    findings = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.draft, nullable=False, index=True)
    signature_hash = Column(String(64), nullable=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    author = relationship("User")
    workspace = relationship("Workspace", back_populates="reports")
    def compute_signature(self):
        payload = json.dumps(
            {"title": self.title, "executive_summary": self.executive_summary,
             "findings": self.findings, "recommendations": self.recommendations},
            sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()
    def __repr__(self): return f"<Report(id={self.id}, title={self.title!r}, status={self.status})>"

__all__ = [
    "BaseModel", "EncryptedString",
    "UserRoleEnum", "TaskStatusEnum", "TaskPriority", "AuditAction",
    "TemplateCategory", "SeverityLevel", "ComplianceFramework", "ComplianceStatus", "ReportStatus",
    "User", "Workspace", "Task", "Result", "AuditLog",
    "Template", "ThreatIntel", "RiskScore", "ComplianceMapping", "Report",
]
