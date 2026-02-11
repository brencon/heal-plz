import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.db.models.incident import Incident, IncidentStatus
from heal_plz.db.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Incident, db)

    async def list_filtered(
        self,
        status: Optional[IncidentStatus] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Incident]:
        query = select(Incident)
        if status:
            query = query.where(Incident.status == status)
        query = query.order_by(Incident.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_repo(
        self,
        repository_id: uuid.UUID,
        status: Optional[IncidentStatus] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Incident]:
        query = select(Incident).where(Incident.repository_id == repository_id)
        if status:
            query = query.where(Incident.status == status)
        query = query.order_by(Incident.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_by_fingerprint(
        self, repository_id: uuid.UUID, fingerprint: str
    ) -> Optional[Incident]:
        from heal_plz.db.models.monitor_event import MonitorEvent

        query = (
            select(Incident)
            .join(MonitorEvent, MonitorEvent.incident_id == Incident.id)
            .where(
                Incident.repository_id == repository_id,
                Incident.status.notin_([IncidentStatus.CLOSED, IncidentStatus.RESOLVED]),
                MonitorEvent.fingerprint == fingerprint,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_next_incident_number(self, repository_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(Incident.incident_number), 0)).where(
                Incident.repository_id == repository_id
            )
        )
        return (result.scalar() or 0) + 1
