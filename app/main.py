"""TILIK — Main Entry Point.

Starts the FastAPI HTTP server for web dashboard, intelligence analytics,
and pure Browser Extension integration.
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from starlette.datastructures import MutableHeaders
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.schemas.patrol import PatrolRequest
from app.api.dashboard.router import dashboard_router
from app.api.v1 import api_v1_router

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("patrol")


# ── Lifespan (startup / shutdown) ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and automatic background tasks."""
    logger.info("🛡️ TILIK starting…")
    os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    init_db()
    logger.info("✅ Database tables initialised.")

    # Background autonomous trending score synchronizer (runs without manual operator intervention)
    async def auto_trending_worker():
        from app.database import SessionLocal
        from app.services.intelligence.trending_engine import TrendingEngine
        while True:
            try:
                await asyncio.sleep(4)  # Initial grace delay
                db = SessionLocal()
                try:
                    engine = TrendingEngine()
                    snapshots = engine.recalculate_all_active_issues(db, window_hours=24)
                    if snapshots:
                        logger.info("Autonomous trending engine: updated %d active topic scores", len(snapshots))
                finally:
                    db.close()
            except Exception as e:
                logger.debug("Autonomous trending engine idle tick: %s", e)
            await asyncio.sleep(300)  # Synchronize every 5 minutes automatically

    trending_task = None
    if os.environ.get("TESTING") != "1":
        trending_task = asyncio.create_task(auto_trending_worker())
    yield
    if trending_task:
        trending_task.cancel()
    logger.info("🛑 Shutting down…")


# ── FastAPI App ──
api = FastAPI(
    title="TILIK — Sistem Pemantauan & Analisis Konten Siber",
    description="REST API untuk Pemantauan Ruang Siber, Analisis Konten, dan Dasbor Intelijen.",
    lifespan=lifespan,
)
app = api  # Standard ASGI entrypoint alias

# Apply OWASP Top 10 Security Headers & Chrome Private Network Access (PNA)
@api.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Anti-leak Cache-Control for sensitive patrol intelligence endpoints
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"

    # Mengizinkan akses dari peramban pada situs publik (YouTube/TikTok) ke localhost (PNA)
    if request.headers.get("access-control-request-private-network"):
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

# Enable Hardened CORS for web dashboard and browser extensions (including content scripts on social media)
api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^(chrome-extension://.*|moz-extension://.*|http://(localhost|127\.0\.0\.1)(:\d+)?|https://(www\.)?(youtube\.com|tiktok\.com|instagram\.com|twitter\.com|x\.com|facebook\.com))$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@api.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        messages.append(f"{field}: {err.get('msg', 'Format data tidak valid')}")
    clean_msg = "; ".join(messages)
    logger.warning(f"Request validation error on {request.url}: {clean_msg}")
    return JSONResponse(status_code=422, content={"detail": clean_msg})

# Mount Dashboard API
api.include_router(dashboard_router)
api.include_router(api_v1_router)

# Serve dashboard static build if exists
dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "dist")
if os.path.exists(dist_dir):
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        api.mount("/dashboard/assets", StaticFiles(directory=assets_dir), name="dashboard_assets")
        api.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @api.get("/dashboard/{full_path:path}")
    async def serve_dashboard(full_path: str):
        # Prevent Directory / Path Traversal (CWE-22)
        safe_base = os.path.realpath(dist_dir)
        target_path = os.path.realpath(os.path.join(safe_base, full_path.lstrip("/\\")))
        if not target_path.startswith(safe_base):
            raise HTTPException(status_code=403, detail="Akses berkas ditolak (Path Traversal Protection)")

        if full_path and os.path.isfile(target_path):
            return FileResponse(target_path)
        index_file = os.path.join(safe_base, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Dashboard index not found")

    @api.get("/dashboard")
    async def redirect_dashboard():
        return RedirectResponse(url="/dashboard/")

    # Seamless URL aliases for browser extension and direct browser navigation
    @api.get("/contents")
    @api.get("/contents/{content_id}")
    async def redirect_contents(content_id: str = ""):
        sub = f"/{content_id}" if content_id else ""
        return RedirectResponse(url=f"/dashboard/#/contents{sub}")

    @api.get("/analytics")
    async def redirect_analytics():
        return RedirectResponse(url="/dashboard/#/analytics")

    @api.get("/trending")
    @api.get("/trending/{issue_id}")
    async def redirect_trending(issue_id: str = ""):
        sub = f"/{issue_id}" if issue_id else ""
        return RedirectResponse(url=f"/dashboard/#/trending{sub}")


@api.get("/")
async def root():
    """Redirect to web dashboard or return API status."""
    if os.path.exists(dist_dir):
        return RedirectResponse(url="/dashboard/")
    return {
        "status": "ok",
        "service": "tilik",
        "message": "TILIK API is running. Access /docs for Swagger UI.",
        "docs_url": "/docs",
    }


@api.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "tilik",
        "timestamp": datetime.utcnow().isoformat(),
    }


@api.post("/api/v1/patrol", status_code=202)
async def submit_patrol(request: PatrolRequest):
    """Accept a patrol URL and enqueue the processing pipeline.

    The actual scraping, hashing, and AI analysis happen in the
    background (via Celery or in-process depending on config).
    """
    from app.services.scraper.base import BaseScraper

    try:
        platform = BaseScraper.detect_platform(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ticket = f"PS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    # Attempt to enqueue via Celery; fall back to sync log
    try:
        from app.workers.tasks import process_patrol_url

        process_patrol_url.delay(
            url=request.url,
            reporter_telegram_id=None,
            ticket_number=ticket,
            source_channel=request.source_channel or "BROWSER_EXTENSION",
            reporter_identifier=request.reporter_identifier or "Analyst-Browser",
        )
    except Exception as e:
        logger.warning("Celery enqueue failed (%s), pipeline will not run in background.", e)

    return {
        "ticket_number": ticket,
        "status": "QUEUED",
        "channel": request.source_channel or "BROWSER_EXTENSION",
        "message": f"Patrol task for {platform} URL has been queued via {request.source_channel or 'BROWSER_EXTENSION'}.",
    }


# ────────────────────────────────────────────
#  Main: run FastAPI server
# ────────────────────────────────────────────

def run_api():
    """Run the FastAPI server."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    run_api()
