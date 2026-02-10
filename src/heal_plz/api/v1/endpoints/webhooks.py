import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.api.dependencies import get_db, get_event_bus
from heal_plz.config import settings
from heal_plz.core.events import EventBus
from heal_plz.core.exceptions import WebhookVerificationError
from heal_plz.db.models.monitor import Monitor, MonitorType
from heal_plz.db.models.repository import Repository
from heal_plz.engine.normalizer import EventNormalizer
from heal_plz.integrations.github.webhooks import verify_signature
from heal_plz.services.alert_service import AlertService
from heal_plz.services.monitor_service import MonitorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])
normalizer = EventNormalizer()


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus),
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
) -> dict:
    body = await request.body()

    if settings.GITHUB_WEBHOOK_SECRET:
        if not verify_signature(body, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
            raise WebhookVerificationError()

    payload = await request.json()
    event_type = x_github_event or "unknown"

    # --- Pillar 1: MONITORING ---
    # Normalize the raw event from the source
    normalized = None
    if event_type == "workflow_run":
        normalized = normalizer.normalize_github_workflow_run(payload)
    elif event_type == "check_run":
        normalized = normalizer.normalize_github_check_run(payload)

    if not normalized:
        return {"status": "ignored", "event": event_type}

    # Auto-register repository and monitor
    repo_data = payload.get("repository", {})
    owner = repo_data.get("owner", {}).get("login", "")
    repo_name = repo_data.get("name", "")

    result = await db.execute(
        select(Repository).where(
            Repository.github_owner == owner,
            Repository.github_repo == repo_name,
        )
    )
    repository = result.scalar_one_or_none()

    if not repository:
        repository = Repository(
            github_owner=owner,
            github_repo=repo_name,
            default_branch=repo_data.get("default_branch", "main"),
            language=repo_data.get("language"),
        )
        db.add(repository)
        await db.flush()
        await db.refresh(repository)
        logger.info("Auto-registered repository %s/%s", owner, repo_name)

    result = await db.execute(
        select(Monitor).where(
            Monitor.repository_id == repository.id,
            Monitor.monitor_type == MonitorType.GITHUB_ACTIONS,
        )
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        monitor = Monitor(
            repository_id=repository.id,
            name=f"GitHub Actions - {owner}/{repo_name}",
            monitor_type=MonitorType.GITHUB_ACTIONS,
        )
        db.add(monitor)
        await db.flush()
        await db.refresh(monitor)

    # Ingest the raw monitor event
    monitor_service = MonitorService(db, event_bus)
    monitor_event = await monitor_service.ingest_event(monitor.id, normalized)

    # --- Pillar 2: ALERTING ---
    # Create or update an alert (grouped by fingerprint)
    # Alerts accumulate occurrences and are classified by severity
    alert_service = AlertService(db, event_bus)
    alert = await alert_service.process_event(
        monitor_event, normalized, repository.id
    )

    # --- Pillar 3: INCIDENT CREATION ---
    # AlertService decides whether to escalate based on rules:
    # - Critical/High severity: escalate immediately (threshold=1)
    # - Medium severity: escalate after 3 occurrences
    # - Low severity: escalate after 5 occurrences
    # - Info severity: escalate after 10 occurrences
    # The incident is created inside alert_service.process_event()
    # only when escalation criteria are met.

    response: dict = {
        "status": "accepted",
        "alert_id": str(alert.id),
        "alert_status": alert.status.value,
        "occurrence_count": alert.occurrence_count,
    }

    if alert.incident_id:
        response["incident_id"] = str(alert.incident_id)
        # Get incident number
        from heal_plz.db.models.incident import Incident
        inc_result = await db.execute(
            select(Incident).where(Incident.id == alert.incident_id)
        )
        incident = inc_result.scalar_one_or_none()
        if incident:
            response["incident_number"] = incident.incident_number

    return response


@router.post("/sentry", status_code=status.HTTP_202_ACCEPTED)
async def sentry_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus),
) -> dict:
    payload = await request.json()
    normalized = normalizer.normalize_sentry_event(payload)

    if not normalized:
        return {"status": "ignored"}

    return {"status": "accepted", "message": "Sentry event normalized"}


@router.post("/cli", status_code=status.HTTP_202_ACCEPTED)
async def cli_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus),
) -> dict:
    payload = await request.json()

    owner = payload.get("repository_owner", "local")
    repo_name = payload.get("repository_name", "unknown")
    severity_str = payload.get("severity", "error")

    from heal_plz.db.models.monitor_event import EventSeverity

    severity_map = {
        "critical": EventSeverity.CRITICAL,
        "error": EventSeverity.ERROR,
        "warning": EventSeverity.WARNING,
        "info": EventSeverity.INFO,
    }

    normalized = normalizer.normalize_cli_report(
        error_message=payload.get("error_message", "Unknown error"),
        error_type=payload.get("error_type"),
        stacktrace=payload.get("stacktrace"),
        file_path=payload.get("file_path"),
        line_number=payload.get("line_number"),
        branch=payload.get("branch"),
        commit_sha=payload.get("commit_sha"),
        severity=severity_map.get(severity_str, EventSeverity.ERROR),
    )

    # Auto-register repository and monitor
    result = await db.execute(
        select(Repository).where(
            Repository.github_owner == owner,
            Repository.github_repo == repo_name,
        )
    )
    repository = result.scalar_one_or_none()

    if not repository:
        repository = Repository(
            github_owner=owner,
            github_repo=repo_name,
            default_branch="main",
            language=payload.get("language"),
        )
        db.add(repository)
        await db.flush()
        await db.refresh(repository)
        logger.info("Auto-registered repository %s/%s", owner, repo_name)

    result = await db.execute(
        select(Monitor).where(
            Monitor.repository_id == repository.id,
            Monitor.monitor_type == MonitorType.LOCAL_CLI,
        )
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        monitor = Monitor(
            repository_id=repository.id,
            name=f"Local CLI - {owner}/{repo_name}",
            monitor_type=MonitorType.LOCAL_CLI,
        )
        db.add(monitor)
        await db.flush()
        await db.refresh(monitor)

    monitor_service = MonitorService(db, event_bus)
    monitor_event = await monitor_service.ingest_event(monitor.id, normalized)

    alert_service = AlertService(db, event_bus)
    alert = await alert_service.process_event(
        monitor_event, normalized, repository.id
    )

    response: dict = {
        "status": "accepted",
        "alert_id": str(alert.id),
        "alert_status": alert.status.value,
        "occurrence_count": alert.occurrence_count,
    }

    if alert.incident_id:
        response["incident_id"] = str(alert.incident_id)
        from heal_plz.db.models.incident import Incident

        inc_result = await db.execute(
            select(Incident).where(Incident.id == alert.incident_id)
        )
        incident = inc_result.scalar_one_or_none()
        if incident:
            response["incident_number"] = incident.incident_number

    return response


@router.post("/generic", status_code=status.HTTP_202_ACCEPTED)
async def generic_webhook(request: Request) -> dict:
    return {"status": "accepted", "message": "Generic webhook received"}
