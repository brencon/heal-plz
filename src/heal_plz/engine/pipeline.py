import logging

from heal_plz.core.events import Event, EventBus, EventType
from heal_plz.core.tasks import BackgroundTaskManager
from heal_plz.db.session import create_session_factory

logger = logging.getLogger(__name__)


class HealingPipeline:
    def __init__(
        self,
        event_bus: EventBus,
        task_manager: BackgroundTaskManager,
        session_factory,
    ) -> None:
        self.event_bus = event_bus
        self.tasks = task_manager
        self.session_factory = session_factory

        event_bus.subscribe(EventType.INCIDENT_CREATED, self._on_incident_created)
        event_bus.subscribe(
            EventType.INVESTIGATION_COMPLETED, self._on_investigation_completed
        )
        event_bus.subscribe(EventType.RCA_COMPLETED, self._on_rca_completed)

    async def _on_incident_created(self, event: Event) -> None:
        incident_id = event.data.get("incident_id")
        if not incident_id:
            return

        logger.info("Pipeline: incident created %s, starting investigation", incident_id)

        async def _investigate():
            async with self.session_factory() as db:
                try:
                    from heal_plz.services.investigation_service import InvestigationService
                    service = InvestigationService(db, self.event_bus)
                    await service.investigate(incident_id)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    logger.exception("Investigation failed for %s", incident_id)

        await self.tasks.submit(
            f"investigate-{incident_id}", _investigate()
        )

    async def _on_investigation_completed(self, event: Event) -> None:
        incident_id = event.data.get("incident_id")
        if not incident_id:
            return

        logger.info("Pipeline: investigation complete for %s, starting RCA", incident_id)

        async def _rca():
            async with self.session_factory() as db:
                try:
                    from heal_plz.services.rca_service import RCAService
                    service = RCAService(db, self.event_bus)
                    await service.analyze(incident_id)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    logger.exception("RCA failed for %s", incident_id)

        await self.tasks.submit(f"rca-{incident_id}", _rca())

    async def _on_rca_completed(self, event: Event) -> None:
        incident_id = event.data.get("incident_id")
        root_cause_id = event.data.get("root_cause_id")
        if not incident_id or not root_cause_id:
            return

        logger.info(
            "Pipeline: RCA complete for %s, generating fix", incident_id
        )

        async def _heal():
            async with self.session_factory() as db:
                try:
                    from heal_plz.services.healing_service import HealingService
                    service = HealingService(db, self.event_bus)
                    await service.generate_fix(incident_id, root_cause_id)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    logger.exception("Healing failed for %s", incident_id)

        await self.tasks.submit(f"heal-{incident_id}", _heal())
