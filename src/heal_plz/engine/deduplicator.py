import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.db.models.incident import Incident
from heal_plz.db.repositories.incident_repo import IncidentRepository
from heal_plz.engine.normalizer import NormalizedEvent


class IncidentDeduplicator:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IncidentRepository(db)

    async def find_existing(
        self, repository_id: uuid.UUID, event: NormalizedEvent
    ) -> Optional[Incident]:
        return await self.repo.find_by_fingerprint(
            repository_id, event.fingerprint
        )
