import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from heal_plz.db.base import Base

if TYPE_CHECKING:
    from heal_plz.db.models.alert import Alert
    from heal_plz.db.models.incident import Incident
    from heal_plz.db.models.monitor import Monitor


class EventSeverity(str, enum.Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class EventSource(str, enum.Enum):
    GITHUB_ACTIONS = "github_actions"
    SENTRY = "sentry"
    LOCAL_CLI = "local_cli"
    WEBHOOK = "webhook"


class MonitorEvent(Base):
    __tablename__ = "monitor_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    monitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("monitors.id"), index=True
    )
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("alerts.id"), nullable=True, index=True
    )
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("incidents.id"), nullable=True, index=True
    )
    event_source: Mapped[EventSource] = mapped_column(Enum(EventSource))
    severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity), default=EventSeverity.ERROR
    )
    title: Mapped[str] = mapped_column(String(500))
    error_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text)
    stacktrace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    environment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )

    monitor: Mapped["Monitor"] = relationship(back_populates="events")
    alert: Mapped[Optional["Alert"]] = relationship(back_populates="events")
    incident: Mapped[Optional["Incident"]] = relationship(back_populates="events")
