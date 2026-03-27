"""
Phase 19 — Deployment & DevOps Tests
Tests for Dockerfile, docker-compose, Alembic, Kubernetes manifests,
GitHub Actions workflow, and Makefile.
"""
import os
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers — resolve paths relative to the backend directory
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/
REPO_ROOT = BACKEND_DIR.parent                      # project root


def _load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _load_yaml_all(path: Path) -> list:
    """Load a YAML file that may contain multiple documents (--- separator)."""
    with open(path, "r") as f:
        return list(yaml.safe_load_all(f))


# ===========================================================================
# TestDockerfile
# ===========================================================================
class TestDockerfile:
    dockerfile_path = BACKEND_DIR / "Dockerfile"

    def test_dockerfile_exists(self):
        assert self.dockerfile_path.exists(), "Dockerfile not found in backend/"

    def test_dockerfile_has_multistage(self):
        content = self.dockerfile_path.read_text()
        stages = [line for line in content.splitlines() if line.strip().upper().startswith("FROM")]
        assert len(stages) >= 2, "Dockerfile should have at least 2 FROM statements (multi-stage)"

    def test_dockerfile_nonroot_user(self):
        content = self.dockerfile_path.read_text()
        assert "appuser" in content, "Dockerfile should create and use non-root user 'appuser'"
        assert "USER appuser" in content, "Dockerfile should switch to non-root user"

    def test_dockerfile_healthcheck(self):
        content = self.dockerfile_path.read_text()
        assert "HEALTHCHECK" in content, "Dockerfile should define a HEALTHCHECK"
        assert "health" in content.lower(), "HEALTHCHECK should reference /health endpoint"

    def test_dockerfile_has_expose_8000(self):
        content = self.dockerfile_path.read_text()
        assert "EXPOSE 8000" in content, "Dockerfile should EXPOSE port 8000"

    def test_dockerfile_has_uvicorn_cmd(self):
        content = self.dockerfile_path.read_text()
        assert "uvicorn" in content, "Dockerfile CMD should use uvicorn"
        assert "app.main:app" in content, "Dockerfile should reference app.main:app"

    def test_dockerfile_builder_stage(self):
        content = self.dockerfile_path.read_text()
        assert "builder" in content.lower() or "AS builder" in content, \
            "Dockerfile should have a named builder stage"

    def test_dockerfile_uses_python_311(self):
        content = self.dockerfile_path.read_text()
        assert "python:3.11" in content, "Dockerfile should use python:3.11"

    def test_dockerfile_copies_requirements(self):
        content = self.dockerfile_path.read_text()
        assert "requirements.txt" in content, "Dockerfile should copy requirements.txt"

    def test_dockerfile_creates_appuser_uid_1000(self):
        content = self.dockerfile_path.read_text()
        assert "1000" in content, "Dockerfile should create user with uid 1000"


# ===========================================================================
# TestDockerCompose
# ===========================================================================
class TestDockerCompose:
    compose_path = BACKEND_DIR / "docker-compose.yml"

    @pytest.fixture(scope="class")
    def compose(self):
        return _load_yaml(self.compose_path)

    def test_docker_compose_exists(self):
        assert self.compose_path.exists(), "docker-compose.yml not found in backend/"

    def test_docker_compose_services(self, compose):
        services = compose.get("services", {})
        required = {"postgres", "redis", "backend", "celery-worker", "celery-beat", "flower"}
        present = set(services.keys())
        assert required.issubset(present), f"Missing services: {required - present}"

    def test_docker_compose_postgres_image(self, compose):
        postgres = compose["services"]["postgres"]
        assert "postgres:15" in postgres["image"], "Postgres service should use postgres:15"

    def test_docker_compose_redis_image(self, compose):
        redis = compose["services"]["redis"]
        assert "redis:7" in redis["image"], "Redis service should use redis:7"

    def test_docker_compose_healthchecks(self, compose):
        services_with_hc = ["postgres", "redis"]
        for svc in services_with_hc:
            assert "healthcheck" in compose["services"][svc], \
                f"Service '{svc}' should have a healthcheck"

    def test_docker_compose_environment_vars(self, compose):
        backend_env = compose["services"]["backend"].get("environment", {})
        if isinstance(backend_env, dict):
            env_keys = set(backend_env.keys())
        else:
            # list format: ["KEY=value", ...]
            env_keys = {item.split("=")[0] for item in backend_env}
        required_vars = {"DATABASE_URL", "REDIS_URL", "SECRET_KEY"}
        assert required_vars.issubset(env_keys), \
            f"Backend service missing env vars: {required_vars - env_keys}"

    def test_docker_compose_volumes(self, compose):
        volumes = compose.get("volumes", {})
        assert len(volumes) >= 2, "docker-compose should define at least 2 named volumes"
        # At least one postgres and one redis volume
        volume_names = " ".join(volumes.keys())
        assert "postgres" in volume_names, "Should have a postgres volume"
        assert "redis" in volume_names, "Should have a redis volume"

    def test_docker_compose_networking(self, compose):
        networks = compose.get("networks", {})
        assert len(networks) >= 1, "docker-compose should define at least one network"

    def test_docker_compose_depends_on(self, compose):
        backend = compose["services"]["backend"]
        depends = backend.get("depends_on", {})
        if isinstance(depends, list):
            assert "postgres" in depends and "redis" in depends
        else:
            assert "postgres" in depends and "redis" in depends

    def test_docker_compose_backend_port(self, compose):
        ports = compose["services"]["backend"].get("ports", [])
        port_strings = [str(p) for p in ports]
        assert any("8000" in p for p in port_strings), "Backend should expose port 8000"

    def test_docker_compose_flower_port(self, compose):
        ports = compose["services"]["flower"].get("ports", [])
        port_strings = [str(p) for p in ports]
        assert any("5555" in p for p in port_strings), "Flower should expose port 5555"

    def test_docker_compose_staging_exists(self):
        staging_path = BACKEND_DIR / "docker-compose.staging.yml"
        assert staging_path.exists(), "docker-compose.staging.yml not found in backend/"

    def test_docker_compose_staging_env_vars(self):
        staging_path = BACKEND_DIR / "docker-compose.staging.yml"
        compose = _load_yaml(staging_path)
        backend_env = compose["services"]["backend"].get("environment", {})
        if isinstance(backend_env, dict):
            # Staging uses ${VAR} references — values should be env-var references
            env_str = str(backend_env)
        else:
            env_str = str(backend_env)
        # Should reference env vars without defaults (staging requires explicit config)
        assert "DATABASE_URL" in env_str, "Staging compose should reference DATABASE_URL"
        assert "SECRET_KEY" in env_str, "Staging compose should reference SECRET_KEY"

    def test_docker_compose_staging_restart_policy(self):
        staging_path = BACKEND_DIR / "docker-compose.staging.yml"
        compose = _load_yaml(staging_path)
        backend = compose["services"]["backend"]
        assert backend.get("restart") == "unless-stopped", \
            "Staging backend should have restart: unless-stopped"

    def test_docker_compose_celery_worker_command(self, compose):
        worker = compose["services"]["celery-worker"]
        command = str(worker.get("command", ""))
        assert "celery" in command and "worker" in command, \
            "celery-worker service should run celery worker"

    def test_docker_compose_celery_beat_command(self, compose):
        beat = compose["services"]["celery-beat"]
        command = str(beat.get("command", ""))
        assert "celery" in command and "beat" in command, \
            "celery-beat service should run celery beat"


# ===========================================================================
# TestAlembic
# ===========================================================================
class TestAlembic:
    ini_path = BACKEND_DIR / "alembic.ini"
    env_path = BACKEND_DIR / "alembic" / "env.py"
    versions_path = BACKEND_DIR / "alembic" / "versions"

    def test_alembic_ini_exists(self):
        assert self.ini_path.exists(), "alembic.ini not found in backend/"

    def test_alembic_env_exists(self):
        assert self.env_path.exists(), "alembic/env.py not found"

    def test_alembic_versions_directory(self):
        assert self.versions_path.exists() and self.versions_path.is_dir(), \
            "alembic/versions/ directory not found"

    def test_alembic_env_has_get_sqlalchemy_url(self):
        content = self.env_path.read_text()
        assert "get_sqlalchemy_url" in content, \
            "alembic/env.py should define get_sqlalchemy_url() function"

    def test_alembic_env_uses_env_var(self):
        content = self.env_path.read_text()
        assert "DATABASE_URL" in content, \
            "alembic/env.py should read DATABASE_URL environment variable"
        assert "os.getenv" in content or "os.environ" in content, \
            "alembic/env.py should use os.getenv/os.environ to read DATABASE_URL"

    def test_alembic_ini_script_location(self):
        content = self.ini_path.read_text()
        assert "script_location" in content, "alembic.ini should have script_location"
        assert "alembic" in content, "script_location should point to alembic directory"

    def test_alembic_migration_tasks_exist(self):
        tasks_path = BACKEND_DIR / "app" / "tasks" / "migration_tasks.py"
        assert tasks_path.exists(), "app/tasks/migration_tasks.py not found"

    def test_alembic_migration_tasks_has_upgrade(self):
        tasks_path = BACKEND_DIR / "app" / "tasks" / "migration_tasks.py"
        content = tasks_path.read_text()
        assert "run_alembic_upgrade" in content, \
            "migration_tasks.py should define run_alembic_upgrade task"

    def test_alembic_migration_tasks_has_downgrade(self):
        tasks_path = BACKEND_DIR / "app" / "tasks" / "migration_tasks.py"
        content = tasks_path.read_text()
        assert "run_alembic_downgrade" in content, \
            "migration_tasks.py should define run_alembic_downgrade task"

    def test_alembic_migration_tasks_return_dict(self):
        tasks_path = BACKEND_DIR / "app" / "tasks" / "migration_tasks.py"
        content = tasks_path.read_text()
        assert '"status"' in content or "'status'" in content, \
            "migration tasks should return dict with 'status' key"


# ===========================================================================
# TestKubernetes
# ===========================================================================
K8S_DIR = BACKEND_DIR / "k8s"

K8S_FILES = [
    "namespace.yaml",
    "configmap.yaml",
    "secrets.yaml",
    "postgres-deployment.yaml",
    "redis-deployment.yaml",
    "backend-deployment.yaml",
    "ingress.yaml",
    "hpa.yaml",
    "serviceaccount.yaml",
]


class TestKubernetes:
    def test_k8s_manifests_all_exist(self):
        missing = [f for f in K8S_FILES if not (K8S_DIR / f).exists()]
        assert not missing, f"Missing k8s manifests: {missing}"

    def test_k8s_manifests_valid_yaml(self):
        for filename in K8S_FILES:
            path = K8S_DIR / filename
            docs = _load_yaml_all(path)
            assert len(docs) >= 1 and docs[0] is not None, \
                f"{filename} is not valid YAML or is empty"

    def test_k8s_namespace_configured(self):
        docs = _load_yaml_all(K8S_DIR / "namespace.yaml")
        ns = docs[0]
        assert ns["kind"] == "Namespace"
        assert ns["metadata"]["name"] == "red-team-saas"

    def test_k8s_namespace_has_labels(self):
        docs = _load_yaml_all(K8S_DIR / "namespace.yaml")
        ns = docs[0]
        assert "labels" in ns["metadata"], "namespace should have labels"
        assert ns["metadata"]["labels"].get("app") == "red-team-saas"

    def test_k8s_postgres_statefulset(self):
        docs = _load_yaml_all(K8S_DIR / "postgres-deployment.yaml")
        kinds = [d["kind"] for d in docs if d]
        assert "StatefulSet" in kinds, "postgres should use a StatefulSet for persistence"

    def test_k8s_postgres_volume_claim_template(self):
        docs = _load_yaml_all(K8S_DIR / "postgres-deployment.yaml")
        sts = next(d for d in docs if d and d["kind"] == "StatefulSet")
        assert "volumeClaimTemplates" in sts["spec"], \
            "StatefulSet should have volumeClaimTemplates"
        storage = sts["spec"]["volumeClaimTemplates"][0]["spec"]["resources"]["requests"]["storage"]
        assert "Gi" in storage, "Postgres should request storage in Gi"

    def test_k8s_redis_deployment(self):
        docs = _load_yaml_all(K8S_DIR / "redis-deployment.yaml")
        kinds = [d["kind"] for d in docs if d]
        assert "Deployment" in kinds, "redis should use a Deployment"

    def test_k8s_redis_service(self):
        docs = _load_yaml_all(K8S_DIR / "redis-deployment.yaml")
        kinds = [d["kind"] for d in docs if d]
        assert "Service" in kinds, "redis-deployment.yaml should include a Service"

    def test_k8s_backend_deployment_replicas_3(self):
        docs = _load_yaml_all(K8S_DIR / "backend-deployment.yaml")
        deployment = next(d for d in docs if d and d["kind"] == "Deployment")
        assert deployment["spec"]["replicas"] == 3, "Backend should have 3 replicas"

    def test_k8s_backend_liveness_probe(self):
        docs = _load_yaml_all(K8S_DIR / "backend-deployment.yaml")
        deployment = next(d for d in docs if d and d["kind"] == "Deployment")
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        assert "livenessProbe" in container, "Backend container should have livenessProbe"
        probe_path = container["livenessProbe"]["httpGet"]["path"]
        assert probe_path == "/health", "Liveness probe should check /health"

    def test_k8s_backend_readiness_probe(self):
        docs = _load_yaml_all(K8S_DIR / "backend-deployment.yaml")
        deployment = next(d for d in docs if d and d["kind"] == "Deployment")
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        assert "readinessProbe" in container, "Backend container should have readinessProbe"

    def test_k8s_backend_resources_configured(self):
        docs = _load_yaml_all(K8S_DIR / "backend-deployment.yaml")
        deployment = next(d for d in docs if d and d["kind"] == "Deployment")
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        assert "resources" in container, "Backend container should have resource limits/requests"
        assert "requests" in container["resources"]
        assert "limits" in container["resources"]

    def test_k8s_backend_security_context(self):
        docs = _load_yaml_all(K8S_DIR / "backend-deployment.yaml")
        deployment = next(d for d in docs if d and d["kind"] == "Deployment")
        spec = deployment["spec"]["template"]["spec"]
        # Either pod-level or container-level securityContext
        pod_sc = spec.get("securityContext", {})
        container_sc = deployment["spec"]["template"]["spec"]["containers"][0].get("securityContext", {})
        run_as_non_root = pod_sc.get("runAsNonRoot") or container_sc.get("runAsNonRoot")
        run_as_user = pod_sc.get("runAsUser") or container_sc.get("runAsUser")
        assert run_as_non_root is True, "Backend should run as non-root"
        assert run_as_user == 1000, "Backend should run as uid 1000"

    def test_k8s_backend_rolling_update(self):
        docs = _load_yaml_all(K8S_DIR / "backend-deployment.yaml")
        deployment = next(d for d in docs if d and d["kind"] == "Deployment")
        strategy = deployment["spec"].get("strategy", {})
        assert strategy.get("type") == "RollingUpdate", "Backend should use RollingUpdate strategy"

    def test_k8s_ingress_tls_configured(self):
        docs = _load_yaml_all(K8S_DIR / "ingress.yaml")
        ingress = next(d for d in docs if d and d["kind"] == "Ingress")
        assert "tls" in ingress["spec"], "Ingress should have TLS configured"
        tls_hosts = ingress["spec"]["tls"][0]["hosts"]
        assert len(tls_hosts) >= 1, "TLS should specify at least one host"

    def test_k8s_ingress_classname_nginx(self):
        docs = _load_yaml_all(K8S_DIR / "ingress.yaml")
        ingress = next(d for d in docs if d and d["kind"] == "Ingress")
        assert ingress["spec"].get("ingressClassName") == "nginx", \
            "Ingress should use nginx ingressClassName"

    def test_k8s_ingress_cert_manager_annotation(self):
        docs = _load_yaml_all(K8S_DIR / "ingress.yaml")
        ingress = next(d for d in docs if d and d["kind"] == "Ingress")
        annotations = ingress["metadata"].get("annotations", {})
        assert any("cert-manager" in k for k in annotations), \
            "Ingress should have cert-manager annotation"

    def test_k8s_hpa_min_max_replicas(self):
        docs = _load_yaml_all(K8S_DIR / "hpa.yaml")
        hpa = next(d for d in docs if d and d["kind"] == "HorizontalPodAutoscaler")
        assert hpa["spec"]["minReplicas"] == 3, "HPA minReplicas should be 3"
        assert hpa["spec"]["maxReplicas"] == 10, "HPA maxReplicas should be 10"

    def test_k8s_hpa_cpu_memory_targets(self):
        docs = _load_yaml_all(K8S_DIR / "hpa.yaml")
        hpa = next(d for d in docs if d and d["kind"] == "HorizontalPodAutoscaler")
        metrics = hpa["spec"]["metrics"]
        resource_names = [m["resource"]["name"] for m in metrics if m.get("type") == "Resource"]
        assert "cpu" in resource_names, "HPA should include CPU metric"
        assert "memory" in resource_names, "HPA should include memory metric"

    def test_k8s_hpa_cpu_threshold_70(self):
        docs = _load_yaml_all(K8S_DIR / "hpa.yaml")
        hpa = next(d for d in docs if d and d["kind"] == "HorizontalPodAutoscaler")
        cpu_metric = next(
            m for m in hpa["spec"]["metrics"]
            if m.get("type") == "Resource" and m["resource"]["name"] == "cpu"
        )
        utilization = cpu_metric["resource"]["target"]["averageUtilization"]
        assert utilization == 70, "CPU target utilization should be 70%"

    def test_k8s_hpa_memory_threshold_80(self):
        docs = _load_yaml_all(K8S_DIR / "hpa.yaml")
        hpa = next(d for d in docs if d and d["kind"] == "HorizontalPodAutoscaler")
        mem_metric = next(
            m for m in hpa["spec"]["metrics"]
            if m.get("type") == "Resource" and m["resource"]["name"] == "memory"
        )
        utilization = mem_metric["resource"]["target"]["averageUtilization"]
        assert utilization == 80, "Memory target utilization should be 80%"

    def test_k8s_serviceaccount_exists(self):
        docs = _load_yaml_all(K8S_DIR / "serviceaccount.yaml")
        kinds = [d["kind"] for d in docs if d]
        assert "ServiceAccount" in kinds, "serviceaccount.yaml should define a ServiceAccount"
        sa = next(d for d in docs if d and d["kind"] == "ServiceAccount")
        assert sa["metadata"]["name"] == "rtsa-sa"

    def test_k8s_rbac_role_and_binding(self):
        docs = _load_yaml_all(K8S_DIR / "serviceaccount.yaml")
        kinds = [d["kind"] for d in docs if d]
        assert "Role" in kinds, "serviceaccount.yaml should define a Role"
        assert "RoleBinding" in kinds, "serviceaccount.yaml should define a RoleBinding"

    def test_k8s_rbac_role_resources(self):
        docs = _load_yaml_all(K8S_DIR / "serviceaccount.yaml")
        role = next(d for d in docs if d and d["kind"] == "Role")
        resources = []
        for rule in role["rules"]:
            resources.extend(rule.get("resources", []))
        assert "configmaps" in resources or "secrets" in resources, \
            "Role should grant access to configmaps and/or secrets"

    def test_k8s_configmap_has_environment(self):
        docs = _load_yaml_all(K8S_DIR / "configmap.yaml")
        cm = next(d for d in docs if d and d["kind"] == "ConfigMap")
        data = cm.get("data", {})
        assert "ENVIRONMENT" in data, "ConfigMap should have ENVIRONMENT key"

    def test_k8s_secrets_type_opaque(self):
        docs = _load_yaml_all(K8S_DIR / "secrets.yaml")
        secret = next(d for d in docs if d and d["kind"] == "Secret")
        assert secret["type"] == "Opaque", "Secret type should be Opaque"

    def test_k8s_all_resources_in_namespace(self):
        """Verify all resources reference the red-team-saas namespace."""
        skip_kinds = {"Namespace"}
        for filename in K8S_FILES:
            docs = _load_yaml_all(K8S_DIR / filename)
            for doc in docs:
                if doc and doc.get("kind") not in skip_kinds:
                    ns = doc.get("metadata", {}).get("namespace")
                    assert ns == "red-team-saas", \
                        f"{filename} resource {doc['kind']} should be in namespace red-team-saas"


# ===========================================================================
# TestGitHubActions
# ===========================================================================
class TestGitHubActions:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "ci-cd.yml"

    @pytest.fixture(scope="class")
    def workflow(self):
        return _load_yaml(self.workflow_path)

    def test_ci_cd_workflow_exists(self):
        assert self.workflow_path.exists(), ".github/workflows/ci-cd.yml not found"

    def test_workflow_valid_yaml(self):
        content = _load_yaml(self.workflow_path)
        assert content is not None, "ci-cd.yml must be valid YAML"

    def test_workflow_has_test_job(self, workflow):
        jobs = workflow.get("jobs", {})
        assert "test" in jobs, "Workflow should have a 'test' job"

    def test_workflow_has_build_job(self, workflow):
        jobs = workflow.get("jobs", {})
        assert "build" in jobs, "Workflow should have a 'build' job"

    def test_workflow_test_services(self, workflow):
        test_job = workflow["jobs"]["test"]
        services = test_job.get("services", {})
        assert "postgres" in services, "test job should have postgres service"
        assert "redis" in services, "test job should have redis service"

    def test_workflow_test_uses_coverage(self, workflow):
        test_job = workflow["jobs"]["test"]
        steps = test_job.get("steps", [])
        steps_str = str(steps)
        assert "--cov" in steps_str or "coverage" in steps_str.lower(), \
            "test job should run tests with coverage"

    def test_workflow_build_needs_test(self, workflow):
        build_job = workflow["jobs"]["build"]
        needs = build_job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "test" in needs, "build job should depend on test job"

    def test_workflow_deploy_staging_needs_build(self, workflow):
        jobs = workflow.get("jobs", {})
        staging_job = jobs.get("deploy-staging") or jobs.get("deploy_staging")
        assert staging_job is not None, "Workflow should have a deploy-staging job"
        needs = staging_job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "build" in needs, "deploy-staging should depend on build"

    def test_workflow_deploy_production_needs_build(self, workflow):
        jobs = workflow.get("jobs", {})
        prod_job = jobs.get("deploy-production") or jobs.get("deploy_production")
        assert prod_job is not None, "Workflow should have a deploy-production job"
        needs = prod_job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "build" in needs, "deploy-production should depend on build"

    def test_workflow_deploy_staging_if_develop_branch(self, workflow):
        jobs = workflow.get("jobs", {})
        staging_job = jobs.get("deploy-staging") or jobs.get("deploy_staging")
        condition = str(staging_job.get("if", ""))
        assert "develop" in condition, "deploy-staging should only run on develop branch"

    def test_workflow_deploy_production_if_main_branch(self, workflow):
        jobs = workflow.get("jobs", {})
        prod_job = jobs.get("deploy-production") or jobs.get("deploy_production")
        condition = str(prod_job.get("if", ""))
        assert "main" in condition, "deploy-production should only run on main branch"

    def test_workflow_triggers_on_push(self, workflow):
        # PyYAML parses 'on:' as True (YAML 1.1 boolean alias); handle both keys
        on = workflow.get("on") or workflow.get(True, {}) or {}
        assert "push" in on, "Workflow should trigger on push"

    def test_workflow_triggers_on_pull_request(self, workflow):
        on = workflow.get("on") or workflow.get(True, {}) or {}
        assert "pull_request" in on, "Workflow should trigger on pull_request"

    def test_workflow_build_uses_buildx(self, workflow):
        build_job = workflow["jobs"]["build"]
        steps_str = str(build_job.get("steps", []))
        assert "buildx" in steps_str.lower(), "build job should set up Docker Buildx"

    def test_workflow_build_pushes_image(self, workflow):
        build_job = workflow["jobs"]["build"]
        steps_str = str(build_job.get("steps", []))
        assert "push" in steps_str.lower(), "build job should push Docker image"

    def test_workflow_uses_cache(self, workflow):
        build_job = workflow["jobs"]["build"]
        steps_str = str(build_job.get("steps", []))
        assert "cache" in steps_str.lower(), "build job should use Docker layer caching"


# ===========================================================================
# TestMakefile
# ===========================================================================
class TestMakefile:
    makefile_path = BACKEND_DIR / "Makefile"

    @pytest.fixture(scope="class")
    def makefile_content(self):
        return self.makefile_path.read_text()

    def test_makefile_exists(self):
        assert self.makefile_path.exists(), "Makefile not found in backend/"

    def test_makefile_docker_targets(self, makefile_content):
        required = ["docker-build", "docker-push", "docker-compose-up", "docker-compose-down"]
        for target in required:
            assert target in makefile_content, f"Makefile missing target: {target}"

    def test_makefile_k8s_targets(self, makefile_content):
        required = ["k8s-deploy", "k8s-destroy", "k8s-logs"]
        for target in required:
            assert target in makefile_content, f"Makefile missing target: {target}"

    def test_makefile_alembic_targets(self, makefile_content):
        required = ["alembic-upgrade", "alembic-downgrade", "alembic-history"]
        for target in required:
            assert target in makefile_content, f"Makefile missing target: {target}"

    def test_makefile_deployment_targets(self, makefile_content):
        required = ["deploy-staging", "deploy-production", "ci-test", "ci-build"]
        for target in required:
            assert target in makefile_content, f"Makefile missing target: {target}"

    def test_makefile_has_phony_declarations(self, makefile_content):
        assert ".PHONY" in makefile_content, "Makefile should have .PHONY declarations"

    def test_makefile_alembic_upgrade_head(self, makefile_content):
        assert "alembic upgrade head" in makefile_content, \
            "alembic-upgrade target should run 'alembic upgrade head'"

    def test_makefile_alembic_downgrade_minus_one(self, makefile_content):
        assert "alembic downgrade -1" in makefile_content, \
            "alembic-downgrade target should run 'alembic downgrade -1'"

    def test_makefile_kubectl_apply(self, makefile_content):
        assert "kubectl apply" in makefile_content, \
            "k8s-deploy target should use kubectl apply"

    def test_makefile_rollout_status(self, makefile_content):
        assert "rollout status" in makefile_content, \
            "deploy targets should check rollout status"


# ===========================================================================
# TestEnvExample
# ===========================================================================
class TestEnvExample:
    env_example_path = BACKEND_DIR / ".env.example"

    def test_env_example_exists(self):
        assert self.env_example_path.exists(), ".env.example not found in backend/"

    def test_env_example_has_database_url(self):
        content = self.env_example_path.read_text()
        assert "DATABASE_URL" in content

    def test_env_example_has_redis_url(self):
        content = self.env_example_path.read_text()
        assert "REDIS_URL" in content

    def test_env_example_has_secret_key(self):
        content = self.env_example_path.read_text()
        assert "SECRET_KEY" in content

    def test_env_example_has_aws_vars(self):
        content = self.env_example_path.read_text()
        assert "AWS_ACCESS_KEY_ID" in content

    def test_env_example_has_github_vars(self):
        content = self.env_example_path.read_text()
        assert "GITHUB_CLIENT_ID" in content

    def test_env_example_has_smtp_vars(self):
        content = self.env_example_path.read_text()
        assert "SMTP_HOST" in content


# ===========================================================================
# TestDockerignore
# ===========================================================================
class TestDockerignore:
    dockerignore_path = BACKEND_DIR / ".dockerignore"

    def test_dockerignore_exists(self):
        assert self.dockerignore_path.exists(), ".dockerignore not found in backend/"

    def test_dockerignore_excludes_pycache(self):
        content = self.dockerignore_path.read_text()
        assert "__pycache__" in content

    def test_dockerignore_excludes_venv(self):
        content = self.dockerignore_path.read_text()
        assert "venv" in content

    def test_dockerignore_excludes_tests(self):
        content = self.dockerignore_path.read_text()
        assert "tests" in content

    def test_dockerignore_excludes_git(self):
        content = self.dockerignore_path.read_text()
        assert ".git" in content
