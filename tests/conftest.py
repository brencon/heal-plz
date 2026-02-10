import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from heal_plz.core.events import EventBus
from heal_plz.core.tasks import BackgroundTaskManager
from heal_plz.db.base import Base
from heal_plz.db.models import *  # noqa: F401, F403
from heal_plz.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def app():
    application = create_app()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    event_bus = EventBus()
    task_manager = BackgroundTaskManager(max_concurrent=2)

    application.state.settings = application.state.settings if hasattr(application.state, "settings") else None
    application.state.db_session_factory = session_factory
    application.state.event_bus = event_bus
    application.state.task_manager = task_manager

    yield application

    await engine.dispose()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session(app) -> AsyncGenerator[AsyncSession, None]:
    async with app.state.db_session_factory() as session:
        yield session
