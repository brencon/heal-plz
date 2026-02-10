from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.api.dependencies import get_db
from heal_plz.db.models.alert import Alert, AlertSeverity, AlertStatus
from heal_plz.db.models.incident import Incident, IncidentStatus
from heal_plz.db.models.repository import Repository
from heal_plz.db.models.resolution import Resolution, ResolutionStatus
from heal_plz.schemas.dashboard import AlertBreakdown, DashboardOverview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(
    db: AsyncSession = Depends(get_db),
) -> DashboardOverview:
    total_repos = (await db.execute(select(func.count(Repository.id)))).scalar() or 0
    total_incidents = (
        await db.execute(select(func.count(Incident.id)))
    ).scalar() or 0
    open_incidents = (
        await db.execute(
            select(func.count(Incident.id)).where(
                Incident.status.in_([
                    IncidentStatus.OPEN,
                    IncidentStatus.INVESTIGATING,
                    IncidentStatus.ROOT_CAUSE_IDENTIFIED,
                    IncidentStatus.FIX_IN_PROGRESS,
                    IncidentStatus.FIX_PENDING_REVIEW,
                ])
            )
        )
    ).scalar() or 0
    resolved_incidents = (
        await db.execute(
            select(func.count(Incident.id)).where(
                Incident.status.in_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED])
            )
        )
    ).scalar() or 0

    total_alerts = (await db.execute(select(func.count(Alert.id)))).scalar() or 0
    active_alerts = (
        await db.execute(
            select(func.count(Alert.id)).where(
                Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED])
            )
        )
    ).scalar() or 0

    severity_counts = {}
    for sev in AlertSeverity:
        count = (
            await db.execute(
                select(func.count(Alert.id)).where(
                    Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]),
                    Alert.severity == sev,
                )
            )
        ).scalar() or 0
        severity_counts[sev.value] = count

    total_fixes = (
        await db.execute(
            select(func.count(Resolution.id)).where(
                Resolution.status.in_([
                    ResolutionStatus.FIX_GENERATED,
                    ResolutionStatus.PR_CREATED,
                    ResolutionStatus.PR_MERGED,
                    ResolutionStatus.VERIFIED,
                ])
            )
        )
    ).scalar() or 0
    total_prs = (
        await db.execute(
            select(func.count(Resolution.id)).where(
                Resolution.pr_number.isnot(None)
            )
        )
    ).scalar() or 0

    heal_rate = 0.0
    if total_incidents > 0:
        heal_rate = resolved_incidents / total_incidents

    return DashboardOverview(
        total_repositories=total_repos,
        total_incidents=total_incidents,
        open_incidents=open_incidents,
        resolved_incidents=resolved_incidents,
        total_alerts=total_alerts,
        active_alerts=active_alerts,
        active_alerts_by_severity=AlertBreakdown(**severity_counts),
        total_fixes_generated=total_fixes,
        total_prs_created=total_prs,
        auto_heal_success_rate=round(heal_rate, 3),
        mean_time_to_resolution_hours=None,
    )
