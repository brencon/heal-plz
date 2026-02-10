from heal_plz.db.models.monitor_event import EventSeverity
from heal_plz.engine.output_analyzer import OutputAnalyzer


class TestOutputAnalyzer:
    def setup_method(self):
        self.analyzer = OutputAnalyzer()

    def test_python_traceback(self):
        output = """Traceback (most recent call last):
  File "app/main.py", line 42, in handle_request
    result = process(data)
  File "app/utils.py", line 15, in process
    return data["key"]
KeyError: 'key'
"""
        errors = self.analyzer.analyze_output(output)
        assert len(errors) == 1
        err = errors[0]
        assert err.error_type == "KeyError"
        assert err.stacktrace is not None
        assert "app/main.py" in err.stacktrace
        assert err.severity == EventSeverity.ERROR

    def test_single_line_error(self):
        error = self.analyzer.feed_line("ValueError: invalid literal for int()")
        assert error is not None
        assert error.error_type == "ValueError"
        assert error.severity == EventSeverity.ERROR

    def test_single_line_exception(self):
        error = self.analyzer.feed_line("RuntimeException: connection timed out")
        assert error is not None
        assert error.error_type == "RuntimeException"

    def test_test_failure_FAILED(self):
        error = self.analyzer.feed_line("FAILED tests/test_api.py::test_login - AssertionError")
        assert error is not None
        assert error.error_type == "TestFailure"
        assert error.severity == EventSeverity.ERROR

    def test_test_failure_FAIL(self):
        error = self.analyzer.feed_line("FAIL tests/test_utils.py::test_parse")
        assert error is not None
        assert error.error_type == "TestFailure"

    def test_build_error_with_location(self):
        error = self.analyzer.feed_line("src/main.py:42:10: E302 expected 2 blank lines")
        assert error is not None
        assert error.error_type == "BuildError"
        assert error.file_path == "src/main.py"
        assert error.line_number == 42
        assert error.severity == EventSeverity.WARNING

    def test_normal_output_no_error(self):
        error = self.analyzer.feed_line("Starting server on port 8000")
        assert error is None

    def test_normal_info_log_no_error(self):
        error = self.analyzer.feed_line("[INFO] Application initialized successfully")
        assert error is None

    def test_multi_line_traceback_buffering(self):
        lines = [
            "Traceback (most recent call last):",
            '  File "app.py", line 10, in main',
            "    foo()",
            '  File "app.py", line 5, in foo',
            "    raise RuntimeError('boom')",
            "RuntimeError: boom",
        ]
        errors = []
        for line in lines:
            err = self.analyzer.feed_line(line)
            if err:
                errors.append(err)

        assert len(errors) == 1
        assert errors[0].error_type == "RuntimeError"
        assert errors[0].stacktrace is not None

    def test_flush_incomplete_buffer(self):
        self.analyzer.feed_line("Traceback (most recent call last):")
        self.analyzer.feed_line('  File "app.py", line 10, in main')
        self.analyzer.feed_line("    foo()")
        # No closing error line — flush should still produce an error
        error = self.analyzer.flush()
        assert error is not None
        assert error.stacktrace is not None

    def test_analyze_output_multiple_errors(self):
        output = """Starting app...
ValueError: bad value
Some normal output
TypeError: expected str, got int
"""
        errors = self.analyzer.analyze_output(output)
        assert len(errors) == 2
        types = {e.error_type for e in errors}
        assert "ValueError" in types
        assert "TypeError" in types

    def test_go_panic(self):
        error = self.analyzer.feed_line("panic: runtime error: index out of range")
        # panic starts a block, so first line shouldn't emit yet
        assert error is None
        # Feed blank lines to end the block
        self.analyzer.feed_line("")
        error = self.analyzer.feed_line("")
        assert error is not None

    def test_reset_clears_state(self):
        self.analyzer.feed_line("Traceback (most recent call last):")
        self.analyzer.feed_line('  File "app.py", line 10, in main')
        self.analyzer.reset()
        error = self.analyzer.flush()
        assert error is None
