"""Authentication commands: login, logout, whoami, config"""
import typer
from cli.client import APIClient, get_client
from cli.config import get_config
from cli.output import error, info, success

app = typer.Typer(help="Authentication commands")


@app.command()
def login(
    url: str = typer.Option(None, "--url", "-u", help="API base URL"),
    username: str = typer.Option(None, "--user", "-U", help="Username"),
    password: str = typer.Option(
        None, "--pass", "-P", help="Password", hide_input=True
    ),
):
    """Login and save session token."""
    cfg = get_config()

    if url:
        cfg.api_url = url

    if not username:
        username = typer.prompt("Username")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    client = APIClient(cfg)
    try:
        data = client.post("/auth/login", {"username": username, "password": password})
        if data is None:
            error("Login failed")
            raise typer.Exit(1)
        cfg.access_token = data["access_token"]
        cfg.refresh_token = data.get("refresh_token")
        cfg.username = username
        cfg.save()
        success(f"Logged in as {username}")
    except typer.Exit:
        error("Login failed")
        raise


@app.command()
def logout():
    """Clear saved credentials."""
    cfg = get_config()
    cfg.clear_auth()
    success("Logged out")


@app.command()
def whoami():
    """Show current user info."""
    client = get_client()
    data = client.get("/auth/me")
    if data:
        info(f"Username: {data.get('username', '-')}")
        info(f"Email:    {data.get('email', '-')}")
        info(f"Role:     {data.get('role', '-')}")


@app.command("config")
def configure(
    url: str = typer.Option(None, "--url", help="Set API URL"),
    fmt: str = typer.Option(None, "--format", help="Output format: table|json"),
):
    """Configure CLI settings."""
    cfg = get_config()
    if url:
        cfg.api_url = url
        success(f"API URL set to: {url}")
    if fmt:
        if fmt not in ("table", "json"):
            error("Format must be 'table' or 'json'")
            raise typer.Exit(1)
        cfg.output_format = fmt
        success(f"Output format set to: {fmt}")
    cfg.save()
    info(f"API URL: {cfg.api_url}")
    info(f"Format:  {cfg.output_format}")
    info(f"User:    {cfg.username or 'not logged in'}")
