"""v1 API Routers."""

from fastapi import APIRouter
from app.api.v1.dashboard import router as dashboard_v1_router
from app.api.v1.admin import router as admin_v1_router
from app.api.v1.assistant import router as assistant_v1_router
from app.api.v1.integrity import router as integrity_v1_router
from app.api.v1.report_export import router as report_export_v1_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(dashboard_v1_router)
api_v1_router.include_router(admin_v1_router)
api_v1_router.include_router(assistant_v1_router)
api_v1_router.include_router(integrity_v1_router)
api_v1_router.include_router(report_export_v1_router)

