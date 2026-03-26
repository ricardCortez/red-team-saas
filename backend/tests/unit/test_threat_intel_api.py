"""Unit tests for Threat Intelligence API endpoints - Phase 12"""
import pytest
from unittest.mock import patch, MagicMock
from app.models.cve import CVE
from app.models.mitre_technique import MitreTechnique
from app.models.ioc import IOC, IOCType, IOCThreatLevel


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_and_login(client, email="ti@example.com", username="tiuser", role=None):
    data = {
        "email": email,
        "username": username,
        "password": "TestPass123!",
        "full_name": "TI User",
    }
    client.post("/api/v1/auth/register", json=data)
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": email, "password": "TestPass123!"},
    )
    return resp.json()["access_token"]


def _admin_token(client):
    """Register an admin user and return token."""
    data = {
        "email": "admin@example.com",
        "username": "adminuser",
        "password": "AdminPass123!",
        "full_name": "Admin",
    }
    client.post("/api/v1/auth/register", json=data)
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    token = resp.json()["access_token"]

    # Promote to admin + superuser via DB
    from app.database import SessionLocal
    from app.models.user import User, UserRoleEnum
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@example.com").first()
        if user:
            user.is_superuser = True
            user.role = UserRoleEnum.admin
            db.commit()
    finally:
        db.close()

    return token


# ── CVE tests ─────────────────────────────────────────────────────────────────

class TestCVEEndpoints:

    def test_get_cve_from_cache(self, client, db_session):
        token = _register_and_login(client)
        cve = CVE(
            cve_id="CVE-2024-0001",
            description="Test CVE",
            cvss_v3_score=7.5,
            severity="high",
        )
        db_session.add(cve)
        db_session.commit()

        resp = client.get(
            "/api/v1/threat-intel/cve/CVE-2024-0001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["cve_id"] == "CVE-2024-0001"

    def test_get_cve_fetches_nvd_on_miss(self, client):
        token = _register_and_login(client, email="user2@example.com", username="user2")
        nvd_data = {
            "cve_id": "CVE-2024-9999",
            "description": "From NVD",
            "cvss_v3_score": 9.0,
            "cvss_v3_vector": None,
            "cvss_v2_score": None,
            "severity": "critical",
            "cwe_ids": [],
            "affected_products": [],
            "references": [],
            "published_at": None,
            "modified_at": None,
        }
        with patch("app.core.threat_intel.nvd_client.NVDClient.get_cve", return_value=nvd_data):
            with patch("app.core.threat_intel.nvd_client.time.sleep"):
                resp = client.get(
                    "/api/v1/threat-intel/cve/CVE-2024-9999",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert resp.status_code == 200

    def test_get_cve_not_found(self, client):
        token = _register_and_login(client, email="user3@example.com", username="user3")
        with patch("app.core.threat_intel.nvd_client.NVDClient.get_cve", return_value=None):
            resp = client.get(
                "/api/v1/threat-intel/cve/CVE-9999-0000",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 404


# ── MITRE tests ───────────────────────────────────────────────────────────────

class TestMITREEndpoints:

    def test_list_mitre_techniques(self, client, db_session):
        token = _register_and_login(client, email="mitre1@example.com", username="mitre1")
        for i in range(3):
            t = MitreTechnique(
                technique_id=f"T100{i}",
                name=f"Technique {i}",
                tactic="execution",
                tactic_name="Execution",
            )
            db_session.add(t)
        db_session.commit()

        resp = client.get(
            "/api/v1/threat-intel/mitre/techniques",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

    def test_filter_techniques_by_tactic(self, client, db_session):
        token = _register_and_login(client, email="mitre2@example.com", username="mitre2")
        db_session.add(MitreTechnique(
            technique_id="T2001", name="Phishing", tactic="initial-access", tactic_name="Initial Access",
        ))
        db_session.add(MitreTechnique(
            technique_id="T2002", name="PowerShell", tactic="execution", tactic_name="Execution",
        ))
        db_session.commit()

        resp = client.get(
            "/api/v1/threat-intel/mitre/techniques?tactic=initial-access",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["tactic"] == "initial-access"

    def test_get_technique_with_related_cves(self, client, db_session):
        token = _register_and_login(client, email="mitre3@example.com", username="mitre3")
        db_session.add(MitreTechnique(
            technique_id="T3001", name="Test Technique", tactic="execution", tactic_name="Execution",
        ))
        db_session.commit()

        resp = client.get(
            "/api/v1/threat-intel/mitre/T3001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["technique_id"] == "T3001"
        assert "related_cves" in data

    def test_get_technique_not_found(self, client):
        token = _register_and_login(client, email="mitre4@example.com", username="mitre4")
        resp = client.get(
            "/api/v1/threat-intel/mitre/T9999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ── IOC tests ─────────────────────────────────────────────────────────────────

class TestIOCEndpoints:

    def test_check_ioc_found(self, client, db_session):
        token = _register_and_login(client, email="ioc1@example.com", username="ioc1")
        db_session.add(IOC(
            value="192.168.0.100",
            ioc_type=IOCType.IP,
            threat_level=IOCThreatLevel.HIGH,
            source="feodotracker",
            confidence=0.9,
            is_active=True,
        ))
        db_session.commit()

        resp = client.get(
            "/api/v1/threat-intel/ioc/check?value=192.168.0.100",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_ioc"] is True
        assert data["intel"]["value"] == "192.168.0.100"

    def test_check_ioc_not_found(self, client):
        token = _register_and_login(client, email="ioc2@example.com", username="ioc2")
        resp = client.get(
            "/api/v1/threat-intel/ioc/check?value=8.8.8.8",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_ioc"] is False
        assert data["intel"] is None

    def test_add_custom_ioc(self, client):
        token = _register_and_login(client, email="ioc3@example.com", username="ioc3")
        resp = client.post(
            "/api/v1/threat-intel/ioc"
            "?value=evil.example.com"
            "&ioc_type=domain"
            "&threat_level=high"
            "&description=Malicious+C2+domain",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] == "evil.example.com"
        assert data["source"] == "custom"

    def test_add_custom_ioc_invalid_type(self, client):
        token = _register_and_login(client, email="ioc4@example.com", username="ioc4")
        resp = client.post(
            "/api/v1/threat-intel/ioc?value=test&ioc_type=invalid_type",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_list_iocs(self, client, db_session):
        token = _register_and_login(client, email="ioc5@example.com", username="ioc5")
        db_session.add(IOC(
            value="1.2.3.4", ioc_type=IOCType.IP, threat_level=IOCThreatLevel.HIGH,
            source="test", confidence=0.8, is_active=True,
        ))
        db_session.commit()

        resp = client.get(
            "/api/v1/threat-intel/ioc",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


# ── Enrichment & Profile ──────────────────────────────────────────────────────

class TestEnrichmentEndpoints:

    def test_enrich_finding_endpoint(self, client):
        token = _register_and_login(client, email="enrich1@example.com", username="enrich1")
        mock_job = MagicMock()
        mock_job.id = "task-uuid-1234"

        with patch("app.tasks.threat_intel_tasks.enrich_finding_task.apply_async",
                   return_value=mock_job):
            resp = client.post(
                "/api/v1/threat-intel/enrich/finding/1",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["task_id"] == "task-uuid-1234"

    def test_project_threat_profile(self, client):
        token = _register_and_login(client, email="profile1@example.com", username="profile1")
        resp = client.get(
            "/api/v1/threat-intel/project/99999/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cves" in data
        assert "kev_count" in data
        assert "tactics_coverage" in data


# ── Admin-only sync endpoints ─────────────────────────────────────────────────

class TestAdminSyncEndpoints:

    def test_sync_mitre_admin_only_rejects_regular_user(self, client):
        token = _register_and_login(client, email="regular1@example.com", username="regular1")
        resp = client.post(
            "/api/v1/threat-intel/sync/mitre",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_sync_iocs_admin_only_rejects_regular_user(self, client):
        token = _register_and_login(client, email="regular2@example.com", username="regular2")
        resp = client.post(
            "/api/v1/threat-intel/sync/iocs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_sync_mitre_admin_allowed(self, client):
        token = _admin_token(client)
        mock_job = MagicMock()
        mock_job.id = "admin-task-1"

        with patch("app.tasks.threat_intel_tasks.sync_mitre_techniques.apply_async",
                   return_value=mock_job):
            resp = client.post(
                "/api/v1/threat-intel/sync/mitre",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 202
        assert resp.json()["status"] == "queued"

    def test_sync_iocs_admin_allowed(self, client):
        token = _admin_token(client)
        mock_job = MagicMock()
        mock_job.id = "admin-task-2"

        with patch("app.tasks.threat_intel_tasks.sync_ioc_feeds.apply_async",
                   return_value=mock_job):
            resp = client.post(
                "/api/v1/threat-intel/sync/iocs",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 202
        assert resp.json()["status"] == "queued"
