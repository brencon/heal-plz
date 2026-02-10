import pytest
from httpx import AsyncClient


def _make_workflow_payload(workflow_name: str, repo_name: str, branch: str = "main"):
    return {
        "action": "completed",
        "workflow_run": {
            "name": workflow_name,
            "conclusion": "failure",
            "head_branch": branch,
            "head_sha": "abc123",
            "id": 11111,
        },
        "repository": {
            "name": repo_name,
            "full_name": f"owner/{repo_name}",
            "owner": {"login": "owner"},
            "default_branch": "main",
            "language": "Python",
        },
    }


async def _send_webhook(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post(
        "/api/v1/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "workflow_run"},
    )
    assert resp.status_code == 202
    return resp.json()


@pytest.mark.asyncio
async def test_high_severity_alert_escalates_immediately(client: AsyncClient):
    """Workflow failures are ERROR → AlertSeverity.HIGH → threshold=1."""
    payload = _make_workflow_payload("CI", "high-sev-repo")
    data = await _send_webhook(client, payload)

    assert data["alert_status"] == "escalated"
    assert data["occurrence_count"] == 1
    assert "incident_id" in data
    assert data["incident_number"] == 1


@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient):
    payload = _make_workflow_payload("Lint", "list-alerts-repo")
    data = await _send_webhook(client, payload)

    resp = await client.get("/api/v1/alerts/")
    assert resp.status_code == 200
    alerts = resp.json()
    assert any(a["id"] == data["alert_id"] for a in alerts)


@pytest.mark.asyncio
async def test_get_alert(client: AsyncClient):
    payload = _make_workflow_payload("Tests", "get-alert-repo")
    data = await _send_webhook(client, payload)

    resp = await client.get(f"/api/v1/alerts/{data['alert_id']}")
    assert resp.status_code == 200
    alert = resp.json()
    assert alert["severity"] == "high"
    assert alert["occurrence_count"] == 1
    assert alert["incident_id"] is not None


@pytest.mark.asyncio
async def test_acknowledge_alert(client: AsyncClient):
    payload = _make_workflow_payload("Deploy", "ack-repo")
    data = await _send_webhook(client, payload)

    resp = await client.post(f"/api/v1/alerts/{data['alert_id']}/acknowledge")
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_suppress_alert(client: AsyncClient):
    payload = _make_workflow_payload("Build", "suppress-repo")
    data = await _send_webhook(client, payload)

    resp = await client.post(f"/api/v1/alerts/{data['alert_id']}/suppress")
    assert resp.status_code == 200
    assert resp.json()["status"] == "suppressed"


@pytest.mark.asyncio
async def test_resolve_alert(client: AsyncClient):
    payload = _make_workflow_payload("E2E", "resolve-repo")
    data = await _send_webhook(client, payload)

    resp = await client.post(f"/api/v1/alerts/{data['alert_id']}/resolve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_update_alert_auto_escalate(client: AsyncClient):
    payload = _make_workflow_payload("Perf", "update-repo")
    data = await _send_webhook(client, payload)

    resp = await client.patch(
        f"/api/v1/alerts/{data['alert_id']}",
        json={"auto_escalate": False},
    )
    assert resp.status_code == 200
    assert resp.json()["auto_escalate"] is False


@pytest.mark.asyncio
async def test_get_nonexistent_alert(client: AsyncClient):
    resp = await client.get("/api/v1/alerts/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
