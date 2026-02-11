import json
import logging
import time
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from heal_plz.config import settings
from heal_plz.core.events import Event, EventBus, EventType
from heal_plz.db.models.evidence import Evidence, EvidenceType
from heal_plz.db.models.incident import Incident, IncidentStatus
from heal_plz.db.models.investigation import Investigation, InvestigationStatus
from heal_plz.db.models.monitor_event import MonitorEvent
from heal_plz.engine.code_context import CodeContext, CodeContextBuilder
from heal_plz.integrations.github.client import GitHubClient
from heal_plz.integrations.llm.prompts import INVESTIGATION_PROMPT
from heal_plz.services.incident_service import IncidentService

logger = logging.getLogger(__name__)


class InvestigationService:
    def __init__(self, db: AsyncSession, event_bus: EventBus) -> None:
        self.db = db
        self.event_bus = event_bus

    async def investigate(self, incident_id: str) -> Investigation:
        import uuid as _uuid

        inc_id = _uuid.UUID(incident_id)
        result = await self.db.execute(
            select(Incident)
            .where(Incident.id == inc_id)
            .options(selectinload(Incident.repository))
        )
        incident = result.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        incident_service = IncidentService(self.db, self.event_bus)
        await incident_service.transition_status(inc_id, IncidentStatus.INVESTIGATING)

        investigation = Investigation(
            incident_id=inc_id,
            status=InvestigationStatus.GATHERING_CONTEXT,
            started_at=datetime.utcnow(),
        )
        self.db.add(investigation)
        await self.db.flush()
        await self.db.refresh(investigation)

        start_time = time.time()

        events_result = await self.db.execute(
            select(MonitorEvent)
            .where(MonitorEvent.incident_id == inc_id)
            .order_by(MonitorEvent.created_at.desc())
            .limit(1)
        )
        latest_event = events_result.scalar_one_or_none()

        if latest_event and latest_event.stacktrace:
            evidence = Evidence(
                investigation_id=investigation.id,
                evidence_type=EvidenceType.STACKTRACE,
                title="Error stacktrace",
                content=latest_event.stacktrace,
                file_path=latest_event.file_path,
                relevance_score=1.0,
            )
            self.db.add(evidence)

        repo = incident.repository
        code_context: Optional[CodeContext] = None

        if repo and settings.GITHUB_TOKEN:
            try:
                github = GitHubClient(settings.GITHUB_TOKEN)
                builder = CodeContextBuilder(github)
                code_context = await builder.build(
                    owner=repo.github_owner,
                    repo=repo.github_repo,
                    stacktrace=latest_event.stacktrace if latest_event else None,
                    file_path=latest_event.file_path if latest_event else None,
                    line_number=latest_event.line_number if latest_event else None,
                    commit_sha=latest_event.commit_sha if latest_event else None,
                )

                for path, file_ctx in code_context.files.items():
                    ev = Evidence(
                        investigation_id=investigation.id,
                        evidence_type=EvidenceType.CODE_SNIPPET,
                        title=f"Source: {path}",
                        content=file_ctx.content[:5000],
                        file_path=path,
                        relevance_score=0.8,
                    )
                    self.db.add(ev)

                for path, file_ctx in code_context.test_files.items():
                    ev = Evidence(
                        investigation_id=investigation.id,
                        evidence_type=EvidenceType.TEST_OUTPUT,
                        title=f"Test: {path}",
                        content=file_ctx.content[:5000],
                        file_path=path,
                        relevance_score=0.6,
                    )
                    self.db.add(ev)

            except Exception:
                logger.exception("Failed to build code context for %s", incident_id)

        investigation.status = InvestigationStatus.ANALYZING

        llm_result = await self._run_llm_analysis(
            incident, latest_event, code_context
        )

        if llm_result:
            investigation.llm_analysis = llm_result
            investigation.summary = llm_result.get("immediate_cause", "")
            investigation.affected_files = llm_result.get("affected_files", [])
            investigation.affected_functions = llm_result.get("affected_functions", [])
            investigation.confidence_score = llm_result.get("confidence", 0.0)

        duration = time.time() - start_time
        investigation.status = InvestigationStatus.COMPLETE
        investigation.completed_at = datetime.utcnow()
        investigation.duration_seconds = duration

        await self.db.flush()

        await self.event_bus.publish(
            Event(
                type=EventType.INVESTIGATION_COMPLETED,
                data={
                    "incident_id": incident_id,
                    "investigation_id": str(investigation.id),
                    "confidence": investigation.confidence_score,
                },
            )
        )

        logger.info(
            "Investigation complete for incident %s (%.1fs, confidence=%.2f)",
            incident_id,
            duration,
            investigation.confidence_score or 0,
        )
        return investigation

    async def _run_llm_analysis(
        self,
        incident: Incident,
        event: Optional[MonitorEvent],
        code_context: Optional[CodeContext],
    ) -> Optional[dict]:
        if not settings.ANTHROPIC_API_KEY:
            return None

        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

            prompt = INVESTIGATION_PROMPT.format(
                error_type=event.error_type if event else "Unknown",
                error_message=event.error_message if event else incident.description,
                file_path=event.file_path if event else "Unknown",
                line_number=event.line_number if event else "Unknown",
                environment=event.environment if event else "Unknown",
                stacktrace=event.stacktrace if event and event.stacktrace else "Not available",
                code_context=code_context.to_prompt_context() if code_context else "Not available",
            )

            response = await client.messages.create(
                model=settings.PRIMARY_LLM_MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text
            json_match = text
            if "```json" in text:
                json_match = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                json_match = text.split("```")[1].split("```")[0]

            return json.loads(json_match.strip())

        except Exception:
            logger.exception("LLM analysis failed")
            return None
