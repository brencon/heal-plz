import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.config import settings
from heal_plz.core.events import Event, EventBus, EventType
from heal_plz.db.models.incident import Incident, IncidentStatus
from heal_plz.db.models.investigation import Investigation
from heal_plz.db.models.resolution import Resolution, ResolutionStatus, ResolutionStrategy
from heal_plz.db.models.root_cause import RootCause
from heal_plz.db.models.verification import Verification, VerificationResult
from heal_plz.engine.code_context import CodeContextBuilder
from heal_plz.engine.fix_generator import FixGenerator, FixResult
from heal_plz.engine.fix_verifier import FixVerifier
from heal_plz.engine.pr_creator import PRCreator
from heal_plz.integrations.github.client import GitHubClient
from heal_plz.services.incident_service import IncidentService

logger = logging.getLogger(__name__)


class HealingService:
    def __init__(self, db: AsyncSession, event_bus: EventBus) -> None:
        self.db = db
        self.event_bus = event_bus

    async def generate_fix(
        self, incident_id: str, root_cause_id: str
    ) -> Optional[Resolution]:
        import uuid as _uuid

        inc_id = _uuid.UUID(incident_id)
        rc_id = _uuid.UUID(root_cause_id)

        result = await self.db.execute(
            select(Incident).where(Incident.id == inc_id)
        )
        incident = result.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        result = await self.db.execute(
            select(RootCause).where(RootCause.id == rc_id)
        )
        root_cause = result.scalar_one_or_none()
        if not root_cause:
            raise ValueError(f"RootCause {root_cause_id} not found")

        incident_service = IncidentService(self.db, self.event_bus)
        await incident_service.transition_status(inc_id, IncidentStatus.FIX_IN_PROGRESS)

        resolution = Resolution(
            incident_id=inc_id,
            root_cause_id=rc_id,
            status=ResolutionStatus.GENERATING_FIX,
            strategy=ResolutionStrategy.SUGGEST_FIX,
            max_attempts=settings.MAX_FIX_ATTEMPTS,
        )
        self.db.add(resolution)
        await self.db.flush()
        await self.db.refresh(resolution)

        repo = incident.repository
        github = GitHubClient(settings.ANTHROPIC_API_KEY)
        context_builder = CodeContextBuilder(github)

        code_context = await context_builder.build(
            owner=repo.github_owner,
            repo=repo.github_repo,
            file_path=root_cause.file_path,
        )

        generator = FixGenerator(max_attempts=settings.MAX_FIX_ATTEMPTS)
        fix_result = await generator.generate(root_cause, code_context)

        if not fix_result.success:
            resolution.status = ResolutionStatus.FAILED
            await self.db.flush()
            logger.error("Fix generation failed for incident %s", incident_id)
            return resolution

        verifier = FixVerifier()
        verification_suite = await verifier.verify_changes(
            [{"path": c.path, "content": c.content} for c in fix_result.changes]
        )

        for check in verification_suite.checks:
            v = Verification(
                resolution_id=resolution.id,
                verification_type=check.check_type,
                result=check.result,
                output=check.output,
                duration_seconds=check.duration_seconds,
            )
            self.db.add(v)

        if not verification_suite.all_passed:
            resolution.status = ResolutionStatus.FAILED
            await self.db.flush()
            logger.warning(
                "Fix verification failed for incident %s: %s",
                incident_id,
                verification_suite.summary,
            )
            return resolution

        resolution.status = ResolutionStatus.FIX_GENERATED
        resolution.fix_description = fix_result.description
        resolution.files_changed = [
            {"path": c.path} for c in fix_result.changes
        ]
        resolution.llm_model_used = fix_result.model
        resolution.llm_tokens_used = fix_result.tokens_used
        resolution.attempt_number = fix_result.attempt
        await self.db.flush()

        pr_creator = PRCreator(github)
        pr_data = await pr_creator.create_pr(
            owner=repo.github_owner,
            repo=repo.github_repo,
            incident=incident,
            root_cause=root_cause,
            fix_result=fix_result,
            base_branch=repo.default_branch,
        )

        if pr_data:
            resolution.status = ResolutionStatus.PR_CREATED
            resolution.pr_number = pr_data.get("number")
            resolution.pr_url = pr_data.get("html_url")
            resolution.pr_state = pr_data.get("state")
            resolution.branch_name = f"heal-plz/{incident.incident_number}-*"

            await incident_service.transition_status(
                inc_id, IncidentStatus.FIX_PENDING_REVIEW
            )
        else:
            resolution.status = ResolutionStatus.FIX_GENERATED

        await self.db.flush()

        await self.event_bus.publish(
            Event(
                type=EventType.FIX_GENERATED,
                data={
                    "incident_id": incident_id,
                    "resolution_id": str(resolution.id),
                    "pr_number": resolution.pr_number,
                    "pr_url": resolution.pr_url,
                },
            )
        )

        logger.info(
            "Fix generated for incident %s, PR: %s",
            incident_id,
            resolution.pr_url or "not created",
        )
        return resolution
