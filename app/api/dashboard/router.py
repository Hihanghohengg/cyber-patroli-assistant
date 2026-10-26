"""Main router for Web Dashboard API.

Aggregates auth, overview, trending topics, content explorer,
HITL validation, and analytics sub-routers.
"""

from fastapi import APIRouter

from app.api.dashboard.auth import router as auth_router
from app.api.dashboard.overview import router as overview_router
from app.api.dashboard.trending import router as trending_router
from app.api.dashboard.contents import router as contents_router
from app.api.dashboard.validation import router as validation_router
from app.api.dashboard.analytics import router as analytics_router
from app.api.v1.admin import router as admin_router

dashboard_router = APIRouter(prefix="/api/dashboard")

dashboard_router.include_router(auth_router)
dashboard_router.include_router(overview_router)
dashboard_router.include_router(trending_router)
dashboard_router.include_router(contents_router)
dashboard_router.include_router(validation_router)
dashboard_router.include_router(analytics_router)
dashboard_router.include_router(admin_router)
