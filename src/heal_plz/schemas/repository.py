import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RepositoryCreate(BaseModel):
    github_owner: str
    github_repo: str
    github_installation_id: Optional[int] = None
    default_branch: str = "main"
    language: Optional[str] = None
    config: Optional[dict] = None


class RepositoryUpdate(BaseModel):
    default_branch: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[dict] = None


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    github_owner: str
    github_repo: str
    github_installation_id: Optional[int]
    default_branch: str
    language: Optional[str]
    is_active: bool
    config: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
