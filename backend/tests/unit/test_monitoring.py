"""
tests/unit/test_monitoring.py

Phase 20 — Production Launch & Monitoring
Tests for Prometheus metrics, Sentry config, ELK Stack, Grafana, and alerting.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # d:/Proyectos/read-team-saas
BACKEND_ROOT = PROJECT_ROOT / "backend"


# ---------------------------------------------------------------------------
# 1. Prometheus configuration files
# ---------------------------------------------------------------------------


class TestPrometheusConfig:
    def test_prometheus_yml_exists(self):
        assert (PROJECT_ROOT / "prometheus" / "prometheus.yml").exists()

    def test_prometheus_yml_has_scrape_configs(self):
        content = (PROJECT_ROOT / "prometheus" / "prometheus.yml").read_text()
        assert "scrape_configs" in content

    def test_prometheus_yml_has_app_job(self):
        content = (PROJECT_ROOT / "prometheus" / "prometheus.yml").read_text()
        assert "red-team-saas" in content

    def test_prometheus_yml_has_metrics_path(self):
        content = (PROJECT_ROOT / "prometheus" / "prometheus.yml").read_text()
        assert "/metrics" in content

    def test_prometheus_yml_has_alertmanager(self):
        content = (PROJECT_ROOT / "prometheus" / "prometheus.yml").read_text()
        assert "alertmanagers" in content

    def test_alert_rules_yml_exists(self):
        assert (PROJECT_ROOT / "prometheus" / "alert-rules.yml").exists()

    def test_alert_rules_has_high_error_rate(self):
        content = (PROJECT_ROOT / "prometheus" / "alert-rules.yml").read_text()
        assert "HighErrorRate" in content

    def test_alert_rules_has_high_latency(self):
        content = (PROJECT_ROOT / "prometheus" / "alert-rules.yml").read_text()
        assert "HighLatency" in content

    def test_alert_rules_has_disk_space(self):
        content = (PROJECT_ROOT / "prometheus" / "alert-rules.yml").read_text()
        assert "DiskSpaceRunningOut" in content

    def test_alert_rules_has_database_alert(self):
        content = (PROJECT_ROOT / "prometheus" / "alert-rules.yml").read_text()
        assert "DatabaseConnectionPoolExhausted" in content

    def test_alert_rules_has_redis_alert(self):
        content = (PROJECT_ROOT / "prometheus" / "alert-rules.yml").read_text()
        assert "RedisMemoryHigh" in content

    def test_alert_rules_has_severity_labels(self):
        content = (PROJECT_ROOT / "prometheus" / "alert-rules.yml").read_text()
        assert "severity" in content

    def test_alertmanager_yml_exists(self):
        assert (PROJECT_ROOT / "prometheus" / "alertmanager.yml").exists()

    def test_alertmanager_has_slack_receiver(self):
        content = (PROJECT_ROOT / "prometheus" / "alertmanager.yml").read_text()
        assert "slack" in content


# ---------------------------------------------------------------------------
# 2. Prometheus metrics middleware
# ---------------------------------------------------------------------------


class TestMetricsMiddleware:
    def test_metrics_middleware_module_importable(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import MetricsMiddleware
        assert MetricsMiddleware is not None

    def test_request_count_counter_exists(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import REQUEST_COUNT
        assert REQUEST_COUNT is not None

    def test_request_duration_histogram_exists(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import REQUEST_DURATION
        assert REQUEST_DURATION is not None

    def test_active_requests_gauge_exists(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import ACTIVE_REQUESTS
        assert ACTIVE_REQUESTS is not None

    def test_rate_limit_counter_exists(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import RATE_LIMIT_EXCEEDED
        assert RATE_LIMIT_EXCEEDED is not None

    def test_finding_count_counter_exists(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import FINDING_COUNT
        assert FINDING_COUNT is not None

    def test_tool_execution_histogram_exists(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import TOOL_EXECUTION_DURATION
        assert TOOL_EXECUTION_DURATION is not None

    def test_db_query_histogram_exists(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import DB_QUERY_DURATION
        assert DB_QUERY_DURATION is not None

    def test_normalize_path_replaces_uuids(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import _normalize_path
        path = "/api/v1/projects/550e8400-e29b-41d4-a716-446655440000/scans"
        result = _normalize_path(path)
        assert "{id}" in result
        assert "550e8400" not in result

    def test_normalize_path_replaces_numeric_ids(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import _normalize_path
        path = "/api/v1/users/42/profile"
        result = _normalize_path(path)
        assert "{id}" in result
        assert "42" not in result

    def test_normalize_path_keeps_plain_path(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.middleware.metrics_middleware import _normalize_path
        path = "/api/v1/health"
        assert _normalize_path(path) == path


# ---------------------------------------------------------------------------
# 3. Sentry configuration
# ---------------------------------------------------------------------------


class TestSentryConfig:
    def test_sentry_config_module_importable(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.core.sentry_config import init_sentry
        assert callable(init_sentry)

    def test_init_sentry_no_op_without_dsn(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.core.sentry_config import init_sentry
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SENTRY_DSN", None)
            # Should not raise
            init_sentry()

    def test_before_send_filters_404(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.core.sentry_config import _before_send
        from fastapi import HTTPException
        exc = HTTPException(status_code=404)
        hint = {"exc_info": (type(exc), exc, None)}
        result = _before_send({}, hint)
        assert result is None

    def test_before_send_filters_401(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.core.sentry_config import _before_send
        from fastapi import HTTPException
        exc = HTTPException(status_code=401)
        hint = {"exc_info": (type(exc), exc, None)}
        result = _before_send({}, hint)
        assert result is None

    def test_before_send_allows_500(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.core.sentry_config import _before_send
        event = {"message": "Internal Server Error"}
        result = _before_send(event, {})
        assert result == event


# ---------------------------------------------------------------------------
# 4. Grafana & Kubernetes manifests
# ---------------------------------------------------------------------------


class TestGrafanaConfig:
    def test_grafana_datasource_yaml_exists(self):
        assert (PROJECT_ROOT / "k8s" / "grafana-datasource.yaml").exists()

    def test_grafana_datasource_has_prometheus(self):
        content = (PROJECT_ROOT / "k8s" / "grafana-datasource.yaml").read_text()
        assert "Prometheus" in content

    def test_grafana_datasource_has_elasticsearch(self):
        content = (PROJECT_ROOT / "k8s" / "grafana-datasource.yaml").read_text()
        assert "Elasticsearch" in content

    def test_grafana_deployment_yaml_exists(self):
        assert (PROJECT_ROOT / "k8s" / "grafana-deployment.yaml").exists()

    def test_grafana_deployment_has_ingress(self):
        content = (PROJECT_ROOT / "k8s" / "grafana-deployment.yaml").read_text()
        assert "Ingress" in content

    def test_grafana_deployment_has_secret_ref(self):
        content = (PROJECT_ROOT / "k8s" / "grafana-deployment.yaml").read_text()
        assert "secretKeyRef" in content

    def test_prometheus_deployment_yaml_exists(self):
        assert (PROJECT_ROOT / "k8s" / "prometheus-deployment.yaml").exists()

    def test_prometheus_deployment_has_rbac(self):
        content = (PROJECT_ROOT / "k8s" / "prometheus-deployment.yaml").read_text()
        assert "ClusterRole" in content

    def test_elasticsearch_deployment_yaml_exists(self):
        assert (PROJECT_ROOT / "k8s" / "elasticsearch-deployment.yaml").exists()

    def test_elasticsearch_deployment_has_memory_limits(self):
        content = (PROJECT_ROOT / "k8s" / "elasticsearch-deployment.yaml").read_text()
        assert "limits" in content

    def test_kibana_deployment_yaml_exists(self):
        assert (PROJECT_ROOT / "k8s" / "kibana-deployment.yaml").exists()

    def test_kibana_deployment_has_elasticsearch_env(self):
        content = (PROJECT_ROOT / "k8s" / "kibana-deployment.yaml").read_text()
        assert "ELASTICSEARCH_HOSTS" in content


# ---------------------------------------------------------------------------
# 5. ELK Stack — Logstash
# ---------------------------------------------------------------------------


class TestELKStack:
    def test_logstash_conf_exists(self):
        assert (PROJECT_ROOT / "logstash" / "logstash.conf").exists()

    def test_logstash_has_input_tcp(self):
        content = (PROJECT_ROOT / "logstash" / "logstash.conf").read_text()
        assert "tcp" in content

    def test_logstash_has_elasticsearch_output(self):
        content = (PROJECT_ROOT / "logstash" / "logstash.conf").read_text()
        assert "elasticsearch" in content

    def test_logstash_has_filter_section(self):
        content = (PROJECT_ROOT / "logstash" / "logstash.conf").read_text()
        assert "filter" in content

    def test_logstash_has_grok_pattern(self):
        content = (PROJECT_ROOT / "logstash" / "logstash.conf").read_text()
        assert "grok" in content

    def test_logstash_index_pattern(self):
        content = (PROJECT_ROOT / "logstash" / "logstash.conf").read_text()
        assert "logs-" in content


# ---------------------------------------------------------------------------
# 6. Docker Compose monitoring
# ---------------------------------------------------------------------------


class TestDockerComposeMonitoring:
    def test_docker_compose_monitoring_exists(self):
        assert (PROJECT_ROOT / "docker-compose.monitoring.yml").exists()

    def test_docker_compose_has_prometheus_service(self):
        content = (PROJECT_ROOT / "docker-compose.monitoring.yml").read_text()
        assert "prometheus:" in content

    def test_docker_compose_has_grafana_service(self):
        content = (PROJECT_ROOT / "docker-compose.monitoring.yml").read_text()
        assert "grafana:" in content

    def test_docker_compose_has_elasticsearch(self):
        content = (PROJECT_ROOT / "docker-compose.monitoring.yml").read_text()
        assert "elasticsearch:" in content

    def test_docker_compose_has_kibana(self):
        content = (PROJECT_ROOT / "docker-compose.monitoring.yml").read_text()
        assert "kibana:" in content

    def test_docker_compose_has_logstash(self):
        content = (PROJECT_ROOT / "docker-compose.monitoring.yml").read_text()
        assert "logstash:" in content

    def test_docker_compose_has_named_volumes(self):
        content = (PROJECT_ROOT / "docker-compose.monitoring.yml").read_text()
        assert "prometheus_data:" in content
        assert "grafana_data:" in content
        assert "elasticsearch_data:" in content


# ---------------------------------------------------------------------------
# 7. JSON logging configuration
# ---------------------------------------------------------------------------


class TestLoggingConfig:
    def test_logging_config_module_importable(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        import app.logging_config  # noqa: F401

    def test_logging_config_exposes_logger(self):
        sys.path.insert(0, str(BACKEND_ROOT))
        from app.logging_config import logger
        assert logger is not None


# ---------------------------------------------------------------------------
# 8. main.py integration
# ---------------------------------------------------------------------------


class TestMainIntegration:
    def test_main_imports_metrics_middleware(self):
        content = (BACKEND_ROOT / "app" / "main.py").read_text()
        assert "MetricsMiddleware" in content

    def test_main_imports_sentry(self):
        content = (BACKEND_ROOT / "app" / "main.py").read_text()
        assert "init_sentry" in content

    def test_main_has_metrics_endpoint(self):
        content = (BACKEND_ROOT / "app" / "main.py").read_text()
        assert '"/metrics"' in content

    def test_main_calls_init_sentry(self):
        content = (BACKEND_ROOT / "app" / "main.py").read_text()
        assert "init_sentry()" in content


# ---------------------------------------------------------------------------
# 9. Requirements
# ---------------------------------------------------------------------------


class TestRequirements:
    def test_prometheus_client_in_requirements(self):
        content = (BACKEND_ROOT / "requirements.txt").read_text()
        assert "prometheus-client" in content

    def test_python_json_logger_in_requirements(self):
        content = (BACKEND_ROOT / "requirements.txt").read_text()
        assert "python-json-logger" in content

    def test_sentry_sdk_in_requirements(self):
        content = (BACKEND_ROOT / "requirements.txt").read_text()
        assert "sentry-sdk" in content

    def test_prometheus_client_installed(self):
        import prometheus_client  # noqa: F401

    def test_prometheus_client_generates_metrics(self):
        from prometheus_client import Counter, generate_latest
        c = Counter("test_monitoring_counter_total", "Test counter for monitoring tests")
        c.inc()
        output = generate_latest().decode("utf-8")
        assert "test_monitoring_counter_total" in output
