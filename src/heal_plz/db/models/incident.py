import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from heal_plz.db.base import Base

if TYPE_CHECKING:
    from heal_plz.db.models.investigation import Investigation
    from heal_plz.db.models.monitor_event import MonitorEvent
    from heal_plz.db.models.repository import Repository
    from heal_plz.db.models.resolution import Resolution
    from heal_plz.db.models.root_cause import RootCause
    from heal_plz.db.models.timeline import TimelineEntry


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ROOT_CAUSE_IDENTIFIED = "root_cause_identified"
    FIX_IN_PROGRESS = "fix_in_progress"
    FIX_PENDING_REVIEW = "fix_pending_review"
    FIX_MERGED = "fix_merged"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    CLOSED = "closed"
    WONT_FIX = "wont_fix"


class IncidentPriority(str, enum.Enum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id"), index=True
    )
    incident_number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus), default=IncidentStatus.OPEN, index=True
    )
    priority: Mapped[IncidentPriority] = mapped_column(
        Enum(IncidentPriority), default=IncidentPriority.P2
    )
    error_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    auto_heal_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="incidents")
    events: Mapped[list["MonitorEvent"]] = relationship(back_populates="incident")
    investigation: Mapped[Optional["Investigation"]] = relationship(
        back_populates="incident", uselist=False
    )
    root_causes: Mapped[list["RootCause"]] = relationship(back_populates="incident")
    resolutions: Mapped[list["Resolution"]] = relationship(back_populates="incident")
    timeline_entries: Mapped[list["TimelineEntry"]] = relationship(
        back_populates="incident"
    )
