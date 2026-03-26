"""Wordlist management commands"""
from typing import List, Optional

import typer

from cli.client import get_client
from cli.config import get_config
from cli.output import error, info, print_json, print_table, success

app = typer.Typer(help="Wordlist management")


@app.command("list")
def list_wordlists(
    fmt: Optional[str] = typer.Option(None, "--format", "-f"),
):
    """List all available wordlists (system + custom)."""
    client = get_client()
    data = client.get("/wordlists")
    fmt = fmt or get_config().output_format
    if fmt == "json":
        print_json(data)
    else:
        system = data.get("system", [])
        custom = data.get("custom", [])
        sys_rows = [
            [w["name"], w["path"], "✓" if w.get("available") else "✗"]
            for w in system
        ]
        print_table("System Wordlists", ["Name", "Path", "Available"], sys_rows)
        if custom:
            cus_rows = [
                [w["name"], w["path"], w.get("word_count", 0), w.get("size_bytes", 0)]
                for w in custom
            ]
            print_table(
                "Custom Wordlists", ["Name", "Path", "Words", "Bytes"], cus_rows
            )
        else:
            info("No custom wordlists")


@app.command("upload")
def upload_wordlist(
    name: str = typer.Argument(..., help="Name for the wordlist"),
    file: str = typer.Argument(..., help="Path to a text file (one word per line)"),
):
    """Upload a custom wordlist from a local file."""
    try:
        with open(file) as fh:
            words = [line.strip() for line in fh if line.strip()]
    except FileNotFoundError:
        error(f"File not found: {file}")
        raise typer.Exit(1)

    if not words:
        error("File is empty or contains no valid words")
        raise typer.Exit(1)

    client = get_client()
    data = client.post("/wordlists/custom", {"name": name, "words": words})
    success(f"Uploaded '{name}': {data.get('word_count', len(words))} words → {data.get('path', '-')}")
