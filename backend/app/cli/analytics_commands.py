"""Analytics CLI Commands — Phase 15

Usage:
    python -m app.cli.analytics_commands metrics <project-id>
    python -m app.cli.analytics_commands kpis <project-id>
    python -m app.cli.analytics_commands risk-score <project-id>
    python -m app.cli.analytics_commands calculate <project-id>
    python -m app.cli.analytics_commands snapshot <project-id>

Requires: pip install typer rich
"""
import typer
from rich.console import Console
from rich.table import Table
from rich import box

app = typer.Typer(name="analytics", help="Phase 15 Analytics commands for Red Team SaaS")
console = Console()


def _get_db():
    from app.database import SessionLocal
    return SessionLocal()


def _get_realtime():
    from app.services.realtime_metrics import RealtimeMetricsService
    return RealtimeMetricsService()


# ── metrics ───────────────────────────────────────────────────────────────────

@app.command()
def metrics(project_id: int = typer.Argument(..., help="Project ID")):
    """Show live Redis metric counters for a project."""
    rt = _get_realtime()

    if not rt.health_check():
        console.print("[red]Redis is not reachable — cannot fetch real-time metrics.[/red]")
        raise typer.Exit(1)

    data = rt.get_current_metrics(str(project_id))

    if not data:
        console.print(f"[yellow]No real-time metrics found for project {project_id}.[/yellow]")
        return

    table = Table(title=f"Real-time Metrics — Project {project_id}", box=box.ROUNDED)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="bright_green", justify="right")

    for metric, value in sorted(data.items()):
        table.add_row(metric, str(value))

    console.print(table)


# ── kpis ──────────────────────────────────────────────────────────────────────

@app.command()
def kpis(
    project_id: int = typer.Argument(..., help="Project ID"),
    limit: int = typer.Option(10, help="Max KPIs to display"),
):
    """Display the latest KPIs for a project."""
    db = _get_db()
    try:
        from app.crud.analytics import crud_analytics
        kpi_list = crud_analytics.get_kpis(db, project_id, limit=limit)

        if not kpi_list:
            console.print(f"[yellow]No KPI data for project {project_id}. Run 'calculate' first.[/yellow]")
            return

        table = Table(title=f"KPIs — Project {project_id}", box=box.ROUNDED)
        table.add_column("Type",   style="cyan")
        table.add_column("Value",  style="bright_green", justify="right")
        table.add_column("Unit",   style="yellow")
        table.add_column("Target", style="dim", justify="right")
        table.add_column("Status", style="magenta")
        table.add_column("Trend",  style="blue")

        for k in kpi_list:
            status_color = "green" if k.status.value == "ON_TRACK" else "red"
            trend_icon   = "↑" if k.trend.value == "IMPROVING" else ("↓" if k.trend.value == "DEGRADING" else "→")
            table.add_row(
                str(k.kpi_type.value),
                str(round(k.current_value, 2)),
                k.current_unit,
                str(k.target_value) if k.target_value is not None else "—",
                f"[{status_color}]{k.status.value}[/{status_color}]",
                trend_icon,
            )

        console.print(table)
    finally:
        db.close()


# ── risk-score ────────────────────────────────────────────────────────────────

@app.command(name="risk-score")
def risk_score(project_id: int = typer.Argument(..., help="Project ID")):
    """Show the latest project risk score and its components."""
    db = _get_db()
    try:
        from app.crud.analytics import crud_analytics
        rs = crud_analytics.get_latest_risk_score(db, project_id)

        if not rs:
            console.print(f"[yellow]No risk score for project {project_id}. Run 'calculate' first.[/yellow]")
            return

        level_color = {
            "CRITICAL": "red",
            "HIGH":     "orange3",
            "MEDIUM":   "yellow",
            "LOW":      "green",
            "MINIMAL":  "bright_green",
        }.get(rs.risk_level.value, "white")

        console.rule(f"[bold]Risk Score — Project {project_id}[/bold]")
        console.print(f"Overall Score : [{level_color}][bold]{rs.overall_score}/100[/bold][/{level_color}]")
        console.print(f"Risk Level    : [{level_color}]{rs.risk_level.value}[/{level_color}]")
        console.print(f"Change        : [bold]{rs.score_change:+d}[/bold] since last calculation")
        console.print(f"Calculated at : {rs.calculated_at}")

        if rs.score_component:
            table = Table(title="Score Components", box=box.SIMPLE)
            table.add_column("Component", style="cyan")
            table.add_column("Points",    style="yellow", justify="right")
            for comp, pts in rs.score_component.items():
                table.add_row(comp.replace("_", " ").title(), str(pts))
            console.print(table)
    finally:
        db.close()


# ── calculate ─────────────────────────────────────────────────────────────────

@app.command()
def calculate(
    project_id: int = typer.Argument(..., help="Project ID"),
    skip_risk: bool = typer.Option(False, help="Skip risk score calculation"),
):
    """Calculate and persist all KPIs and the risk score for a project."""
    db = _get_db()
    try:
        from app.services.analytics_engine import AnalyticsEngine
        engine = AnalyticsEngine(db, _get_realtime())

        with console.status("[yellow]Calculating KPIs…[/yellow]"):
            kpi_list = engine.calculate_all_kpis(project_id)
        console.print(f"[green]✓ {len(kpi_list)} KPIs calculated[/green]")

        if not skip_risk:
            with console.status("[yellow]Calculating risk score…[/yellow]"):
                rs = engine.calculate_risk_score(project_id)
            console.print(f"[green]✓ Risk Score: {rs.overall_score}/100 ({rs.risk_level.value})[/green]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


# ── snapshot ──────────────────────────────────────────────────────────────────

@app.command()
def snapshot(
    project_id: int = typer.Argument(..., help="Project ID"),
    snapshot_type: str = typer.Option("daily", help="Snapshot type: daily | weekly | monthly"),
):
    """Create an analytics snapshot for a project."""
    db = _get_db()
    try:
        from app.services.analytics_engine import AnalyticsEngine
        with console.status(f"[yellow]Creating {snapshot_type} snapshot…[/yellow]"):
            engine = AnalyticsEngine(db, _get_realtime())
            snap = engine.create_analytics_snapshot(project_id, snapshot_type)
        console.print(f"[green]✓ Snapshot {snap.id} created ({snap.snapshot_date})[/green]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


# ── tool-analytics ────────────────────────────────────────────────────────────

@app.command(name="tool-analytics")
def tool_analytics(project_id: int = typer.Argument(..., help="Project ID")):
    """Show tool effectiveness analytics for a project."""
    db = _get_db()
    try:
        from app.crud.analytics import crud_analytics
        tools = crud_analytics.get_tool_analytics(db, project_id)

        if not tools:
            console.print(f"[yellow]No tool analytics for project {project_id}.[/yellow]")
            return

        table = Table(title=f"Tool Analytics — Project {project_id}", box=box.ROUNDED)
        table.add_column("Tool",          style="cyan")
        table.add_column("Effectiveness", style="green",  justify="right")
        table.add_column("FP Rate",       style="yellow", justify="right")
        table.add_column("Findings",      justify="right")
        table.add_column("Trend",         style="blue")

        for t in tools:
            table.add_row(
                t.tool_name,
                f"{t.effectiveness_score:.1f}%",
                f"{t.false_positive_rate:.1f}%",
                str(t.findings_discovered),
                t.trend_30_days.value,
            )

        console.print(table)
    finally:
        db.close()


if __name__ == "__main__":
    app()
