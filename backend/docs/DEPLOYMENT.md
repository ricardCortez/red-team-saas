# Deployment Guide — Red Team SaaS

## Table of Contents

1. [Local Development](#local-development)
2. [Staging Deployment](#staging-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Database Migrations](#database-migrations)

---

## Local Development

### Prerequisites

- Docker >= 24.0
- Docker Compose >= 2.20
- Python 3.11+

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/read-team-saas.git
cd read-team-saas/backend

# 2. Configure environment
cp .env.example .env
# Edit .env with your local values

# 3. Start all services
docker-compose up -d

# 4. Run database migrations
docker-compose exec backend alembic upgrade head

# 5. Verify the app is running
curl http://localhost:8000/health
```

### Access Points

| Service   | URL                          |
|-----------|------------------------------|
| API       | http://localhost:8000        |
| Swagger   | http://localhost:8000/api/docs |
| ReDoc     | http://localhost:8000/api/redoc |
| Flower    | http://localhost:5555        |
| Postgres  | localhost:5432               |
| Redis     | localhost:6379               |

### Development Commands

```bash
# Start services
make docker-compose-up

# View logs
docker-compose logs -f backend

# Stop services
make docker-compose-down

# Rebuild and restart
docker-compose up -d --build backend

# Run tests locally
make ci-test
```

---

## Staging Deployment

### Prerequisites

- Docker with registry access
- `.env` file configured for staging

### Build and Push

```bash
# 1. Build the image
make docker-build

# 2. Push to registry
make docker-push

# 3. Deploy using staging compose
docker-compose -f docker-compose.staging.yml up -d
```

### Environment Variables for Staging

Copy `.env.example` to `.env` and fill in all values:

```bash
REGISTRY=ghcr.io/your-org
VERSION=latest
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=your-production-secret
```

---

## Kubernetes Deployment

### Prerequisites

- `kubectl` configured with cluster access
- Namespace `red-team-saas` created

### Initial Setup

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create ConfigMap and Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml   # Update with real values first!

# 3. Deploy storage (StatefulSet for postgres)
kubectl apply -f k8s/postgres-deployment.yaml

# 4. Deploy Redis
kubectl apply -f k8s/redis-deployment.yaml

# 5. Create ServiceAccount and RBAC
kubectl apply -f k8s/serviceaccount.yaml

# 6. Deploy backend
kubectl apply -f k8s/backend-deployment.yaml

# 7. Configure Ingress and TLS
kubectl apply -f k8s/ingress.yaml

# 8. Configure HPA
kubectl apply -f k8s/hpa.yaml

# Or deploy everything at once:
make k8s-deploy
```

### Check Deployment Status

```bash
# Check pods
kubectl get pods -n red-team-saas

# Check services
kubectl get svc -n red-team-saas

# Follow backend logs
make k8s-logs

# Check HPA status
kubectl get hpa -n red-team-saas
```

### Rolling Update (new image)

```bash
kubectl set image deployment/backend \
  backend=ghcr.io/your-org/red-team-saas:NEW_TAG \
  -n red-team-saas

kubectl rollout status deployment/backend -n red-team-saas
```

### Teardown

```bash
make k8s-destroy
# or
kubectl delete namespace red-team-saas
```

---

## Database Migrations

### Alembic Commands

```bash
# Apply all pending migrations
make alembic-upgrade
# or
alembic upgrade head

# Rollback one migration
make alembic-downgrade
# or
alembic downgrade -1

# View migration history
make alembic-history
# or
alembic history --verbose

# Create a new migration
alembic revision --autogenerate -m "describe your change"

# Show current revision
alembic current
```

### Running Migrations in Kubernetes

Migrations should run as an init-container or a Job before the backend starts:

```bash
# Run as a one-off Job
kubectl run alembic-upgrade \
  --image=ghcr.io/your-org/red-team-saas:latest \
  --restart=Never \
  -n red-team-saas \
  -- alembic upgrade head

# Check job status
kubectl logs alembic-upgrade -n red-team-saas
```

### Running via Docker Compose

```bash
docker-compose exec backend alembic upgrade head
```

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) runs:

1. **test** — on every PR and push: runs unit tests with coverage
2. **build** — on push: builds and pushes Docker image to GHCR
3. **deploy-staging** — on push to `develop`: deploys to staging k8s cluster
4. **deploy-production** — on push to `main`: deploys to production (requires approval)

### Required GitHub Secrets

| Secret                 | Description                        |
|------------------------|------------------------------------|
| `KUBECONFIG_STAGING`   | kubectl config for staging cluster |
| `KUBECONFIG_PRODUCTION`| kubectl config for prod cluster    |
| `GITHUB_TOKEN`         | Auto-provided by GitHub Actions    |
