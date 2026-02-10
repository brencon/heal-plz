import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.api.dependencies import get_db, get_event_bus, get_task_manager
from heal_plz.core.events import EventBus
from heal_plz.core.exceptions import NotFoundError
from heal_plz.core.tasks import BackgroundTaskManager
from heal_plz.db.models.incident import IncidentStatus
from heal_plz.db.repositories.incident_repo import IncidentRepository
from heal_plz.engine.state_machine import validate_transition
from heal_plz.schemas.incident import IncidentResponse, IncidentUpdate

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/", response_model=list[IncidentResponse])
async def list_incidents(
    repository_id: Optional[uuid.UUID] = None,
    status_filter: Optional[IncidentStatus] = None,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[IncidentResponse]:
    repo = IncidentRepository(db)
    if repository_id:
        results = await repo.get_by_repo(
            repository_id, status=status_filter, offset=offset, limit=limit
        )
    else:
        results = await repo.list(offset=offset, limit=limit)
    return [IncidentResponse.model_validate(r) for r in results]


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    repo = IncidentRepository(db)
    obj = await repo.get(incident_id)
    if not obj:
        raise NotFoundError("Incident", str(incident_id))
    return IncidentResponse.model_validate(obj)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: uuid.UUID,
    data: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    repo = IncidentRepository(db)
    obj = await repo.get(incident_id)
    if not obj:
        raise NotFoundError("Incident", str(incident_id))
    updated = await repo.update(obj, data.model_dump(exclude_unset=True))
    return IncidentResponse.model_validate(updated)


@router.post("/{incident_id}/close", response_model=IncidentResponse)
async def close_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    repo = IncidentRepository(db)
    obj = await repo.get(incident_id)
    if not obj:
        raise NotFoundError("Incident", str(incident_id))
    validate_transition(obj.status, IncidentStatus.CLOSED)
    updated = await repo.update(obj, {"status": IncidentStatus.CLOSED})
    return IncidentResponse.model_validate(updated)


@router.post("/{incident_id}/reopen", response_model=IncidentResponse)
async def reopen_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    repo = IncidentRepository(db)
    obj = await repo.get(incident_id)
    if not obj:
        raise NotFoundError("Incident", str(incident_id))
    validate_transition(obj.status, IncidentStatus.OPEN)
    updated = await repo.update(obj, {"status": IncidentStatus.OPEN})
    return IncidentResponse.model_validate(updated)


@router.post(
    "/{incident_id}/investigate",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_investigation(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus),
    task_manager: BackgroundTaskManager = Depends(get_task_manager),
) -> dict:
    repo = IncidentRepository(db)
    obj = await repo.get(incident_id)
    if not obj:
        raise NotFoundError("Incident", str(incident_id))

    from heal_plz.services.investigation_service import InvestigationService

    service = InvestigationService(db, event_bus)
    await task_manager.submit(
        f"investigate-{incident_id}",
        service.investigate(str(incident_id)),
    )
    return {"status": "accepted", "message": "Investigation started"}


@router.post(
    "/{incident_id}/heal",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_healing(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus),
    task_manager: BackgroundTaskManager = Depends(get_task_manager),
) -> dict:
    repo = IncidentRepository(db)
    obj = await repo.get(incident_id)
    if not obj:
        raise NotFoundError("Incident", str(incident_id))
    return {"status": "accepted", "message": "Healing triggered"}
