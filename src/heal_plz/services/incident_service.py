import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.core.events import Event, EventBus, EventType
from heal_plz.db.models.incident import Incident, IncidentPriority, IncidentStatus
from heal_plz.db.models.monitor import Monitor
from heal_plz.db.models.monitor_event import EventSeverity, MonitorEvent
from heal_plz.db.models.timeline import TimelineEntry
from heal_plz.db.repositories.incident_repo import IncidentRepository
from heal_plz.engine.deduplicator import IncidentDeduplicator
from heal_plz.engine.normalizer import NormalizedEvent
from heal_plz.engine.state_machine import validate_transition

logger = logging.getLogger(__name__)

SEVERITY_TO_PRIORITY = {
    EventSeverity.CRITICAL: IncidentPriority.P0,
    EventSeverity.ERROR: IncidentPriority.P2,
    EventSeverity.WARNING: IncidentPriority.P3,
    EventSeverity.INFO: IncidentPriority.P4,
}


class IncidentService:
    def __init__(self, db: AsyncSession, event_bus: EventBus) -> None:
        self.db = db
        self.event_bus = event_bus
        self.repo = IncidentRepository(db)
        self.deduplicator = IncidentDeduplicator(db)

    async def process_event(
        self,
        monitor_event: MonitorEvent,
        normalized: NormalizedEvent,
        repository_id: uuid.UUID,
    ) -> Incident:
        existing = await self.deduplicator.find_existing(
            repository_id, normalized
        )

        if existing:
            return await self._update_existing(existing, monitor_event)

        return await self._create_new(
            repository_id, monitor_event, normalized
        )

    async def _create_new(
        self,
        repository_id: uuid.UUID,
        monitor_event: MonitorEvent,
        normalized: NormalizedEvent,
    ) -> Incident:
        incident_number = await self.repo.get_next_incident_number(repository_id)

        incident = Incident(
            repository_id=repository_id,
            incident_number=incident_number,
            title=normalized.title,
            description=normalized.error_message,
            status=IncidentStatus.OPEN,
            priority=SEVERITY_TO_PRIORITY.get(
                normalized.severity, IncidentPriority.P2
            ),
            error_category=normalized.error_type,
            event_count=1,
        )
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)

        monitor_event.incident_id = incident.id
        await self.db.flush()

        timeline = TimelineEntry(
            incident_id=incident.id,
            event_type="incident_created",
            title="Incident created",
            description=f"Auto-created from {normalized.source.value} event",
            actor="heal-plz",
        )
        self.db.add(timeline)
        await self.db.flush()

        await self.event_bus.publish(
            Event(
                type=EventType.INCIDENT_CREATED,
                data={
                    "incident_id": str(incident.id),
                    "repository_id": str(repository_id),
                    "incident_number": incident_number,
                },
            )
        )

        logger.info(
            "Created incident #%d: %s", incident_number, normalized.title
        )
        return incident

    async def _update_existing(
        self, incident: Incident, monitor_event: MonitorEvent
    ) -> Incident:
        incident.event_count += 1
        incident.last_seen_at = datetime.utcnow()
        monitor_event.incident_id = incident.id
        await self.db.flush()

        logger.info(
            "Updated incident #%d, event count: %d",
            incident.incident_number,
            incident.event_count,
        )
        return incident

    async def transition_status(
        self, incident_id: uuid.UUID, new_status: IncidentStatus
    ) -> Incident:
        incident = await self.repo.get(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        validate_transition(incident.status, new_status)
        old_status = incident.status
        incident.status = new_status

        if new_status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()

        await self.db.flush()

        timeline = TimelineEntry(
            incident_id=incident.id,
            event_type="status_change",
            title=f"Status changed: {old_status.value} → {new_status.value}",
            actor="heal-plz",
        )
        self.db.add(timeline)
        await self.db.flush()

        await self.event_bus.publish(
            Event(
                type=EventType.INCIDENT_UPDATED,
                data={
                    "incident_id": str(incident.id),
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                },
            )
        )

        return incident
