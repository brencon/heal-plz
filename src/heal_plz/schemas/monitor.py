import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from heal_plz.db.models.monitor import MonitorStatus, MonitorType


class MonitorCreate(BaseModel):
    name: str
    monitor_type: MonitorType
    config: Optional[dict] = None


class MonitorUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[MonitorStatus] = None
    config: Optional[dict] = None


class MonitorResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    name: str
    monitor_type: MonitorType
    status: MonitorStatus
    config: Optional[dict]
    last_event_at: Optional[datetime]
    error_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonitorEventResponse(BaseModel):
    id: uuid.UUID
    monitor_id: uuid.UUID
    alert_id: Optional[uuid.UUID]
    incident_id: Optional[uuid.UUID]
    event_source: str
    severity: str
    title: str
    error_type: Optional[str]
    error_message: str
    file_path: Optional[str]
    line_number: Optional[int]
    branch: Optional[str]
    commit_sha: Optional[str]
    fingerprint: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
