from fastapi import APIRouter

from heal_plz.api.v1.endpoints import alerts, dashboard, incidents, monitors, repositories, webhooks

api_router = APIRouter()
api_router.include_router(repositories.router)
api_router.include_router(monitors.router)
api_router.include_router(alerts.router)
api_router.include_router(incidents.router)
api_router.include_router(webhooks.router)
api_router.include_router(dashboard.router)
