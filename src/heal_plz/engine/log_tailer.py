import asyncio
import logging
import os
from pathlib import Path
from typing import Callable, Optional

from heal_plz.engine.output_analyzer import DetectedError, OutputAnalyzer

logger = logging.getLogger(__name__)


class LogTailer:
    def __init__(
        self,
        path: str,
        on_error: Callable[[DetectedError, str], None],
        patterns: Optional[list[str]] = None,
    ) -> None:
        self.path = Path(path)
        self.on_error = on_error
        self.patterns = patterns or ["ERROR", "CRITICAL", "Traceback", "Exception"]
        self._analyzer = OutputAnalyzer()
        self._running = False
        self._position = 0

    async def start(self) -> None:
        self._running = True

        if self.path.exists():
            self._position = self.path.stat().st_size

        logger.info("Tailing log: %s (from position %d)", self.path, self._position)

        while self._running:
            try:
                await self._check_file()
            except Exception as e:
                logger.error("Error tailing %s: %s", self.path, e)
            await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False

    async def _check_file(self) -> None:
        if not self.path.exists():
            return

        size = self.path.stat().st_size
        if size < self._position:
            self._position = 0

        if size <= self._position:
            return

        with open(self.path) as f:
            f.seek(self._position)
            new_content = f.read()
            self._position = f.tell()

        for line in new_content.splitlines():
            if not any(p in line for p in self.patterns):
                continue
            error = self._analyzer.feed_line(line)
            if error:
                self.on_error(error, str(self.path))

        final = self._analyzer.flush()
        if final:
            self.on_error(final, str(self.path))
