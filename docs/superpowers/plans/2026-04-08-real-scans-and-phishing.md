# Real Scan Execution + Phishing Campaigns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stub `execute_scan` Celery task with real tool execution, then implement phishing campaigns as a full standalone feature (backend + frontend).

**Architecture:**
- Part 1 (Scans): `execute_scan` loops over `scan.tools`, creates a `Task` per tool, runs each via `SubprocessExecutor`, stores `Result` + `Finding` rows, and publishes progress to Redis. The existing `SubprocessExecutor`, `ToolRegistry`, and `findings_processor` are reused as-is.
- Part 2 (Phishing): A new standalone module with its own model (`PhishingCampaign`, `PhishingTarget`), GoPhish HTTP client, CRUD, API endpoints, Celery sync task, and React UI page. GoPhish is treated as an external service configured per-campaign.

**Tech Stack:** FastAPI, SQLAlchemy, Celery/Redis, Pydantic v2, React/TypeScript, Tailwind CSS, GoPhish REST API (via `httpx`)

---

## Part 1 — Real Scan Execution

### Task 1: Register scan_tasks in Celery and wire tool imports

**Files:**
- Modify: `backend/app/tasks/celery_app.py`
- Modify: `backend/app/tasks/scan_tasks.py`

- [ ] **Step 1: Add scan_tasks to Celery includes**

In `backend/app/tasks/celery_app.py`, add `"app.tasks.scan_tasks"` to the includes list:

```python
celery_app = Celery(
    "redteam_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.scan_tasks",        # ← add this first
        "app.tasks.tool_executor",
        "app.tasks.cleanup_tasks",
        "app.tasks.report_tasks",
        "app.tasks.analytics_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.threat_intel_tasks",
        "app.tasks.compliance_tasks",
        "app.tasks.integration_tasks",
    ],
)
```

- [ ] **Step 2: Verify Celery can load without error**

```bash
cd backend
python -c "from app.tasks.celery_app import celery_app; print('OK', celery_app.tasks.keys())"
```

Expected: prints `OK` and a list of task names.

- [ ] **Step 3: Commit**

```bash
git add backend/app/tasks/celery_app.py
git commit -m "feat(scans): register scan_tasks in Celery includes"
```

---

### Task 2: Implement real execute_scan task

**Files:**
- Modify: `backend/app/tasks/scan_tasks.py`

The task must:
1. Import all tool definitions so they self-register in `ToolRegistry`
2. Load the scan; set status=running, started_at=now
3. For each tool_name in `scan.tools` JSON array:
   - Create a `Task` DB record (linked to project + user)
   - Instantiate tool from `ToolRegistry`
   - Run via `SubprocessExecutor` with a Redis progress-line callback
   - Store a `Result` record with raw/parsed output and findings JSON
   - Call `process_result_findings(db, result_obj)` → creates `Finding` rows
   - Back-fill `finding.scan_id` on every new Finding
   - Increment `scan.progress` and write it to Redis (`scan:{id}:progress`)
4. Set scan.status = completed if any tool succeeded, else failed
5. Set scan.completed_at = now

- [ ] **Step 1: Replace scan_tasks.py**

```python
"""Celery task for real scan execution — runs each tool sequentially."""
import json
import logging
from datetime import datetime, timezone

from celery import shared_task

from app.tasks.celery_app import celery_app
from app.tasks.base_task import BaseRedTeamTask

# Import tool definitions so they auto-register in ToolRegistry
import app.core.tool_definitions  # noqa: F401

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    base=BaseRedTeamTask,
    name="app.tasks.scan_tasks.execute_scan",
    max_retries=1,
    default_retry_delay=30,
)
def execute_scan(self, scan_id: int):
    """Execute all tools listed in a scan sequentially."""
    from app.database import SessionLocal
    from app.models.scan import Scan, ScanStatus
    from app.models.task import Task as TaskModel, TaskStatusEnum
    from app.models.result import Result
    from app.models.finding import Finding
    from app.core.tool_engine.tool_registry import ToolRegistry
    from app.core.tool_engine.executor import SubprocessExecutor
    from app.core.findings_processor import process_result_findings
    from app.core.security import EncryptionHandler

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.warning("execute_scan: scan %s not found", scan_id)
            return {"scan_id": scan_id, "status": "not_found"}

        # Parse tools and options from JSON columns
        try:
            tools: list = json.loads(scan.tools) if scan.tools else []
        except (json.JSONDecodeError, TypeError):
            tools = []

        try:
            # EncryptedString auto-decrypts to a JSON string on read
            options: dict = json.loads(scan.options) if scan.options else {}
        except (json.JSONDecodeError, TypeError):
            options = {}

        if not tools:
            scan.status = ScanStatus.completed
            scan.progress = 100
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"scan_id": scan_id, "status": "completed", "tools": 0}

        # Mark scan as running
        scan.status = ScanStatus.running
        scan.started_at = datetime.now(timezone.utc)
        scan.progress = 0
        db.commit()

        total = len(tools)
        completed = 0
        any_success = False

        for tool_name in tools:
            task_obj = None
            try:
                # Create a Task record for this tool execution
                task_obj = TaskModel(
                    name=f"{scan.name} — {tool_name}",
                    user_id=scan.created_by,
                    project_id=scan.project_id,
                    status=TaskStatusEnum.running,
                    tool_name=tool_name,
                    target=scan.target,
                    options=options,
                )
                db.add(task_obj)
                db.commit()
                db.refresh(task_obj)

                output_lines = []

                def _on_output(line: str, _task_id=task_obj.id):
                    output_lines.append(line)
                    try:
                        from app.core.redis_client import redis_client
                        redis_client.publish(
                            f"task:{_task_id}:output",
                            json.dumps({"line": line, "task_id": _task_id}),
                        )
                    except Exception:
                        pass

                tool_class = ToolRegistry.get(tool_name)
                tool_instance = tool_class()
                executor = SubprocessExecutor(output_callback=_on_output)
                result = executor.execute(tool_instance, scan.target, options)

                # Persist result
                result_obj = Result(
                    task_id=task_obj.id,
                    tool_name=tool_name,
                    tool=tool_name,
                    target=scan.target,
                    raw_output=EncryptionHandler.encrypt(result.raw_output) if result.raw_output else None,
                    parsed_output=result.parsed_output,
                    findings=result.findings,
                    risk_score=result.risk_score,
                    exit_code=result.exit_code,
                    duration_seconds=result.duration_seconds,
                    success=result.success,
                    error_message=result.error,
                )
                db.add(result_obj)
                task_obj.status = TaskStatusEnum.completed if result.success else TaskStatusEnum.failed
                task_obj.error_message = result.error
                db.commit()
                db.refresh(result_obj)

                # Extract findings → Finding rows
                if result.findings:
                    try:
                        created = process_result_findings(db, result_obj)
                        # Back-fill scan_id so findings are linked to the scan
                        for f in created:
                            f.scan_id = scan_id
                        db.commit()
                    except Exception as fp_exc:
                        logger.warning("findings_processor failed (scan %s, tool %s): %s", scan_id, tool_name, fp_exc)

                if result.success:
                    any_success = True

            except ValueError as ve:
                # Tool not registered in registry (not installed or unknown name)
                logger.warning("execute_scan: tool '%s' not in registry: %s", tool_name, ve)
                if task_obj:
                    task_obj.status = TaskStatusEnum.failed
                    task_obj.error_message = str(ve)
                    db.commit()

            except Exception as exc:
                logger.error("execute_scan: tool '%s' failed for scan %s: %s", tool_name, scan_id, exc)
                if task_obj:
                    try:
                        task_obj.status = TaskStatusEnum.failed
                        task_obj.error_message = str(exc)
                        db.commit()
                    except Exception:
                        pass

            finally:
                completed += 1
                progress = int(completed / total * 100)
                scan.progress = progress
                db.commit()
                # Publish progress to Redis for real-time polling
                try:
                    from app.core.redis_client import redis_client
                    redis_client.set(f"scan:{scan_id}:progress", str(progress), ex=3600)
                except Exception:
                    pass

        # Finalise scan
        scan.status = ScanStatus.completed if any_success else ScanStatus.failed
        scan.progress = 100
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("execute_scan: scan %s done — status=%s tools=%s", scan_id, scan.status, total)
        return {"scan_id": scan_id, "status": scan.status, "tools": total}

    except Exception as exc:
        logger.exception("execute_scan: unhandled error for scan %s: %s", scan_id, exc)
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.status = ScanStatus.failed
                scan.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        db.close()
```

- [ ] **Step 2: Verify task loads**

```bash
cd backend
python -c "
from app.tasks.scan_tasks import execute_scan
print('Task registered:', execute_scan.name)
from app.core.tool_engine.tool_registry import ToolRegistry
print('Tools registered:', ToolRegistry.all_names())
"
```

Expected: prints task name and list of tool names (nmap, nikto, gobuster, etc.)

- [ ] **Step 3: Commit**

```bash
git add backend/app/tasks/scan_tasks.py
git commit -m "feat(scans): implement real tool execution in execute_scan task"
```

---

### Task 3: Fix Redis client usage in scan_tasks (sync vs async)

The existing `redis_client` in `app.core.redis` is async (`redis.asyncio`). The `redis_client` in `app.core.redis_client` is used in `tool_executor.py` synchronously — verify which one to use.

**Files:**
- Read: `backend/app/core/redis_client.py`

- [ ] **Step 1: Check redis_client.py**

```bash
cat backend/app/core/redis_client.py
```

If it's a sync Redis client (no `asyncio`), the scan_tasks.py code is correct as-is.

If it's also async, replace the Redis calls in scan_tasks.py with a direct sync Redis connection:

```python
# In the _on_output callback and progress update, replace:
from app.core.redis_client import redis_client
redis_client.publish(...)
redis_client.set(...)

# With:
import redis as sync_redis
_r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
_r.publish(...)
_r.set(...)
```

- [ ] **Step 2: Verify by running a quick import check**

```bash
cd backend
python -c "
from app.core.redis_client import redis_client
print(type(redis_client))
"
```

If output contains `asyncio`, apply the sync fix.

- [ ] **Step 3: Commit if changed**

```bash
git add backend/app/tasks/scan_tasks.py
git commit -m "fix(scans): use sync Redis client in Celery task"
```

---

### Task 4: Test scan execution end-to-end

- [ ] **Step 1: Start services (if not running)**

```bash
docker-compose up -d redis postgres
```

- [ ] **Step 2: Run a test scan via Python (without HTTP layer)**

```bash
cd backend
python -c "
from app.database import SessionLocal
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.project import Project
from app.models.user import User

db = SessionLocal()

# Get first project and user
project = db.query(Project).first()
user = db.query(User).first()

if not project or not user:
    print('ERROR: need at least one project and user in DB')
    exit(1)

import json
scan = Scan(
    name='Test nmap scan',
    project_id=project.id,
    created_by=user.id,
    scan_type=ScanType.recon,
    target='scanme.nmap.org',
    tools=json.dumps(['nmap']),
    options=json.dumps({'profile': 'quick'}),
)
db.add(scan)
db.commit()
db.refresh(scan)
print('Created scan id:', scan.id)
db.close()
"
```

Expected: prints `Created scan id: N`

- [ ] **Step 3: Run the task directly (bypassing Celery)**

```bash
cd backend
python -c "
from app.tasks.scan_tasks import execute_scan
result = execute_scan(SCAN_ID_FROM_STEP_2)
print('Result:', result)
"
```

Replace `SCAN_ID_FROM_STEP_2` with the actual ID.

Expected: `Result: {'scan_id': N, 'status': 'completed', 'tools': 1}` (or `failed` if nmap not installed — that's fine, the error is handled)

- [ ] **Step 4: Verify DB state**

```bash
cd backend
python -c "
from app.database import SessionLocal
from app.models.scan import Scan
from app.models.finding import Finding

db = SessionLocal()
scan = db.query(Scan).order_by(Scan.id.desc()).first()
print('Scan status:', scan.status, 'progress:', scan.progress)
findings = db.query(Finding).filter(Finding.scan_id == scan.id).all()
print('Findings created:', len(findings))
for f in findings[:3]:
    print(' -', f.severity, f.title)
db.close()
"
```

Expected: status=completed or failed, progress=100, findings ≥ 0.

- [ ] **Step 5: Commit**

No new code — just verify. If any bug found, fix and commit:

```bash
git add backend/app/tasks/scan_tasks.py
git commit -m "fix(scans): <describe fix>"
```

---

## Part 2 — Phishing Campaigns

### Task 5: PhishingCampaign and PhishingTarget models

**Files:**
- Create: `backend/app/models/phishing.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create phishing.py model**

```python
"""Phishing campaign models"""
import enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Enum as SQLEnum, Boolean,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel
from app.core.security import EncryptedString


class PhishingCampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class PhishingTargetStatus(str, enum.Enum):
    queued = "queued"
    sent = "sent"
    opened = "opened"
    clicked = "clicked"
    submitted_data = "submitted_data"
    reported = "reported"


class PhishingCampaign(Base, BaseModel):
    """A phishing simulation campaign backed by a GoPhish server."""

    __tablename__ = "phishing_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(PhishingCampaignStatus),
        default=PhishingCampaignStatus.draft,
        nullable=False,
        index=True,
    )

    # GoPhish server config (per-campaign so teams can use different servers)
    gophish_url = Column(String(500), nullable=False)
    gophish_api_key = Column(EncryptedString(500), nullable=False)
    gophish_campaign_id = Column(Integer, nullable=True)  # ID on GoPhish server

    # Campaign content references (names of resources on GoPhish)
    template_name = Column(String(200), nullable=True)
    landing_page_name = Column(String(200), nullable=True)
    smtp_profile_name = Column(String(200), nullable=True)
    target_group_name = Column(String(200), nullable=True)
    phishing_url = Column(String(500), nullable=True)
    launch_date = Column(DateTime(timezone=True), nullable=True)

    # Stats cached from GoPhish (refreshed by sync task)
    stats_total = Column(Integer, default=0)
    stats_sent = Column(Integer, default=0)
    stats_opened = Column(Integer, default=0)
    stats_clicked = Column(Integer, default=0)
    stats_submitted = Column(Integer, default=0)
    stats_last_synced = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project")
    creator = relationship("User", foreign_keys=[created_by])
    targets = relationship(
        "PhishingTarget",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


class PhishingTarget(Base, BaseModel):
    """An individual email target within a phishing campaign."""

    __tablename__ = "phishing_targets"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer,
        ForeignKey("phishing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    status = Column(
        SQLEnum(PhishingTargetStatus),
        default=PhishingTargetStatus.queued,
        nullable=False,
    )

    campaign = relationship("PhishingCampaign", back_populates="targets")
```

- [ ] **Step 2: Add imports to models/__init__.py**

Add after the Phase 17 models import block:

```python
# Phishing
from app.models.phishing import (
    PhishingCampaign,
    PhishingCampaignStatus,
    PhishingTarget,
    PhishingTargetStatus,
)
```

And add to `__all__`:

```python
    # Phishing
    "PhishingCampaign",
    "PhishingCampaignStatus",
    "PhishingTarget",
    "PhishingTargetStatus",
```

- [ ] **Step 3: Verify tables are created**

```bash
cd backend
python -c "
from app.database import init_db
import app.models  # noqa
init_db()
print('Tables created OK')
"
```

Expected: `Tables created OK` (no errors).

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/phishing.py backend/app/models/__init__.py
git commit -m "feat(phishing): add PhishingCampaign and PhishingTarget models"
```

---

### Task 6: Pydantic schemas for phishing

**Files:**
- Create: `backend/app/schemas/phishing.py`

- [ ] **Step 1: Create schemas/phishing.py**

```python
"""Phishing campaign schemas"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PhishingCampaignStatus(str, Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class PhishingTargetStatus(str, Enum):
    queued = "queued"
    sent = "sent"
    opened = "opened"
    clicked = "clicked"
    submitted_data = "submitted_data"
    reported = "reported"


# ── Target ────────────────────────────────────────────────────────────────────

class PhishingTargetCreate(BaseModel):
    email: str = Field(..., max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)


class PhishingTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    status: PhishingTargetStatus
    created_at: datetime


# ── Campaign ──────────────────────────────────────────────────────────────────

class PhishingCampaignCreate(BaseModel):
    project_id: int
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    gophish_url: str = Field(..., max_length=500, description="Base URL of GoPhish server (e.g. http://localhost:3333)")
    gophish_api_key: str = Field(..., description="GoPhish API key")
    template_name: Optional[str] = Field(None, max_length=200)
    landing_page_name: Optional[str] = Field(None, max_length=200)
    smtp_profile_name: Optional[str] = Field(None, max_length=200)
    target_group_name: Optional[str] = Field(None, max_length=200)
    phishing_url: Optional[str] = Field(None, max_length=500)
    launch_date: Optional[datetime] = None


class PhishingCampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    template_name: Optional[str] = None
    landing_page_name: Optional[str] = None
    smtp_profile_name: Optional[str] = None
    target_group_name: Optional[str] = None
    phishing_url: Optional[str] = None
    launch_date: Optional[datetime] = None


class PhishingCampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_by: int
    name: str
    description: Optional[str] = None
    status: PhishingCampaignStatus
    gophish_url: str
    gophish_campaign_id: Optional[int] = None
    template_name: Optional[str] = None
    landing_page_name: Optional[str] = None
    smtp_profile_name: Optional[str] = None
    target_group_name: Optional[str] = None
    phishing_url: Optional[str] = None
    launch_date: Optional[datetime] = None
    stats_total: int = 0
    stats_sent: int = 0
    stats_opened: int = 0
    stats_clicked: int = 0
    stats_submitted: int = 0
    stats_last_synced: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PhishingCampaignListResponse(BaseModel):
    items: List[PhishingCampaignResponse]
    total: int
    skip: int
    limit: int


# ── GoPhish resource lists (returned from GoPhish proxy endpoints) ─────────────

class GoPhishTemplate(BaseModel):
    id: int
    name: str


class GoPhishPage(BaseModel):
    id: int
    name: str


class GoPhishSMTP(BaseModel):
    id: int
    name: str


class GoPhishGroup(BaseModel):
    id: int
    name: str


class GoPhishResourcesResponse(BaseModel):
    templates: List[GoPhishTemplate] = []
    pages: List[GoPhishPage] = []
    smtp_profiles: List[GoPhishSMTP] = []
    groups: List[GoPhishGroup] = []


# ── Per-target results (proxied from GoPhish) ─────────────────────────────────

class PhishingTargetResult(BaseModel):
    email: str
    status: str
    ip: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reported: bool = False


class PhishingCampaignResults(BaseModel):
    campaign_id: int
    gophish_campaign_id: Optional[int] = None
    results: List[PhishingTargetResult] = []
    stats: dict = {}
```

- [ ] **Step 2: Verify import**

```bash
cd backend
python -c "from app.schemas.phishing import PhishingCampaignCreate, PhishingCampaignResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/phishing.py
git commit -m "feat(phishing): add Pydantic schemas"
```

---

### Task 7: GoPhish HTTP client service

**Files:**
- Create: `backend/app/services/gophish_client.py`

- [ ] **Step 1: Create gophish_client.py**

```python
"""HTTP client for the GoPhish REST API.

Usage:
    client = GoPhishClient(base_url="http://localhost:3333", api_key="...")
    campaigns = client.list_campaigns()
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0  # seconds


class GoPhishError(Exception):
    """Raised when GoPhish returns an error response."""


class GoPhishClient:
    def __init__(self, base_url: str, api_key: str):
        self._base = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> Any:
        url = f"{self._base}{path}"
        try:
            r = httpx.get(url, headers=self._headers, timeout=_TIMEOUT, verify=False)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            raise GoPhishError(f"GET {path} returned {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise GoPhishError(f"GET {path} failed: {exc}") from exc

    def _post(self, path: str, data: dict) -> Any:
        url = f"{self._base}{path}"
        try:
            r = httpx.post(url, headers=self._headers, json=data, timeout=_TIMEOUT, verify=False)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            raise GoPhishError(f"POST {path} returned {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise GoPhishError(f"POST {path} failed: {exc}") from exc

    def _delete(self, path: str) -> Any:
        url = f"{self._base}{path}"
        try:
            r = httpx.delete(url, headers=self._headers, timeout=_TIMEOUT, verify=False)
            r.raise_for_status()
            return r.json() if r.content else {}
        except httpx.HTTPStatusError as exc:
            raise GoPhishError(f"DELETE {path} returned {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise GoPhishError(f"DELETE {path} failed: {exc}") from exc

    # ── Campaigns ─────────────────────────────────────────────────────────────

    def list_campaigns(self) -> List[Dict]:
        data = self._get("/api/campaigns/")
        return data if isinstance(data, list) else []

    def create_campaign(self, payload: dict) -> Dict:
        return self._post("/api/campaigns/", payload)

    def get_campaign(self, campaign_id: int) -> Dict:
        return self._get(f"/api/campaigns/{campaign_id}")

    def get_campaign_results(self, campaign_id: int) -> Dict:
        return self._get(f"/api/campaigns/{campaign_id}/results")

    def get_campaign_summary(self, campaign_id: int) -> Dict:
        return self._get(f"/api/campaigns/{campaign_id}/summary")

    def complete_campaign(self, campaign_id: int) -> Dict:
        return self._get(f"/api/campaigns/{campaign_id}/complete")

    def delete_campaign(self, campaign_id: int) -> Dict:
        return self._delete(f"/api/campaigns/{campaign_id}")

    # ── Resources (for campaign creation) ────────────────────────────────────

    def list_templates(self) -> List[Dict]:
        data = self._get("/api/templates/")
        return data if isinstance(data, list) else []

    def list_pages(self) -> List[Dict]:
        data = self._get("/api/pages/")
        return data if isinstance(data, list) else []

    def list_smtp_profiles(self) -> List[Dict]:
        data = self._get("/api/smtp/")
        return data if isinstance(data, list) else []

    def list_groups(self) -> List[Dict]:
        data = self._get("/api/groups/")
        return data if isinstance(data, list) else []
```

- [ ] **Step 2: Verify httpx is available**

```bash
cd backend
python -c "import httpx; print('httpx', httpx.__version__)"
```

If not installed, add to requirements: `httpx>=0.27.0`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/gophish_client.py
git commit -m "feat(phishing): add GoPhish HTTP client"
```

---

### Task 8: Phishing CRUD

**Files:**
- Create: `backend/app/crud/phishing.py`

- [ ] **Step 1: Create crud/phishing.py**

```python
"""CRUD for PhishingCampaign and PhishingTarget"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.phishing import PhishingCampaign, PhishingTarget, PhishingCampaignStatus


class CRUDPhishingCampaign:

    def create(self, db: Session, *, data: dict) -> PhishingCampaign:
        obj = PhishingCampaign(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get(self, db: Session, campaign_id: int) -> Optional[PhishingCampaign]:
        return db.query(PhishingCampaign).filter(PhishingCampaign.id == campaign_id).first()

    def get_multi(
        self,
        db: Session,
        *,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Dict:
        q = db.query(PhishingCampaign)
        if project_id is not None:
            q = q.filter(PhishingCampaign.project_id == project_id)
        if status:
            q = q.filter(PhishingCampaign.status == status)
        total = q.with_entities(func.count()).scalar()
        items = q.order_by(PhishingCampaign.created_at.desc()).offset(skip).limit(limit).all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    def update(self, db: Session, *, obj: PhishingCampaign, data: dict) -> PhishingCampaign:
        for k, v in data.items():
            setattr(obj, k, v)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, *, obj: PhishingCampaign) -> None:
        db.delete(obj)
        db.commit()

    # ── Targets ───────────────────────────────────────────────────────────────

    def add_targets(self, db: Session, *, campaign_id: int, targets: List[dict]) -> List[PhishingTarget]:
        objs = [PhishingTarget(campaign_id=campaign_id, **t) for t in targets]
        db.add_all(objs)
        db.commit()
        for o in objs:
            db.refresh(o)
        return objs

    def list_targets(self, db: Session, *, campaign_id: int) -> List[PhishingTarget]:
        return (
            db.query(PhishingTarget)
            .filter(PhishingTarget.campaign_id == campaign_id)
            .order_by(PhishingTarget.id)
            .all()
        )

    def delete_target(self, db: Session, *, target_id: int, campaign_id: int) -> bool:
        obj = (
            db.query(PhishingTarget)
            .filter(PhishingTarget.id == target_id, PhishingTarget.campaign_id == campaign_id)
            .first()
        )
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True

    def update_stats(self, db: Session, *, campaign: PhishingCampaign, stats: dict) -> PhishingCampaign:
        from datetime import datetime, timezone
        campaign.stats_total = stats.get("total", 0)
        campaign.stats_sent = stats.get("sent", 0)
        campaign.stats_opened = stats.get("opened", 0)
        campaign.stats_clicked = stats.get("clicked", 0)
        campaign.stats_submitted = stats.get("submitted_data", 0)
        campaign.stats_last_synced = datetime.now(timezone.utc)
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign


crud_phishing = CRUDPhishingCampaign()
```

- [ ] **Step 2: Verify import**

```bash
cd backend
python -c "from app.crud.phishing import crud_phishing; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/crud/phishing.py
git commit -m "feat(phishing): add CRUD layer"
```

---

### Task 9: Phishing Celery sync task

**Files:**
- Create: `backend/app/tasks/phishing_tasks.py`
- Modify: `backend/app/tasks/celery_app.py`

- [ ] **Step 1: Create phishing_tasks.py**

```python
"""Celery tasks for phishing campaign stats synchronisation."""
import logging
from celery import shared_task
from app.tasks.base_task import BaseRedTeamTask

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=BaseRedTeamTask,
    name="app.tasks.phishing_tasks.sync_campaign_stats",
    max_retries=2,
    default_retry_delay=30,
)
def sync_campaign_stats(self, campaign_id: int):
    """Fetch latest stats from GoPhish and update the PhishingCampaign row."""
    from app.database import SessionLocal
    from app.models.phishing import PhishingCampaign, PhishingCampaignStatus, PhishingTarget, PhishingTargetStatus
    from app.services.gophish_client import GoPhishClient, GoPhishError
    from app.crud.phishing import crud_phishing

    db = SessionLocal()
    try:
        campaign = db.query(PhishingCampaign).filter(PhishingCampaign.id == campaign_id).first()
        if not campaign or not campaign.gophish_campaign_id:
            logger.info("sync_campaign_stats: campaign %s not found or not launched", campaign_id)
            return {"status": "skipped", "campaign_id": campaign_id}

        client = GoPhishClient(campaign.gophish_url, campaign.gophish_api_key)
        summary = client.get_campaign_summary(campaign.gophish_campaign_id)

        gp_stats = summary.get("stats", {})
        stats = {
            "total": gp_stats.get("total", 0),
            "sent": gp_stats.get("sent", 0),
            "opened": gp_stats.get("opened", 0),
            "clicked": gp_stats.get("clicked", 0),
            "submitted_data": gp_stats.get("submitted_data", 0),
        }
        crud_phishing.update_stats(db, campaign=campaign, stats=stats)

        # Sync per-target statuses from results
        try:
            results_data = client.get_campaign_results(campaign.gophish_campaign_id)
            STATUS_MAP = {
                "Email Sent": PhishingTargetStatus.sent,
                "Email Opened": PhishingTargetStatus.opened,
                "Clicked Link": PhishingTargetStatus.clicked,
                "Submitted Data": PhishingTargetStatus.submitted_data,
                "Email Reported": PhishingTargetStatus.reported,
            }
            for r in results_data.get("results", []):
                email = r.get("email", "")
                raw_status = r.get("status", "")
                new_status = STATUS_MAP.get(raw_status)
                if new_status and email:
                    target = (
                        db.query(PhishingTarget)
                        .filter(
                            PhishingTarget.campaign_id == campaign_id,
                            PhishingTarget.email == email,
                        )
                        .first()
                    )
                    if target:
                        target.status = new_status
            db.commit()
        except Exception as exc:
            logger.warning("sync_campaign_stats: could not sync per-target results: %s", exc)

        logger.info("sync_campaign_stats: campaign %s synced — %s", campaign_id, stats)
        return {"status": "ok", "campaign_id": campaign_id, "stats": stats}

    except GoPhishError as exc:
        logger.error("sync_campaign_stats: GoPhish error for campaign %s: %s", campaign_id, exc)
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception("sync_campaign_stats: unexpected error for campaign %s: %s", campaign_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()
```

- [ ] **Step 2: Add phishing_tasks to Celery includes**

In `backend/app/tasks/celery_app.py`, add:

```python
include=[
    "app.tasks.scan_tasks",
    "app.tasks.phishing_tasks",     # ← add
    "app.tasks.tool_executor",
    ...
],
```

- [ ] **Step 3: Verify**

```bash
cd backend
python -c "from app.tasks.phishing_tasks import sync_campaign_stats; print('OK', sync_campaign_stats.name)"
```

Expected: `OK app.tasks.phishing_tasks.sync_campaign_stats`

- [ ] **Step 4: Commit**

```bash
git add backend/app/tasks/phishing_tasks.py backend/app/tasks/celery_app.py
git commit -m "feat(phishing): add sync_campaign_stats Celery task"
```

---

### Task 10: Phishing API endpoints

**Files:**
- Create: `backend/app/api/v1/endpoints/phishing.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Create endpoints/phishing.py**

```python
"""Phishing campaign endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.phishing import PhishingCampaign, PhishingCampaignStatus
from app.crud.phishing import crud_phishing
from app.schemas.phishing import (
    PhishingCampaignCreate,
    PhishingCampaignUpdate,
    PhishingCampaignResponse,
    PhishingCampaignListResponse,
    PhishingTargetCreate,
    PhishingTargetResponse,
    PhishingCampaignResults,
    PhishingTargetResult,
    GoPhishResourcesResponse,
    GoPhishTemplate,
    GoPhishPage,
    GoPhishSMTP,
    GoPhishGroup,
)
from app.core.audit import log_action

router = APIRouter()


def _get_campaign_or_404(db: Session, campaign_id: int) -> PhishingCampaign:
    c = crud_phishing.get(db, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=PhishingCampaignListResponse)
async def list_campaigns(
    project_id: Optional[int] = Query(None),
    campaign_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = crud_phishing.get_multi(
        db, project_id=project_id, status=campaign_status, skip=skip, limit=limit
    )
    result["items"] = [PhishingCampaignResponse.model_validate(i) for i in result["items"]]
    return result


@router.post("/", response_model=PhishingCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: PhishingCampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    data = payload.model_dump()
    data["created_by"] = current_user.id
    campaign = crud_phishing.create(db, data=data)
    await log_action(db, user_id=current_user.id, action="phishing.create", resource_id=campaign.id)
    return campaign


@router.get("/{campaign_id}", response_model=PhishingCampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_campaign_or_404(db, campaign_id)


@router.put("/{campaign_id}", response_model=PhishingCampaignResponse)
async def update_campaign(
    campaign_id: int,
    payload: PhishingCampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    campaign = _get_campaign_or_404(db, campaign_id)
    if campaign.status == PhishingCampaignStatus.active:
        raise HTTPException(status_code=400, detail="Cannot edit an active campaign")
    data = payload.model_dump(exclude_unset=True)
    return crud_phishing.update(db, obj=campaign, data=data)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    campaign = _get_campaign_or_404(db, campaign_id)
    if campaign.status == PhishingCampaignStatus.active:
        raise HTTPException(status_code=400, detail="Stop the campaign before deleting")
    crud_phishing.delete(db, obj=campaign)
    await log_action(db, user_id=current_user.id, action="phishing.delete", resource_id=campaign_id)


# ── Targets ───────────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/targets", response_model=List[PhishingTargetResponse], status_code=status.HTTP_201_CREATED)
async def add_targets(
    campaign_id: int,
    targets: List[PhishingTargetCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    _get_campaign_or_404(db, campaign_id)
    objs = crud_phishing.add_targets(db, campaign_id=campaign_id, targets=[t.model_dump() for t in targets])
    return [PhishingTargetResponse.model_validate(o) for o in objs]


@router.get("/{campaign_id}/targets", response_model=List[PhishingTargetResponse])
async def list_targets(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_campaign_or_404(db, campaign_id)
    return [PhishingTargetResponse.model_validate(t) for t in crud_phishing.list_targets(db, campaign_id=campaign_id)]


@router.delete("/{campaign_id}/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    campaign_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    _get_campaign_or_404(db, campaign_id)
    deleted = crud_phishing.delete_target(db, target_id=target_id, campaign_id=campaign_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Target not found")


# ── Launch / Stop ─────────────────────────────────────────────────────────────

@router.post("/{campaign_id}/launch", response_model=PhishingCampaignResponse)
async def launch_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    """Create and start the campaign on GoPhish, then mark it as active."""
    from app.services.gophish_client import GoPhishClient, GoPhishError
    import json
    from datetime import datetime, timezone

    campaign = _get_campaign_or_404(db, campaign_id)
    if campaign.status != PhishingCampaignStatus.draft:
        raise HTTPException(status_code=400, detail=f"Campaign is already {campaign.status}")

    targets = crud_phishing.list_targets(db, campaign_id=campaign_id)
    if not targets:
        raise HTTPException(status_code=400, detail="Add at least one target before launching")

    client = GoPhishClient(campaign.gophish_url, campaign.gophish_api_key)
    payload = {
        "name": campaign.name,
        "template": {"name": campaign.template_name or ""},
        "page": {"name": campaign.landing_page_name or ""},
        "smtp": {"name": campaign.smtp_profile_name or ""},
        "url": campaign.phishing_url or "",
        "launch_date": campaign.launch_date.isoformat() if campaign.launch_date else datetime.now(timezone.utc).isoformat(),
        "groups": [{"name": campaign.target_group_name or campaign.name}],
    }

    try:
        gp_campaign = client.create_campaign(payload)
    except GoPhishError as exc:
        raise HTTPException(status_code=502, detail=f"GoPhish error: {exc}")

    updated = crud_phishing.update(db, obj=campaign, data={
        "gophish_campaign_id": gp_campaign.get("id"),
        "status": PhishingCampaignStatus.active,
    })
    await log_action(db, user_id=current_user.id, action="phishing.launch", resource_id=campaign_id)
    return updated


@router.post("/{campaign_id}/stop", response_model=PhishingCampaignResponse)
async def stop_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    """Mark the GoPhish campaign as complete and set status to completed."""
    from app.services.gophish_client import GoPhishClient, GoPhishError

    campaign = _get_campaign_or_404(db, campaign_id)
    if campaign.status != PhishingCampaignStatus.active:
        raise HTTPException(status_code=400, detail="Campaign is not active")

    if campaign.gophish_campaign_id:
        client = GoPhishClient(campaign.gophish_url, campaign.gophish_api_key)
        try:
            client.complete_campaign(campaign.gophish_campaign_id)
        except GoPhishError as exc:
            # Log but don't fail — still mark locally as completed
            pass

    updated = crud_phishing.update(db, obj=campaign, data={"status": PhishingCampaignStatus.completed})
    await log_action(db, user_id=current_user.id, action="phishing.stop", resource_id=campaign_id)
    return updated


# ── Results & Sync ────────────────────────────────────────────────────────────

@router.get("/{campaign_id}/results", response_model=PhishingCampaignResults)
async def get_results(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch per-target results directly from GoPhish."""
    from app.services.gophish_client import GoPhishClient, GoPhishError

    campaign = _get_campaign_or_404(db, campaign_id)
    if not campaign.gophish_campaign_id:
        return PhishingCampaignResults(campaign_id=campaign_id, results=[], stats={})

    client = GoPhishClient(campaign.gophish_url, campaign.gophish_api_key)
    try:
        data = client.get_campaign_results(campaign.gophish_campaign_id)
    except GoPhishError as exc:
        raise HTTPException(status_code=502, detail=f"GoPhish error: {exc}")

    results = [
        PhishingTargetResult(
            email=r.get("email", ""),
            status=r.get("status", ""),
            ip=r.get("ip"),
            latitude=r.get("latitude"),
            longitude=r.get("longitude"),
            reported=r.get("reported", False),
        )
        for r in data.get("results", [])
    ]
    return PhishingCampaignResults(
        campaign_id=campaign_id,
        gophish_campaign_id=campaign.gophish_campaign_id,
        results=results,
        stats=data.get("stats", {}),
    )


@router.post("/{campaign_id}/sync", response_model=PhishingCampaignResponse)
async def sync_stats(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enqueue a stats sync from GoPhish. Returns current state immediately."""
    campaign = _get_campaign_or_404(db, campaign_id)
    try:
        from app.tasks.phishing_tasks import sync_campaign_stats
        sync_campaign_stats.apply_async(args=[campaign_id], queue="default")
    except Exception:
        pass  # Celery unavailable — silently skip
    return campaign


# ── GoPhish resource proxy (for campaign creation form) ──────────────────────

@router.post("/resources", response_model=GoPhishResourcesResponse)
async def get_gophish_resources(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Proxy a call to a GoPhish server and return available templates,
    pages, SMTP profiles, and groups.

    Payload: {gophish_url: str, gophish_api_key: str}
    """
    from app.services.gophish_client import GoPhishClient, GoPhishError

    url = payload.get("gophish_url", "")
    key = payload.get("gophish_api_key", "")
    if not url or not key:
        raise HTTPException(status_code=400, detail="gophish_url and gophish_api_key are required")

    client = GoPhishClient(url, key)
    try:
        templates = [GoPhishTemplate(id=t["id"], name=t["name"]) for t in client.list_templates()]
        pages = [GoPhishPage(id=p["id"], name=p["name"]) for p in client.list_pages()]
        smtp = [GoPhishSMTP(id=s["id"], name=s["name"]) for s in client.list_smtp_profiles()]
        groups = [GoPhishGroup(id=g["id"], name=g["name"]) for g in client.list_groups()]
    except GoPhishError as exc:
        raise HTTPException(status_code=502, detail=f"GoPhish error: {exc}")

    return GoPhishResourcesResponse(templates=templates, pages=pages, smtp_profiles=smtp, groups=groups)
```

- [ ] **Step 2: Register phishing router in router.py**

In `backend/app/api/v1/router.py`, add:

```python
from app.api.v1.endpoints import phishing

# ... (add after existing includes)
api_router.include_router(phishing.router, prefix="/phishing/campaigns", tags=["Phishing"])
```

- [ ] **Step 3: Verify routes load**

```bash
cd backend
python -c "
from app.api.v1.router import api_router
routes = [r.path for r in api_router.routes]
phishing = [r for r in routes if 'phishing' in r]
print('Phishing routes:', phishing)
"
```

Expected: a list of phishing routes.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/endpoints/phishing.py backend/app/api/v1/router.py
git commit -m "feat(phishing): add campaign API endpoints"
```

---

### Task 11: Frontend phishing service

**Files:**
- Create: `frontend/src/services/phishingService.ts`

- [ ] **Step 1: Create phishingService.ts**

```typescript
import api from './api'

export interface PhishingCampaign {
  id: number
  project_id: number
  created_by: number
  name: string
  description?: string
  status: 'draft' | 'active' | 'completed' | 'cancelled'
  gophish_url: string
  gophish_campaign_id?: number
  template_name?: string
  landing_page_name?: string
  smtp_profile_name?: string
  target_group_name?: string
  phishing_url?: string
  launch_date?: string
  stats_total: number
  stats_sent: number
  stats_opened: number
  stats_clicked: number
  stats_submitted: number
  stats_last_synced?: string
  created_at: string
  updated_at: string
}

export interface PhishingTarget {
  id: number
  campaign_id: number
  email: string
  first_name?: string
  last_name?: string
  position?: string
  status: 'queued' | 'sent' | 'opened' | 'clicked' | 'submitted_data' | 'reported'
  created_at: string
}

export interface PhishingTargetResult {
  email: string
  status: string
  ip?: string
  latitude?: number
  longitude?: number
  reported: boolean
}

export interface GoPhishResources {
  templates: { id: number; name: string }[]
  pages: { id: number; name: string }[]
  smtp_profiles: { id: number; name: string }[]
  groups: { id: number; name: string }[]
}

export const phishingService = {
  async list(params?: Record<string, unknown>): Promise<{ items: PhishingCampaign[]; total: number }> {
    const { data } = await api.get('/phishing/campaigns/', { params })
    return data
  },

  async get(id: number): Promise<PhishingCampaign> {
    const { data } = await api.get(`/phishing/campaigns/${id}`)
    return data
  },

  async create(payload: Record<string, unknown>): Promise<PhishingCampaign> {
    const { data } = await api.post('/phishing/campaigns/', payload)
    return data
  },

  async update(id: number, payload: Record<string, unknown>): Promise<PhishingCampaign> {
    const { data } = await api.put(`/phishing/campaigns/${id}`, payload)
    return data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/phishing/campaigns/${id}`)
  },

  async addTargets(campaignId: number, targets: Omit<PhishingTarget, 'id' | 'campaign_id' | 'status' | 'created_at'>[]): Promise<PhishingTarget[]> {
    const { data } = await api.post(`/phishing/campaigns/${campaignId}/targets`, targets)
    return data
  },

  async listTargets(campaignId: number): Promise<PhishingTarget[]> {
    const { data } = await api.get(`/phishing/campaigns/${campaignId}/targets`)
    return data
  },

  async deleteTarget(campaignId: number, targetId: number): Promise<void> {
    await api.delete(`/phishing/campaigns/${campaignId}/targets/${targetId}`)
  },

  async launch(id: number): Promise<PhishingCampaign> {
    const { data } = await api.post(`/phishing/campaigns/${id}/launch`)
    return data
  },

  async stop(id: number): Promise<PhishingCampaign> {
    const { data } = await api.post(`/phishing/campaigns/${id}/stop`)
    return data
  },

  async getResults(id: number): Promise<{ results: PhishingTargetResult[]; stats: Record<string, number> }> {
    const { data } = await api.get(`/phishing/campaigns/${id}/results`)
    return data
  },

  async syncStats(id: number): Promise<PhishingCampaign> {
    const { data } = await api.post(`/phishing/campaigns/${id}/sync`)
    return data
  },

  async getGoPhishResources(gophishUrl: string, apiKey: string): Promise<GoPhishResources> {
    const { data } = await api.post('/phishing/campaigns/resources', {
      gophish_url: gophishUrl,
      gophish_api_key: apiKey,
    })
    return data
  },
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit 2>&1 | grep phishingService || echo "No errors in phishingService"
```

Expected: no errors related to phishingService.ts.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/phishingService.ts
git commit -m "feat(phishing): add frontend phishing service"
```

---

### Task 12: PhishingPage React component

**Files:**
- Create: `frontend/src/pages/PhishingPage.tsx`

- [ ] **Step 1: Create PhishingPage.tsx**

```tsx
import { useEffect, useState } from 'react'
import {
  Mail, Plus, Play, Square, RefreshCw, Trash2, Users,
  BarChart2, ChevronDown, ChevronUp, Loader2, Eye,
} from 'lucide-react'
import {
  phishingService,
  type PhishingCampaign,
  type PhishingTarget,
  type PhishingTargetResult,
} from '../services/phishingService'
import api from '../services/api'
import type { Project } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import Modal from '../components/Common/Modal'
import { formatDate } from '../utils/cn'

type Tab = 'campaigns' | 'targets' | 'results'

const STATUS_COLORS: Record<string, string> = {
  draft: 'text-gray-400',
  active: 'text-green-400',
  completed: 'text-blue-400',
  cancelled: 'text-red-400',
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg text-center">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-[var(--color-text-secondary)] mt-1">{label}</div>
    </div>
  )
}

function ClickRate({ sent, clicked }: { sent: number; clicked: number }) {
  const rate = sent > 0 ? Math.round((clicked / sent) * 100) : 0
  const color = rate > 30 ? 'bg-red-500' : rate > 10 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
        <div className={`h-2 ${color} rounded-full transition-all`} style={{ width: `${Math.min(rate, 100)}%` }} />
      </div>
      <span className="text-xs text-[var(--color-text-secondary)] w-10 text-right">{rate}%</span>
    </div>
  )
}

export default function PhishingPage() {
  const [campaigns, setCampaigns] = useState<PhishingCampaign[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<Record<number, string>>({})

  // Create modal
  const [showCreate, setShowCreate] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [createForm, setCreateForm] = useState({
    project_id: 0,
    name: '',
    description: '',
    gophish_url: 'http://localhost:3333',
    gophish_api_key: '',
    template_name: '',
    landing_page_name: '',
    smtp_profile_name: '',
    target_group_name: '',
    phishing_url: '',
  })

  // Detail panel
  const [selectedCampaign, setSelectedCampaign] = useState<PhishingCampaign | null>(null)
  const [detailTab, setDetailTab] = useState<Tab>('targets')
  const [targets, setTargets] = useState<PhishingTarget[]>([])
  const [results, setResults] = useState<PhishingTargetResult[]>([])
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Add targets modal
  const [showAddTargets, setShowAddTargets] = useState(false)
  const [targetsText, setTargetsText] = useState('')

  const load = () => {
    setLoading(true)
    phishingService.list()
      .then((r) => setCampaigns(r.items))
      .catch(() => setCampaigns([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    api.get('/projects/').then((r) => {
      const items: Project[] = Array.isArray(r.data) ? r.data : r.data.items ?? []
      setProjects(items)
      if (items.length > 0) setCreateForm((f) => ({ ...f, project_id: items[0].id }))
    }).catch(() => {})
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!createForm.project_id) { setSubmitError('Select a project'); return }
    setSubmitting(true)
    setSubmitError('')
    try {
      await phishingService.create(createForm as unknown as Record<string, unknown>)
      setShowCreate(false)
      resetCreateForm()
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setSubmitError(Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ') : detail || 'Failed to create campaign')
    } finally {
      setSubmitting(false)
    }
  }

  const resetCreateForm = () => {
    setCreateForm({
      project_id: projects[0]?.id || 0,
      name: '', description: '',
      gophish_url: 'http://localhost:3333',
      gophish_api_key: '',
      template_name: '', landing_page_name: '',
      smtp_profile_name: '', target_group_name: '',
      phishing_url: '',
    })
    setSubmitError('')
  }

  const handleLaunch = async (id: number) => {
    setActionLoading((p) => ({ ...p, [id]: 'launch' }))
    try {
      const updated = await phishingService.launch(id)
      setCampaigns((p) => p.map((c) => c.id === id ? updated : c))
      if (selectedCampaign?.id === id) setSelectedCampaign(updated)
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Launch failed')
    } finally {
      setActionLoading((p) => { const n = { ...p }; delete n[id]; return n })
    }
  }

  const handleStop = async (id: number) => {
    setActionLoading((p) => ({ ...p, [id]: 'stop' }))
    try {
      const updated = await phishingService.stop(id)
      setCampaigns((p) => p.map((c) => c.id === id ? updated : c))
      if (selectedCampaign?.id === id) setSelectedCampaign(updated)
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Stop failed')
    } finally {
      setActionLoading((p) => { const n = { ...p }; delete n[id]; return n })
    }
  }

  const handleSync = async (id: number) => {
    setActionLoading((p) => ({ ...p, [id]: 'sync' }))
    try {
      const updated = await phishingService.syncStats(id)
      setCampaigns((p) => p.map((c) => c.id === id ? updated : c))
      if (selectedCampaign?.id === id) setSelectedCampaign(updated)
    } finally {
      setActionLoading((p) => { const n = { ...p }; delete n[id]; return n })
    }
  }

  const handleDelete = async (id: number) => {
    setActionLoading((p) => ({ ...p, [id]: 'delete' }))
    try {
      await phishingService.delete(id)
      setCampaigns((p) => p.filter((c) => c.id !== id))
      if (selectedCampaign?.id === id) setSelectedCampaign(null)
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Delete failed')
    } finally {
      setActionLoading((p) => { const n = { ...p }; delete n[id]; return n })
    }
  }

  const openDetail = async (campaign: PhishingCampaign) => {
    setSelectedCampaign(campaign)
    setDetailTab('targets')
    setLoadingDetail(true)
    try {
      const t = await phishingService.listTargets(campaign.id)
      setTargets(t)
    } finally {
      setLoadingDetail(false)
    }
  }

  const loadResults = async (campaign: PhishingCampaign) => {
    setLoadingDetail(true)
    try {
      const r = await phishingService.getResults(campaign.id)
      setResults(r.results)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleAddTargets = async () => {
    if (!selectedCampaign) return
    const lines = targetsText.split('\n').map((l) => l.trim()).filter(Boolean)
    const targets = lines.map((line) => {
      const parts = line.split(',').map((p) => p.trim())
      return {
        email: parts[0] || '',
        first_name: parts[1] || undefined,
        last_name: parts[2] || undefined,
        position: parts[3] || undefined,
      }
    }).filter((t) => t.email)

    if (!targets.length) return
    try {
      const added = await phishingService.addTargets(selectedCampaign.id, targets as any)
      setTargets((prev) => [...prev, ...added])
      setTargetsText('')
      setShowAddTargets(false)
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to add targets')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Mail className="w-5 h-5 text-red-400" /> Phishing Campaigns
          </h2>
          <p className="text-sm text-[var(--color-text-secondary)]">{campaigns.length} campaigns</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} disabled={loading} className="px-3 py-2 bg-[var(--color-bg-tertiary)] text-white rounded-lg hover:bg-[var(--color-bg-tertiary)]/80 text-sm flex items-center gap-2 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm flex items-center gap-2">
            <Plus className="w-4 h-4" /> New Campaign
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Campaign list */}
        <div className="space-y-3">
          {loading ? <Loading text="Loading campaigns..." /> : campaigns.length === 0 ? (
            <EmptyState
              icon={<Mail className="w-12 h-12" />}
              title="No phishing campaigns"
              description="Create a campaign to simulate phishing attacks and measure employee awareness."
              action={<button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm">New Campaign</button>}
            />
          ) : campaigns.map((c) => {
            const busy = actionLoading[c.id]
            const isSelected = selectedCampaign?.id === c.id
            return (
              <Card key={c.id} className={`cursor-pointer transition-colors ${isSelected ? 'border-red-500/50' : ''}`}>
                <div onClick={() => openDetail(c)} className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-white font-medium">{c.name}</h3>
                      {c.description && <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">{c.description}</p>}
                    </div>
                    <span className={`text-xs font-medium capitalize ${STATUS_COLORS[c.status]}`}>{c.status}</span>
                  </div>

                  {(c.status === 'active' || c.status === 'completed') && (
                    <div className="grid grid-cols-4 gap-2">
                      <StatCard label="Sent" value={c.stats_sent} color="text-blue-400" />
                      <StatCard label="Opened" value={c.stats_opened} color="text-yellow-400" />
                      <StatCard label="Clicked" value={c.stats_clicked} color="text-orange-400" />
                      <StatCard label="Submitted" value={c.stats_submitted} color="text-red-400" />
                    </div>
                  )}

                  {c.stats_sent > 0 && (
                    <div>
                      <p className="text-xs text-[var(--color-text-secondary)] mb-1">Click rate</p>
                      <ClickRate sent={c.stats_sent} clicked={c.stats_clicked} />
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between mt-3 pt-3 border-t border-[var(--color-border)]">
                  <span className="text-xs text-[var(--color-text-secondary)]">{formatDate(c.created_at)}</span>
                  <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                    {busy ? (
                      <Loader2 className="w-4 h-4 animate-spin text-[var(--color-text-secondary)]" />
                    ) : (
                      <>
                        {c.status === 'draft' && (
                          <button onClick={() => handleLaunch(c.id)} className="p-1.5 text-green-400 hover:bg-green-400/10 rounded" title="Launch">
                            <Play className="w-4 h-4" />
                          </button>
                        )}
                        {c.status === 'active' && (
                          <>
                            <button onClick={() => handleSync(c.id)} className="p-1.5 text-blue-400 hover:bg-blue-400/10 rounded" title="Sync stats">
                              <RefreshCw className="w-4 h-4" />
                            </button>
                            <button onClick={() => handleStop(c.id)} className="p-1.5 text-yellow-400 hover:bg-yellow-400/10 rounded" title="Stop">
                              <Square className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        {(c.status === 'completed' || c.status === 'cancelled' || c.status === 'draft') && (
                          <button onClick={() => handleDelete(c.id)} className="p-1.5 text-red-400 hover:bg-red-400/10 rounded" title="Delete">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Detail panel */}
        {selectedCampaign && (
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">{selectedCampaign.name}</h3>
              <div className="flex gap-1">
                {(['targets', 'results'] as Tab[]).map((t) => (
                  <button key={t} onClick={() => {
                    setDetailTab(t)
                    if (t === 'results') loadResults(selectedCampaign)
                  }}
                    className={`px-3 py-1.5 rounded-lg text-xs capitalize transition-colors ${detailTab === t ? 'bg-red-600 text-white' : 'text-[var(--color-text-secondary)] hover:text-white'}`}
                  >{t}</button>
                ))}
              </div>
            </div>

            {loadingDetail ? <Loading text="Loading..." /> : (
              <>
                {detailTab === 'targets' && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-[var(--color-text-secondary)]">{targets.length} targets</span>
                      {selectedCampaign.status === 'draft' && (
                        <button onClick={() => setShowAddTargets(true)} className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs flex items-center gap-1">
                          <Plus className="w-3 h-3" /> Add Targets
                        </button>
                      )}
                    </div>
                    {targets.length === 0 ? (
                      <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">No targets yet. Add targets to launch the campaign.</p>
                    ) : (
                      <div className="divide-y divide-[var(--color-border)] max-h-80 overflow-y-auto">
                        {targets.map((t) => (
                          <div key={t.id} className="py-2.5 flex items-center justify-between">
                            <div>
                              <p className="text-sm text-white">{t.first_name || ''} {t.last_name || ''} <span className="text-[var(--color-text-secondary)] ml-1">{t.email}</span></p>
                              {t.position && <p className="text-xs text-[var(--color-text-secondary)]">{t.position}</p>}
                            </div>
                            <span className={`text-xs capitalize px-2 py-0.5 rounded-full ${
                              t.status === 'submitted_data' ? 'bg-red-500/20 text-red-400' :
                              t.status === 'clicked' ? 'bg-orange-500/20 text-orange-400' :
                              t.status === 'opened' ? 'bg-yellow-500/20 text-yellow-400' :
                              t.status === 'sent' ? 'bg-blue-500/20 text-blue-400' :
                              'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'
                            }`}>{t.status.replace('_', ' ')}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {detailTab === 'results' && (
                  <div className="space-y-2">
                    {results.length === 0 ? (
                      <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">No results yet. Launch the campaign first.</p>
                    ) : (
                      <div className="divide-y divide-[var(--color-border)] max-h-80 overflow-y-auto">
                        {results.map((r, i) => (
                          <div key={i} className="py-2.5 flex items-center justify-between">
                            <div>
                              <p className="text-sm text-white">{r.email}</p>
                              {r.ip && <p className="text-xs text-[var(--color-text-secondary)] font-mono">{r.ip}</p>}
                            </div>
                            <span className="text-xs text-[var(--color-text-secondary)]">{r.status}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </Card>
        )}
      </div>

      {/* Create Campaign Modal */}
      <Modal open={showCreate} onClose={() => { if (!submitting) { setShowCreate(false); resetCreateForm() } }} title="New Phishing Campaign" size="lg">
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Campaign Name</label>
              <input required value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                placeholder="Q1 Phishing Test"
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-red-500/50" />
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Project</label>
              <select value={createForm.project_id} onChange={(e) => setCreateForm({ ...createForm, project_id: Number(e.target.value) })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none">
                {projects.length === 0 ? <option value={0}>No projects</option> : projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Description</label>
            <input value={createForm.description} onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
              placeholder="Optional description"
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none" />
          </div>

          <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg border border-[var(--color-border)] space-y-3">
            <p className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">GoPhish Server</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-[var(--color-text-secondary)] mb-1">GoPhish URL</label>
                <input required value={createForm.gophish_url} onChange={(e) => setCreateForm({ ...createForm, gophish_url: e.target.value })}
                  placeholder="http://localhost:3333"
                  className="w-full px-3 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50" />
              </div>
              <div>
                <label className="block text-xs text-[var(--color-text-secondary)] mb-1">API Key</label>
                <input required type="password" value={createForm.gophish_api_key} onChange={(e) => setCreateForm({ ...createForm, gophish_api_key: e.target.value })}
                  placeholder="GoPhish API key"
                  className="w-full px-3 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50" />
              </div>
            </div>
          </div>

          <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg border border-[var(--color-border)] space-y-3">
            <p className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">Campaign Resources (GoPhish names)</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: 'template_name', label: 'Email Template' },
                { key: 'landing_page_name', label: 'Landing Page' },
                { key: 'smtp_profile_name', label: 'SMTP Profile' },
                { key: 'target_group_name', label: 'Target Group' },
              ].map(({ key, label }) => (
                <div key={key}>
                  <label className="block text-xs text-[var(--color-text-secondary)] mb-1">{label}</label>
                  <input value={(createForm as any)[key]} onChange={(e) => setCreateForm({ ...createForm, [key]: e.target.value })}
                    placeholder={`GoPhish ${label} name`}
                    className="w-full px-3 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-white text-sm focus:outline-none" />
                </div>
              ))}
            </div>
            <div>
              <label className="block text-xs text-[var(--color-text-secondary)] mb-1">Phishing URL</label>
              <input value={createForm.phishing_url} onChange={(e) => setCreateForm({ ...createForm, phishing_url: e.target.value })}
                placeholder="https://phishing.example.com"
                className="w-full px-3 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-white text-sm focus:outline-none" />
            </div>
          </div>

          {submitError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">{submitError}</div>
          )}

          <div className="flex justify-end gap-3 pt-2 border-t border-[var(--color-border)]">
            <button type="button" onClick={() => { setShowCreate(false); resetCreateForm() }} disabled={submitting}
              className="px-4 py-2 text-[var(--color-text-secondary)] hover:text-white text-sm disabled:opacity-50">Cancel</button>
            <button type="submit" disabled={submitting || !createForm.project_id}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2">
              {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : 'Create Campaign'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Add Targets Modal */}
      <Modal open={showAddTargets} onClose={() => setShowAddTargets(false)} title="Add Targets">
        <div className="space-y-3">
          <p className="text-sm text-[var(--color-text-secondary)]">
            One target per line. Format: <code className="text-xs bg-[var(--color-bg-tertiary)] px-1 rounded">email, first_name, last_name, position</code>
          </p>
          <textarea value={targetsText} onChange={(e) => setTargetsText(e.target.value)} rows={8}
            placeholder={"john.doe@company.com, John, Doe, Engineer\njane.smith@company.com, Jane, Smith, Manager"}
            className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red-500/50 resize-none" />
          <div className="flex justify-end gap-3">
            <button onClick={() => setShowAddTargets(false)} className="px-4 py-2 text-[var(--color-text-secondary)] text-sm">Cancel</button>
            <button onClick={handleAddTargets} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm">
              Add Targets
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit 2>&1 | grep PhishingPage || echo "No errors in PhishingPage"
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/PhishingPage.tsx
git commit -m "feat(phishing): add PhishingPage UI"
```

---

### Task 13: Wire phishing into App.tsx and Sidebar

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Common/Sidebar.tsx`

- [ ] **Step 1: Add route in App.tsx**

Add import:
```tsx
import PhishingPage from './pages/PhishingPage'
```

Add route inside the `<Route path="/" ...>` group:
```tsx
<Route path="phishing" element={<PhishingPage />} />
```

- [ ] **Step 2: Add sidebar entry in Sidebar.tsx**

Add `Mail` to the lucide-react import:
```tsx
import {
  LayoutDashboard, Scan, Bug, FileText, FolderOpen, Crosshair,
  Shield, Bell, Settings, Wrench, Globe, LogOut, Mail,
} from 'lucide-react'
```

Add to `navItems` array (after Scans, before Findings):
```tsx
{ to: '/phishing', icon: Mail, label: 'Phishing' },
```

- [ ] **Step 3: Verify app compiles**

```bash
cd frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors (or only pre-existing unrelated errors).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Common/Sidebar.tsx
git commit -m "feat(phishing): add Phishing route and sidebar entry"
```

---

### Task 14: Final integration check

- [ ] **Step 1: Start full stack**

```bash
docker-compose up -d
```

- [ ] **Step 2: Check API docs include phishing routes**

Open: `http://localhost:8000/api/docs`

Verify: `Phishing` tag is present with all endpoints.

- [ ] **Step 3: Check frontend builds**

```bash
cd frontend
npm run build 2>&1 | tail -5
```

Expected: build succeeds with no type errors.

- [ ] **Step 4: Smoke test scan flow**

Using the app UI:
1. Create a project
2. Create a scan with `nmap` tool against `scanme.nmap.org`
3. Check the scan's progress updates (via polling)
4. Verify findings appear in the Findings page

- [ ] **Step 5: Smoke test phishing flow**

Using the app UI:
1. Go to Phishing page
2. Create a campaign (with a test GoPhish URL — can be invalid for now)
3. Add a target email
4. Verify the campaign shows in the list

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: real scan execution + phishing campaigns — integration complete"
```

---

## File Map Summary

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/tasks/celery_app.py` | Modify | Add scan_tasks + phishing_tasks to includes |
| `backend/app/tasks/scan_tasks.py` | Rewrite | Real tool execution loop |
| `backend/app/tasks/phishing_tasks.py` | Create | Celery sync task |
| `backend/app/models/phishing.py` | Create | PhishingCampaign + PhishingTarget models |
| `backend/app/models/__init__.py` | Modify | Add phishing model imports |
| `backend/app/schemas/phishing.py` | Create | Pydantic schemas |
| `backend/app/crud/phishing.py` | Create | CRUD class |
| `backend/app/services/gophish_client.py` | Create | GoPhish HTTP wrapper |
| `backend/app/api/v1/endpoints/phishing.py` | Create | API endpoints |
| `backend/app/api/v1/router.py` | Modify | Register phishing router |
| `frontend/src/services/phishingService.ts` | Create | API client |
| `frontend/src/pages/PhishingPage.tsx` | Create | React UI |
| `frontend/src/App.tsx` | Modify | Add phishing route |
| `frontend/src/components/Common/Sidebar.tsx` | Modify | Add phishing nav entry |
