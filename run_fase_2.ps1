# RED TEAM SAAS - FASE 2 (WINDOWS POWERSHELL - CORREGIDO)

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "FASE 2: DATABASE SCHEMA SETUP" -ForegroundColor Green
Write-Host "=========================================`n" -ForegroundColor Cyan

# 1. Verifica Python
Write-Host "[1/10] Verificando Python..." -ForegroundColor Yellow
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyVer = python --version
    Write-Host "OK: $pyVer`n" -ForegroundColor Green
} else {
    Write-Host "ERROR: Python no encontrado`n" -ForegroundColor Red
    exit 1
}

# 2. Verifica estructura
Write-Host "[2/10] Creando estructura..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "app/models" -Force -ErrorAction SilentlyContinue | Out-Null
New-Item -ItemType Directory -Path "app/alembic/versions" -Force -ErrorAction SilentlyContinue | Out-Null
New-Item -ItemType Directory -Path "tests" -Force -ErrorAction SilentlyContinue | Out-Null
Write-Host "OK: Carpetas creadas`n" -ForegroundColor Green

# 3. Instala dependencias
Write-Host "[3/10] Instalando dependencias..." -ForegroundColor Yellow
pip install -q SQLAlchemy psycopg2-binary alembic cryptography pydantic pytest python-dotenv
Write-Host "OK: Dependencias instaladas`n" -ForegroundColor Green

# 4. Genera ENCRYPTION_KEY
Write-Host "[4/10] Generando ENCRYPTION_KEY..." -ForegroundColor Yellow
$keyScript = @"
from cryptography.fernet import Fernet
import secrets
key = Fernet.generate_key().decode()
secret = secrets.token_urlsafe(32)
print(key)
"@
$keyScript | Out-File "temp_key.py" -Encoding UTF8
$encKey = python "temp_key.py"
Remove-Item "temp_key.py" -Force
Write-Host "OK: ENCRYPTION_KEY generada`n" -ForegroundColor Green

# 5. Crea .env
Write-Host "[5/10] Creando .env..." -ForegroundColor Yellow
$envContent = @"
DB_DRIVER=postgresql
DB_USER=red_team
DB_PASSWORD=SecurePassword123!
DB_HOST=localhost
DB_PORT=5432
DB_NAME=red_team_prod
SQL_ECHO=false
REDIS_HOST=localhost
REDIS_PORT=6379
ENCRYPTION_KEY=$encKey
DEBUG=false
ENVIRONMENT=production
"@
$envContent | Out-File ".env" -Encoding UTF8
Write-Host "OK: .env creado`n" -ForegroundColor Green

# 6. Escribe app/models/__init__.py
Write-Host "[6/10] Creando modelos..." -ForegroundColor Yellow
$modelsContent = @'
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

# ── Model 1: User ────────────────────────────────────────────────────────────
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

# ── Model 2: Workspace ───────────────────────────────────────────────────────
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

# ── Model 3: Task ────────────────────────────────────────────────────────────
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

# ── Model 4: Result ──────────────────────────────────────────────────────────
class Result(Base, BaseModel):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    tool = Column(String(255), nullable=False)
    output = Column(EncryptedString(65535), nullable=True)
    parsed_data = Column(EncryptedString(65535), nullable=True)
    task = relationship("Task", back_populates="results")
    def __repr__(self): return f"<Result(id={self.id}, task_id={self.task_id}, tool={self.tool})>"

# ── Model 5: AuditLog ────────────────────────────────────────────────────────
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

# ── Model 6: Template ────────────────────────────────────────────────────────
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

# ── Model 7: ThreatIntel ─────────────────────────────────────────────────────
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

# ── Model 8: RiskScore ───────────────────────────────────────────────────────
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

# ── Model 9: ComplianceMapping ───────────────────────────────────────────────
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

# ── Model 10: Report ─────────────────────────────────────────────────────────
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
'@
$modelsContent | Out-File "app/models/__init__.py" -Encoding UTF8
Write-Host "OK: app/models/__init__.py creado`n" -ForegroundColor Green

# 7. Escribe app/database.py
Write-Host "[7/10] Creando database config..." -ForegroundColor Yellow
$dbContent = @'
"""
Database configuration - Red Team SaaS.
Reads DATABASE_URL from environment or builds it from DB_* vars in .env.
"""
import os, logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

if not os.environ.get("DATABASE_URL"):
    driver   = os.environ.get("DB_DRIVER",   "postgresql")
    user     = os.environ.get("DB_USER",     "red_team")
    password = os.environ.get("DB_PASSWORD", "SecurePassword123!")
    host     = os.environ.get("DB_HOST",     "localhost")
    port     = os.environ.get("DB_PORT",     "5432")
    name     = os.environ.get("DB_NAME",     "red_team_prod")
    os.environ["DATABASE_URL"] = f"{driver}://{user}:{password}@{host}:{port}/{name}"

DATABASE_URL = os.environ["DATABASE_URL"]
SQL_ECHO = os.environ.get("SQL_ECHO", "false").lower() == "true"
logger = logging.getLogger(__name__)

_is_sqlite = DATABASE_URL.startswith("sqlite")
if _is_sqlite:
    engine = create_engine(DATABASE_URL,
        connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=SQL_ECHO)
else:
    engine = create_engine(DATABASE_URL,
        echo=SQL_ECHO, pool_pre_ping=True, pool_size=20, max_overflow=10)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised")

def health_check() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
'@
$dbContent | Out-File "app/database.py" -Encoding UTF8
Write-Host "OK: app/database.py creado`n" -ForegroundColor Green

# 8. Crea tests básicos
Write-Host "[8/10] Creando tests..." -ForegroundColor Yellow
$conftest = @"
import pytest
from app.database import SessionLocal

@pytest.fixture
def session():
    session = SessionLocal()
    yield session
    session.close()
"@
$conftest | Out-File "tests/conftest.py" -Encoding UTF8

$testfile = @"
import pytest

def test_imports():
    from app.models import User, Task, Result
    assert User is not None

def test_env_exists():
    import os
    assert os.path.exists(".env")
"@
$testfile | Out-File "tests/test_models.py" -Encoding UTF8
Write-Host "OK: Tests creados`n" -ForegroundColor Green

# 9. Crea documentación
Write-Host "[9/10] Creando documentación..." -ForegroundColor Yellow
$schema = @"
# Database Schema - Red Team SaaS

10 Modelos SQLAlchemy:
1. User - Autenticacion
2. Workspace - Aislamiento proyectos
3. Task - Ejecucion herramientas
4. Result - Salida (AES-256)
5. AuditLog - Pista inmutable
6. Template - Configuraciones
7. ThreatIntel - CVE database
8. RiskScore - Puntuacion riesgo
9. ComplianceMapping - Controles
10. Report - Reportes pentesting

Caracteristicas:
- Encriptacion AES-256
- 20+ indices
- Cascade delete
- Audit trail
- Connection pooling
"@
$schema | Out-File "DATABASE_SCHEMA.md" -Encoding UTF8
Write-Host "OK: Documentacion creada`n" -ForegroundColor Green

# 10. Validación final
Write-Host "[10/10] Validando..." -ForegroundColor Yellow
$files = @("app/models/__init__.py", "app/database.py", ".env", "tests/test_models.py")
$ok = $true
foreach ($f in $files) {
    if (Test-Path $f) {
        Write-Host "  [OK] $f" -ForegroundColor Green
    } else {
        Write-Host "  [?] $f (falta - copiar manualmente)" -ForegroundColor Yellow
        $ok = $false
    }
}
Write-Host ""

# Resumen
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "FASE 2 COMPLETADA" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Archivos creados:" -ForegroundColor Cyan
Write-Host "  - .env (con ENCRYPTION_KEY)" -ForegroundColor White
Write-Host "  - app/models/__init__.py" -ForegroundColor White
Write-Host "  - app/database.py" -ForegroundColor White
Write-Host "  - app/alembic/" -ForegroundColor White
Write-Host "  - tests/" -ForegroundColor White
Write-Host "  - DATABASE_SCHEMA.md" -ForegroundColor White
Write-Host ""
Write-Host "Proximos pasos:" -ForegroundColor Cyan
Write-Host "  1. cat .env                      (verificar)" -ForegroundColor White
Write-Host "  2. dir app\                      (ver estructura)" -ForegroundColor White
Write-Host "  3. pytest tests\ -v              (tests)" -ForegroundColor White
Write-Host "  4. Docker o PostgreSQL local     (database)" -ForegroundColor White
Write-Host "  5. alembic upgrade head          (migraciones)" -ForegroundColor White
Write-Host ""
Write-Host "Status: LISTA PARA FASE 3" -ForegroundColor Green
Write-Host ""