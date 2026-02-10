import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from heal_plz.db.base import Base

if TYPE_CHECKING:
    from heal_plz.db.models.evidence import Evidence
    from heal_plz.db.models.incident import Incident


class InvestigationStatus(str, enum.Enum):
    PENDING = "pending"
    GATHERING_CONTEXT = "gathering_context"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id"), unique=True, index=True
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus), default=InvestigationStatus.PENDING
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affected_files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    affected_functions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    related_commits: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    code_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    dependency_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    llm_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )

    incident: Mapped["Incident"] = relationship(back_populates="investigation")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="investigation")
