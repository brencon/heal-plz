import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from heal_plz.engine.output_analyzer import DetectedError, OutputAnalyzer

logger = logging.getLogger(__name__)


class _ChangeHandler(FileSystemEventHandler):
    def __init__(
        self,
        extensions: list[str],
        callback: Callable[[str], None],
        debounce_seconds: float = 1.0,
    ) -> None:
        self.extensions = extensions
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._pending: dict[str, float] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def on_modified(self, event):
        if event.is_directory:
            return
        if not isinstance(event, FileModifiedEvent):
            return
        path = event.src_path
        if not any(path.endswith(ext) for ext in self.extensions):
            return
        if self._loop:
            self._loop.call_soon_threadsafe(self.callback, path)


class OnChangeCheck:
    def __init__(self, command: str, severity: str = "warning") -> None:
        self.command = command
        self.severity = severity


class FileWatcher:
    def __init__(
        self,
        paths: list[str],
        extensions: list[str],
        on_error: Callable[[DetectedError, str], None],
        on_change_checks: Optional[list[OnChangeCheck]] = None,
    ) -> None:
        self.paths = [Path(p) for p in paths]
        self.extensions = extensions
        self.on_error = on_error
        self.on_change_checks = on_change_checks or []
        self._observer: Optional[Observer] = None
        self._analyzer = OutputAnalyzer()
        self._running = False

    async def start(self) -> None:
        self._running = True
        loop = asyncio.get_event_loop()

        handler = _ChangeHandler(
            extensions=self.extensions,
            callback=lambda path: asyncio.ensure_future(self._on_file_changed(path)),
        )
        handler.set_loop(loop)

        self._observer = Observer()
        for path in self.paths:
            if path.exists():
                self._observer.schedule(handler, str(path), recursive=True)
                logger.info("Watching: %s", path)

        self._observer.start()

        while self._running:
            await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)

    async def _on_file_changed(self, file_path: str) -> None:
        logger.debug("File changed: %s", file_path)

        for check in self.on_change_checks:
            cmd = check.command.replace("{file}", file_path)
            try:
                result = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                stdout, _ = await result.communicate()
                output = stdout.decode("utf-8", errors="replace")

                if result.returncode != 0:
                    self._analyzer.reset()
                    errors = self._analyzer.analyze_output(output)
                    for error in errors:
                        self.on_error(error, file_path)

                    if not errors:
                        from heal_plz.db.models.monitor_event import EventSeverity

                        severity_map = {
                            "warning": EventSeverity.WARNING,
                            "error": EventSeverity.ERROR,
                            "info": EventSeverity.INFO,
                        }
                        self.on_error(
                            DetectedError(
                                error_type="CheckFailure",
                                message=f"Check failed: {cmd}",
                                stacktrace=output[:2000] if output else None,
                                file_path=file_path,
                                line_number=None,
                                severity=severity_map.get(
                                    check.severity, EventSeverity.WARNING
                                ),
                            ),
                            file_path,
                        )
            except Exception as e:
                logger.error("Error running check '%s': %s", cmd, e)
