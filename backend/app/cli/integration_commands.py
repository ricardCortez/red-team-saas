"""Integration Hub CLI Commands — Phase 16

Usage:
    python -m app.cli.integration_commands list <project-id>
    python -m app.cli.integration_commands test <integration-id>
    python -m app.cli.integration_commands audit-logs <project-id>
    python -m app.cli.integration_commands rules <project-id>
    python -m app.cli.integration_commands stats <project-id>
"""
from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="integrations", help="Phase 16 Integration Hub commands")
console = Console()


def _get_db():
    from app.database import SessionLocal
    return SessionLocal()


# ── list ───────────────────────────────────────────────────────────────────────

@app.command(name="list")
def list_integrations(
    project_id: int = typer.Argument(..., help="Project ID"),
    integration_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
):
    """List all integrations for a project."""
    db = _get_db()
    try:
        from app.crud.integration import IntegrationCRUD
        integrations = IntegrationCRUD.list_integrations(db, project_id, integration_type, status)

        if not integrations:
            console.print(f"[yellow]No integrations found for project {project_id}.[/yellow]")
            return

        table = Table(title=f"Integrations — Project {project_id}", box=box.ROUNDED)
        table.add_column("ID",          style="dim",     justify="right")
        table.add_column("Name",        style="cyan")
        table.add_column("Type",        style="green")
        table.add_column("Status",      style="magenta")
        table.add_column("Last Tested", style="yellow")
        table.add_column("Result",      style="blue")

        for i in integrations:
            status_color = {
                "active":       "green",
                "error":        "red",
                "inactive":     "dim",
                "pending_auth": "yellow",
            }.get(str(i.status.value if hasattr(i.status, "value") else i.status), "white")

            tested = i.last_tested_at.strftime("%Y-%m-%d %H:%M") if i.last_tested_at else "Never"
            result = i.last_tested_result or "—"

            table.add_row(
                str(i.id),
                i.name,
                str(i.integration_type.value if hasattr(i.integration_type, "value") else i.integration_type),
                f"[{status_color}]{i.status.value if hasattr(i.status, 'value') else i.status}[/{status_color}]",
                tested,
                result,
            )

        console.print(table)
    finally:
        db.close()


# ── test ───────────────────────────────────────────────────────────────────────

@app.command()
def test(integration_id: int = typer.Argument(..., help="Integration ID")):
    """Test the connection of a specific integration."""
    db = _get_db()
    try:
        from app.crud.integration import IntegrationCRUD
        from app.core.security import EncryptionHandler
        from app.services.integrations import INTEGRATION_CLASSES

        integration = IntegrationCRUD.get_integration(db, integration_id)
        if not integration:
            console.print(f"[red]Integration {integration_id} not found.[/red]")
            raise typer.Exit(1)

        name = integration.name
        int_type = (
            integration.integration_type.value
            if hasattr(integration.integration_type, "value")
            else integration.integration_type
        )

        console.print(f"[yellow]Testing {name} ({int_type})…[/yellow]")

        int_class = INTEGRATION_CLASSES.get(int_type.lower())
        if not int_class:
            console.print(f"[red]Unknown integration type: {int_type}[/red]")
            raise typer.Exit(1)

        token = EncryptionHandler.decrypt(integration.auth_token or "")
        instance = int_class(token, integration.config or {})

        success = asyncio.run(instance.test_connection())

        IntegrationCRUD.update_integration_status(
            db,
            integration_id,
            "active" if success else "error",
            "success" if success else "failed",
        )

        if success:
            console.print(f"[green]✓ {name} connection successful.[/green]")
        else:
            console.print(f"[red]✗ {name} connection failed.[/red]")

    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


# ── audit-logs ─────────────────────────────────────────────────────────────────

@app.command(name="audit-logs")
def audit_logs(
    project_id: int = typer.Argument(..., help="Project ID"),
    limit: int = typer.Option(50, help="Max entries to display"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
):
    """Show integration audit logs for a project."""
    db = _get_db()
    try:
        from app.crud.integration import IntegrationCRUD
        logs = IntegrationCRUD.get_audit_logs(db, project_id=project_id, status=status, limit=limit)

        if not logs:
            console.print(f"[yellow]No audit logs found for project {project_id}.[/yellow]")
            return

        table = Table(title=f"Integration Audit Logs — Project {project_id}", box=box.ROUNDED)
        table.add_column("ID",          style="dim",     justify="right")
        table.add_column("Integration", justify="right")
        table.add_column("Action",      style="cyan")
        table.add_column("Status",      style="magenta")
        table.add_column("External ID", style="green")
        table.add_column("Timestamp",   style="yellow")
        table.add_column("Error",       style="red")

        for log in logs:
            s_color = "green" if log.status == "success" else "red"
            table.add_row(
                str(log.id),
                str(log.integration_id),
                log.action,
                f"[{s_color}]{log.status}[/{s_color}]",
                log.external_id or "—",
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                (log.error_message or "")[:60],
            )

        console.print(table)
    finally:
        db.close()


# ── rules ──────────────────────────────────────────────────────────────────────

@app.command()
def rules(
    project_id: int = typer.Argument(..., help="Project ID"),
    trigger_type: Optional[str] = typer.Option(None, "--trigger", help="Filter by trigger type"),
):
    """List notification rules for a project."""
    db = _get_db()
    try:
        from app.crud.integration import IntegrationCRUD
        rule_list = IntegrationCRUD.get_notification_rules(db, project_id, trigger_type)

        if not rule_list:
            console.print(f"[yellow]No notification rules found for project {project_id}.[/yellow]")
            return

        table = Table(title=f"Notification Rules — Project {project_id}", box=box.ROUNDED)
        table.add_column("ID",           style="dim",     justify="right")
        table.add_column("Name",         style="cyan")
        table.add_column("Trigger",      style="green")
        table.add_column("Enabled",      style="magenta")
        table.add_column("Integrations", style="yellow")

        for r in rule_list:
            enabled_str = "[green]Yes[/green]" if r.is_enabled else "[red]No[/red]"
            trigger = r.trigger_type.value if hasattr(r.trigger_type, "value") else str(r.trigger_type)
            table.add_row(
                str(r.id),
                r.name,
                trigger,
                enabled_str,
                str(len(r.integration_ids or [])),
            )

        console.print(table)
    finally:
        db.close()


# ── stats ──────────────────────────────────────────────────────────────────────

@app.command()
def stats(project_id: int = typer.Argument(..., help="Project ID")):
    """Show integration health statistics for a project."""
    db = _get_db()
    try:
        from app.crud.integration import IntegrationCRUD
        data = IntegrationCRUD.integration_stats(db, project_id)

        console.rule(f"[bold]Integration Stats — Project {project_id}[/bold]")
        console.print(f"Total        : [bold]{data['total']}[/bold]")
        console.print(f"Active       : [green]{data['active']}[/green]")
        console.print(f"Error        : [red]{data['error']}[/red]")
        console.print(f"Pending Auth : [yellow]{data['pending_auth']}[/yellow]")

        if data["by_type"]:
            table = Table(title="By Type", box=box.SIMPLE)
            table.add_column("Type",  style="cyan")
            table.add_column("Count", style="green", justify="right")
            for t, count in sorted(data["by_type"].items()):
                table.add_row(t, str(count))
            console.print(table)

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    app()
