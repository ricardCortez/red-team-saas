"""Target (scope) management commands"""
from typing import Optional

import typer

from cli.client import get_client
from cli.config import get_config
from cli.output import error, info, print_json, print_table, success

app = typer.Typer(help="Target (scope) management")


def _resolve_project(project_id: Optional[int]) -> int:
    pid = project_id or get_config().default_project_id
    if not pid:
        error("No project specified. Use --project or: redteam projects use <id>")
        raise typer.Exit(1)
    return pid


@app.command("list")
def list_targets(
    project_id: Optional[int] = typer.Option(None, "--project", "-p"),
    status: Optional[str] = typer.Option(None, "--status"),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """List targets in project scope."""
    pid = _resolve_project(project_id)
    client = get_client()
    params: dict = {}
    if status:
        params["status"] = status
    data = client.get(f"/projects/{pid}/targets", params=params)
    fmt = fmt or get_config().output_format
    if fmt == "json":
        print_json(data)
    else:
        items = data.get("items", data) if isinstance(data, dict) else data
        rows = [
            [t["id"], t["value"], t["target_type"], t.get("status", "-"), t.get("tags") or "-"]
            for t in (items if isinstance(items, list) else [])
        ]
        print_table(
            f"Targets — Project {pid}",
            ["ID", "Value", "Type", "Status", "Tags"],
            rows,
        )


@app.command("add")
def add_target(
    value: str = typer.Argument(..., help="IP, CIDR, hostname, or URL"),
    type: str = typer.Option("ip", "--type", "-t", help="ip|cidr|hostname|url|ip_range"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p"),
    tags: Optional[str] = typer.Option(None, "--tags"),
    desc: Optional[str] = typer.Option(None, "--desc"),
):
    """Add a target to project scope."""
    pid = _resolve_project(project_id)
    client = get_client()
    payload: dict = {"value": value, "target_type": type}
    if tags:
        payload["tags"] = tags
    if desc:
        payload["description"] = desc
    data = client.post(f"/projects/{pid}/targets", payload)
    success(f"Target added: ID={data['id']} Value={data['value']}")


@app.command("bulk-add")
def bulk_add(
    file: str = typer.Argument(..., help="File with one target per line (value[,type])"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p"),
    default_type: str = typer.Option("ip", "--type", "-t", help="Default type when not in file"),
):
    """Bulk-import targets from a text file."""
    pid = _resolve_project(project_id)
    targets = []
    with open(file) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            targets.append(
                {
                    "value": parts[0].strip(),
                    "target_type": parts[1].strip() if len(parts) > 1 else default_type,
                }
            )
    if not targets:
        error("No valid targets found in file")
        raise typer.Exit(1)
    client = get_client()
    result = client.post(f"/projects/{pid}/targets/bulk", {"targets": targets})
    count = len(result) if isinstance(result, list) else result.get("created", len(targets))
    success(f"Added {count} targets")


@app.command("validate")
def validate_scope(
    value: str = typer.Argument(..., help="Target value to check"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p"),
):
    """Check whether a target is within project scope."""
    pid = _resolve_project(project_id)
    client = get_client()
    data = client.post(f"/projects/{pid}/targets/validate", params={"target": value})
    if data and data.get("in_scope"):
        success(f"{value} is IN SCOPE ✓")
    else:
        error(f"{value} is OUT OF SCOPE ✗")
        raise typer.Exit(1)
