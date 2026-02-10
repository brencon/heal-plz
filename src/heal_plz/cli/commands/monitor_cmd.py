import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import httpx
import typer
import yaml

from heal_plz.engine.file_watcher import FileWatcher, OnChangeCheck
from heal_plz.engine.log_tailer import LogTailer
from heal_plz.engine.output_analyzer import DetectedError

logger = logging.getLogger(__name__)

app = typer.Typer(help="Background monitoring daemon")

DEFAULT_SERVER = "http://localhost:8765"
PID_FILE = Path(".healplz.pid")
CONFIG_FILE = Path(".healplz.yaml")


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def _detect_repo() -> tuple[str, str]:
    try:
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if ":" in remote and "@" in remote:
            path = remote.split(":")[-1].replace(".git", "")
        else:
            path = "/".join(remote.rstrip("/").split("/")[-2:]).replace(".git", "")
        parts = path.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return "local", "unknown"


def _send_error(server: str, owner: str, repo: str, error: DetectedError, source: str) -> None:
    payload = {
        "repository_owner": owner,
        "repository_name": repo,
        "error_message": error.message,
        "error_type": error.error_type,
        "stacktrace": error.stacktrace,
        "file_path": error.file_path or source,
        "line_number": error.line_number,
        "severity": error.severity.value,
    }

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        payload["branch"] = branch
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        resp = httpx.post(f"{server}/api/v1/webhooks/cli", json=payload, timeout=5)
        data = resp.json()
        status_msg = f"Alert {data.get('alert_status', '?')}: {error.error_type or 'error'}"
        if "incident_id" in data:
            status_msg += f" → Incident #{data['incident_number']}"
        logger.info(status_msg)
    except Exception as e:
        logger.error("Failed to report error: %s", e)


async def _run_daemon(server: str, owner: str, repo: str, config: dict) -> None:
    tasks = []

    def on_error(error: DetectedError, source: str) -> None:
        _send_error(server, owner, repo, error, source)

    monitor_config = config.get("monitor", {})

    # Set up log tailers
    for log_conf in monitor_config.get("logs", []):
        tailer = LogTailer(
            path=log_conf["path"],
            on_error=on_error,
            patterns=log_conf.get("patterns"),
        )
        tasks.append(asyncio.create_task(tailer.start()))

    # Set up file watcher
    file_watch = monitor_config.get("file_watch", {})
    watch_paths = file_watch.get("paths", [])
    if watch_paths:
        checks = []
        for check_conf in file_watch.get("on_change", []):
            checks.append(OnChangeCheck(
                command=check_conf["command"],
                severity=check_conf.get("severity", "warning"),
            ))

        watcher = FileWatcher(
            paths=watch_paths,
            extensions=file_watch.get("extensions", [".py"]),
            on_error=on_error,
            on_change_checks=checks,
        )
        tasks.append(asyncio.create_task(watcher.start()))

    if not tasks:
        logger.warning("No monitors configured. Create a .healplz.yaml file.")
        return

    logger.info("Monitor daemon started with %d watchers", len(tasks))

    stop_event = asyncio.Event()

    def handle_signal():
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    await stop_event.wait()

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Monitor daemon stopped")


@app.command()
def start(
    server: str = typer.Option(DEFAULT_SERVER, help="heal-plz server URL"),
    foreground: bool = typer.Option(False, "--fg", help="Run in foreground"),
) -> None:
    """Start the monitoring daemon."""
    config = _load_config()
    owner = config.get("repository", {}).get("owner")
    repo = config.get("repository", {}).get("name")
    server = config.get("server", server)

    if not owner or not repo:
        detected_owner, detected_repo = _detect_repo()
        owner = owner or detected_owner
        repo = repo or detected_repo

    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            typer.echo(f"Monitor already running (PID {pid})")
            raise typer.Exit(1)
        except ProcessLookupError:
            PID_FILE.unlink()

    if foreground:
        typer.echo(
            typer.style(
                f"[heal-plz] Monitor starting ({owner}/{repo})",
                fg=typer.colors.CYAN,
            )
        )
        typer.echo(
            typer.style(f"[heal-plz] Server: {server}", fg=typer.colors.CYAN)
        )

        monitor_config = config.get("monitor", {})
        logs = monitor_config.get("logs", [])
        file_watch = monitor_config.get("file_watch", {})

        if logs:
            for lc in logs:
                typer.echo(f"  Tailing: {lc['path']}")
        if file_watch.get("paths"):
            typer.echo(f"  Watching: {', '.join(file_watch['paths'])}")

        PID_FILE.write_text(str(os.getpid()))
        try:
            asyncio.run(_run_daemon(server, owner, repo, config))
        finally:
            if PID_FILE.exists():
                PID_FILE.unlink()
    else:
        typer.echo("Background mode: use --fg for foreground")
        typer.echo(f"  heal-plz monitor start --fg")


@app.command()
def stop() -> None:
    """Stop the monitoring daemon."""
    if not PID_FILE.exists():
        typer.echo("Monitor is not running")
        raise typer.Exit(1)

    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        typer.echo(f"Monitor stopped (PID {pid})")
    except ProcessLookupError:
        typer.echo("Monitor was not running")
    finally:
        PID_FILE.unlink(missing_ok=True)


@app.command(name="status")
def monitor_status() -> None:
    """Show monitoring daemon status."""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            typer.echo(typer.style(f"Monitor running (PID {pid})", fg=typer.colors.GREEN))
        except ProcessLookupError:
            typer.echo("Monitor not running (stale PID file)")
            PID_FILE.unlink()
    else:
        typer.echo("Monitor not running")

    config = _load_config()
    if config:
        typer.echo("")
        typer.echo("Configuration (.healplz.yaml):")
        monitor_config = config.get("monitor", {})
        logs = monitor_config.get("logs", [])
        file_watch = monitor_config.get("file_watch", {})

        if logs:
            typer.echo("  Log files:")
            for lc in logs:
                typer.echo(f"    - {lc['path']} (patterns: {lc.get('patterns', ['*'])})")
        if file_watch.get("paths"):
            typer.echo(f"  File watch: {', '.join(file_watch['paths'])}")
            for check in file_watch.get("on_change", []):
                typer.echo(f"    on_change: {check['command']}")
    else:
        typer.echo("")
        typer.echo("No .healplz.yaml found. Create one to configure monitoring.")
