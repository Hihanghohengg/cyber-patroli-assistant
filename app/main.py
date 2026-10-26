"""Cyber Patrol Assistant — Main Entry Point.

Starts both the FastAPI HTTP server (for webhooks / API) and the
Telegram bot (long-polling mode) concurrently using asyncio.
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
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
    """Initialize database tables on startup."""
    logger.info("🛡️  Cyber Patrol Assistant starting…")
    os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    init_db()
    logger.info("✅ Database tables initialised.")
    yield
    logger.info("🛑 Shutting down…")


# ── FastAPI App ──
api = FastAPI(
    title="Cyber Patrol Assistant & Social Intelligence API",
    description="REST API for Cyber Patrol, Social Media Profiling, and Social Intelligence Dashboard.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for web dashboard
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        file_path = os.path.join(dist_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Dashboard index not found")

    @api.get("/dashboard")
    async def redirect_dashboard():
        return RedirectResponse(url="/dashboard/")


@api.get("/")
async def root():
    """Redirect to web dashboard or return API status."""
    if os.path.exists(dist_dir):
        return RedirectResponse(url="/dashboard/")
    return {
        "status": "ok",
        "service": "cyber-patrol-assistant",
        "message": "Cyber Patrol Assistant API is running. Access /docs for Swagger UI.",
        "docs_url": "/docs",
    }


@api.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "cyber-patrol-assistant",
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
            reporter_telegram_id=request.reporter_telegram_id,
            ticket_number=ticket,
            source_channel=request.source_channel,
            reporter_identifier=request.reporter_identifier or (f"Telegram:{request.reporter_telegram_id}" if request.reporter_telegram_id else request.source_channel),
        )
    except Exception as e:
        logger.warning("Celery enqueue failed (%s), pipeline will not run in background.", e)

    return {
        "ticket_number": ticket,
        "status": "QUEUED",
        "channel": request.source_channel,
        "message": f"Patrol task for {platform} URL has been queued via {request.source_channel}.",
    }


# ────────────────────────────────────────────
#  Main: run FastAPI + Telegram Bot concurrently
# ────────────────────────────────────────────

async def run_api():
    """Run the FastAPI server."""
    config = uvicorn.Config(
        api,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_bot():
    """Run the Telegram bot in long-polling mode."""
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN.startswith("123456"):
        logger.warning("⚠️  Telegram bot token not configured — bot will not start.")
        return

    try:
        from app.bot.handlers import build_bot_application
    except ImportError as e:
        logger.warning("⚠️  python-telegram-bot is not installed (%s) — bot will not start.", e)
        return

    bot_app = None
    try:
        bot_app = build_bot_application()
        logger.info("🤖 Telegram bot starting (long-polling)…")
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)

        # Keep the bot alive
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("❌ Telegram bot encountered an error: %s", e)
    finally:
        if bot_app is not None:
            try:
                if bot_app.updater and bot_app.updater.running:
                    await bot_app.updater.stop()
                if bot_app.running:
                    await bot_app.stop()
                    await bot_app.shutdown()
            except Exception:
                pass


async def main():
    """Run API server and Telegram bot concurrently."""
    await asyncio.gather(
        run_api(),
        run_bot(),
        return_exceptions=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
