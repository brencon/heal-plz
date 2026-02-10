import asyncio
import enum
import logging
from typing import Coroutine, Optional

logger = logging.getLogger(__name__)


class TaskPriority(enum.IntEnum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class BackgroundTaskManager:
    def __init__(self, max_concurrent: int = 5) -> None:
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tasks: dict[str, asyncio.Task] = {}

    async def submit(
        self,
        task_id: str,
        coro: Coroutine,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        async def _run():
            async with self._semaphore:
                try:
                    return await coro
                except Exception:
                    logger.exception("Background task %s failed", task_id)
                    raise

        task = asyncio.create_task(_run())
        self._tasks[task_id] = task
        return task_id

    def get_status(self, task_id: str) -> Optional[str]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        if task.done():
            return "completed" if not task.exception() else "failed"
        return "running"

    async def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False
