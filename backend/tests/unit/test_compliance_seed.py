"""Unit tests for compliance framework seed data - Phase 13"""
import pytest
from app.seeds.compliance_frameworks import seed_compliance_frameworks, FRAMEWORKS_DATA
from app.models.compliance import ComplianceFramework, ComplianceRequirement, ComplianceFrameworkType
from app.crud.compliance import ComplianceCRUD


class TestComplianceFrameworkSeed:

    def test_seed_creates_frameworks(self, db_session):
        count = seed_compliance_frameworks(db_session)
        assert count >= 3  # PCI-DSS, HIPAA, GDPR

    def test_seed_idempotent(self, db_session):
        count1 = seed_compliance_frameworks(db_session)
        count2 = seed_compliance_frameworks(db_session)
        assert count2 == 0  # nothing new on second run

    def test_seed_pci_dss_requirements(self, db_session):
        seed_compliance_frameworks(db_session)
        fw = ComplianceCRUD.get_framework_by_type(db_session, "pci_dss_3.2.1")
        assert fw is not None

        reqs = ComplianceCRUD.get_requirements_by_framework(db_session, fw.id)
        assert len(reqs) >= 5
        req_ids = [r.requirement_id for r in reqs]
        assert "1.1" in req_ids
        assert "6.5.1" in req_ids

    def test_seed_hipaa_requirements(self, db_session):
        seed_compliance_frameworks(db_session)
        fw = ComplianceCRUD.get_framework_by_type(db_session, "hipaa")
        assert fw is not None
        reqs = ComplianceCRUD.get_requirements_by_framework(db_session, fw.id)
        assert len(reqs) >= 3

    def test_seed_gdpr_requirements(self, db_session):
        seed_compliance_frameworks(db_session)
        fw = ComplianceCRUD.get_framework_by_type(db_session, "gdpr")
        assert fw is not None
        reqs = ComplianceCRUD.get_requirements_by_framework(db_session, fw.id)
        assert len(reqs) >= 3

    def test_seed_requirement_has_tool_mappings(self, db_session):
        seed_compliance_frameworks(db_session)
        fw = ComplianceCRUD.get_framework_by_type(db_session, "pci_dss_3.2.1")
        reqs = ComplianceCRUD.get_requirements_by_framework(db_session, fw.id)
        has_tool = any(req.tool_mappings for req in reqs)
        assert has_tool

    def test_seed_requirement_has_cve_patterns(self, db_session):
        seed_compliance_frameworks(db_session)
        fw = ComplianceCRUD.get_framework_by_type(db_session, "pci_dss_3.2.1")
        reqs = ComplianceCRUD.get_requirements_by_framework(db_session, fw.id)
        has_patterns = any(req.related_cve_patterns for req in reqs)
        assert has_patterns

    def test_frameworks_data_structure(self):
        assert ComplianceFrameworkType.PCI_DSS_3_2_1 in FRAMEWORKS_DATA
        assert ComplianceFrameworkType.HIPAA in FRAMEWORKS_DATA
        assert ComplianceFrameworkType.GDPR in FRAMEWORKS_DATA

        for fw_type, data in FRAMEWORKS_DATA.items():
            assert "name" in data
            assert "version" in data
            assert "requirements" in data
            assert isinstance(data["requirements"], list)
