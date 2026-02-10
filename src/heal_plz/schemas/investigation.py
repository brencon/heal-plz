import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from heal_plz.db.models.evidence import EvidenceType
from heal_plz.db.models.investigation import InvestigationStatus


class InvestigationResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    status: InvestigationStatus
    summary: Optional[str]
    affected_files: Optional[list]
    affected_functions: Optional[list]
    related_commits: Optional[list]
    confidence_score: Optional[float]
    duration_seconds: Optional[float]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    evidence_type: EvidenceType
    title: str
    content: str
    file_path: Optional[str]
    relevance_score: Optional[float]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
