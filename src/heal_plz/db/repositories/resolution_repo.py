import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.db.models.resolution import Resolution, ResolutionStatus
from heal_plz.db.repositories.base import BaseRepository


class ResolutionRepository(BaseRepository[Resolution]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Resolution, db)

    async def get_by_incident(
        self, incident_id: uuid.UUID
    ) -> list[Resolution]:
        result = await self.db.execute(
            select(Resolution)
            .where(Resolution.incident_id == incident_id)
            .order_by(Resolution.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_by_pr_number(
        self, pr_number: int, repository_id: uuid.UUID
    ) -> Optional[Resolution]:
        from heal_plz.db.models.incident import Incident

        result = await self.db.execute(
            select(Resolution)
            .join(Incident)
            .where(
                Resolution.pr_number == pr_number,
                Incident.repository_id == repository_id,
            )
        )
        return result.scalar_one_or_none()
