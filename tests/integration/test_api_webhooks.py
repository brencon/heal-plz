import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_github_webhook_creates_alert_and_escalates(client: AsyncClient):
    """HIGH severity (workflow failure) escalates immediately (threshold=1)."""
    payload = {
        "action": "completed",
        "workflow_run": {
            "name": "CI",
            "conclusion": "failure",
            "head_branch": "main",
            "head_sha": "abc123",
            "id": 12345,
        },
        "repository": {
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": {"login": "owner"},
            "default_branch": "main",
            "language": "Python",
        },
    }
    response = await client.post(
        "/api/v1/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "workflow_run"},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "alert_id" in data
    assert data["alert_status"] == "escalated"
    assert data["occurrence_count"] == 1
    assert "incident_id" in data
    assert data["incident_number"] == 1


@pytest.mark.asyncio
async def test_github_webhook_deduplicates_alerts(client: AsyncClient):
    """Same fingerprint groups into same alert and same incident."""
    payload = {
        "action": "completed",
        "workflow_run": {
            "name": "Build",
            "conclusion": "failure",
            "head_branch": "feature",
            "head_sha": "def456",
            "id": 99999,
        },
        "repository": {
            "name": "dedup-repo",
            "full_name": "owner/dedup-repo",
            "owner": {"login": "owner"},
            "default_branch": "main",
            "language": "Python",
        },
    }
    headers = {"X-GitHub-Event": "workflow_run"}

    r1 = await client.post("/api/v1/webhooks/github", json=payload, headers=headers)
    r2 = await client.post("/api/v1/webhooks/github", json=payload, headers=headers)

    d1 = r1.json()
    d2 = r2.json()

    assert d1["alert_id"] == d2["alert_id"]
    assert d1["incident_id"] == d2["incident_id"]
    assert d1["occurrence_count"] == 1
    assert d2["occurrence_count"] == 2


@pytest.mark.asyncio
async def test_github_webhook_ignores_success(client: AsyncClient):
    payload = {
        "action": "completed",
        "workflow_run": {
            "name": "CI",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": "abc123",
        },
    }
    response = await client.post(
        "/api/v1/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "workflow_run"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_github_webhook_ignores_unknown_event(client: AsyncClient):
    response = await client.post(
        "/api/v1/webhooks/github",
        json={"action": "opened"},
        headers={"X-GitHub-Event": "issues"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_cli_webhook_creates_alert(client: AsyncClient):
    payload = {
        "repository_owner": "testowner",
        "repository_name": "testrepo",
        "error_message": "TypeError: expected str, got int",
        "error_type": "TypeError",
        "file_path": "src/app.py",
        "line_number": 42,
        "severity": "error",
        "branch": "main",
    }
    response = await client.post("/api/v1/webhooks/cli", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "alert_id" in data
    assert data["alert_status"] in ("active", "escalated")
    assert data["occurrence_count"] >= 1


@pytest.mark.asyncio
async def test_cli_webhook_auto_registers_repo(client: AsyncClient):
    payload = {
        "repository_owner": "newowner",
        "repository_name": "newrepo",
        "error_message": "SomeError: something failed",
        "severity": "warning",
    }
    response = await client.post("/api/v1/webhooks/cli", json=payload)
    assert response.status_code == 202

    repos = await client.get("/api/v1/repositories/")
    repo_names = [r["github_repo"] for r in repos.json()]
    assert "newrepo" in repo_names


@pytest.mark.asyncio
async def test_cli_webhook_creates_monitor(client: AsyncClient):
    payload = {
        "repository_owner": "cliowner",
        "repository_name": "clirepo",
        "error_message": "RuntimeError: crash",
        "severity": "error",
    }
    await client.post("/api/v1/webhooks/cli", json=payload)

    monitors = await client.get("/api/v1/monitors/")
    data = monitors.json()
    local_cli = [m for m in data if m["monitor_type"] == "local_cli"]
    assert len(local_cli) >= 1
