import asyncio
import logging
import os
import subprocess
import sys
from typing import Optional

import httpx
import typer

from heal_plz.engine.output_analyzer import OutputAnalyzer

logger = logging.getLogger(__name__)

app = typer.Typer()

DEFAULT_SERVER = "http://localhost:8765"

_repo_root: Optional[str] = None


def _get_repo_root() -> Optional[str]:
    global _repo_root
    if _repo_root is None:
        try:
            _repo_root = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            _repo_root = ""
    return _repo_root or None


def _normalize_path(file_path: Optional[str]) -> Optional[str]:
    if not file_path or not os.path.isabs(file_path):
        return file_path
    repo_root = _get_repo_root()
    if repo_root and file_path.startswith(repo_root + "/"):
        return file_path[len(repo_root) + 1:]
    return file_path


def _send_error(server: str, owner: str, repo: str, error) -> None:
    payload = {
        "repository_owner": owner,
        "repository_name": repo,
        "error_message": error.message,
        "error_type": error.error_type,
        "stacktrace": error.stacktrace,
        "file_path": _normalize_path(error.file_path),
        "line_number": error.line_number,
        "severity": error.severity.value,
    }

    # Get git branch/sha if available
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
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        payload["commit_sha"] = sha
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        resp = httpx.post(
            f"{server}/api/v1/webhooks/cli",
            json=payload,
            timeout=5,
        )
        data = resp.json()
        status_msg = f"Alert {data.get('alert_status', '?')}"
        if "incident_id" in data:
            status_msg += f" → Incident #{data['incident_number']}"
        typer.echo(
            typer.style(f"  [heal-plz] {status_msg}", fg=typer.colors.CYAN)
        )
    except Exception as e:
        typer.echo(
            typer.style(f"  [heal-plz] Failed to report: {e}", fg=typer.colors.RED),
            err=True,
        )


async def _watch_process(
    command: str,
    server: str,
    owner: str,
    repo: str,
) -> int:
    analyzer = OutputAnalyzer()

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async def read_stream(stream):
        while True:
            line_bytes = await stream.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace")
            # Pass through to terminal
            sys.stdout.write(line)
            sys.stdout.flush()
            # Analyze for errors
            error = analyzer.feed_line(line)
            if error:
                _send_error(server, owner, repo, error)

    await read_stream(proc.stdout)

    # Flush any remaining buffered error
    final = analyzer.flush()
    if final:
        _send_error(server, owner, repo, final)

    return_code = await proc.wait()

    if return_code != 0:
        typer.echo(
            typer.style(
                f"  [heal-plz] Process exited with code {return_code}",
                fg=typer.colors.YELLOW,
            )
        )

    return return_code


def _detect_repo() -> tuple[str, str]:
    try:
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        # Parse owner/repo from git remote URL
        # Handles: git@github.com:owner/repo.git and https://github.com/owner/repo.git
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


@app.command()
def watch(
    command: str = typer.Argument(..., help="Command to run and watch"),
    server: str = typer.Option(DEFAULT_SERVER, help="heal-plz server URL"),
    owner: Optional[str] = typer.Option(None, help="Repository owner (auto-detected from git)"),
    repo: Optional[str] = typer.Option(None, help="Repository name (auto-detected from git)"),
) -> None:
    """Wrap a command and watch its output for errors.

    Examples:
        heal-plz watch "python app.py"
        heal-plz watch "npm test"
        heal-plz watch "go build ./..."
    """
    if not owner or not repo:
        detected_owner, detected_repo = _detect_repo()
        owner = owner or detected_owner
        repo = repo or detected_repo

    typer.echo(
        typer.style(
            f"[heal-plz] Watching: {command} ({owner}/{repo})",
            fg=typer.colors.CYAN,
        )
    )
    typer.echo(
        typer.style(
            f"[heal-plz] Server: {server}",
            fg=typer.colors.CYAN,
        )
    )
    typer.echo("")

    return_code = asyncio.run(_watch_process(command, server, owner, repo))
    raise typer.Exit(return_code)
