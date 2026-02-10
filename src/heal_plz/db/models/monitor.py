import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from heal_plz.db.base import Base

if TYPE_CHECKING:
    from heal_plz.db.models.monitor_event import MonitorEvent
    from heal_plz.db.models.repository import Repository


class MonitorType(str, enum.Enum):
    GITHUB_ACTIONS = "github_actions"
    SENTRY = "sentry"
    LOCAL_CLI = "local_cli"
    LOG_STREAM = "log_stream"
    CUSTOM_WEBHOOK = "custom_webhook"


class MonitorStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    monitor_type: Mapped[MonitorType] = mapped_column(Enum(MonitorType))
    status: Mapped[MonitorStatus] = mapped_column(
        Enum(MonitorStatus), default=MonitorStatus.ACTIVE
    )
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_event_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )

    repository: Mapped["Repository"] = relationship(back_populates="monitors")
    events: Mapped[list["MonitorEvent"]] = relationship(back_populates="monitor")
