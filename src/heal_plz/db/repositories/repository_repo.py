from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.db.models.repository import Repository
from heal_plz.db.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository[Repository]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Repository, db)

    async def find_by_github(
        self, owner: str, repo: str
    ) -> Optional[Repository]:
        result = await self.db.execute(
            select(Repository).where(
                Repository.github_owner == owner,
                Repository.github_repo == repo,
            )
        )
        return result.scalar_one_or_none()
