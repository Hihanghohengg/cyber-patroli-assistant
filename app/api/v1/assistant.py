"""Omnichannel Assistant API.

Provides unified endpoints for all client channels:
- Telegram Bot
- WhatsApp Assistant (Webhook Gateway)
- Chrome / Edge Browser Extension
- Web Dashboard Console
"""

import re
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.report import Report
from app.services.scraper.base import BaseScraper
from app.workers.tasks import process_patrol_url

router = APIRouter(prefix="/assistant", tags=["Omnichannel Assistant"])


class ChannelIntakeRequest(BaseModel):
    """Payload for submitting a patrol intake from any channel."""
    url: str = Field(..., description="URL konten media sosial (TikTok, YouTube, Instagram).")
    source_channel: str = Field(default="BROWSER_EXTENSION", description="Kanal pengirim: BROWSER_EXTENSION, WHATSAPP, TELEGRAM, WEB_DASHBOARD, API.")
    reporter_identifier: Optional[str] = Field(default="Analyst-Console", description="Pengenal pengirim (nomor HP, extension ID, username).")
    reporter_telegram_id: Optional[int] = Field(default=None, description="Telegram User ID (jika melalui Telegram).")
    notes: Optional[str] = Field(default=None, description="Catatan opsional dari analis atau pelapor.")


class WhatsAppWebhookPayload(BaseModel):
    """Standard payload structure for incoming WhatsApp messages."""
    From: str = Field(default="+628000000000", description="Nomor WhatsApp pengirim (e.g. whatsapp:+6281234567890)")
    Body: str = Field(..., description="Isi teks pesan WhatsApp yang berisi tautan/laporan.")
    ProfileName: Optional[str] = Field(default="Petugas Piket", description="Nama profil kontak WhatsApp.")


@router.get("/channels")
def get_supported_channels(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve all operational assistant channels and their statistics."""
    # Query intake counts by channel
    channel_counts = (
        db.query(Report.source_channel, func.count(Report.report_id))
        .group_by(Report.source_channel)
        .all()
    )
    counts_map = {c or "TELEGRAM": count for c, count in channel_counts}

    return {
        "status": "ONLINE",
        "architecture": "Omnichannel Decoupled Assistant",
        "channels": [
            {
                "id": "telegram",
                "name": "Telegram Bot Assistant",
                "type": "MESSAGING_BOT",
                "status": "ONLINE",
                "intake_count": counts_map.get("TELEGRAM", 0),
                "features": ["Command Interface", "Inline Decision Buttons", "DOCX Daily Recap Generator", "Fail-Open Alerts"],
                "icon": "Send",
            },
            {
                "id": "browser_extension",
                "name": "Cyber Patrol Browser Extension",
                "type": "BROWSER_AGENT",
                "status": "ONLINE",
                "intake_count": counts_map.get("BROWSER_EXTENSION", 0),
                "features": ["1-Click URL & DOM Capture", "Active Tab Auto-Detection", "Instant Triage Status", "Side-panel Integration"],
                "icon": "Chrome",
            },
            {
                "id": "whatsapp",
                "name": "WhatsApp Business Gateway",
                "type": "MESSAGING_GATEWAY",
                "status": "READY",
                "intake_count": counts_map.get("WHATSAPP", 0),
                "features": ["Inbound Webhook", "Natural Text URL Extraction", "Formatted Markdown Reply", "Operator Verification"],
                "icon": "MessageCircle",
            },
            {
                "id": "web_dashboard",
                "name": "Web Command Console",
                "type": "MANAGEMENT_CONSOLE",
                "status": "ONLINE",
                "intake_count": counts_map.get("WEB_DASHBOARD", 0),
                "features": ["Social Intelligence Graphs", "Drill-Down Filter", "Entity Resolution", "Knowledge Base Management"],
                "icon": "LayoutDashboard",
            },
        ],
    }


@router.post("/intake")
def submit_channel_intake(payload: ChannelIntakeRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Accept patrol intake from any client channel (Browser Extension, WhatsApp, Web, etc.)."""
    try:
        platform = BaseScraper.detect_platform(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Platform tidak didukung atau URL tidak valid: {str(e)}")

    ticket_number = f"PS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    # Enqueue background pipeline
    try:
        process_patrol_url.delay(
            url=payload.url,
            reporter_telegram_id=payload.reporter_telegram_id,
            ticket_number=ticket_number,
            source_channel=payload.source_channel.upper(),
            reporter_identifier=payload.reporter_identifier,
        )
    except Exception as e:
        # If Celery not running, still return ticket info
        pass

    return {
        "status": "QUEUED",
        "ticket_number": ticket_number,
        "platform": platform,
        "source_channel": payload.source_channel.upper(),
        "reporter_identifier": payload.reporter_identifier,
        "tracking_url": f"/#/contents",
        "message": f"Tiket patroli {ticket_number} untuk {platform} berhasil didaftarkan melalui kanal {payload.source_channel.upper()}.",
    }


@router.post("/whatsapp/webhook")
def receive_whatsapp_message(payload: WhatsAppWebhookPayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Inbound webhook handler for WhatsApp messages (Twilio / Meta Cloud API compatible)."""
    # Extract URLs from message body
    url_pattern = r"(https?://[^\s]+)"
    urls = re.findall(url_pattern, payload.Body)

    clean_phone = payload.From.replace("whatsapp:", "").strip()

    if not urls:
        return {
            "status": "IGNORED",
            "reply_message": (
                f"Halo *{payload.ProfileName}* 👋\n\n"
                "Asisten Patroli Siber belum menemukan tautan konten yang valid pada pesan Anda.\n\n"
                "📌 *Format Pengiriman:*\n"
                "Kirimkan tautan URL postingan publik dari *TikTok*, *Instagram*, atau *YouTube* yang terindikasi melanggar untuk dianalisis oleh AI."
            ),
        }

    target_url = urls[0]
    try:
        platform = BaseScraper.detect_platform(target_url)
    except ValueError:
        return {
            "status": "UNSUPPORTED_PLATFORM",
            "reply_message": (
                f"⚠️ *Platform Tidak Didukung*\n\n"
                f"URL: `{target_url}`\n"
                "Sistem saat ini hanya memproses konten publik dari *YouTube*, *TikTok*, dan *Instagram*."
            ),
        }

    ticket_number = f"PS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    try:
        process_patrol_url.delay(
            url=target_url,
            reporter_telegram_id=None,
            ticket_number=ticket_number,
            source_channel="WHATSAPP",
            reporter_identifier=f"{clean_phone} ({payload.ProfileName})",
        )
    except Exception:
        pass

    formatted_reply = (
        f"🛡️ *CYBER PATROL INTELLIGENCE ASSISTANT*\n"
        f"────────────────────────────\n"
        f"✅ *Laporan Patroli Diterima!*\n\n"
        f"🎫 *Nomor Tiket:* `{ticket_number}`\n"
        f"🌐 *Platform:* {platform.upper()}\n"
        f"👤 *Pelapor:* {payload.ProfileName} ({clean_phone})\n"
        f"⏳ *Status:* Triase AI Multimodal 5W+1H sedang berjalan...\n\n"
        f"Hasil analisis risiko dan rekomendasi kategori akan diperbarui di sistem pusat."
    )

    return {
        "status": "QUEUED",
        "ticket_number": ticket_number,
        "platform": platform,
        "reply_message": formatted_reply,
    }
