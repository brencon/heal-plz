from heal_plz.core.exceptions import InvalidStateTransitionError
from heal_plz.db.models.incident import IncidentStatus

VALID_TRANSITIONS: dict[IncidentStatus, list[IncidentStatus]] = {
    IncidentStatus.OPEN: [
        IncidentStatus.INVESTIGATING,
        IncidentStatus.WONT_FIX,
        IncidentStatus.CLOSED,
    ],
    IncidentStatus.INVESTIGATING: [
        IncidentStatus.ROOT_CAUSE_IDENTIFIED,
        IncidentStatus.OPEN,
        IncidentStatus.WONT_FIX,
    ],
    IncidentStatus.ROOT_CAUSE_IDENTIFIED: [
        IncidentStatus.FIX_IN_PROGRESS,
        IncidentStatus.WONT_FIX,
    ],
    IncidentStatus.FIX_IN_PROGRESS: [
        IncidentStatus.FIX_PENDING_REVIEW,
        IncidentStatus.ROOT_CAUSE_IDENTIFIED,
    ],
    IncidentStatus.FIX_PENDING_REVIEW: [
        IncidentStatus.FIX_MERGED,
        IncidentStatus.FIX_IN_PROGRESS,
    ],
    IncidentStatus.FIX_MERGED: [
        IncidentStatus.VERIFYING,
    ],
    IncidentStatus.VERIFYING: [
        IncidentStatus.RESOLVED,
        IncidentStatus.FIX_IN_PROGRESS,
    ],
    IncidentStatus.RESOLVED: [
        IncidentStatus.CLOSED,
        IncidentStatus.OPEN,
    ],
    IncidentStatus.CLOSED: [
        IncidentStatus.OPEN,
    ],
    IncidentStatus.WONT_FIX: [
        IncidentStatus.OPEN,
    ],
}


def validate_transition(
    current: IncidentStatus, target: IncidentStatus
) -> None:
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise InvalidStateTransitionError(current.value, target.value)
