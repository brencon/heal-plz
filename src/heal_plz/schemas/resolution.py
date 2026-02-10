import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from heal_plz.db.models.resolution import ResolutionStatus, ResolutionStrategy
from heal_plz.db.models.root_cause import RootCauseCategory
from heal_plz.db.models.verification import VerificationResult, VerificationType


class RootCauseResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    category: RootCauseCategory
    description: str
    file_path: Optional[str]
    line_range_start: Optional[int]
    line_range_end: Optional[int]
    function_name: Optional[str]
    suggested_fix_description: Optional[str]
    confidence_score: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResolutionResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    root_cause_id: Optional[uuid.UUID]
    status: ResolutionStatus
    strategy: ResolutionStrategy
    fix_description: Optional[str]
    files_changed: Optional[list]
    branch_name: Optional[str]
    pr_number: Optional[int]
    pr_url: Optional[str]
    pr_state: Optional[str]
    llm_model_used: Optional[str]
    llm_tokens_used: Optional[int]
    llm_cost_usd: Optional[float]
    attempt_number: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationResponse(BaseModel):
    id: uuid.UUID
    resolution_id: uuid.UUID
    verification_type: VerificationType
    result: VerificationResult
    output: Optional[str]
    duration_seconds: Optional[float]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
