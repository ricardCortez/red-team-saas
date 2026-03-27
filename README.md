# 🔴 Red Team SaaS Platform
**Comprehensive API for Automated Security Testing & Red Team Operations**

[![Build Status](https://github.com/yourorg/red-team-saas/workflows/CI%2FCD/badge.svg)](https://github.com/yourorg/red-team-saas/actions)
[![Tests](https://img.shields.io/badge/tests-1060%2B%20passing-brightgreen)](./docs/TESTING.md)
[![Coverage](https://img.shields.io/badge/coverage-%3E80%25-brightgreen)](#testing)
[![License](https://img.shields.io/badge/license-Commercial-red)](#license)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](#version)
[![Status](https://img.shields.io/badge/status-Production%20Ready-success)](#status)

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [API Documentation](#api-documentation)
- [Monitoring](#monitoring)
- [Testing](#testing)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

---

## 🚀 Quick Start

### Docker Compose (Easiest — 5 minutes)

**Windows (PowerShell):**
```powershell
# Clone repository
git clone https://github.com/yourorg/red-team-saas.git
cd red-team-saas\backend

# Copy environment
Copy-Item .env.example .env

# Start services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Verify health
Invoke-WebRequest http://localhost:8000/health

# Open docs
Start-Process "http://localhost:8000/api/docs"
```

**Linux (Bash):**
```bash
# Clone repository
git clone https://github.com/yourorg/red-team-saas.git
cd red-team-saas/backend

# Copy environment
cp .env.example .env

# Start services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Verify health
curl http://localhost:8000/health | jq '.'

# Open docs
firefox http://localhost:8000/api/docs
```

**Services Available:**
- 🌐 **API**: http://localhost:8000
- 📚 **Swagger UI**: http://localhost:8000/api/docs
- 📖 **ReDoc**: http://localhost:8000/api/redoc
- 🔍 **Prometheus**: http://localhost:9090
- 📊 **Grafana**: http://localhost:3000 (admin/admin)
- 🌳 **Flower (Tasks)**: http://localhost:5555

For detailed setup, see:
- 🪟 [Windows Setup Guide](./docs/DEPLOYMENT_WINDOWS.md)
- 🐧 [Linux Setup Guide](./docs/DEPLOYMENT_LINUX.md)
- ⚡ [Quick Start Guide](./docs/QUICK_START.md)

---

## 📖 Overview

**Red Team SaaS** is a production-ready platform for automated security testing and red team operations. It integrates 9+ penetration testing tools, compliance mapping, real-time analytics, and enterprise integrations into a unified API.

### Current Status
- ✅ **Phase 20 Complete** — All features implemented
- ✅ **1060+ Tests Passing** — 100% success rate, 0 regressions
- ✅ **Production Ready** — Ready for immediate deployment
- ✅ **Enterprise Grade** — Monitoring, security, documentation
- ✅ **Fully Documented** — 8+ detailed guides

### Technology Stack

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy (ORM)
- PostgreSQL (database)
- Redis (caching)
- Celery (task queue)

**Infrastructure:**
- Docker (containerization)
- Kubernetes (orchestration)
- GitHub Actions (CI/CD)
- Alembic (migrations)

**Monitoring:**
- Prometheus (metrics)
- Grafana (dashboards)
- Elasticsearch + Kibana (logging)
- Sentry (error tracking)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                           │
│  (Web UI, CLI, SDKs — Python, TypeScript)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌─────────────────────────▼────────────────────────────────────┐
│                  API LAYER (FastAPI)                        │
│  70+ REST Endpoints: Auth, Tools, Compliance, Analytics     │
│  Rate Limiting │ IP Whitelisting │ Request Signing          │
└────────────────────────┬────────────────────────────────────┘
                         │
┌─────────────────────────▼────────────────────────────────────┐
│                  SERVICE LAYER                              │
│  Auth │ Tools │ Reports │ Analytics │ Compliance │ Alerts   │
│  Task Execution (Celery) │ Caching (Redis)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌─────────────────────────▼────────────────────────────────────┐
│              DATA PERSISTENCE LAYER                         │
│  PostgreSQL │ Redis │ S3 (Reports) │ Elasticsearch (Logs)   │
└─────────────────────────────────────────────────────────────┘

MONITORING: Prometheus → Grafana | Logstash → Kibana | Sentry
```

---

## ✨ Features

### Core Capabilities
| Feature | Details | Status |
|---------|---------|--------|
| **Authentication** | JWT + API Keys + OAuth2 (GitHub, Google) | ✅ |
| **Tools** | 9+ integrated (Nmap, Hydra, John, Medusa, CeWL, WPScan, etc) | ✅ |
| **Compliance** | PCI-DSS 3.2.1, HIPAA, GDPR mapping with scoring | ✅ |
| **Analytics** | Real-time KPIs, risk scoring, tool effectiveness | ✅ |
| **Reports** | PDF, HTML, Excel with digital signatures | ✅ |
| **Integrations** | Slack, GitHub, Jira, custom webhooks | ✅ |
| **CLI** | Full-featured command-line interface (20+ commands) | ✅ |
| **Threat Intel** | CVE/MITRE ATT&CK/IOC feeds | ✅ |

### Security Features
- ✅ Rate limiting (60 req/min, per-endpoint customizable)
- ✅ IP whitelisting (CIDR blocks)
- ✅ Request signing (HMAC-SHA256 for webhooks)
- ✅ AES-256 encryption at rest
- ✅ Comprehensive audit logging
- ✅ Role-based access control (RBAC)
- ✅ Non-root Docker user
- ✅ Security headers + CORS

### Infrastructure Features
- ✅ Docker multi-stage build (~150MB)
- ✅ Kubernetes with HPA (3-10 replicas)
- ✅ Health checks (liveness + readiness probes)
- ✅ Horizontal auto-scaling
- ✅ Database migrations (Alembic)
- ✅ GitHub Actions CI/CD
- ✅ Environment-based configuration

### Monitoring & Observability
- ✅ Prometheus metrics scraping
- ✅ Grafana 4 dashboards (system, security, business, infrastructure)
- ✅ ELK stack (centralized logging)
- ✅ Sentry error tracking
- ✅ Alert rules (error rate, latency, resource usage)
- ✅ Custom business metrics

---

## 📦 Installation

### Requirements

**Docker (Recommended):**
- Docker Desktop 4.0+ (Windows/Mac)
- Docker + Docker Compose (Linux)

**Local Development (Optional):**
- Python 3.11+
- PostgreSQL 14+ (can use Docker)
- Redis 7+ (can use Docker)

### Clone Repository

```bash
# Clone
git clone https://github.com/yourorg/red-team-saas.git
cd red-team-saas

# Verify structure
ls -la  # Should see: backend/, docs/, .github/, README.md
```

### Copy Environment

```bash
# Navigate to backend
cd backend

# Copy template
cp .env.example .env

# Edit if needed (set SECRET_KEY, etc)
# nano .env  (or use your editor)
```

For detailed configuration, see [Configuration](#configuration) below.

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file in `backend/` directory:

```bash
# Core
ENVIRONMENT=production              # development, staging, production
DEBUG=false                         # true/false
VERSION=1.0.0                       # Version string

# Database
DATABASE_URL=postgresql://...       # PostgreSQL connection
POSTGRES_USER=rtsa_user            # DB username
POSTGRES_PASSWORD=...              # DB password
POSTGRES_DB=rtsa_db                # DB name

# Cache
REDIS_URL=redis://...              # Redis connection
REDIS_PASSWORD=...                 # Redis password (if secured)

# Security
SECRET_KEY=your-secret-key         # JWT secret (CHANGE IN PRODUCTION)
JWT_ALGORITHM=HS256                # JWT algorithm
JWT_EXPIRATION_HOURS=24            # Token TTL

# API
API_BASE_URL=https://api.readteam.dev

# Optional: AWS/S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=red-team-saas

# Optional: OAuth
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Optional: Monitoring
SENTRY_DSN=https://...
PROMETHEUS_PORT=8001
```

See `.env.example` for complete reference.

---

## 🏃 Running Locally

### With Docker Compose (Recommended)

```bash
cd backend

# Start all services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Without Docker (Local Development)

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL & Redis (Docker)
docker run -d -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Set environment
export DATABASE_URL="postgresql://postgres:password@localhost:5432/rtsa_db"
export REDIS_URL="redis://localhost:6379"
export SECRET_KEY="dev-key"

# Create database
docker exec $(docker ps -q -f "image=postgres") createdb -U postgres rtsa_db

# Run migrations
alembic upgrade head

# Start FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal: Start Celery worker (optional)
celery -A app.tasks.celery_app worker --loglevel=info

# In another terminal: Start Celery beat (optional)
celery -A app.tasks.celery_app beat --loglevel=info
```

For detailed setup: See [Windows Guide](./docs/DEPLOYMENT_WINDOWS.md) or [Linux Guide](./docs/DEPLOYMENT_LINUX.md)

---

## 📚 API Documentation

### Interactive Docs
- **Swagger UI** (interactive): http://localhost:8000/api/docs
- **ReDoc** (static): http://localhost:8000/api/redoc
- **OpenAPI Spec**: http://localhost:8000/api/openapi.json

### Main Endpoints

```
Authentication:
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh
  POST   /api/v1/security/api-keys

Projects:
  GET    /api/v1/projects
  POST   /api/v1/projects
  GET    /api/v1/projects/{id}
  PUT    /api/v1/projects/{id}
  DELETE /api/v1/projects/{id}

Tools:
  GET    /api/v1/tools
  POST   /api/v1/tools/{id}/execute
  GET    /api/v1/tools/{id}/status

Findings:
  GET    /api/v1/findings
  POST   /api/v1/findings
  GET    /api/v1/findings/{id}

Reports:
  POST   /api/v1/reports
  GET    /api/v1/reports/{id}
  GET    /api/v1/reports/{id}/download

Compliance:
  GET    /api/v1/compliance/frameworks
  GET    /api/v1/compliance/results/{id}

Analytics:
  GET    /api/v1/analytics/{project_id}/kpis
  GET    /api/v1/analytics/{project_id}/risk-score
```

For complete API reference, access Swagger UI at `/api/docs`

---

## 📊 Monitoring

### Prometheus
- **URL**: http://localhost:9090
- **Metrics endpoint**: http://localhost:8000/metrics
- **Key metrics**:
  - `http_requests_total` — Total HTTP requests
  - `http_request_duration_seconds` — Request latency (p50, p95, p99)
  - `db_query_duration_seconds` — Database query times
  - `findings_created_total` — Findings discovered

### Grafana
- **URL**: http://localhost:3000
- **Credentials**: admin / admin
- **Dashboards**:
  1. System Overview (HTTP, database, cache metrics)
  2. Security (rate limits, auth failures, IP blocks)
  3. Business (projects, findings, reports)
  4. Infrastructure (CPU, memory, disk)

### ELK Stack
- **Kibana**: http://localhost:5601
- **Log types**: application, security events, database queries, integrations

### Sentry (if configured)
Configure `SENTRY_DSN` in `.env` for error tracking.

---

## ✅ Testing

### Run Tests

```bash
# All tests
pytest tests/unit/ -v

# With coverage report
pytest tests/unit/ --cov=app --cov-report=html

# Specific test file
pytest tests/unit/test_security.py -v

# Specific test
pytest tests/unit/test_security.py::TestRateLimiter::test_token_bucket -xvs
```

**Test Stats:**
- 1060+ unit tests
- 100% pass rate
- >80% code coverage
- 0 regressions across 20 phases

---

## 🌐 Deployment

### Docker Image Build

```bash
cd backend

# Build
docker build -t red-team-saas:latest -f Dockerfile .

# Tag for registry
docker tag red-team-saas:latest myregistry.azurecr.io/red-team-saas:latest

# Push
docker push myregistry.azurecr.io/red-team-saas:latest
```

### Kubernetes

```bash
# Create namespace
kubectl create namespace red-team-saas

# Create secrets
kubectl create secret generic rtsa-secrets \
  --from-literal=DATABASE_URL="postgresql://..." \
  -n red-team-saas

# Deploy
kubectl apply -f k8s/

# Verify
kubectl get pods -n red-team-saas
```

For detailed deployment guides:
- [Kubernetes Guide](./docs/DEPLOYMENT.md)
- [Windows VPS Guide](./docs/DEPLOYMENT_WINDOWS.md)
- [Linux VPS Guide](./docs/DEPLOYMENT_LINUX.md)

---

## 📁 Project Structure

```
red-team-saas/
├── backend/                          # Main application
│   ├── app/                          # FastAPI app
│   │   ├── api/                      # 70+ REST endpoints
│   │   ├── models/                   # 100+ SQLAlchemy models
│   │   ├── services/                 # 20+ service classes
│   │   ├── crud/                     # Database access
│   │   ├── tasks/                    # 15+ Celery tasks
│   │   ├── middleware/               # Security, metrics
│   │   ├── cli/                      # CLI commands
│   │   ├── core/                     # Config, security
│   │   └── main.py                   # FastAPI app
│   ├── alembic/                      # Database migrations
│   ├── tests/                        # 1060+ unit tests
│   ├── docs/                         # Documentation
│   ├── k8s/                          # Kubernetes manifests
│   ├── prometheus/                   # Monitoring config
│   ├── logstash/                     # Log processing
│   ├── Dockerfile                    # Container image
│   ├── docker-compose.yml            # Dev environment
│   ├── docker-compose.monitoring.yml # Monitoring stack
│   ├── requirements.txt              # Python dependencies
│   ├── Makefile                      # Build automation
│   ├── .env.example                  # Config template
│   └── alembic.ini                   # Alembic config
├── docs/                             # Detailed guides
│   ├── QUICK_START.md               # 5-minute setup
│   ├── DEPLOYMENT_WINDOWS.md        # Windows detailed
│   ├── DEPLOYMENT_LINUX.md          # Linux detailed
│   ├── AUTHENTICATION.md            # Auth guide
│   ├── RATE_LIMITS.md              # Rate limiting
│   ├── API_VERSIONING.md           # API versioning
│   └── DEPLOYMENT.md                # General deployment
├── .github/
│   └── workflows/
│       └── ci-cd.yml                # GitHub Actions pipeline
└── README.md                        # This file
```

---

## 🆘 Troubleshooting

### Service won't start

```bash
# Check Docker daemon
docker ps

# View logs
docker-compose logs backend

# Restart service
docker-compose restart backend
```

### Database connection failed

```bash
# Verify PostgreSQL
docker ps | grep postgres

# Test connection
psql -U rtsa_user -d rtsa_db -h localhost

# Check DATABASE_URL
echo $DATABASE_URL
```

### Port already in use

**Windows:**
```powershell
netstat -ano | Select-String ":8000"
Stop-Process -Id <PID> -Force
```

**Linux:**
```bash
lsof -i :8000
kill -9 <PID>
```

### API slow or errors

```bash
# Check metrics
curl http://localhost:9090/api/v1/query?query=http_requests_total

# View Grafana
firefox http://localhost:3000

# Check application logs
docker-compose logs -f backend
```

For more help: See [Detailed Troubleshooting](./docs/TROUBLESHOOTING.md)

---

## 📞 Support

### Documentation
- 🚀 [Quick Start (5 min)](./docs/QUICK_START.md)
- 🪟 [Windows Setup](./docs/DEPLOYMENT_WINDOWS.md)
- 🐧 [Linux Setup](./docs/DEPLOYMENT_LINUX.md)
- 📚 [Full Documentation](./docs/)

### Community
- **GitHub Issues**: [Create issue](https://github.com/yourorg/red-team-saas/issues)
- **Email**: support@readteam.dev
- **API Docs**: http://localhost:8000/api/docs (when running)

---

## 📄 License

All rights reserved. Commercial license required for production use.

**Version**: 1.0.0
**Status**: ✅ Production Ready
**Last Updated**: March 2026

---

## 🎯 Project Status Summary

### Phases Completed: 20/20 ✅

| Phase | Feature | Status |
|-------|---------|--------|
| 1-3 | Core Auth & API | ✅ Complete |
| 4 | Task Execution (Celery) | ✅ Complete |
| 5-6 | Reports & Findings | ✅ Complete |
| 7-8 | Analytics & Alerts | ✅ Complete |
| 9-10 | Projects & Brute Force Tools | ✅ Complete |
| 11-12 | CLI & Threat Intelligence | ✅ Complete |
| 13 | Compliance Engine | ✅ Complete |
| 14-15 | Advanced Reports & Analytics | ✅ Complete |
| 16 | Integration Hub | ✅ Complete |
| 17 | Security Hardening | ✅ Complete |
| 18 | API Documentation | ✅ Complete |
| 19 | DevOps & Deployment | ✅ Complete |
| 20 | Production Monitoring | ✅ Complete |

### Test Summary
- **Total Tests**: 1060+ ✅
- **Pass Rate**: 100% ✅
- **Failures**: 0 ✅
- **Coverage**: >80% ✅

### Ready for Production
- ✅ Docker containers configured
- ✅ Kubernetes manifests ready
- ✅ CI/CD pipeline automated
- ✅ Monitoring stack deployed
- ✅ Documentation complete
- ✅ Security hardened
- ✅ Performance optimized

---

## 🚀 Get Started Now

1. **Clone**: `git clone https://github.com/yourorg/red-team-saas.git`
2. **Setup**: `cd red-team-saas/backend && cp .env.example .env`
3. **Run**: `docker-compose up -d`
4. **Access**: http://localhost:8000/api/docs

See [Quick Start](#quick-start) for detailed instructions.

---

**Built with ❤️ for security professionals**
