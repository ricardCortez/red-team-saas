"""
Red Team SaaS — Python SDK usage example.

This example assumes the SDK has been generated from the OpenAPI spec:
    openapi-python-client generate \
        --url http://localhost:8000/api/openapi.json \
        --output-dir ./python-sdk

Alternatively, you can use httpx/requests directly as shown below.
"""

import httpx

BASE_URL = "http://localhost:8000/api/v1"
API_KEY = "rtsa_your_api_key_here"

headers = {"Authorization": f"Bearer {API_KEY}"}


def create_project() -> dict:
    """Create a new pentest project."""
    payload = {
        "name": "Q1 External Audit",
        "description": "Quarterly external penetration test",
    }
    resp = httpx.post(f"{BASE_URL}/projects", json=payload, headers=headers)
    resp.raise_for_status()
    project = resp.json()
    print(f"Created project: {project['id']} — {project['name']}")
    return project


def list_findings(project_id: int) -> list:
    """List findings for a project."""
    resp = httpx.get(
        f"{BASE_URL}/findings",
        params={"project_id": project_id},
        headers=headers,
    )
    resp.raise_for_status()
    findings = resp.json()
    print(f"Found {len(findings)} findings")
    for f in findings:
        print(f"  [{f.get('severity', 'N/A')}] {f.get('title', 'Untitled')}")
    return findings


def generate_report(project_id: int) -> dict:
    """Generate a PDF report for the project."""
    payload = {
        "project_id": project_id,
        "format": "pdf",
        "template": "executive_summary",
    }
    resp = httpx.post(f"{BASE_URL}/reports", json=payload, headers=headers)
    resp.raise_for_status()
    report = resp.json()
    print(f"Report queued: {report.get('id')}")
    return report


if __name__ == "__main__":
    project = create_project()
    list_findings(project["id"])
    generate_report(project["id"])
