from typing import Any, Optional

from pydantic import BaseModel

from heal_plz.db.models.monitor_event import EventSeverity, EventSource


class WebhookPayload(BaseModel):
    source: EventSource
    payload: dict[str, Any]


class CLIErrorReport(BaseModel):
    repository_owner: str
    repository_name: str
    error_type: Optional[str] = None
    error_message: str
    stacktrace: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    severity: EventSeverity = EventSeverity.ERROR
    environment: str = "development"
