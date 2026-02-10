import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.core.events import Event, EventBus, EventType
from heal_plz.db.models.alert import Alert, AlertSeverity, AlertStatus
from heal_plz.db.models.incident import Incident, IncidentPriority, IncidentStatus
from heal_plz.db.models.monitor_event import EventSeverity, MonitorEvent
from heal_plz.db.models.timeline import TimelineEntry
from heal_plz.db.repositories.incident_repo import IncidentRepository
from heal_plz.engine.normalizer import NormalizedEvent

logger = logging.getLogger(__name__)

EVENT_TO_ALERT_SEVERITY = {
    EventSeverity.CRITICAL: AlertSeverity.CRITICAL,
    EventSeverity.ERROR: AlertSeverity.HIGH,
    EventSeverity.WARNING: AlertSeverity.MEDIUM,
    EventSeverity.INFO: AlertSeverity.INFO,
}

ALERT_TO_INCIDENT_PRIORITY = {
    AlertSeverity.CRITICAL: IncidentPriority.P0,
    AlertSeverity.HIGH: IncidentPriority.P1,
    AlertSeverity.MEDIUM: IncidentPriority.P2,
    AlertSeverity.LOW: IncidentPriority.P3,
    AlertSeverity.INFO: IncidentPriority.P4,
}

ESCALATION_RULES = {
    AlertSeverity.CRITICAL: 1,
    AlertSeverity.HIGH: 1,
    AlertSeverity.MEDIUM: 3,
    AlertSeverity.LOW: 5,
    AlertSeverity.INFO: 10,
}


class AlertService:
    def __init__(self, db: AsyncSession, event_bus: EventBus) -> None:
        self.db = db
        self.event_bus = event_bus

    async def process_event(
        self,
        monitor_event: MonitorEvent,
        normalized: NormalizedEvent,
        repository_id: uuid.UUID,
    ) -> Alert:
        existing = await self._find_existing_alert(
            repository_id, normalized.fingerprint
        )

        if existing:
            alert = await self._update_alert(existing, monitor_event)
        else:
            alert = await self._create_alert(
                repository_id, monitor_event, normalized
            )

        should_escalate = self._should_escalate(alert)

        if should_escalate and not alert.incident_id:
            incident = await self._escalate_to_incident(alert, normalized)
            logger.info(
                "Alert %s escalated to incident #%d",
                alert.id,
                incident.incident_number,
            )

        return alert

    async def _find_existing_alert(
        self, repository_id: uuid.UUID, fingerprint: str
    ) -> Optional[Alert]:
        result = await self.db.execute(
            select(Alert).where(
                Alert.repository_id == repository_id,
                Alert.fingerprint == fingerprint,
                Alert.status.in_([
                    AlertStatus.ACTIVE,
                    AlertStatus.ACKNOWLEDGED,
                    AlertStatus.ESCALATED,
                    AlertStatus.SUPPRESSED,
                ]),
            )
        )
        return result.scalar_one_or_none()

    async def _create_alert(
        self,
        repository_id: uuid.UUID,
        monitor_event: MonitorEvent,
        normalized: NormalizedEvent,
    ) -> Alert:
        severity = EVENT_TO_ALERT_SEVERITY.get(
            normalized.severity, AlertSeverity.MEDIUM
        )

        alert = Alert(
            repository_id=repository_id,
            fingerprint=normalized.fingerprint,
            title=normalized.title,
            description=normalized.error_message,
            severity=severity,
            error_type=normalized.error_type,
            source=normalized.source.value,
            environment=normalized.environment,
            file_path=normalized.file_path,
            occurrence_count=1,
            escalation_threshold=ESCALATION_RULES.get(severity, 3),
        )
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)

        monitor_event.alert_id = alert.id
        await self.db.flush()

        logger.info(
            "Created alert %s: %s (severity=%s, threshold=%d)",
            alert.id,
            normalized.title,
            severity.value,
            alert.escalation_threshold,
        )
        return alert

    async def _update_alert(
        self, alert: Alert, monitor_event: MonitorEvent
    ) -> Alert:
        alert.occurrence_count += 1
        alert.last_seen_at = datetime.utcnow()
        monitor_event.alert_id = alert.id
        await self.db.flush()

        logger.info(
            "Updated alert %s, occurrence_count=%d",
            alert.id,
            alert.occurrence_count,
        )
        return alert

    def _should_escalate(self, alert: Alert) -> bool:
        if alert.status == AlertStatus.SUPPRESSED:
            return False
        if alert.suppressed_until and alert.suppressed_until > datetime.utcnow():
            return False
        if not alert.auto_escalate:
            return False
        return alert.occurrence_count >= alert.escalation_threshold

    async def _escalate_to_incident(
        self, alert: Alert, normalized: NormalizedEvent
    ) -> Incident:
        alert.status = AlertStatus.ESCALATED

        repo = IncidentRepository(self.db)
        incident_number = await repo.get_next_incident_number(alert.repository_id)

        priority = ALERT_TO_INCIDENT_PRIORITY.get(
            alert.severity, IncidentPriority.P2
        )

        incident = Incident(
            repository_id=alert.repository_id,
            incident_number=incident_number,
            title=alert.title,
            description=alert.description,
            status=IncidentStatus.OPEN,
            priority=priority,
            error_category=alert.error_type,
            event_count=alert.occurrence_count,
            first_seen_at=alert.first_seen_at,
            last_seen_at=alert.last_seen_at,
        )
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)

        alert.incident_id = incident.id

        result = await self.db.execute(
            select(MonitorEvent).where(MonitorEvent.alert_id == alert.id)
        )
        events = result.scalars().all()
        for event in events:
            event.incident_id = incident.id

        timeline = TimelineEntry(
            incident_id=incident.id,
            event_type="incident_created",
            title="Incident created from alert escalation",
            description=(
                f"Alert {alert.id} escalated after {alert.occurrence_count} "
                f"occurrences (threshold: {alert.escalation_threshold})"
            ),
            metadata_={
                "alert_id": str(alert.id),
                "severity": alert.severity.value,
                "occurrence_count": alert.occurrence_count,
            },
            actor="heal-plz",
        )
        self.db.add(timeline)
        await self.db.flush()

        await self.event_bus.publish(
            Event(
                type=EventType.INCIDENT_CREATED,
                data={
                    "incident_id": str(incident.id),
                    "repository_id": str(alert.repository_id),
                    "incident_number": incident_number,
                    "alert_id": str(alert.id),
                },
            )
        )

        return incident
