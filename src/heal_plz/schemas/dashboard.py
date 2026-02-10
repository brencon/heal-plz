from pydantic import BaseModel


class AlertBreakdown(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class DashboardOverview(BaseModel):
    total_repositories: int
    total_incidents: int
    open_incidents: int
    resolved_incidents: int
    total_alerts: int
    active_alerts: int
    active_alerts_by_severity: AlertBreakdown
    total_fixes_generated: int
    total_prs_created: int
    auto_heal_success_rate: float
    mean_time_to_resolution_hours: float | None
