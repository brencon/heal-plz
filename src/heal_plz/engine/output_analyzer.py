import re
from dataclasses import dataclass, field
from typing import Optional

from heal_plz.db.models.monitor_event import EventSeverity
from heal_plz.engine.stacktrace_parser import StacktraceParser


@dataclass
class DetectedError:
    error_type: Optional[str]
    message: str
    stacktrace: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]
    severity: EventSeverity
    language: Optional[str] = None


# Patterns that signal the START of an error block
ERROR_START_PATTERNS = [
    re.compile(r"^Traceback \(most recent call last\):"),
    re.compile(r"^goroutine \d+ \["),
    re.compile(r"^panic:"),
    re.compile(r"^Exception in thread"),
    re.compile(r"^Unhandled exception"),
]

# Single-line error patterns (error_type, message captured)
SINGLE_LINE_ERRORS = [
    re.compile(r"^(\w+(?:\.\w+)*Error): (.+)$"),
    re.compile(r"^(\w+Exception): (.+)$"),
    re.compile(r"^FATAL: (.+)$"),
]

# Test failure patterns
TEST_FAILURE_PATTERNS = [
    re.compile(r"^FAILED\s+(.+)$"),
    re.compile(r"^FAIL\s+(.+)$"),
    re.compile(r"^E\s+(\w+Error.+)$"),
    re.compile(r"^={3,}\s*FAILURES\s*={3,}$"),
    re.compile(r"^-{3,}\s*ERRORS\s*-{3,}$"),
]

# Build/lint failure patterns
BUILD_FAILURE_PATTERNS = [
    re.compile(r"error\[E\d+\]:"),
    re.compile(r"^error: (.+)$", re.IGNORECASE),
    re.compile(r"^(.+):(\d+):(\d+): error: (.+)$"),
    re.compile(r"^(.+):(\d+):(\d+): (E\d+ .+)$"),
]

# Max lines to buffer for multi-line error blocks
MAX_BUFFER_LINES = 50


class OutputAnalyzer:
    def __init__(self) -> None:
        self._parser = StacktraceParser()
        self._buffer: list[str] = []
        self._in_error_block = False
        self._blank_line_count = 0

    def reset(self) -> None:
        self._buffer.clear()
        self._in_error_block = False
        self._blank_line_count = 0

    def feed_line(self, line: str) -> Optional[DetectedError]:
        stripped = line.rstrip()

        if self._in_error_block:
            if stripped == "":
                self._blank_line_count += 1
                if self._blank_line_count >= 2:
                    return self._flush_buffer()
                self._buffer.append(stripped)
                return None

            self._blank_line_count = 0
            self._buffer.append(stripped)

            if len(self._buffer) >= MAX_BUFFER_LINES:
                return self._flush_buffer()

            # Check if this line has an error conclusion (e.g., "KeyError: 'foo'")
            for pattern in SINGLE_LINE_ERRORS:
                if pattern.match(stripped):
                    return self._flush_buffer()

            return None

        # Check for error block start
        for pattern in ERROR_START_PATTERNS:
            if pattern.match(stripped):
                self._in_error_block = True
                self._blank_line_count = 0
                self._buffer = [stripped]
                return None

        # Check for single-line errors (not in a block)
        for pattern in SINGLE_LINE_ERRORS:
            m = pattern.match(stripped)
            if m:
                return DetectedError(
                    error_type=m.group(1),
                    message=stripped,
                    stacktrace=None,
                    file_path=None,
                    line_number=None,
                    severity=EventSeverity.ERROR,
                )

        # Check for test failures
        for pattern in TEST_FAILURE_PATTERNS:
            m = pattern.match(stripped)
            if m:
                return DetectedError(
                    error_type="TestFailure",
                    message=stripped,
                    stacktrace=None,
                    file_path=None,
                    line_number=None,
                    severity=EventSeverity.ERROR,
                )

        # Check for build/lint errors
        for pattern in BUILD_FAILURE_PATTERNS:
            m = pattern.match(stripped)
            if m:
                file_path = None
                line_number = None
                if m.lastindex and m.lastindex >= 2:
                    try:
                        file_path = m.group(1)
                        line_number = int(m.group(2))
                    except (IndexError, ValueError):
                        pass
                return DetectedError(
                    error_type="BuildError",
                    message=stripped,
                    stacktrace=None,
                    file_path=file_path,
                    line_number=line_number,
                    severity=EventSeverity.WARNING,
                )

        return None

    def flush(self) -> Optional[DetectedError]:
        if self._buffer:
            return self._flush_buffer()
        return None

    def _flush_buffer(self) -> Optional[DetectedError]:
        if not self._buffer:
            self._in_error_block = False
            return None

        text = "\n".join(self._buffer)
        self._buffer.clear()
        self._in_error_block = False
        self._blank_line_count = 0

        parsed = self._parser.parse(text)

        if parsed.frames:
            first_frame = parsed.frames[0]
            return DetectedError(
                error_type=parsed.error_type,
                message=parsed.error_message or text.split("\n")[-1],
                stacktrace=text,
                file_path=first_frame.file_path,
                line_number=first_frame.line_number,
                severity=EventSeverity.ERROR,
                language=parsed.language,
            )

        return DetectedError(
            error_type=parsed.error_type or "UnknownError",
            message=text.split("\n")[-1] if text else "Unknown error",
            stacktrace=text,
            file_path=None,
            line_number=None,
            severity=EventSeverity.ERROR,
        )

    def analyze_output(self, text: str) -> list[DetectedError]:
        self.reset()
        errors = []
        for line in text.split("\n"):
            error = self.feed_line(line)
            if error:
                errors.append(error)
        final = self.flush()
        if final:
            errors.append(final)
        return errors
