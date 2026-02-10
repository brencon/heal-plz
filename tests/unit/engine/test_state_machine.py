import pytest

from heal_plz.core.exceptions import InvalidStateTransitionError
from heal_plz.db.models.incident import IncidentStatus
from heal_plz.engine.state_machine import validate_transition


class TestStateMachine:
    def test_open_to_investigating(self):
        validate_transition(IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)

    def test_open_to_wont_fix(self):
        validate_transition(IncidentStatus.OPEN, IncidentStatus.WONT_FIX)

    def test_open_to_closed(self):
        validate_transition(IncidentStatus.OPEN, IncidentStatus.CLOSED)

    def test_investigating_to_root_cause_identified(self):
        validate_transition(
            IncidentStatus.INVESTIGATING,
            IncidentStatus.ROOT_CAUSE_IDENTIFIED,
        )

    def test_resolved_to_closed(self):
        validate_transition(IncidentStatus.RESOLVED, IncidentStatus.CLOSED)

    def test_closed_to_open(self):
        validate_transition(IncidentStatus.CLOSED, IncidentStatus.OPEN)

    def test_invalid_open_to_resolved(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_transition(IncidentStatus.OPEN, IncidentStatus.RESOLVED)

    def test_invalid_open_to_fix_in_progress(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_transition(IncidentStatus.OPEN, IncidentStatus.FIX_IN_PROGRESS)

    def test_invalid_resolved_to_investigating(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_transition(IncidentStatus.RESOLVED, IncidentStatus.INVESTIGATING)
