"""Unit tests – Phase 2 SQLAlchemy models (Workspace, Template, ThreatIntel, RiskScore, ComplianceMapping, Report)"""
import json
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.workspace import Workspace
from app.models.task import Task, TaskStatusEnum
from app.models.template import Template, TemplateCategory
from app.models.threat_intel import ThreatIntel, SeverityLevel
from app.models.risk_score import RiskScore
from app.models.compliance_mapping import ComplianceMapping, ComplianceFramework, ComplianceStatus
from app.models.report import Report, ReportStatus
from app.core.security import PasswordHandler


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_user(db, suffix=""):
    user = User(
        email=f"user{suffix}@example.com",
        username=f"user{suffix}",
        hashed_password=PasswordHandler.hash_password("Pass123!"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_workspace(db, owner):
    ws = Workspace(
        owner_id=owner.id,
        name="ACME Corp Pentest",
        client_name="ACME Corp",
        description="External pentest Q1 2026",
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def _make_task(db, user, workspace=None):
    task = Task(
        user_id=user.id,
        workspace_id=workspace.id if workspace else None,
        tool_name="nmap",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ── Workspace ─────────────────────────────────────────────────────────────────

class TestWorkspaceModel:
    def test_create_workspace(self, db_session):
        user = _make_user(db_session, "ws1")
        ws = _make_workspace(db_session, user)
        assert ws.id is not None
        assert ws.name == "ACME Corp Pentest"
        assert ws.is_active is True

    def test_workspace_defaults(self, db_session):
        user = _make_user(db_session, "ws2")
        ws = Workspace(owner_id=user.id, name="Minimal")
        db_session.add(ws)
        db_session.commit()
        db_session.refresh(ws)
        assert ws.is_active is True
        assert ws.client_name is None
        assert ws.scope is None

    def test_workspace_timestamps(self, db_session):
        user = _make_user(db_session, "ws3")
        ws = _make_workspace(db_session, user)
        assert ws.created_at is not None
        assert ws.updated_at is not None

    def test_workspace_repr(self, db_session):
        user = _make_user(db_session, "ws4")
        ws = _make_workspace(db_session, user)
        assert "ACME Corp Pentest" in repr(ws)

    def test_task_linked_to_workspace(self, db_session):
        user = _make_user(db_session, "ws5")
        ws = _make_workspace(db_session, user)
        task = _make_task(db_session, user, workspace=ws)
        assert task.workspace_id == ws.id

    def test_workspace_cascade_delete_tasks(self, db_session):
        user = _make_user(db_session, "ws6")
        ws = _make_workspace(db_session, user)
        _make_task(db_session, user, workspace=ws)
        db_session.delete(ws)
        db_session.commit()
        remaining = db_session.query(Task).filter_by(workspace_id=ws.id).all()
        assert remaining == []


# ── Template ──────────────────────────────────────────────────────────────────

class TestTemplateModel:
    def test_create_template(self, db_session):
        user = _make_user(db_session, "tmpl1")
        tmpl = Template(
            user_id=user.id,
            name="SSH Brute Force",
            category=TemplateCategory.brute_force,
            tool_configs=json.dumps([{"tool": "hydra", "port": 22}]),
        )
        db_session.add(tmpl)
        db_session.commit()
        db_session.refresh(tmpl)
        assert tmpl.id is not None
        assert tmpl.category == TemplateCategory.brute_force

    def test_template_defaults(self, db_session):
        user = _make_user(db_session, "tmpl2")
        tmpl = Template(
            user_id=user.id,
            name="Minimal Template",
            category=TemplateCategory.osint,
        )
        db_session.add(tmpl)
        db_session.commit()
        db_session.refresh(tmpl)
        assert tmpl.is_public is False
        assert tmpl.usage_count == 0

    def test_all_template_categories(self, db_session):
        user = _make_user(db_session, "tmpl3")
        for i, cat in enumerate(TemplateCategory):
            tmpl = Template(user_id=user.id, name=f"tmpl_{i}", category=cat)
            db_session.add(tmpl)
        db_session.commit()
        count = db_session.query(Template).filter_by(user_id=user.id).count()
        assert count == len(TemplateCategory)

    def test_template_public_flag(self, db_session):
        user = _make_user(db_session, "tmpl4")
        tmpl = Template(
            user_id=user.id,
            name="Public Template",
            category=TemplateCategory.network,
            is_public=True,
        )
        db_session.add(tmpl)
        db_session.commit()
        db_session.refresh(tmpl)
        assert tmpl.is_public is True

    def test_template_repr(self, db_session):
        user = _make_user(db_session, "tmpl5")
        tmpl = Template(user_id=user.id, name="Repr Test", category=TemplateCategory.custom)
        db_session.add(tmpl)
        db_session.commit()
        assert "Repr Test" in repr(tmpl)


# ── ThreatIntel ───────────────────────────────────────────────────────────────

class TestThreatIntelModel:
    def test_create_threat_intel(self, db_session):
        threat = ThreatIntel(
            cve_id="CVE-2024-12345",
            title="Critical RCE in Example Library",
            severity=SeverityLevel.critical,
            cvss_score=9.8,
        )
        db_session.add(threat)
        db_session.commit()
        db_session.refresh(threat)
        assert threat.id is not None
        assert threat.cve_id == "CVE-2024-12345"
        assert threat.severity == SeverityLevel.critical

    def test_threat_intel_defaults(self, db_session):
        threat = ThreatIntel(
            title="No CVE",
            severity=SeverityLevel.medium,
        )
        db_session.add(threat)
        db_session.commit()
        db_session.refresh(threat)
        assert threat.exploit_available is False
        assert threat.patch_available is False
        assert threat.cve_id is None

    def test_unique_cve_id_constraint(self, db_session):
        t1 = ThreatIntel(cve_id="CVE-2024-99999", title="T1", severity=SeverityLevel.high)
        t2 = ThreatIntel(cve_id="CVE-2024-99999", title="T2", severity=SeverityLevel.low)
        db_session.add(t1)
        db_session.commit()
        db_session.add(t2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_all_severity_levels(self, db_session):
        for i, sev in enumerate(SeverityLevel):
            t = ThreatIntel(title=f"Threat {i}", severity=sev)
            db_session.add(t)
        db_session.commit()
        count = db_session.query(ThreatIntel).count()
        assert count == len(SeverityLevel)

    def test_threat_intel_json_fields(self, db_session):
        products = json.dumps(["Apache 2.4", "nginx 1.25"])
        refs = json.dumps(["https://nvd.nist.gov/vuln/detail/CVE-2024-00001"])
        threat = ThreatIntel(
            title="JSON fields test",
            severity=SeverityLevel.high,
            affected_products=products,
            references=refs,
            tags=json.dumps(["rce", "network"]),
        )
        db_session.add(threat)
        db_session.commit()
        db_session.refresh(threat)
        assert json.loads(threat.affected_products) == ["Apache 2.4", "nginx 1.25"]

    def test_threat_intel_repr(self, db_session):
        threat = ThreatIntel(cve_id="CVE-2024-11111", title="Repr", severity=SeverityLevel.low)
        db_session.add(threat)
        db_session.commit()
        r = repr(threat)
        assert "CVE-2024-11111" in r


# ── RiskScore ─────────────────────────────────────────────────────────────────

class TestRiskScoreModel:
    def test_create_risk_score(self, db_session):
        user = _make_user(db_session, "rs1")
        task = _make_task(db_session, user)
        rs = RiskScore(task_id=task.id, score=7.5, justification="High impact RCE vector")
        db_session.add(rs)
        db_session.commit()
        db_session.refresh(rs)
        assert rs.id is not None
        assert float(rs.score) == 7.5

    @pytest.mark.parametrize("score,expected_level", [
        (9.5, "CRITICAL"),
        (9.0, "CRITICAL"),
        (8.0, "HIGH"),
        (7.0, "HIGH"),
        (5.0, "MEDIUM"),
        (4.0, "MEDIUM"),
        (2.0, "LOW"),
        (1.0, "LOW"),
        (0.5, "INFO"),
        (0.0, "INFO"),
    ])
    def test_risk_level_thresholds(self, db_session, score, expected_level):
        user = _make_user(db_session, f"rs_lv_{score}")
        task = _make_task(db_session, user)
        rs = RiskScore(task_id=task.id, score=score)
        db_session.add(rs)
        db_session.commit()
        db_session.refresh(rs)
        assert rs.risk_level == expected_level

    def test_risk_score_components_json(self, db_session):
        user = _make_user(db_session, "rs2")
        task = _make_task(db_session, user)
        components = {"network": 3.0, "authentication": 2.5, "impact": 2.0}
        rs = RiskScore(task_id=task.id, score=7.5, components=json.dumps(components))
        db_session.add(rs)
        db_session.commit()
        db_session.refresh(rs)
        loaded = json.loads(rs.components)
        assert loaded["network"] == 3.0

    def test_risk_score_repr(self, db_session):
        user = _make_user(db_session, "rs3")
        task = _make_task(db_session, user)
        rs = RiskScore(task_id=task.id, score=6.0)
        db_session.add(rs)
        db_session.commit()
        assert "MEDIUM" in repr(rs)


# ── ComplianceMapping ─────────────────────────────────────────────────────────

class TestComplianceMappingModel:
    def test_create_compliance_mapping(self, db_session):
        user = _make_user(db_session, "cm1")
        task = _make_task(db_session, user)
        cm = ComplianceMapping(
            framework=ComplianceFramework.pci_dss,
            control_id="6.5.1",
            control_name="Injection flaws",
            task_id=task.id,
        )
        db_session.add(cm)
        db_session.commit()
        db_session.refresh(cm)
        assert cm.id is not None
        assert cm.framework == ComplianceFramework.pci_dss

    def test_compliance_default_status(self, db_session):
        user = _make_user(db_session, "cm2")
        cm = ComplianceMapping(
            framework=ComplianceFramework.hipaa,
            control_id="164.312(a)(1)",
            control_name="Access Control",
        )
        db_session.add(cm)
        db_session.commit()
        db_session.refresh(cm)
        assert cm.status == ComplianceStatus.not_assessed

    def test_all_compliance_frameworks(self, db_session):
        for i, fw in enumerate(ComplianceFramework):
            cm = ComplianceMapping(
                framework=fw,
                control_id=f"CTRL-{i}",
                control_name=f"Control {i}",
            )
            db_session.add(cm)
        db_session.commit()
        count = db_session.query(ComplianceMapping).count()
        assert count == len(ComplianceFramework)

    def test_compliance_linked_to_threat_intel(self, db_session):
        threat = ThreatIntel(title="Linked threat", severity=SeverityLevel.high)
        db_session.add(threat)
        db_session.commit()
        cm = ComplianceMapping(
            framework=ComplianceFramework.gdpr,
            control_id="Art.32",
            control_name="Security of processing",
            threat_intel_id=threat.id,
        )
        db_session.add(cm)
        db_session.commit()
        db_session.refresh(cm)
        assert cm.threat_intel_id == threat.id

    def test_compliance_repr(self, db_session):
        cm = ComplianceMapping(
            framework=ComplianceFramework.iso27001,
            control_id="A.14.2.1",
            control_name="Secure development policy",
        )
        db_session.add(cm)
        db_session.commit()
        r = repr(cm)
        assert "ISO27001" in r


# ── Report ────────────────────────────────────────────────────────────────────

class TestReportModel:
    def test_create_report(self, db_session):
        user = _make_user(db_session, "rpt1")
        report = Report(
            author_id=user.id,
            title="Q1 2026 External Pentest Report",
            status=ReportStatus.draft,
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        assert report.id is not None
        assert report.status == ReportStatus.draft

    def test_report_default_status(self, db_session):
        user = _make_user(db_session, "rpt2")
        report = Report(author_id=user.id, title="Draft Report")
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        assert report.status == ReportStatus.draft

    def test_report_all_statuses(self, db_session):
        user = _make_user(db_session, "rpt3")
        for i, status in enumerate(ReportStatus):
            r = Report(author_id=user.id, title=f"Report {i}", status=status)
            db_session.add(r)
        db_session.commit()
        count = db_session.query(Report).filter_by(author_id=user.id).count()
        assert count == len(ReportStatus)

    def test_report_linked_to_workspace(self, db_session):
        user = _make_user(db_session, "rpt4")
        ws = _make_workspace(db_session, user)
        report = Report(author_id=user.id, workspace_id=ws.id, title="Scoped Report")
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        assert report.workspace_id == ws.id

    def test_report_compute_signature(self, db_session):
        user = _make_user(db_session, "rpt5")
        report = Report(
            author_id=user.id,
            title="Signed Report",
            executive_summary="No critical issues found.",
            findings=json.dumps([{"title": "Open port 22", "severity": "low"}]),
            recommendations="Close unnecessary ports.",
        )
        db_session.add(report)
        db_session.commit()
        sig = report.compute_signature()
        assert len(sig) == 64  # SHA-256 hex digest is 64 chars
        # Deterministic: same content → same signature
        assert sig == report.compute_signature()

    def test_report_signature_changes_with_content(self, db_session):
        user = _make_user(db_session, "rpt6")
        report = Report(author_id=user.id, title="Original Title")
        db_session.add(report)
        db_session.commit()
        sig1 = report.compute_signature()
        report.title = "Modified Title"
        sig2 = report.compute_signature()
        assert sig1 != sig2

    def test_report_repr(self, db_session):
        user = _make_user(db_session, "rpt7")
        report = Report(author_id=user.id, title="Repr Report")
        db_session.add(report)
        db_session.commit()
        assert "Repr Report" in repr(report)


# ── Cross-model integration ───────────────────────────────────────────────────

class TestPhase2Integration:
    def test_all_phase2_tables_accessible(self, db_session):
        """Smoke test: query all Phase 2 tables without error."""
        assert db_session.query(Workspace).count() >= 0
        assert db_session.query(Template).count() >= 0
        assert db_session.query(ThreatIntel).count() >= 0
        assert db_session.query(RiskScore).count() >= 0
        assert db_session.query(ComplianceMapping).count() >= 0
        assert db_session.query(Report).count() >= 0

    def test_full_pentest_workflow(self, db_session):
        """Create a workspace, run a task, score it, map to compliance, produce a report."""
        # 1. User + workspace
        user = _make_user(db_session, "wf1")
        ws = _make_workspace(db_session, user)

        # 2. Task scoped to workspace
        task = _make_task(db_session, user, workspace=ws)
        assert task.workspace_id == ws.id

        # 3. Risk score for the task
        rs = RiskScore(task_id=task.id, score=8.5, justification="Critical attack surface")
        db_session.add(rs)
        db_session.commit()
        assert rs.risk_level == "HIGH"

        # 4. Threat intel entry
        cve = ThreatIntel(
            cve_id="CVE-2026-00001",
            title="Test vuln",
            severity=SeverityLevel.high,
            cvss_score=8.1,
        )
        db_session.add(cve)
        db_session.commit()

        # 5. Compliance mapping linking task and CVE
        cm = ComplianceMapping(
            framework=ComplianceFramework.pci_dss,
            control_id="6.3.1",
            control_name="Security patches",
            task_id=task.id,
            threat_intel_id=cve.id,
            status=ComplianceStatus.non_compliant,
        )
        db_session.add(cm)
        db_session.commit()

        # 6. Final report
        report = Report(
            author_id=user.id,
            workspace_id=ws.id,
            title="Full Workflow Report",
            findings=json.dumps([{"cve": "CVE-2026-00001", "severity": "high"}]),
            status=ReportStatus.final,
        )
        db_session.add(report)
        db_session.commit()
        report.signature_hash = report.compute_signature()
        db_session.commit()

        assert report.signature_hash is not None
        assert len(report.signature_hash) == 64


# ── Field-level encryption ─────────────────────────────────────────────────────

class TestFieldEncryption:
    """Validate AES-256 (Fernet) transparent encryption on Task.parameters
    and Result.output / Result.parsed_data."""

    def test_task_parameters_decrypts_correctly(self, db_session):
        user = _make_user(db_session, "enc1")
        import json
        payload = json.dumps({"target": "10.0.0.1", "password": "SuperSecret!"})
        task = Task(user_id=user.id, tool_name="hydra", parameters=payload)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        # ORM returns decrypted value
        assert task.parameters == payload

    def test_task_parameters_not_plaintext_in_db(self, db_session):
        """Raw DB bytes must not contain the plaintext password."""
        from sqlalchemy import text as sa_text
        user = _make_user(db_session, "enc2")
        secret = "UltraSecretPassword99!"
        import json
        payload = json.dumps({"password": secret})
        task = Task(user_id=user.id, tool_name="medusa", parameters=payload)
        db_session.add(task)
        db_session.commit()

        raw = db_session.execute(
            sa_text("SELECT parameters FROM tasks WHERE id = :id"),
            {"id": task.id},
        ).scalar()
        assert raw is not None
        assert secret not in raw, "Plaintext found in database – encryption not applied!"

    def test_task_parameters_null_passthrough(self, db_session):
        user = _make_user(db_session, "enc3")
        task = Task(user_id=user.id, tool_name="nmap", parameters=None)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        assert task.parameters is None

    def test_result_output_decrypts_correctly(self, db_session):
        user = _make_user(db_session, "enc4")
        task = _make_task(db_session, user)
        from app.models.result import Result
        output_text = "Discovered credentials: admin:password123"
        result = Result(task_id=task.id, tool="hydra", output=output_text)
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        assert result.output == output_text

    def test_result_output_not_plaintext_in_db(self, db_session):
        from sqlalchemy import text as sa_text
        from app.models.result import Result
        user = _make_user(db_session, "enc5")
        task = _make_task(db_session, user)
        secret_output = "FOUND_CRED:root:toor"
        result = Result(task_id=task.id, tool="brutex", output=secret_output)
        db_session.add(result)
        db_session.commit()

        raw = db_session.execute(
            sa_text("SELECT output FROM results WHERE id = :id"),
            {"id": result.id},
        ).scalar()
        assert raw is not None
        assert secret_output not in raw, "Plaintext found in results.output – not encrypted!"

    def test_result_parsed_data_encrypted(self, db_session):
        from sqlalchemy import text as sa_text
        from app.models.result import Result
        user = _make_user(db_session, "enc6")
        task = _make_task(db_session, user)
        import json
        parsed = json.dumps({"users": ["admin", "root"], "hashes": ["aad3b..."]})
        result = Result(task_id=task.id, tool="crackmapexec", parsed_data=parsed)
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        # ORM decrypts transparently
        assert json.loads(result.parsed_data)["users"] == ["admin", "root"]
        # Raw DB is encrypted
        raw = db_session.execute(
            sa_text("SELECT parsed_data FROM results WHERE id = :id"),
            {"id": result.id},
        ).scalar()
        assert "admin" not in raw

    def test_encryption_is_deterministic_per_field_but_unique(self, db_session):
        """Two tasks with the same parameters must produce different ciphertext (random IV)."""
        from sqlalchemy import text as sa_text
        user = _make_user(db_session, "enc7")
        payload = '{"target": "192.168.1.1"}'
        t1 = Task(user_id=user.id, tool_name="nmap", parameters=payload)
        t2 = Task(user_id=user.id, tool_name="nmap", parameters=payload)
        db_session.add_all([t1, t2])
        db_session.commit()

        raw1 = db_session.execute(
            sa_text("SELECT parameters FROM tasks WHERE id = :id"), {"id": t1.id}
        ).scalar()
        raw2 = db_session.execute(
            sa_text("SELECT parameters FROM tasks WHERE id = :id"), {"id": t2.id}
        ).scalar()
        # Fernet uses a random IV, so two encryptions of same plaintext differ
        assert raw1 != raw2
