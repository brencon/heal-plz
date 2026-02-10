import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from heal_plz.db.models.incident import IncidentPriority, IncidentStatus


class IncidentUpdate(BaseModel):
    priority: Optional[IncidentPriority] = None
    auto_heal_enabled: Optional[bool] = None
    assigned_to: Optional[str] = None
    tags: Optional[list[str]] = None


class IncidentResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    incident_number: int
    title: str
    description: str
    status: IncidentStatus
    priority: IncidentPriority
    error_category: Optional[str]
    event_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    auto_heal_enabled: bool
    assigned_to: Optional[str]
    tags: Optional[list]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class IncidentSummary(BaseModel):
    id: uuid.UUID
    incident_number: int
    title: str
    status: IncidentStatus
    priority: IncidentPriority
    event_count: int
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)
