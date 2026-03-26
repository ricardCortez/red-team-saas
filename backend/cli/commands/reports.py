"""Report generation and download commands"""
import os
import time
from typing import Optional

import typer

from cli.client import get_client
from cli.config import get_config
from cli.output import error, info, print_json, print_table, success

app = typer.Typer(help="Report generation")


@app.command("create")
def create_report(
    project_id: int = typer.Argument(...),
    title: str = typer.Option(..., "--title", "-t", help="Report title"),
    type: str = typer.Option(
        "technical", "--type", help="executive|technical|compliance"
    ),
    format: str = typer.Option("pdf", "--format", "-f", help="pdf|html"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Poll until report is ready"),
):
    """Generate a report for a project."""
    client = get_client()
    data = client.post(
        "/reports",
        {
            "project_id": project_id,
            "title": title,
            "report_type": type,
            "report_format": format,
        },
    )
    report_id = data["id"]
    success(f"Report queued: ID={report_id}")

    if wait:
        info("Waiting for report generation...")
        while True:
            r = client.get(f"/reports/{report_id}")
            if r["status"] == "ready":
                success("Report ready!")
                break
            elif r["status"] == "failed":
                error(f"Report failed: {r.get('error_message')}")
                raise typer.Exit(1)
            time.sleep(3)


@app.command("list")
def list_reports(
    project_id: Optional[int] = typer.Option(None, "--project", "-p"),
    status: Optional[str] = typer.Option(None, "--status"),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """List reports."""
    client = get_client()
    params: dict = {}
    if project_id:
        params["project_id"] = project_id
    if status:
        params["status"] = status
    data = client.get("/reports", params=params)
    fmt = fmt or get_config().output_format
    if fmt == "json":
        print_json(data)
    else:
        items = data.get("items", data) if isinstance(data, dict) else data
        rows = [
            [
                r["id"],
                r.get("title", "-"),
                r.get("report_type", "-"),
                r.get("status", "-"),
                r.get("overall_risk", 0),
                r.get("total_findings", 0),
            ]
            for r in (items if isinstance(items, list) else [])
        ]
        print_table(
            "Reports", ["ID", "Title", "Type", "Status", "Risk", "Findings"], rows
        )


@app.command("download")
def download_report(
    report_id: int = typer.Argument(...),
    output: str = typer.Option(".", "--output", "-o", help="Output directory"),
):
    """Download a generated report to a local file."""
    client = get_client()
    r = client.get(f"/reports/{report_id}")
    if r.get("status") != "ready":
        error(f"Report not ready. Status: {r.get('status')}")
        raise typer.Exit(1)

    ext = "pdf" if r.get("report_format") == "pdf" else "html"
    dest = os.path.join(output, f"report_{report_id}.{ext}")
    size = client.download(f"/reports/{report_id}/download", dest)
    success(f"Downloaded: {dest} ({size // 1024} KB)")
