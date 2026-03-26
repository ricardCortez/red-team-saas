"""Findings management commands"""
from typing import Optional

import typer

from cli.client import get_client
from cli.config import get_config
from cli.output import console, error, info, print_findings, print_json, print_table, severity_text, success

app = typer.Typer(help="Findings management")


@app.command("list")
def list_findings(
    project_id: Optional[int] = typer.Option(None, "--project", "-p"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s"),
    status: Optional[str] = typer.Option(None, "--status"),
    host: Optional[str] = typer.Option(None, "--host"),
    limit: int = typer.Option(50, "--limit", "-n"),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """List findings."""
    client = get_client()
    params: dict = {"limit": limit, "exclude_duplicates": True}
    if project_id:
        params["project_id"] = project_id
    if severity:
        params["severity"] = severity
    if status:
        params["status"] = status
    if host:
        params["host"] = host
    data = client.get("/findings", params=params)
    fmt = fmt or get_config().output_format
    items = data.get("items", data) if isinstance(data, dict) else data
    print_findings(items if isinstance(items, list) else [], fmt)
    if isinstance(data, dict):
        info(f"Total: {data.get('total', 0)}")


@app.command("get")
def get_finding(
    finding_id: int = typer.Argument(...),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """Get full detail for a single finding."""
    client = get_client()
    data = client.get(f"/findings/{finding_id}")
    fmt = fmt or get_config().output_format
    if fmt == "json":
        print_json(data)
    else:
        console.print(f"[bold]{data.get('title', '-')}[/bold]")
        console.print(severity_text(data.get("severity", "info")))
        info(f"Host:      {data.get('host', '-')}")
        info(f"Port:      {data.get('port', '-')}")
        info(f"Tool:      {data.get('tool_name', '-')}")
        info(f"Risk:      {data.get('risk_score', 0)}/10")
        info(f"Status:    {data.get('status', '-')}")
        if data.get("description"):
            info(f"Desc:      {data['description']}")


@app.command("update")
def update_finding(
    finding_id: int = typer.Argument(...),
    status: Optional[str] = typer.Option(None, "--status"),
    severity: Optional[str] = typer.Option(None, "--severity"),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    """Update finding status, severity, or notes."""
    client = get_client()
    payload: dict = {}
    if status:
        payload["status"] = status
    if severity:
        payload["severity"] = severity
    if notes:
        payload["notes"] = notes
    client.patch(f"/findings/{finding_id}", payload)
    success(f"Finding {finding_id} updated")


@app.command("fp")
def mark_false_positive(
    finding_id: int = typer.Argument(...),
    reason: str = typer.Argument(..., help="Reason for false positive"),
):
    """Mark a finding as a false positive."""
    client = get_client()
    client.post(f"/findings/{finding_id}/false-positive", params={"reason": reason})
    success(f"Finding {finding_id} marked as false positive")


@app.command("stats")
def finding_stats(
    project_id: int = typer.Argument(...),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """Show findings statistics for a project."""
    client = get_client()
    data = client.get(f"/findings/stats/{project_id}")
    fmt = fmt or get_config().output_format
    if fmt == "json":
        print_json(data)
    else:
        by_sev = data.get("by_severity", {})
        rows = [[sev.upper(), count] for sev, count in by_sev.items()]
        print_table("Findings by Severity", ["Severity", "Count"], rows)
        info(f"Total open: {data.get('total_open', 0)}")
