import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from heal_plz.db.models.alert import AlertSeverity, AlertStatus


class AlertResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    incident_id: Optional[uuid.UUID]
    fingerprint: str
    title: str
    description: str
    status: AlertStatus
    severity: AlertSeverity
    error_type: Optional[str]
    source: str
    environment: Optional[str]
    file_path: Optional[str]
    occurrence_count: int
    escalation_threshold: int
    auto_escalate: bool
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertUpdate(BaseModel):
    auto_escalate: Optional[bool] = None
    suppressed_until: Optional[datetime] = None


class AlertSummary(BaseModel):
    id: uuid.UUID
    title: str
    status: AlertStatus
    severity: AlertSeverity
    occurrence_count: int
    last_seen_at: datetime
    incident_id: Optional[uuid.UUID]

    model_config = ConfigDict(from_attributes=True)
