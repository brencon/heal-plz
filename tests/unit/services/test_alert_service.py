import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from heal_plz.core.events import EventBus
from heal_plz.db.base import Base
from heal_plz.db.models import *  # noqa: F401, F403
from heal_plz.db.models.alert import Alert, AlertSeverity, AlertStatus
from heal_plz.db.models.incident import Incident
from heal_plz.db.models.monitor import Monitor, MonitorType
from heal_plz.db.models.monitor_event import EventSeverity, EventSource, MonitorEvent
from heal_plz.db.models.repository import Repository
from heal_plz.engine.normalizer import NormalizedEvent
from heal_plz.services.alert_service import AlertService


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def repo_and_monitor(db: AsyncSession):
    repository = Repository(
        github_owner="owner", github_repo="test-repo", default_branch="main"
    )
    db.add(repository)
    await db.flush()
    await db.refresh(repository)

    monitor = Monitor(
        repository_id=repository.id,
        name="CI Monitor",
        monitor_type=MonitorType.GITHUB_ACTIONS,
    )
    db.add(monitor)
    await db.flush()
    await db.refresh(monitor)
    return repository, monitor


def _make_normalized(severity: EventSeverity, title: str = "Test error") -> NormalizedEvent:
    return NormalizedEvent(
        source=EventSource.GITHUB_ACTIONS,
        severity=severity,
        title=title,
        error_message=f"Error: {title}",
        error_type="TestError",
        environment="ci",
    )


async def _create_monitor_event(
    db: AsyncSession, monitor_id: uuid.UUID, normalized: NormalizedEvent
) -> MonitorEvent:
    event = MonitorEvent(
        monitor_id=monitor_id,
        event_source=normalized.source,
        severity=normalized.severity,
        title=normalized.title,
        error_type=normalized.error_type,
        error_message=normalized.error_message,
        raw_payload={},
        fingerprint=normalized.fingerprint,
        environment=normalized.environment,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@pytest.mark.asyncio
async def test_high_severity_escalates_on_first_occurrence(db, repo_and_monitor):
    """HIGH severity → threshold=1 → immediate escalation."""
    repository, monitor = repo_and_monitor
    event_bus = EventBus()
    service = AlertService(db, event_bus)

    normalized = _make_normalized(EventSeverity.ERROR)
    monitor_event = await _create_monitor_event(db, monitor.id, normalized)

    alert = await service.process_event(monitor_event, normalized, repository.id)

    assert alert.status == AlertStatus.ESCALATED
    assert alert.occurrence_count == 1
    assert alert.incident_id is not None


@pytest.mark.asyncio
async def test_medium_severity_does_not_escalate_immediately(db, repo_and_monitor):
    """WARNING → MEDIUM severity → threshold=3 → no escalation on first event."""
    repository, monitor = repo_and_monitor
    event_bus = EventBus()
    service = AlertService(db, event_bus)

    normalized = _make_normalized(EventSeverity.WARNING)
    monitor_event = await _create_monitor_event(db, monitor.id, normalized)

    alert = await service.process_event(monitor_event, normalized, repository.id)

    assert alert.status == AlertStatus.ACTIVE
    assert alert.occurrence_count == 1
    assert alert.incident_id is None


@pytest.mark.asyncio
async def test_medium_severity_escalates_after_threshold(db, repo_and_monitor):
    """WARNING → MEDIUM severity → threshold=3 → escalates on 3rd occurrence."""
    repository, monitor = repo_and_monitor
    event_bus = EventBus()
    service = AlertService(db, event_bus)

    normalized = _make_normalized(EventSeverity.WARNING)

    for i in range(3):
        monitor_event = await _create_monitor_event(db, monitor.id, normalized)
        alert = await service.process_event(monitor_event, normalized, repository.id)

    assert alert.status == AlertStatus.ESCALATED
    assert alert.occurrence_count == 3
    assert alert.incident_id is not None

    result = await db.execute(select(Incident).where(Incident.id == alert.incident_id))
    incident = result.scalar_one()
    assert incident.event_count == 3


@pytest.mark.asyncio
async def test_info_severity_requires_10_occurrences(db, repo_and_monitor):
    """INFO severity → threshold=10 → no escalation before 10 events."""
    repository, monitor = repo_and_monitor
    event_bus = EventBus()
    service = AlertService(db, event_bus)

    normalized = _make_normalized(EventSeverity.INFO)

    for i in range(9):
        monitor_event = await _create_monitor_event(db, monitor.id, normalized)
        alert = await service.process_event(monitor_event, normalized, repository.id)

    assert alert.status == AlertStatus.ACTIVE
    assert alert.occurrence_count == 9
    assert alert.incident_id is None

    monitor_event = await _create_monitor_event(db, monitor.id, normalized)
    alert = await service.process_event(monitor_event, normalized, repository.id)

    assert alert.status == AlertStatus.ESCALATED
    assert alert.occurrence_count == 10
    assert alert.incident_id is not None


@pytest.mark.asyncio
async def test_suppressed_alert_does_not_escalate(db, repo_and_monitor):
    """Suppressed alerts never escalate regardless of occurrence count."""
    repository, monitor = repo_and_monitor
    event_bus = EventBus()
    service = AlertService(db, event_bus)

    normalized = _make_normalized(EventSeverity.WARNING, title="Suppression test")
    me1 = await _create_monitor_event(db, monitor.id, normalized)
    alert = await service.process_event(me1, normalized, repository.id)

    assert alert.status == AlertStatus.ACTIVE
    assert alert.incident_id is None

    alert.status = AlertStatus.SUPPRESSED
    await db.flush()

    me2 = await _create_monitor_event(db, monitor.id, normalized)
    alert = await service.process_event(me2, normalized, repository.id)

    assert alert.status == AlertStatus.SUPPRESSED
    assert alert.occurrence_count == 2
    assert alert.incident_id is None

    me3 = await _create_monitor_event(db, monitor.id, normalized)
    alert = await service.process_event(me3, normalized, repository.id)

    assert alert.status == AlertStatus.SUPPRESSED
    assert alert.occurrence_count == 3
    assert alert.incident_id is None


@pytest.mark.asyncio
async def test_auto_escalate_false_prevents_escalation(db, repo_and_monitor):
    """auto_escalate=False prevents escalation even when threshold is reached."""
    repository, monitor = repo_and_monitor
    event_bus = EventBus()
    service = AlertService(db, event_bus)

    normalized = _make_normalized(EventSeverity.WARNING, title="No-auto test")
    me1 = await _create_monitor_event(db, monitor.id, normalized)
    alert = await service.process_event(me1, normalized, repository.id)

    alert.auto_escalate = False
    await db.flush()

    for _ in range(5):
        me = await _create_monitor_event(db, monitor.id, normalized)
        alert = await service.process_event(me, normalized, repository.id)

    assert alert.occurrence_count == 6
    assert alert.incident_id is None


@pytest.mark.asyncio
async def test_deduplication_by_fingerprint(db, repo_and_monitor):
    """Same fingerprint groups into the same alert."""
    repository, monitor = repo_and_monitor
    event_bus = EventBus()
    service = AlertService(db, event_bus)

    normalized = _make_normalized(EventSeverity.WARNING)
    me1 = await _create_monitor_event(db, monitor.id, normalized)
    alert1 = await service.process_event(me1, normalized, repository.id)

    me2 = await _create_monitor_event(db, monitor.id, normalized)
    alert2 = await service.process_event(me2, normalized, repository.id)

    assert alert1.id == alert2.id
    assert alert2.occurrence_count == 2


@pytest.mark.asyncio
async def test_different_fingerprints_create_separate_alerts(db, repo_and_monitor):
    """Different fingerprints create separate alerts."""
    repository, monitor = repo_and_monitor
    event_bus = EventBus()
    service = AlertService(db, event_bus)

    norm1 = _make_normalized(EventSeverity.WARNING, title="Error A")
    me1 = await _create_monitor_event(db, monitor.id, norm1)
    alert1 = await service.process_event(me1, norm1, repository.id)

    norm2 = _make_normalized(EventSeverity.WARNING, title="Error B")
    me2 = await _create_monitor_event(db, monitor.id, norm2)
    alert2 = await service.process_event(me2, norm2, repository.id)

    assert alert1.id != alert2.id
    assert alert1.occurrence_count == 1
    assert alert2.occurrence_count == 1
