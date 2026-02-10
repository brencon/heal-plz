import hashlib
import logging
from typing import Any, Optional

from heal_plz.db.models.monitor_event import EventSeverity, EventSource

logger = logging.getLogger(__name__)


class NormalizedEvent:
    def __init__(
        self,
        source: EventSource,
        severity: EventSeverity,
        title: str,
        error_message: str,
        error_type: Optional[str] = None,
        stacktrace: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        commit_sha: Optional[str] = None,
        branch: Optional[str] = None,
        environment: Optional[str] = None,
        raw_payload: Optional[dict] = None,
    ):
        self.source = source
        self.severity = severity
        self.title = title
        self.error_message = error_message
        self.error_type = error_type
        self.stacktrace = stacktrace
        self.file_path = file_path
        self.line_number = line_number
        self.commit_sha = commit_sha
        self.branch = branch
        self.environment = environment
        self.raw_payload = raw_payload or {}
        self.fingerprint = self._compute_fingerprint()

    def _compute_fingerprint(self) -> str:
        parts = [
            self.error_type or "",
            self.file_path or "",
            self.error_message[:200] if self.error_message else "",
        ]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()


class EventNormalizer:
    def normalize_github_workflow_run(
        self, payload: dict[str, Any]
    ) -> Optional[NormalizedEvent]:
        action = payload.get("action")
        if action != "completed":
            return None

        run = payload.get("workflow_run", {})
        conclusion = run.get("conclusion")
        if conclusion != "failure":
            return None

        repo = payload.get("repository", {})
        repo_name = repo.get("full_name", "unknown")
        workflow_name = run.get("name", "unknown")
        branch = run.get("head_branch", "unknown")
        commit_sha = run.get("head_sha")

        return NormalizedEvent(
            source=EventSource.GITHUB_ACTIONS,
            severity=EventSeverity.ERROR,
            title=f"CI Failure: {workflow_name} on {branch}",
            error_message=f"Workflow '{workflow_name}' failed on {repo_name} branch {branch}",
            error_type="WorkflowFailure",
            commit_sha=commit_sha,
            branch=branch,
            environment="ci",
            raw_payload=payload,
        )

    def normalize_github_check_run(
        self, payload: dict[str, Any]
    ) -> Optional[NormalizedEvent]:
        action = payload.get("action")
        if action != "completed":
            return None

        check_run = payload.get("check_run", {})
        conclusion = check_run.get("conclusion")
        if conclusion not in ("failure", "timed_out"):
            return None

        name = check_run.get("name", "unknown")
        output = check_run.get("output", {})
        summary = output.get("summary", "")
        text = output.get("text", "")

        head_sha = check_run.get("head_sha")

        return NormalizedEvent(
            source=EventSource.GITHUB_ACTIONS,
            severity=EventSeverity.ERROR,
            title=f"Check Failed: {name}",
            error_message=summary or f"Check '{name}' {conclusion}",
            error_type="CheckRunFailure",
            stacktrace=text[:5000] if text else None,
            commit_sha=head_sha,
            environment="ci",
            raw_payload=payload,
        )

    def normalize_sentry_event(
        self, payload: dict[str, Any]
    ) -> Optional[NormalizedEvent]:
        data = payload.get("data", {})
        event = data.get("event", {})
        if not event:
            return None

        title = event.get("title", "Unknown error")
        level = event.get("level", "error")

        exception_data = event.get("exception", {})
        values = exception_data.get("values", [])

        error_type = None
        error_message = title
        stacktrace_text = None
        file_path = None
        line_number = None

        if values:
            exc = values[-1]
            error_type = exc.get("type")
            error_message = exc.get("value", title)
            st = exc.get("stacktrace", {})
            frames = st.get("frames", [])
            if frames:
                last_frame = frames[-1]
                file_path = last_frame.get("filename")
                line_number = last_frame.get("lineno")
                stacktrace_lines = []
                for f in frames:
                    stacktrace_lines.append(
                        f"  File \"{f.get('filename')}\", line {f.get('lineno')}, in {f.get('function')}"
                    )
                stacktrace_text = "\n".join(stacktrace_lines)

        severity_map = {
            "fatal": EventSeverity.CRITICAL,
            "error": EventSeverity.ERROR,
            "warning": EventSeverity.WARNING,
            "info": EventSeverity.INFO,
        }

        return NormalizedEvent(
            source=EventSource.SENTRY,
            severity=severity_map.get(level, EventSeverity.ERROR),
            title=title,
            error_message=error_message,
            error_type=error_type,
            stacktrace=stacktrace_text,
            file_path=file_path,
            line_number=line_number,
            environment=event.get("environment", "production"),
            raw_payload=payload,
        )

    def normalize_cli_report(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        stacktrace: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        branch: Optional[str] = None,
        commit_sha: Optional[str] = None,
        severity: EventSeverity = EventSeverity.ERROR,
    ) -> NormalizedEvent:
        title = f"Local Error: {error_type or 'Unknown'}"
        if file_path:
            title += f" in {file_path}"

        return NormalizedEvent(
            source=EventSource.LOCAL_CLI,
            severity=severity,
            title=title,
            error_message=error_message,
            error_type=error_type,
            stacktrace=stacktrace,
            file_path=file_path,
            line_number=line_number,
            branch=branch,
            commit_sha=commit_sha,
            environment="development",
        )
