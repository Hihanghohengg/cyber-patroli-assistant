"""v1 API Routers."""

from fastapi import APIRouter
from app.api.v1.dashboard import router as dashboard_v1_router
from app.api.v1.admin import router as admin_v1_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(dashboard_v1_router)
api_v1_router.include_router(admin_v1_router)
