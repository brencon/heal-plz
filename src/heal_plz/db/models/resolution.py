import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from heal_plz.db.base import Base

if TYPE_CHECKING:
    from heal_plz.db.models.incident import Incident
    from heal_plz.db.models.root_cause import RootCause
    from heal_plz.db.models.verification import Verification


class ResolutionStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING_FIX = "generating_fix"
    FIX_GENERATED = "fix_generated"
    PR_CREATED = "pr_created"
    PR_REVIEW = "pr_review"
    PR_APPROVED = "pr_approved"
    PR_MERGED = "pr_merged"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class ResolutionStrategy(str, enum.Enum):
    AUTO_FIX = "auto_fix"
    SUGGEST_FIX = "suggest_fix"
    MANUAL = "manual"
    ROLLBACK = "rollback"


class Resolution(Base):
    __tablename__ = "resolutions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id"), index=True
    )
    root_cause_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("root_causes.id"), nullable=True
    )
    status: Mapped[ResolutionStatus] = mapped_column(
        Enum(ResolutionStatus), default=ResolutionStatus.PENDING
    )
    strategy: Mapped[ResolutionStrategy] = mapped_column(
        Enum(ResolutionStrategy), default=ResolutionStrategy.SUGGEST_FIX
    )
    fix_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    files_changed: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    branch_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pr_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    llm_model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    llm_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    incident: Mapped["Incident"] = relationship(back_populates="resolutions")
    root_cause: Mapped[Optional["RootCause"]] = relationship(
        back_populates="resolutions"
    )
    verifications: Mapped[list["Verification"]] = relationship(
        back_populates="resolution"
    )
