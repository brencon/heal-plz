import asyncio
import enum
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


class EventType(str, enum.Enum):
    MONITOR_EVENT_RECEIVED = "monitor_event_received"
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    INVESTIGATION_STARTED = "investigation_started"
    INVESTIGATION_COMPLETED = "investigation_completed"
    RCA_COMPLETED = "rca_completed"
    FIX_GENERATED = "fix_generated"
    PR_CREATED = "pr_created"
    PR_MERGED = "pr_merged"
    VERIFICATION_COMPLETED = "verification_completed"
    INCIDENT_RESOLVED = "incident_resolved"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Callable]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False

    def subscribe(
        self, event_type: EventType, handler: Callable[..., Coroutine]
    ) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        await self._queue.put(event)

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            handlers = self._handlers.get(event.type, [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception:
                    logger.exception(
                        "Event handler error for %s", event.type, exc_info=True
                    )

    async def stop(self) -> None:
        self._running = False
