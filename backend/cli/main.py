"""Red Team SaaS CLI — entry point"""
import typer

from cli.commands import auth, findings, projects, reports, scan, targets, wordlists

app = typer.Typer(
    name="redteam",
    help="Red Team SaaS CLI — Professional penetration testing toolkit",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(auth.app, name="auth", help="Authentication")
app.add_typer(projects.app, name="projects", help="Project management")
app.add_typer(targets.app, name="targets", help="Scope management")
app.add_typer(scan.app, name="scan", help="Scan execution")
app.add_typer(findings.app, name="findings", help="Findings")
app.add_typer(reports.app, name="reports", help="Reports")
app.add_typer(wordlists.app, name="wordlists", help="Wordlist management")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context = typer.Option(None, hidden=True),
    version: bool = typer.Option(False, "--version", "-v", is_eager=True),
) -> None:
    """Red Team SaaS CLI"""
    if version:
        typer.echo("Red Team SaaS CLI v1.0.0")
        raise typer.Exit()


if __name__ == "__main__":
    app()
