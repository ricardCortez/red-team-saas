.PHONY: docs generate-sdks generate-python-sdk generate-typescript-sdk test lint \
        docker-build docker-push docker-compose-up docker-compose-down \
        k8s-deploy k8s-destroy k8s-logs \
        alembic-upgrade alembic-downgrade alembic-history \
        ci-test ci-build deploy-staging deploy-production

REGISTRY ?= ghcr.io/your-org
IMAGE_NAME ?= red-team-saas
VERSION ?= latest
NAMESPACE ?= red-team-saas

# =============================================================================
# Documentation
# =============================================================================
docs:
	@echo "Documentation available at:"
	@echo "  - Swagger UI:    http://localhost:8000/api/docs"
	@echo "  - ReDoc:         http://localhost:8000/api/redoc"
	@echo "  - OpenAPI JSON:  http://localhost:8000/api/openapi.json"

# =============================================================================
# SDK generation
# =============================================================================
generate-sdks: generate-python-sdk generate-typescript-sdk

generate-python-sdk:
	openapi-python-client generate \
		--url http://localhost:8000/api/openapi.json \
		--output-dir ./python-sdk

generate-typescript-sdk:
	npx openapi-ts --input http://localhost:8000/api/openapi.json --output ./typescript-sdk

# =============================================================================
# Testing & Linting
# =============================================================================
test:
	pytest tests/ -v

lint:
	ruff check app/ tests/

ci-test:
	pytest tests/unit/ --cov=app --cov-report=term-missing -v

# =============================================================================
# Docker
# =============================================================================
docker-build:
	docker build -t $(IMAGE_NAME):latest -f Dockerfile .

docker-push:
	docker tag $(IMAGE_NAME):latest $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
	docker push $(REGISTRY)/$(IMAGE_NAME):$(VERSION)

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

ci-build:
	docker build -t $(REGISTRY)/$(IMAGE_NAME):$(VERSION) -f Dockerfile .

# =============================================================================
# Kubernetes
# =============================================================================
k8s-deploy:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/serviceaccount.yaml
	kubectl apply -f k8s/postgres-deployment.yaml
	kubectl apply -f k8s/redis-deployment.yaml
	kubectl apply -f k8s/backend-deployment.yaml
	kubectl apply -f k8s/ingress.yaml
	kubectl apply -f k8s/hpa.yaml

k8s-destroy:
	kubectl delete namespace $(NAMESPACE)

k8s-logs:
	kubectl logs -f deployment/backend -n $(NAMESPACE)

# =============================================================================
# Alembic migrations
# =============================================================================
alembic-upgrade:
	alembic upgrade head

alembic-downgrade:
	alembic downgrade -1

alembic-history:
	alembic history --verbose

# =============================================================================
# Deployment helpers
# =============================================================================
deploy-staging:
	kubectl set image deployment/backend backend=$(REGISTRY)/$(IMAGE_NAME):$(VERSION) -n $(NAMESPACE)
	kubectl rollout status deployment/backend -n $(NAMESPACE) --timeout=300s

deploy-production:
	kubectl set image deployment/backend backend=$(REGISTRY)/$(IMAGE_NAME):$(VERSION) -n $(NAMESPACE)
	kubectl rollout status deployment/backend -n $(NAMESPACE) --timeout=300s
