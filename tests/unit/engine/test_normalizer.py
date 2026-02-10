from heal_plz.db.models.monitor_event import EventSeverity, EventSource
from heal_plz.engine.normalizer import EventNormalizer


class TestEventNormalizer:
    def setup_method(self):
        self.normalizer = EventNormalizer()

    def test_github_workflow_run_failure(self):
        payload = {
            "action": "completed",
            "workflow_run": {
                "name": "CI",
                "conclusion": "failure",
                "head_branch": "main",
                "head_sha": "abc123",
                "id": 12345,
            },
            "repository": {
                "full_name": "owner/repo",
            },
        }
        result = self.normalizer.normalize_github_workflow_run(payload)
        assert result is not None
        assert result.source == EventSource.GITHUB_ACTIONS
        assert result.severity == EventSeverity.ERROR
        assert "CI" in result.title
        assert result.commit_sha == "abc123"
        assert result.branch == "main"
        assert result.fingerprint

    def test_github_workflow_run_success_ignored(self):
        payload = {
            "action": "completed",
            "workflow_run": {
                "name": "CI",
                "conclusion": "success",
                "head_branch": "main",
                "head_sha": "abc123",
            },
        }
        result = self.normalizer.normalize_github_workflow_run(payload)
        assert result is None

    def test_github_workflow_run_in_progress_ignored(self):
        payload = {
            "action": "in_progress",
            "workflow_run": {
                "name": "CI",
                "conclusion": None,
            },
        }
        result = self.normalizer.normalize_github_workflow_run(payload)
        assert result is None

    def test_sentry_event(self):
        payload = {
            "data": {
                "event": {
                    "title": "TypeError: cannot read property",
                    "level": "error",
                    "environment": "production",
                    "exception": {
                        "values": [
                            {
                                "type": "TypeError",
                                "value": "cannot read property 'x' of undefined",
                                "stacktrace": {
                                    "frames": [
                                        {
                                            "filename": "app.js",
                                            "lineno": 42,
                                            "function": "handleClick",
                                        }
                                    ]
                                },
                            }
                        ]
                    },
                }
            }
        }
        result = self.normalizer.normalize_sentry_event(payload)
        assert result is not None
        assert result.source == EventSource.SENTRY
        assert result.error_type == "TypeError"
        assert result.file_path == "app.js"
        assert result.line_number == 42

    def test_cli_report(self):
        result = self.normalizer.normalize_cli_report(
            error_message="ImportError: no module named foo",
            error_type="ImportError",
            file_path="main.py",
            line_number=10,
        )
        assert result.source == EventSource.LOCAL_CLI
        assert result.error_type == "ImportError"
        assert "main.py" in result.title

    def test_fingerprint_consistency(self):
        result1 = self.normalizer.normalize_cli_report(
            error_message="same error",
            error_type="TypeError",
            file_path="app.py",
        )
        result2 = self.normalizer.normalize_cli_report(
            error_message="same error",
            error_type="TypeError",
            file_path="app.py",
        )
        assert result1.fingerprint == result2.fingerprint

    def test_fingerprint_uniqueness(self):
        result1 = self.normalizer.normalize_cli_report(
            error_message="error one",
            error_type="TypeError",
            file_path="a.py",
        )
        result2 = self.normalizer.normalize_cli_report(
            error_message="error two",
            error_type="ValueError",
            file_path="b.py",
        )
        assert result1.fingerprint != result2.fingerprint
