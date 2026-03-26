"""Rich-based output helpers for the CLI"""
import json as _json
from typing import Any, Dict, List

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()

SEVERITY_COLORS: Dict[str, str] = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "green",
    "info": "blue",
}

STATUS_COLORS: Dict[str, str] = {
    "running": "cyan",
    "completed": "green",
    "failed": "red",
    "pending": "yellow",
    "cancelled": "dim",
    "archived": "dim",
}


def print_json(data: Any) -> None:
    typer.echo(_json.dumps(data, indent=2, default=str))


def print_table(title: str, columns: List[str], rows: List[List[Any]]) -> None:
    table = Table(title=title, show_header=True, header_style="bold cyan")
    for col in columns:
        table.add_column(col)
    for row in rows:
        str_row = []
        for v in row:
            if isinstance(v, Text):
                str_row.append(v)
            else:
                str_row.append(str(v) if v is not None else "-")
        table.add_row(*str_row)
    console.print(table)


def severity_text(sev: str) -> Text:
    color = SEVERITY_COLORS.get(sev.lower(), "white")
    return Text(sev.upper(), style=color)


def status_text(status: str) -> Text:
    color = STATUS_COLORS.get(status.lower(), "white")
    return Text(status.upper(), style=color)


def print_findings(findings: List[Dict], fmt: str = "table") -> None:
    if fmt == "json":
        print_json(findings)
        return
    rows = [
        [
            f["id"],
            severity_text(f.get("severity", "info")),
            f.get("title", "-"),
            f.get("host", "-"),
            f.get("tool_name", "-"),
            f.get("risk_score", 0),
        ]
        for f in findings
    ]
    print_table("Findings", ["ID", "Severity", "Title", "Host", "Tool", "Risk"], rows)


def print_projects(projects: List[Dict], fmt: str = "table") -> None:
    if fmt == "json":
        print_json(projects)
        return
    rows = [
        [
            p["id"],
            p["name"],
            p.get("status", "-"),
            p.get("member_count", 0),
            p.get("target_count", 0),
            (p.get("created_at") or "-")[:10],
        ]
        for p in projects
    ]
    print_table(
        "Projects",
        ["ID", "Name", "Status", "Members", "Targets", "Created"],
        rows,
    )


def print_tasks(tasks: List[Dict], fmt: str = "table") -> None:
    if fmt == "json":
        print_json(tasks)
        return
    rows = [
        [
            t.get("id", "-"),
            t.get("tool_name", "-"),
            t.get("target", "-"),
            status_text(t.get("status", "unknown")),
            (t.get("created_at") or "-")[:19],
        ]
        for t in tasks
    ]
    print_table("Scans", ["ID", "Tool", "Target", "Status", "Created"], rows)


def success(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def error(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}", style="red")


def info(msg: str) -> None:
    console.print(f"[blue]ℹ[/blue] {msg}")
