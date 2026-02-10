import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from heal_plz.db.base import Base

if TYPE_CHECKING:
    from heal_plz.db.models.investigation import Investigation


class EvidenceType(str, enum.Enum):
    STACKTRACE = "stacktrace"
    LOG_SNIPPET = "log_snippet"
    CODE_SNIPPET = "code_snippet"
    TEST_OUTPUT = "test_output"
    BUILD_LOG = "build_log"
    GIT_DIFF = "git_diff"
    GIT_BLAME = "git_blame"
    DEPENDENCY_INFO = "dependency_info"
    CONFIG_FILE = "config_file"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id"), index=True
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(Enum(EvidenceType))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )

    investigation: Mapped["Investigation"] = relationship(back_populates="evidence")
