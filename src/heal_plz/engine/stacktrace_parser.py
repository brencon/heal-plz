import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class StackFrame:
    file_path: str
    line_number: Optional[int]
    function_name: Optional[str]
    code_line: Optional[str] = None


@dataclass
class ParsedStacktrace:
    frames: list[StackFrame]
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    language: Optional[str] = None


class StacktraceParser:
    PYTHON_FRAME = re.compile(
        r'File "([^"]+)", line (\d+)(?:, in (\w+))?'
    )
    PYTHON_ERROR = re.compile(r"^(\w+(?:\.\w+)*Error|\w+Exception): (.+)$", re.MULTILINE)

    JS_FRAME = re.compile(
        r"at (?:(.+?) \()?(.+?):(\d+):\d+\)?"
    )
    JS_ERROR = re.compile(r"^(\w+Error): (.+)$", re.MULTILINE)

    GO_FRAME = re.compile(
        r"^\t(.+\.go):(\d+)(?: \+0x[0-9a-f]+)?$", re.MULTILINE
    )
    GO_GOROUTINE = re.compile(r"^goroutine \d+ \[(.+)\]:$", re.MULTILINE)

    JAVA_FRAME = re.compile(
        r"at ([\w.$]+)\(([\w.]+):(\d+)\)"
    )
    JAVA_ERROR = re.compile(
        r"^([\w.]+(?:Exception|Error)): (.+)$", re.MULTILINE
    )

    def parse(self, stacktrace: str) -> ParsedStacktrace:
        if not stacktrace:
            return ParsedStacktrace(frames=[])

        for language, parser in [
            ("python", self._parse_python),
            ("javascript", self._parse_javascript),
            ("go", self._parse_go),
            ("java", self._parse_java),
        ]:
            result = parser(stacktrace)
            if result.frames:
                result.language = language
                return result

        return ParsedStacktrace(frames=[])

    def _parse_python(self, text: str) -> ParsedStacktrace:
        frames = []
        for match in self.PYTHON_FRAME.finditer(text):
            frames.append(
                StackFrame(
                    file_path=match.group(1),
                    line_number=int(match.group(2)),
                    function_name=match.group(3),
                )
            )

        error_type = None
        error_message = None
        error_match = self.PYTHON_ERROR.search(text)
        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2)

        return ParsedStacktrace(
            frames=frames,
            error_type=error_type,
            error_message=error_message,
        )

    def _parse_javascript(self, text: str) -> ParsedStacktrace:
        frames = []
        for match in self.JS_FRAME.finditer(text):
            frames.append(
                StackFrame(
                    file_path=match.group(2),
                    line_number=int(match.group(3)),
                    function_name=match.group(1),
                )
            )

        error_type = None
        error_message = None
        error_match = self.JS_ERROR.search(text)
        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2)

        return ParsedStacktrace(
            frames=frames,
            error_type=error_type,
            error_message=error_message,
        )

    def _parse_go(self, text: str) -> ParsedStacktrace:
        frames = []
        for match in self.GO_FRAME.finditer(text):
            frames.append(
                StackFrame(
                    file_path=match.group(1),
                    line_number=int(match.group(2)),
                    function_name=None,
                )
            )

        return ParsedStacktrace(frames=frames)

    def _parse_java(self, text: str) -> ParsedStacktrace:
        frames = []
        for match in self.JAVA_FRAME.finditer(text):
            frames.append(
                StackFrame(
                    file_path=match.group(2),
                    line_number=int(match.group(3)),
                    function_name=match.group(1),
                )
            )

        error_type = None
        error_message = None
        error_match = self.JAVA_ERROR.search(text)
        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2)

        return ParsedStacktrace(
            frames=frames,
            error_type=error_type,
            error_message=error_message,
        )
