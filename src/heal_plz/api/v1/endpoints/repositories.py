import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.api.dependencies import get_db
from heal_plz.core.exceptions import ConflictError, NotFoundError
from heal_plz.db.models.repository import Repository
from heal_plz.db.repositories.repository_repo import RepositoryRepository
from heal_plz.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
    RepositoryUpdate,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("/", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    data: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    repo = RepositoryRepository(db)
    existing = await repo.find_by_github(data.github_owner, data.github_repo)
    if existing:
        raise ConflictError(
            f"Repository {data.github_owner}/{data.github_repo} already exists"
        )
    obj = Repository(
        github_owner=data.github_owner,
        github_repo=data.github_repo,
        github_installation_id=data.github_installation_id,
        default_branch=data.default_branch,
        language=data.language,
        config=data.config,
    )
    created = await repo.create(obj)
    return RepositoryResponse.model_validate(created)


@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[RepositoryResponse]:
    repo = RepositoryRepository(db)
    results = await repo.list(offset=offset, limit=limit)
    return [RepositoryResponse.model_validate(r) for r in results]


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    repo = RepositoryRepository(db)
    obj = await repo.get(repo_id)
    if not obj:
        raise NotFoundError("Repository", str(repo_id))
    return RepositoryResponse.model_validate(obj)


@router.patch("/{repo_id}", response_model=RepositoryResponse)
async def update_repository(
    repo_id: uuid.UUID,
    data: RepositoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    repo = RepositoryRepository(db)
    obj = await repo.get(repo_id)
    if not obj:
        raise NotFoundError("Repository", str(repo_id))
    updated = await repo.update(obj, data.model_dump(exclude_unset=True))
    return RepositoryResponse.model_validate(updated)
