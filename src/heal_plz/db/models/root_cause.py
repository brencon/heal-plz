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
    from heal_plz.db.models.resolution import Resolution


class RootCauseCategory(str, enum.Enum):
    LOGIC_ERROR = "logic_error"
    TYPE_ERROR = "type_error"
    NULL_REFERENCE = "null_reference"
    DEPENDENCY_ISSUE = "dependency_issue"
    CONFIGURATION_ERROR = "configuration_error"
    RACE_CONDITION = "race_condition"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    API_MISMATCH = "api_mismatch"
    SYNTAX_ERROR = "syntax_error"
    MISSING_IMPORT = "missing_import"
    TEST_ASSERTION = "test_assertion"
    BUILD_CONFIGURATION = "build_configuration"
    LINT_VIOLATION = "lint_violation"
    OTHER = "other"


class RootCause(Base):
    __tablename__ = "root_causes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id"), index=True
    )
    category: Mapped[RootCauseCategory] = mapped_column(Enum(RootCauseCategory))
    description: Mapped[str] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    line_range_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_range_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    function_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    suggested_fix_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    council_deliberation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )

    incident: Mapped["Incident"] = relationship(back_populates="root_causes")
    resolutions: Mapped[list["Resolution"]] = relationship(back_populates="root_cause")
