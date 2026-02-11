import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.api.dependencies import get_db, get_event_bus, get_session_factory, get_task_manager
from heal_plz.core.events import EventBus
from heal_plz.core.exceptions import NotFoundError
from heal_plz.core.tasks import BackgroundTaskManager
from heal_plz.db.models.evidence import Evidence
from heal_plz.db.models.incident import IncidentStatus
from heal_plz.db.models.investigation import Investigation
from heal_plz.db.models.resolution import Resolution
from heal_plz.db.models.root_cause import RootCause
from heal_plz.db.models.verification import Verification
from heal_plz.db.repositories.incident_repo import IncidentRepository
from heal_plz.engine.state_machine import validate_transition
from heal_plz.schemas.incident import (
    IncidentPipelineResponse,
    IncidentResponse,
    IncidentUpdate,
)
from heal_plz.schemas.investigation import EvidenceResponse, InvestigationResponse
from heal_plz.schemas.resolution import (
    ResolutionResponse,
    RootCauseResponse,
    VerificationResponse,
)

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
        results = await repo.list_filtered(
            status=status_filter, offset=offset, limit=limit
        )
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


@router.get("/{incident_id}/pipeline", response_model=IncidentPipelineResponse)
async def get_incident_pipeline(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IncidentPipelineResponse:
    repo = IncidentRepository(db)
    incident = await repo.get(incident_id)
    if not incident:
        raise NotFoundError("Incident", str(incident_id))

    investigation_result = await db.execute(
        select(Investigation).where(Investigation.incident_id == incident_id)
    )
    investigation = investigation_result.scalar_one_or_none()

    evidence_list: list[EvidenceResponse] = []
    if investigation:
        evidence_result = await db.execute(
            select(Evidence)
            .where(Evidence.investigation_id == investigation.id)
            .order_by(Evidence.created_at)
        )
        evidence_list = [
            EvidenceResponse.model_validate(e) for e in evidence_result.scalars().all()
        ]

    rca_result = await db.execute(
        select(RootCause)
        .where(RootCause.incident_id == incident_id)
        .order_by(RootCause.created_at.desc())
    )
    root_causes = [
        RootCauseResponse.model_validate(r) for r in rca_result.scalars().all()
    ]

    res_result = await db.execute(
        select(Resolution)
        .where(Resolution.incident_id == incident_id)
        .order_by(Resolution.created_at.desc())
    )
    resolutions_raw = res_result.scalars().all()
    resolutions = [ResolutionResponse.model_validate(r) for r in resolutions_raw]

    verifications: list[VerificationResponse] = []
    if resolutions_raw:
        res_ids = [r.id for r in resolutions_raw]
        ver_result = await db.execute(
            select(Verification)
            .where(Verification.resolution_id.in_(res_ids))
            .order_by(Verification.created_at)
        )
        verifications = [
            VerificationResponse.model_validate(v)
            for v in ver_result.scalars().all()
        ]

    return IncidentPipelineResponse(
        incident=IncidentResponse.model_validate(incident),
        investigation=(
            InvestigationResponse.model_validate(investigation)
            if investigation
            else None
        ),
        evidence=evidence_list,
        root_causes=root_causes,
        resolutions=resolutions,
        verifications=verifications,
    )


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
    session_factory=Depends(get_session_factory),
) -> dict:
    repo = IncidentRepository(db)
    obj = await repo.get(incident_id)
    if not obj:
        raise NotFoundError("Incident", str(incident_id))

    async def _investigate():
        from heal_plz.services.investigation_service import InvestigationService

        async with session_factory() as bg_db:
            try:
                service = InvestigationService(bg_db, event_bus)
                await service.investigate(str(incident_id))
                await bg_db.commit()
            except Exception:
                await bg_db.rollback()
                raise

    await task_manager.submit(
        f"investigate-{incident_id}", _investigate()
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
    session_factory=Depends(get_session_factory),
) -> dict:
    repo = IncidentRepository(db)
    obj = await repo.get(incident_id)
    if not obj:
        raise NotFoundError("Incident", str(incident_id))

    # Find the latest root cause for this incident
    rca_result = await db.execute(
        select(RootCause)
        .where(RootCause.incident_id == incident_id)
        .order_by(RootCause.created_at.desc())
        .limit(1)
    )
    root_cause = rca_result.scalar_one_or_none()
    root_cause_id = str(root_cause.id) if root_cause else None

    async def _heal():
        from heal_plz.services.healing_service import HealingService

        async with session_factory() as bg_db:
            try:
                service = HealingService(bg_db, event_bus)
                await service.generate_fix(str(incident_id), root_cause_id)
                await bg_db.commit()
            except Exception:
                await bg_db.rollback()
                raise

    await task_manager.submit(
        f"heal-{incident_id}", _heal()
    )
    return {"status": "accepted", "message": "Healing started"}
