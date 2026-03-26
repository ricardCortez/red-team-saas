"""Project management commands"""
from typing import Optional

import typer

from cli.client import get_client
from cli.config import get_config
from cli.output import error, info, print_json, print_projects, print_table, success

app = typer.Typer(help="Project management")


@app.command("list")
def list_projects(
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """List all accessible projects."""
    client = get_client()
    params = {}
    if status:
        params["status"] = status
    data = client.get("/projects", params=params)
    fmt = fmt or get_config().output_format
    items = data.get("items", data) if isinstance(data, dict) else data
    print_projects(items if isinstance(items, list) else [], fmt)
    if isinstance(data, dict):
        info(f"Total: {data.get('total', len(items))}")


@app.command("create")
def create_project(
    name: str = typer.Argument(..., help="Project name"),
    type: str = typer.Option("pentest", "--type", "-t", help="pentest|red_team|vulnerability_assessment|compliance"),
    client_name: Optional[str] = typer.Option(None, "--client", help="Client name"),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="Description"),
):
    """Create a new project."""
    client = get_client()
    payload: dict = {"name": name, "project_type": type}
    if client_name:
        payload["client_name"] = client_name
    if desc:
        payload["description"] = desc
    data = client.post("/projects", payload)
    success(f"Project created: ID={data['id']} Name={data['name']}")


@app.command("get")
def get_project(
    project_id: int = typer.Argument(...),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """Get project details."""
    client = get_client()
    data = client.get(f"/projects/{project_id}")
    fmt = fmt or get_config().output_format
    if fmt == "json":
        print_json(data)
    else:
        info(f"ID:      {data['id']}")
        info(f"Name:    {data['name']}")
        info(f"Status:  {data.get('status', '-')}")
        info(f"Type:    {data.get('project_type', '-')}")
        info(f"Members: {data.get('member_count', 0)}")
        info(f"Targets: {data.get('target_count', 0)}")


@app.command("archive")
def archive_project(project_id: int = typer.Argument(...)):
    """Archive a project."""
    client = get_client()
    client.post(f"/projects/{project_id}/archive")
    success(f"Project {project_id} archived")


@app.command("members")
def list_members(project_id: int = typer.Argument(...)):
    """List project members."""
    client = get_client()
    members = client.get(f"/projects/{project_id}/members")
    rows = [
        [m["id"], m["user_id"], m["role"], (m.get("added_at") or "-")[:10]]
        for m in (members if isinstance(members, list) else [])
    ]
    print_table(f"Members — Project {project_id}", ["ID", "User ID", "Role", "Added"], rows)


@app.command("add-member")
def add_member(
    project_id: int = typer.Argument(...),
    user_id: int = typer.Argument(...),
    role: str = typer.Option("viewer", "--role", "-r", help="lead|operator|viewer"),
):
    """Add a member to a project."""
    client = get_client()
    client.post(f"/projects/{project_id}/members", {"user_id": user_id, "role": role})
    success(f"User {user_id} added as {role}")


@app.command("use")
def use_project(project_id: int = typer.Argument(...)):
    """Set the default project for subsequent commands."""
    cfg = get_config()
    cfg.default_project_id = project_id
    cfg.save()
    success(f"Default project set to {project_id}")
