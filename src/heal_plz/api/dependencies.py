from typing import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from heal_plz.core.events import EventBus
from heal_plz.core.tasks import BackgroundTaskManager


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


def get_task_manager(request: Request) -> BackgroundTaskManager:
    return request.app.state.task_manager
