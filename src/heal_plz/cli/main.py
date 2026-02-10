import json
import sys
from typing import Optional

import httpx
import typer

from heal_plz.cli.commands.monitor_cmd import app as monitor_app
from heal_plz.cli.commands.watch import watch as watch_command

app = typer.Typer(
    name="heal-plz",
    help="Self-healing coding platform CLI",
    no_args_is_help=True,
)

app.add_typer(monitor_app, name="monitor")
app.command()(watch_command)

DEFAULT_SERVER = "http://localhost:8765"


def _server_url(server: str) -> str:
    return server.rstrip("/")


@app.command()
def status(
    incident_id: Optional[str] = typer.Argument(None, help="Incident ID to check"),
    server: str = typer.Option(DEFAULT_SERVER, help="heal-plz server URL"),
) -> None:
    """Check incident status or list recent incidents."""
    url = _server_url(server)

    if incident_id:
        resp = httpx.get(f"{url}/api/v1/incidents/{incident_id}")
        if resp.status_code == 200:
            data = resp.json()
            typer.echo(f"Incident #{data['incident_number']}: {data['title']}")
            typer.echo(f"  Status:   {data['status']}")
            typer.echo(f"  Priority: {data['priority']}")
            typer.echo(f"  Events:   {data['event_count']}")
        else:
            typer.echo(f"Error: {resp.status_code}", err=True)
    else:
        resp = httpx.get(f"{url}/api/v1/incidents/", params={"limit": 10})
        if resp.status_code == 200:
            incidents = resp.json()
            if not incidents:
                typer.echo("No incidents found.")
                return
            for inc in incidents:
                typer.echo(
                    f"  #{inc['incident_number']:>4}  "
                    f"[{inc['status']:>20}]  "
                    f"{inc['priority']}  "
                    f"{inc['title'][:60]}"
                )
        else:
            typer.echo(f"Error: {resp.status_code}", err=True)


@app.command()
def report(
    message: str = typer.Argument(..., help="Error message"),
    error_type: Optional[str] = typer.Option(None, help="Error type (e.g., TypeError)"),
    file: Optional[str] = typer.Option(None, help="File path where error occurred"),
    line: Optional[int] = typer.Option(None, help="Line number"),
    owner: str = typer.Option(..., help="GitHub repo owner"),
    repo: str = typer.Option(..., help="GitHub repo name"),
    server: str = typer.Option(DEFAULT_SERVER, help="heal-plz server URL"),
) -> None:
    """Report a local error to the heal-plz server."""
    url = _server_url(server)

    payload = {
        "repository_owner": owner,
        "repository_name": repo,
        "error_message": message,
        "error_type": error_type,
        "file_path": file,
        "line_number": line,
        "severity": "error",
        "environment": "development",
    }

    resp = httpx.post(f"{url}/api/v1/webhooks/generic", json=payload)
    if resp.status_code in (200, 202):
        typer.echo("Error reported successfully.")
        data = resp.json()
        if "incident_id" in data:
            typer.echo(f"  Incident ID: {data['incident_id']}")
    else:
        typer.echo(f"Failed to report: {resp.status_code}", err=True)


@app.command()
def dashboard(
    server: str = typer.Option(DEFAULT_SERVER, help="heal-plz server URL"),
) -> None:
    """Show platform dashboard overview."""
    url = _server_url(server)
    resp = httpx.get(f"{url}/api/v1/dashboard/overview")
    if resp.status_code == 200:
        data = resp.json()
        typer.echo("heal-plz Dashboard")
        typer.echo("=" * 40)
        typer.echo(f"  Repositories:     {data['total_repositories']}")
        typer.echo(f"  Total Incidents:  {data['total_incidents']}")
        typer.echo(f"  Open:             {data['open_incidents']}")
        typer.echo(f"  Resolved:         {data['resolved_incidents']}")
        typer.echo(f"  Fixes Generated:  {data['total_fixes_generated']}")
        typer.echo(f"  PRs Created:      {data['total_prs_created']}")
        typer.echo(f"  Heal Rate:        {data['auto_heal_success_rate']:.1%}")
    else:
        typer.echo(f"Error: {resp.status_code}", err=True)


@app.command()
def health(
    server: str = typer.Option(DEFAULT_SERVER, help="heal-plz server URL"),
) -> None:
    """Check server health."""
    url = _server_url(server)
    try:
        resp = httpx.get(f"{url}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            typer.echo(f"Server: {data['status']} (v{data['version']}, {data['environment']})")
        else:
            typer.echo(f"Server returned: {resp.status_code}", err=True)
    except httpx.ConnectError:
        typer.echo(f"Cannot connect to {url}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
