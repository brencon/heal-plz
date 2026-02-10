import pytest
from httpx import AsyncClient


async def _create_incident(client: AsyncClient) -> dict:
    """Send a workflow failure webhook (HIGH severity → immediate escalation)."""
    payload = {
        "action": "completed",
        "workflow_run": {
            "name": "Tests",
            "conclusion": "failure",
            "head_branch": "dev",
            "head_sha": "xyz789",
            "id": 55555,
        },
        "repository": {
            "name": "inc-repo",
            "full_name": "owner/inc-repo",
            "owner": {"login": "owner"},
            "default_branch": "main",
            "language": "TypeScript",
        },
    }
    resp = await client.post(
        "/api/v1/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "workflow_run"},
    )
    data = resp.json()
    assert "incident_id" in data, f"Expected escalation to incident, got: {data}"
    return data


@pytest.mark.asyncio
async def test_list_incidents(client: AsyncClient):
    await _create_incident(client)
    response = await client.get("/api/v1/incidents/")
    assert response.status_code == 200
    incidents = response.json()
    assert len(incidents) >= 1


@pytest.mark.asyncio
async def test_get_incident(client: AsyncClient):
    data = await _create_incident(client)
    response = await client.get(f"/api/v1/incidents/{data['incident_id']}")
    assert response.status_code == 200
    incident = response.json()
    assert incident["incident_number"] == data["incident_number"]
    assert incident["status"] == "open"


@pytest.mark.asyncio
async def test_close_and_reopen_incident(client: AsyncClient):
    data = await _create_incident(client)
    inc_id = data["incident_id"]

    resp = await client.post(f"/api/v1/incidents/{inc_id}/close")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    resp = await client.post(f"/api/v1/incidents/{inc_id}/reopen")
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"


@pytest.mark.asyncio
async def test_update_incident_priority(client: AsyncClient):
    data = await _create_incident(client)
    inc_id = data["incident_id"]

    resp = await client.patch(
        f"/api/v1/incidents/{inc_id}",
        json={"priority": "p0"},
    )
    assert resp.status_code == 200
    assert resp.json()["priority"] == "p0"


@pytest.mark.asyncio
async def test_get_nonexistent_incident(client: AsyncClient):
    resp = await client.get("/api/v1/incidents/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
