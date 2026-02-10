import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.config import settings
from heal_plz.core.events import Event, EventBus, EventType
from heal_plz.db.models.incident import Incident, IncidentStatus
from heal_plz.db.models.investigation import Investigation
from heal_plz.db.models.root_cause import RootCause, RootCauseCategory
from heal_plz.integrations.llm.council import council_wrapper
from heal_plz.integrations.llm.prompts import RCA_COUNCIL_PROMPT
from heal_plz.services.incident_service import IncidentService

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "logic_error": RootCauseCategory.LOGIC_ERROR,
    "type_error": RootCauseCategory.TYPE_ERROR,
    "null_reference": RootCauseCategory.NULL_REFERENCE,
    "dependency_issue": RootCauseCategory.DEPENDENCY_ISSUE,
    "configuration_error": RootCauseCategory.CONFIGURATION_ERROR,
    "race_condition": RootCauseCategory.RACE_CONDITION,
    "resource_exhaustion": RootCauseCategory.RESOURCE_EXHAUSTION,
    "api_mismatch": RootCauseCategory.API_MISMATCH,
    "syntax_error": RootCauseCategory.SYNTAX_ERROR,
    "missing_import": RootCauseCategory.MISSING_IMPORT,
    "test_assertion": RootCauseCategory.TEST_ASSERTION,
    "build_configuration": RootCauseCategory.BUILD_CONFIGURATION,
    "lint_violation": RootCauseCategory.LINT_VIOLATION,
}


class RCAService:
    def __init__(self, db: AsyncSession, event_bus: EventBus) -> None:
        self.db = db
        self.event_bus = event_bus

    async def analyze(self, incident_id: str) -> RootCause:
        import uuid as _uuid

        inc_id = _uuid.UUID(incident_id)

        result = await self.db.execute(
            select(Investigation).where(Investigation.incident_id == inc_id)
        )
        investigation = result.scalar_one_or_none()
        if not investigation:
            raise ValueError(f"No investigation found for incident {incident_id}")

        llm_analysis = investigation.llm_analysis or {}
        confidence = llm_analysis.get("confidence", 0.0)

        if confidence >= settings.COUNCIL_CONFIDENCE_THRESHOLD:
            root_cause = self._create_from_analysis(inc_id, llm_analysis)
        else:
            council_result = await self._council_deliberation(
                investigation, llm_analysis
            )
            if council_result:
                root_cause = self._create_from_council(
                    inc_id, council_result, llm_analysis
                )
            else:
                root_cause = self._create_from_analysis(inc_id, llm_analysis)

        self.db.add(root_cause)
        await self.db.flush()
        await self.db.refresh(root_cause)

        incident_service = IncidentService(self.db, self.event_bus)
        await incident_service.transition_status(
            inc_id, IncidentStatus.ROOT_CAUSE_IDENTIFIED
        )

        await self.event_bus.publish(
            Event(
                type=EventType.RCA_COMPLETED,
                data={
                    "incident_id": incident_id,
                    "root_cause_id": str(root_cause.id),
                    "category": root_cause.category.value,
                    "confidence": root_cause.confidence_score,
                },
            )
        )

        logger.info(
            "RCA complete for incident %s: %s (confidence=%.2f)",
            incident_id,
            root_cause.category.value,
            root_cause.confidence_score,
        )
        return root_cause

    def _create_from_analysis(
        self, incident_id, analysis: dict
    ) -> RootCause:
        category_str = analysis.get("root_cause_category", "other")
        category = CATEGORY_MAP.get(category_str, RootCauseCategory.OTHER)

        return RootCause(
            incident_id=incident_id,
            category=category,
            description=analysis.get("root_cause_description", "Unknown"),
            file_path=(analysis.get("affected_files") or [None])[0],
            suggested_fix_description=analysis.get("suggested_fix_approach"),
            confidence_score=analysis.get("confidence", 0.0),
        )

    def _create_from_council(
        self, incident_id, council_result: dict, original_analysis: dict
    ) -> RootCause:
        recommendation = council_result.get("recommendation", "")

        category_str = original_analysis.get("root_cause_category", "other")
        category = CATEGORY_MAP.get(category_str, RootCauseCategory.OTHER)

        return RootCause(
            incident_id=incident_id,
            category=category,
            description=recommendation or original_analysis.get(
                "root_cause_description", "Unknown"
            ),
            file_path=(original_analysis.get("affected_files") or [None])[0],
            suggested_fix_description=original_analysis.get(
                "suggested_fix_approach"
            ),
            confidence_score=0.9,
            council_deliberation=council_result,
        )

    async def _council_deliberation(
        self, investigation: Investigation, analysis: dict
    ) -> Optional[dict]:
        if not council_wrapper.available:
            logger.info("LLM Council not available, using single-model analysis")
            return None

        prompt = RCA_COUNCIL_PROMPT.format(
            investigation_summary=investigation.summary or "No summary",
            evidence_summary=json.dumps(investigation.affected_files or []),
            error_type=analysis.get("root_cause_category", "unknown"),
            error_message=analysis.get("immediate_cause", "unknown"),
            file_path=(analysis.get("affected_files") or ["unknown"])[0],
            line_number="unknown",
        )

        return await council_wrapper.query(prompt, mode="full")
