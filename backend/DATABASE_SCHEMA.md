# Database Schema — Red Team SaaS

## Overview

16 tables across two phases. All tables share `created_at` / `updated_at` timestamp columns (UTC).

---

## Phase 1 Models (10 tables)

| Table | Description |
|---|---|
| `users` | Authentication, RBAC roles (admin / manager / pentester / viewer / api_user) |
| `tasks` | Pentest tool executions; links to a user and optional workspace |
| `results` | Raw + parsed output for each task |
| `audit_logs` | Immutable action trail (who did what, from which IP) |
| `generic_tool_configs` | Dynamic CLI tool registry with execution modes |
| `tool_executions` | Run history of registered generic tools |
| `brute_force_configs` | Hydra / John / Medusa attack configuration |
| `brute_force_results` | Valid credentials discovered during brute force |
| `plugins` | Community plugin marketplace (Option B) |
| `plugin_executions` | Plugin run history |

---

## Phase 2 Models (6 new tables)

### `workspaces`
Project / client isolation layer.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `owner_id` | INTEGER FK → users | |
| `name` | VARCHAR(255) | indexed |
| `description` | TEXT | |
| `client_name` | VARCHAR(255) | indexed |
| `scope` | TEXT | JSON list of IPs/domains |
| `is_active` | BOOLEAN | default `true` |

Relations:
- `owner` → `User`
- `tasks` → `Task[]` (cascade delete)
- `reports` → `Report[]` (cascade delete)

---

### `templates`
Reusable tool configuration bundles.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `user_id` | INTEGER FK → users | |
| `name` | VARCHAR(255) | indexed |
| `description` | TEXT | |
| `category` | ENUM | brute_force / osint / enumeration / exploitation / post_exploitation / phishing / network / custom |
| `tool_configs` | TEXT | JSON payload |
| `is_public` | BOOLEAN | default `false` |
| `usage_count` | INTEGER | default `0` |

---

### `threat_intel`
CVE / vulnerability database.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `cve_id` | VARCHAR(20) | UNIQUE, nullable |
| `title` | VARCHAR(500) | |
| `description` | TEXT | |
| `severity` | ENUM | critical / high / medium / low / info |
| `cvss_score` | NUMERIC(4,2) | 0.0 – 10.0 |
| `affected_products` | TEXT | JSON list |
| `exploit_available` | BOOLEAN | indexed |
| `patch_available` | BOOLEAN | |
| `references` | TEXT | JSON list of URLs |
| `published_date` | TIMESTAMPTZ | |
| `last_modified` | TIMESTAMPTZ | |
| `tags` | TEXT | JSON list |

---

### `risk_scores`
Numeric risk assessment per task (0.0 – 10.0).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `task_id` | INTEGER FK → tasks | indexed |
| `score` | NUMERIC(4,2) | |
| `components` | TEXT | JSON score breakdown |
| `justification` | TEXT | |

Computed property `risk_level`:

| Score range | Level |
|---|---|
| ≥ 9.0 | CRITICAL |
| ≥ 7.0 | HIGH |
| ≥ 4.0 | MEDIUM |
| ≥ 1.0 | LOW |
| < 1.0 | INFO |

---

### `compliance_mappings`
Maps tasks / CVEs to compliance controls.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `framework` | ENUM | PCI-DSS / HIPAA / GDPR / ISO27001 / SOC2 / NIST |
| `control_id` | VARCHAR(50) | e.g. `PCI-DSS 6.5.1` |
| `control_name` | VARCHAR(255) | |
| `description` | TEXT | |
| `status` | ENUM | compliant / non_compliant / not_assessed / in_remediation |
| `task_id` | INTEGER FK → tasks | nullable |
| `threat_intel_id` | INTEGER FK → threat_intel | nullable |
| `notes` | TEXT | |

---

### `reports`
Pentest reports with SHA-256 digital signatures.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `author_id` | INTEGER FK → users | indexed |
| `workspace_id` | INTEGER FK → workspaces | nullable, indexed |
| `title` | VARCHAR(500) | |
| `executive_summary` | TEXT | |
| `findings` | TEXT | JSON list of findings |
| `recommendations` | TEXT | |
| `status` | ENUM | draft / review / final / archived |
| `signature_hash` | VARCHAR(64) | SHA-256 of title + summary + findings + recommendations |
| `signed_at` | TIMESTAMPTZ | |

Method `compute_signature()` → deterministic SHA-256 hex digest of report content.

---

## Task ← Workspace Relation (Phase 2 addition)

`tasks.workspace_id` (nullable FK → `workspaces.id`) was added in Phase 2 to scope tasks to a client project.

---

## Indexes Summary

| Table | Indexed columns |
|---|---|
| users | email (unique), username (unique), is_active |
| workspaces | owner_id, name, client_name, is_active |
| tasks | user_id, workspace_id, status |
| results | task_id |
| audit_logs | user_id, action |
| generic_tool_configs | tool_name (unique), category |
| tool_executions | tool_config_id |
| brute_force_configs | tool_name, target |
| brute_force_results | config_id |
| plugins | name (unique), category |
| plugin_executions | plugin_id |
| templates | user_id, name, category, is_public |
| threat_intel | cve_id (unique), severity, exploit_available |
| risk_scores | task_id |
| compliance_mappings | framework, control_id, status, task_id, threat_intel_id |
| reports | author_id, workspace_id, status |

**Total indexes: 35+**

---

## Alembic Migrations

```bash
# Apply all migrations (run from backend/)
alembic upgrade head

# Roll back one revision
alembic downgrade -1

# Show current state
alembic current

# Show full history
alembic history --verbose

# Auto-generate migration after model changes
alembic revision --autogenerate -m "describe change"
```

The `DATABASE_URL` environment variable overrides `alembic.ini` at runtime:

```
DATABASE_URL=postgresql://redteam:password@localhost:5432/redteam_db
```

---

## Running Tests

```bash
# From backend/
cd backend

# All tests
pytest tests/ -v

# Phase 2 models only
pytest tests/unit/test_phase2_models.py -v

# With coverage report
pytest tests/ --cov=app --cov-report=term-missing
```

Tests use SQLite in-memory — no live database required.

---

## Security Notes

- Sensitive CLI parameters stored in `tasks.parameters` (VARCHAR) — encrypt at application layer using `EncryptionHandler` (Fernet AES-128-CBC) before persisting.
- `audit_logs` is append-only by convention; DELETE permission should be revoked from the application DB user.
- `reports.signature_hash` provides tamper-evidence; re-compute and compare on read to verify integrity.
