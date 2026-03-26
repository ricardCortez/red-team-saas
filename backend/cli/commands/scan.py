"""Scan execution commands"""
import time
from typing import Optional

import typer

from cli.client import get_client
from cli.config import get_config
from cli.output import console, error, info, print_json, print_tasks, status_text, success

app = typer.Typer(help="Scan execution")


@app.command("run")
def run_scan(
    tool: str = typer.Argument(..., help="Tool name (nmap, hydra, wpscan, ...)"),
    target: str = typer.Argument(..., help="Target IP, hostname, or URL"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    ports: Optional[str] = typer.Option(None, "--ports"),
    protocol: Optional[str] = typer.Option(None, "--protocol"),
    passlist: Optional[str] = typer.Option(None, "--passlist"),
    userlist: Optional[str] = typer.Option(None, "--userlist"),
    timeout: Optional[int] = typer.Option(None, "--timeout"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Poll until completion"),
    stream: bool = typer.Option(False, "--stream", "-S", help="Stream live output via SSE"),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """Launch a scan against a target."""
    pid = project_id or get_config().default_project_id

    options: dict = {}
    if profile:
        options["profile"] = profile
    if ports:
        options["ports"] = ports
    if protocol:
        options["protocol"] = protocol
    if passlist:
        options["passlist"] = passlist
    if userlist:
        options["userlist"] = userlist
    if timeout:
        options["timeout"] = timeout

    client = get_client()
    payload: dict = {"tool_name": tool, "target": target, "options": options}
    if pid:
        payload["project_id"] = pid

    data = client.post("/executions", payload)
    task_id = data["id"]
    success(f"Scan launched: ID={task_id} | {tool} → {target}")

    if stream:
        _stream_output(client, task_id)
    elif wait:
        _wait_for_completion(client, task_id)


def _stream_output(client, task_id: int) -> None:
    info("Streaming output (Ctrl+C to stop)...")
    try:
        for event in client.stream_sse(f"/executions/{task_id}/stream"):
            if "line" in event:
                console.print(f"  {event['line']}", style="dim")
            elif event.get("event") == "done":
                st = event.get("status", "unknown")
                console.print(f"\n[bold]Scan {status_text(st)}[/bold]")
                break
    except KeyboardInterrupt:
        info("Stopped streaming. Scan continues in background.")


def _wait_for_completion(client, task_id: int, poll_interval: int = 3) -> None:
    info("Waiting for completion...")
    final_status = "unknown"
    with console.status("[cyan]Running...") as spinner:
        while True:
            data = client.get(f"/executions/{task_id}/status")
            final_status = data.get("status", "unknown")
            spinner.update(f"[cyan]Status: {final_status}")
            if final_status in ("completed", "failed", "cancelled"):
                break
            time.sleep(poll_interval)
    if final_status == "completed":
        success("Scan completed")
    else:
        error(f"Scan ended with status: {final_status}")


@app.command("status")
def scan_status(
    task_id: int = typer.Argument(...),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """Get the status of a scan."""
    client = get_client()
    data = client.get(f"/executions/{task_id}/status")
    fmt = fmt or get_config().output_format
    if fmt == "json":
        print_json(data)
    else:
        info(f"Task ID:  {data.get('task_id', task_id)}")
        info(f"Status:   {data.get('status', '-')}")
        info(f"Celery:   {data.get('celery_state', '-')}")
        if data.get("error_message"):
            error(f"Error: {data['error_message']}")


@app.command("cancel")
def cancel_scan(task_id: int = typer.Argument(...)):
    """Cancel a running scan."""
    client = get_client()
    client.delete(f"/executions/{task_id}")
    success(f"Scan {task_id} cancelled")


@app.command("list")
def list_scans(
    project_id: Optional[int] = typer.Option(None, "--project", "-p"),
    status: Optional[str] = typer.Option(None, "--status"),
    limit: int = typer.Option(20, "--limit", "-n"),
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """List recent scans."""
    client = get_client()
    params: dict = {"limit": limit}
    if project_id:
        params["project_id"] = project_id
    if status:
        params["status"] = status
    data = client.get("/executions", params=params)
    fmt = fmt or get_config().output_format
    items = data.get("items", data) if isinstance(data, dict) else data
    print_tasks(items if isinstance(items, list) else [], fmt)


@app.command("stream")
def stream_output(task_id: int = typer.Argument(...)):
    """Stream live output of a running scan."""
    client = get_client()
    _stream_output(client, task_id)
