import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.core.events import Event, EventBus, EventType
from heal_plz.db.models.monitor import Monitor
from heal_plz.db.models.monitor_event import MonitorEvent
from heal_plz.engine.normalizer import NormalizedEvent

logger = logging.getLogger(__name__)


class MonitorService:
    def __init__(self, db: AsyncSession, event_bus: EventBus) -> None:
        self.db = db
        self.event_bus = event_bus

    async def ingest_event(
        self, monitor_id: uuid.UUID, normalized: NormalizedEvent
    ) -> MonitorEvent:
        result = await self.db.execute(
            select(Monitor).where(Monitor.id == monitor_id)
        )
        monitor = result.scalar_one_or_none()
        if monitor:
            monitor.last_event_at = datetime.utcnow()

        event = MonitorEvent(
            monitor_id=monitor_id,
            event_source=normalized.source,
            severity=normalized.severity,
            title=normalized.title,
            error_type=normalized.error_type,
            error_message=normalized.error_message,
            stacktrace=normalized.stacktrace,
            file_path=normalized.file_path,
            line_number=normalized.line_number,
            commit_sha=normalized.commit_sha,
            branch=normalized.branch,
            raw_payload=normalized.raw_payload,
            fingerprint=normalized.fingerprint,
            environment=normalized.environment,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)

        await self.event_bus.publish(
            Event(
                type=EventType.MONITOR_EVENT_RECEIVED,
                data={
                    "monitor_event_id": str(event.id),
                    "monitor_id": str(monitor_id),
                    "fingerprint": normalized.fingerprint,
                    "repository_id": str(monitor.repository_id) if monitor else None,
                },
            )
        )

        logger.info("Ingested event %s from monitor %s", event.id, monitor_id)
        return event
