import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from heal_plz.db.base import Base

if TYPE_CHECKING:
    from heal_plz.db.models.incident import Incident
    from heal_plz.db.models.monitor import Monitor


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    github_owner: Mapped[str] = mapped_column(String(255), index=True)
    github_repo: Mapped[str] = mapped_column(String(255), index=True)
    github_installation_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    monitors: Mapped[list["Monitor"]] = relationship(back_populates="repository")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="repository")
