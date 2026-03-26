"""Seed compliance frameworks and requirements - Phase 13

Usage:
    from app.seeds.compliance_frameworks import seed_compliance_frameworks
    from app.database import SessionLocal
    db = SessionLocal()
    seed_compliance_frameworks(db)
    db.close()
"""
from __future__ import annotations

import logging
from sqlalchemy.orm import Session
from app.models.compliance import (
    ComplianceFramework,
    ComplianceRequirement,
    ComplianceFrameworkType,
)

logger = logging.getLogger(__name__)

FRAMEWORKS_DATA: dict = {
    ComplianceFrameworkType.PCI_DSS_3_2_1: {
        "name":               "PCI DSS 3.2.1",
        "version":            "3.2.1",
        "description":        "Payment Card Industry Data Security Standard v3.2.1",
        "total_requirements": 12,
        "requirements": [
            {
                "requirement_id":       "1.1",
                "requirement_text":     "Establish firewall configuration standards",
                "control_objective":    "Network security",
                "severity":             "CRITICAL",
                "related_cve_patterns": ["CWE-200", "CWE-295"],
                "tool_mappings":        {"nmap": ["open-port"], "metasploit": ["firewall-bypass"]},
            },
            {
                "requirement_id":       "2.1",
                "requirement_text":     "Always change vendor-supplied defaults",
                "control_objective":    "Secure configuration",
                "severity":             "CRITICAL",
                "related_cve_patterns": ["CWE-798", "CWE-255"],
                "tool_mappings":        {"hydra": ["default-creds"], "medusa": ["default-pass"]},
            },
            {
                "requirement_id":       "6.5.1",
                "requirement_text":     "Injection flaws",
                "control_objective":    "Application security",
                "severity":             "CRITICAL",
                "related_cve_patterns": ["CWE-89", "CWE-78", "CWE-434"],
                "tool_mappings":        {"sqlmap": ["sql-inject"]},
            },
            {
                "requirement_id":       "8.1",
                "requirement_text":     "User ID access control",
                "control_objective":    "Access control",
                "severity":             "HIGH",
                "related_cve_patterns": ["CWE-287"],
                "tool_mappings":        {"hydra": ["weak-pass"], "john": ["cracked-hash"]},
            },
            {
                "requirement_id":       "10.1",
                "requirement_text":     "Implement audit logging",
                "control_objective":    "Logging and monitoring",
                "severity":             "HIGH",
                "related_cve_patterns": ["CWE-778"],
                "tool_mappings":        {"nmap": ["no-audit"]},
            },
        ],
    },

    ComplianceFrameworkType.HIPAA: {
        "name":               "HIPAA",
        "version":            "2013",
        "description":        "Health Insurance Portability and Accountability Act",
        "total_requirements": 18,
        "requirements": [
            {
                "requirement_id":       "164.312(a)(1)",
                "requirement_text":     "Access control — user authentication",
                "control_objective":    "Authentication",
                "severity":             "CRITICAL",
                "related_cve_patterns": ["CWE-287", "CWE-640"],
                "tool_mappings":        {"hydra": ["weak-auth"], "medusa": ["brute-force"]},
            },
            {
                "requirement_id":       "164.312(a)(2)(i)",
                "requirement_text":     "Encryption and decryption of ePHI",
                "control_objective":    "Encryption",
                "severity":             "CRITICAL",
                "related_cve_patterns": ["CWE-327", "CWE-326"],
                "tool_mappings":        {"sslscan": ["weak-cipher"]},
            },
            {
                "requirement_id":       "164.312(b)",
                "requirement_text":     "Audit controls — implement logging",
                "control_objective":    "Logging",
                "severity":             "HIGH",
                "related_cve_patterns": ["CWE-778"],
                "tool_mappings":        {"nmap": ["syslog-open"]},
            },
        ],
    },

    ComplianceFrameworkType.GDPR: {
        "name":               "GDPR",
        "version":            "2018",
        "description":        "General Data Protection Regulation (EU) 2016/679",
        "total_requirements": 99,
        "requirements": [
            {
                "requirement_id":       "32",
                "requirement_text":     "Security of processing — implement technical measures",
                "control_objective":    "Data security",
                "severity":             "CRITICAL",
                "related_cve_patterns": ["CWE-200", "CWE-327"],
                "tool_mappings":        {"nmap": ["weak-ssl"]},
            },
            {
                "requirement_id":       "33",
                "requirement_text":     "Notification of personal data breach",
                "control_objective":    "Incident response",
                "severity":             "CRITICAL",
                "related_cve_patterns": ["CWE-200"],
                "tool_mappings":        {"osint": ["data-leak"]},
            },
            {
                "requirement_id":       "5(1)(f)",
                "requirement_text":     "Integrity and confidentiality",
                "control_objective":    "Data protection",
                "severity":             "HIGH",
                "related_cve_patterns": ["CWE-327", "CWE-295"],
                "tool_mappings":        {"sslscan": ["cert-issues"]},
            },
        ],
    },
}


def seed_compliance_frameworks(db: Session) -> int:
    """Upsert all built-in frameworks and their requirements. Returns count of new frameworks."""
    created = 0
    for framework_type, fw_data in FRAMEWORKS_DATA.items():
        existing = db.query(ComplianceFramework).filter(
            ComplianceFramework.framework_type == framework_type
        ).first()
        if existing:
            logger.debug(f"Framework {framework_type} already exists, skipping.")
            continue

        framework = ComplianceFramework(
            name               = fw_data["name"],
            framework_type     = framework_type,
            version            = fw_data["version"],
            description        = fw_data["description"],
            total_requirements = fw_data["total_requirements"],
        )
        db.add(framework)
        db.flush()  # get id before inserting requirements

        for req_data in fw_data.get("requirements", []):
            requirement = ComplianceRequirement(
                framework_id = framework.id,
                **req_data,
            )
            db.add(requirement)

        db.commit()
        created += 1
        logger.info(f"Seeded framework: {fw_data['name']}")

    return created
