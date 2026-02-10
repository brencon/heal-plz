import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.api.dependencies import get_db
from heal_plz.core.exceptions import NotFoundError
from heal_plz.db.models.monitor import Monitor
from heal_plz.db.models.monitor_event import MonitorEvent
from heal_plz.db.models.repository import Repository
from heal_plz.schemas.monitor import (
    MonitorCreate,
    MonitorEventResponse,
    MonitorResponse,
    MonitorUpdate,
)

router = APIRouter(tags=["monitors"])


@router.get(
    "/monitors/",
    response_model=list[MonitorResponse],
)
async def list_all_monitors(
    db: AsyncSession = Depends(get_db),
) -> list[MonitorResponse]:
    result = await db.execute(select(Monitor).order_by(Monitor.created_at.desc()))
    monitors = result.scalars().all()
    return [MonitorResponse.model_validate(m) for m in monitors]


@router.get("/monitors/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    monitor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MonitorResponse:
    result = await db.execute(select(Monitor).where(Monitor.id == monitor_id))
    monitor = result.scalar_one_or_none()
    if not monitor:
        raise NotFoundError("Monitor", str(monitor_id))
    return MonitorResponse.model_validate(monitor)


@router.get(
    "/monitors/{monitor_id}/events",
    response_model=list[MonitorEventResponse],
)
async def list_monitor_events(
    monitor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None),
) -> list[MonitorEventResponse]:
    result = await db.execute(select(Monitor).where(Monitor.id == monitor_id))
    if not result.scalar_one_or_none():
        raise NotFoundError("Monitor", str(monitor_id))

    query = (
        select(MonitorEvent)
        .where(MonitorEvent.monitor_id == monitor_id)
        .order_by(MonitorEvent.created_at.desc())
        .limit(limit)
    )
    if severity:
        query = query.where(MonitorEvent.severity == severity)

    result = await db.execute(query)
    events = result.scalars().all()
    return [MonitorEventResponse.model_validate(e) for e in events]


@router.post(
    "/repositories/{repo_id}/monitors",
    response_model=MonitorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_monitor(
    repo_id: uuid.UUID,
    data: MonitorCreate,
    db: AsyncSession = Depends(get_db),
) -> MonitorResponse:
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = result.scalar_one_or_none()
    if not repository:
        raise NotFoundError("Repository", str(repo_id))

    monitor = Monitor(
        repository_id=repo_id,
        name=data.name,
        monitor_type=data.monitor_type,
        config=data.config,
    )
    db.add(monitor)
    await db.flush()
    await db.refresh(monitor)
    return MonitorResponse.model_validate(monitor)


@router.get(
    "/repositories/{repo_id}/monitors",
    response_model=list[MonitorResponse],
)
async def list_monitors(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[MonitorResponse]:
    result = await db.execute(
        select(Monitor).where(Monitor.repository_id == repo_id)
    )
    monitors = result.scalars().all()
    return [MonitorResponse.model_validate(m) for m in monitors]


@router.patch("/monitors/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: uuid.UUID,
    data: MonitorUpdate,
    db: AsyncSession = Depends(get_db),
) -> MonitorResponse:
    result = await db.execute(select(Monitor).where(Monitor.id == monitor_id))
    monitor = result.scalar_one_or_none()
    if not monitor:
        raise NotFoundError("Monitor", str(monitor_id))

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(monitor, key, value)
    await db.flush()
    await db.refresh(monitor)
    return MonitorResponse.model_validate(monitor)
