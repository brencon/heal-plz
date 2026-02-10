import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from heal_plz.api.v1.router import api_router
from heal_plz.config import settings
from heal_plz.core.events import EventBus
from heal_plz.core.tasks import BackgroundTaskManager
from heal_plz.db.base import Base
from heal_plz.db.models import *  # noqa: F401, F403 — register all models
from heal_plz.db.session import create_engine, create_session_factory
from heal_plz.schemas.common import HealthResponse

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting heal-plz...")

    engine = create_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    session_factory = create_session_factory(engine)
    event_bus = EventBus()
    task_manager = BackgroundTaskManager(
        max_concurrent=settings.MAX_CONCURRENT_TASKS
    )

    app.state.settings = settings
    app.state.db_session_factory = session_factory
    app.state.event_bus = event_bus
    app.state.task_manager = task_manager

    from heal_plz.engine.pipeline import HealingPipeline

    pipeline = HealingPipeline(event_bus, task_manager, session_factory)
    app.state.pipeline = pipeline

    event_bus_task = asyncio.create_task(event_bus.start())
    logger.info("heal-plz started successfully (pipeline active)")

    yield

    logger.info("Shutting down heal-plz...")
    await event_bus.stop()
    event_bus_task.cancel()
    try:
        await event_bus_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
    logger.info("heal-plz shut down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="heal-plz",
        description="Self-healing coding platform with enterprise response management and resolution",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard_redirect():
        return RedirectResponse(url="/static/index.html")

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            environment=settings.ENVIRONMENT,
        )

    return app


app = create_app()
