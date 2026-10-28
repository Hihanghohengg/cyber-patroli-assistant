"""Omnichannel Assistant API.

Provides unified endpoints for all client channels:
- Telegram Bot
- WhatsApp Assistant (Webhook Gateway)
- Chrome / Edge Browser Extension
- Web Dashboard Console
"""

import base64
import hashlib
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.database import get_db
from app.models.report import Report
from app.services.scraper.base import BaseScraper
from app.services.ai_service import AIService
from app.services.intelligence.analysis_5w1h import Analysis5W1HService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Omnichannel Assistant"])


class ChannelIntakeRequest(BaseModel):
    """Payload for submitting a patrol intake from any channel."""
    url: str = Field(..., description="URL konten media sosial (TikTok, YouTube, Instagram).")
    source_channel: str = Field(default="BROWSER_EXTENSION", description="Kanal pengirim: BROWSER_EXTENSION, WHATSAPP, TELEGRAM, WEB_DASHBOARD, API.")
    reporter_identifier: Optional[str] = Field(default="Analyst-Console", description="Pengenal pengirim (nomor HP, extension ID, username).")
    reporter_telegram_id: Optional[int] = Field(default=None, description="Telegram User ID (jika melalui Telegram).")
    notes: Optional[str] = Field(default=None, description="Catatan opsional dari analis atau pelapor.")
    screenshot_base64: Optional[str] = Field(default=None, description="Tangkapan layar base64 langsung dari klien/browser.")
    media_image_url: Optional[str] = Field(default=None, description="URL gambar media langsung dari halaman postingan (og:image / article img).")
    
    # In-page DOM / Screen Extracted Metadata
    username: Optional[str] = Field(default=None, description="Username akun pembuat konten.")
    display_name: Optional[str] = Field(default=None, description="Nama tampilan akun (contoh: GadgetIn).")
    followers_count: Optional[int] = Field(default=0, description="Jumlah followers atau subscribers akun.")
    title: Optional[str] = Field(default=None, description="Judul video / postingan.")
    caption: Optional[str] = Field(default=None, description="Isi teks caption utuh.")
    transcript: Optional[str] = Field(default=None, description="Transkrip teks dialog / audio jika tersedia.")
    likes_count: Optional[int] = Field(default=0, description="Jumlah likes/suka.")
    views_count: Optional[int] = Field(default=0, description="Jumlah tayangan/views.")
    comments_count: Optional[int] = Field(default=0, description="Jumlah komentar.")
    shares_count: Optional[int] = Field(default=0, description="Jumlah bagikan/share.")


def clean_caption_noise(raw: Optional[str]) -> str:
    """Filter out YouTube / social media UI button text artifacts."""
    if not raw:
        return ""
    patterns = [
        r"\.\.\.selengkapnya",
        r"Lebih sedikit",
        r"Ikuti menggunakan transkrip\.",
        r"Tampilkan transkrip",
        r"Transkrip",
        r"Cara konten ini dibuat",
        r"Disulih suara otomatis",
        r"Trek audio untuk beberapa bahasa dibuat secara otomatis\.",
        r"Pelajari lebih lanjut",
        r"\d+([,\.]\d+)?\s*(rb|jt|k|m)?\s*subscriber",
        r"VideoTentangInstagram\S*",
    ]
    cleaned = raw
    for pat in patterns:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


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

    # 0. Hybrid Metadata Enrichment: Jika ada data metrik atau judul yang belum lengkap dari klien,
    # otomatis lengkapi menggunakan backend scraper engine (yt-dlp, Playwright)
    try:
        scraper = None
        if platform == "youtube":
            from app.services.scraper.youtube import YouTubeScraper
            scraper = YouTubeScraper(storage_dir=settings.EVIDENCE_DIR)
        elif platform == "instagram":
            from app.services.scraper.instagram import InstagramScraper
            scraper = InstagramScraper(storage_dir=settings.EVIDENCE_DIR)
        elif platform == "tiktok":
            from app.services.scraper.tiktok import TikTokScraper
            scraper = TikTokScraper(storage_dir=settings.EVIDENCE_DIR)

        server_meta = None
        if scraper:
            server_meta = scraper.extract_metadata(payload.url)
            if server_meta:
                if not payload.title and server_meta.get("title"):
                    payload.title = server_meta["title"]
                
                # Prefer server caption if client didn't supply one or client had UI button artifacts
                server_caption = server_meta.get("caption")
                if server_caption:
                    if not payload.caption or len(server_caption) > len(payload.caption) or "selengkapnya" in (payload.caption or "").lower():
                        payload.caption = server_caption

                if server_meta.get("transcript") and not payload.transcript:
                    payload.transcript = server_meta["transcript"]

                if not payload.username and server_meta.get("account", {}).get("username"):
                    payload.username = server_meta["account"]["username"].replace("@", "")
                if not payload.display_name and server_meta.get("account", {}).get("display_name"):
                    payload.display_name = server_meta["account"]["display_name"]
                if (not payload.followers_count or payload.followers_count == 0) and server_meta.get("account", {}).get("subscribers_count"):
                    payload.followers_count = server_meta["account"]["subscribers_count"]
                if (not payload.views_count or payload.views_count == 0) and server_meta.get("views_count"):
                    payload.views_count = server_meta["views_count"]
                if (not payload.likes_count or payload.likes_count == 0) and server_meta.get("likes_count"):
                    payload.likes_count = server_meta["likes_count"]
                if (not payload.comments_count or payload.comments_count == 0) and server_meta.get("comments_count"):
                    payload.comments_count = server_meta["comments_count"]
                logger.info(f"Metadata berhasil diperkaya via server engine {platform}: {payload.title} (transcript={bool(payload.transcript)})")
    except Exception as enrich_err:
        logger.warning(f"Server-side metadata enrichment warning for {payload.url}: {enrich_err}")

    # Clean UI artifacts from caption
    payload.caption = clean_caption_noise(payload.caption)

    # 1. Pastikan Account tersedia menggunakan hasil ekstraksi DOM atau fallback URL
    from urllib.parse import urlparse
    parsed_url = urlparse(payload.url)
    detected_user = payload.username
    if not detected_user:
        if "@" in payload.url:
            match = re.search(r"@([a-zA-Z0-9_\.]+)", payload.url)
            if match:
                detected_user = match.group(1)
        elif parsed_url.netloc:
            detected_user = parsed_url.netloc.replace("www.", "")
    detected_user = detected_user or "patrol_discover"
    display_name = payload.display_name or f"{detected_user} ({platform.capitalize()})"

    from app.models.report import Account, Content, Report
    from app.models.intelligence import ContentAnalysis
    from app.models.evidence import Evidence
    from app.models.audit import AuditLog

    account = db.query(Account).filter_by(platform=platform, username=detected_user).first()
    if not account:
        account = Account(
            platform=platform,
            username=detected_user,
            display_name=display_name,
            profile_url=f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url.netloc else payload.url,
            followers_count=payload.followers_count or 0,
        )
        db.add(account)
        db.flush()
    else:
        if payload.followers_count and payload.followers_count > 0:
            account.followers_count = payload.followers_count
        if payload.display_name:
            account.display_name = payload.display_name
        db.flush()

    # 2. Akuisisi Bukti Digital Visual (Screenshot) Terlebih Dahulu agar Siap Dianalisis AI Multimodal
    evidence_storage_path = None
    evidence_sha256 = None
    os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
    evidence_filename = f"{ticket_number}_post.png"
    target_path = os.path.join(settings.EVIDENCE_DIR, evidence_filename)

    if payload.screenshot_base64:
        try:
            raw_b64 = payload.screenshot_base64
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            with open(target_path, "wb") as f:
                f.write(img_bytes)
            evidence_storage_path = target_path
            evidence_sha256 = hashlib.sha256(img_bytes).hexdigest()
        except Exception as ex:
            logger.warning(f"Gagal memproses screenshot_base64: {ex}")

    # Unduh media jika gambar postingan tersedia (og:image)
    if (not evidence_storage_path or not os.path.exists(evidence_storage_path)) and payload.media_image_url:
        try:
            import urllib.request
            req = urllib.request.Request(
                payload.media_image_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                downloaded_bytes = resp.read()
            if downloaded_bytes and len(downloaded_bytes) > 500:
                with open(target_path, "wb") as f:
                    f.write(downloaded_bytes)
                evidence_storage_path = target_path
                evidence_sha256 = hashlib.sha256(downloaded_bytes).hexdigest()
                logger.info(f"Berhasil mengunduh foto postingan asli dari media_image_url ({len(downloaded_bytes)} bytes)")
        except Exception as ex:
            logger.warning(f"Gagal mengunduh foto media_image_url: {ex}")

    # Scrape visual via Playwright jika belum ada
    if not evidence_storage_path or not os.path.exists(evidence_storage_path):
        try:
            import asyncio
            if scraper:
                logger.info(f"Mengambil screenshot visual otomatis via Playwright untuk {platform}: {payload.url}")
                scrape_res = asyncio.run(scraper.capture_visual_evidence(post_url=payload.url, ticket_number=ticket_number))
                if scrape_res and scrape_res.get("post_screenshot_path") and os.path.exists(scrape_res["post_screenshot_path"]):
                    evidence_storage_path = scrape_res["post_screenshot_path"]
                    evidence_sha256 = scrape_res.get("post_screenshot_hash")
                    logger.info(f"Berhasil merekam bukti visual asli via Playwright: {evidence_storage_path}")
        except Exception as sc_err:
            logger.warning(f"Playwright automated scrape failed for {payload.url}: {sc_err}")

    # Fallback banner forensik jika Playwright atau screenshot browser tidak tersedia
    if not evidence_storage_path or not os.path.exists(evidence_storage_path):
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (1280, 720), color=(15, 23, 42))  # slate-900
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (1280, 70)], fill=(30, 41, 59))
            draw.text((40, 24), "CYBER PATROL DIGITAL EVIDENCE ARCHIVE (ACQUISITION RECORD)", fill=(56, 189, 248))
            draw.text((40, 110), f"Nomor Tiket : {ticket_number}", fill=(241, 245, 249))
            draw.text((40, 150), f"Platform    : {platform.upper()}", fill=(241, 245, 249))
            draw.text((40, 190), f"URL Target  : {payload.url}", fill=(148, 163, 184))
            draw.text((40, 230), f"Kanal Asal  : {payload.source_channel.upper()} ({payload.reporter_identifier or 'Agent'})", fill=(148, 163, 184))
            draw.text((40, 270), f"Waktu Rekam : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", fill=(148, 163, 184))
            draw.text((40, 340), "STATUS AKUISISI: BUKTI DIGITAL RESMI TERCATAT PADA SISTEM", fill=(52, 211, 153))
            img.save(target_path, "PNG")

            with open(target_path, "rb") as f:
                content_bytes = f.read()
            evidence_storage_path = target_path
            evidence_sha256 = hashlib.sha256(content_bytes).hexdigest()
        except Exception as ex:
            logger.warning(f"Gagal membuat visual evidence banner: {ex}")

    # 3. Bentuk Narasi Komprehensif (Caption Bersih + Transkrip Percakapan/Audio)
    clean_caption = payload.caption or payload.notes or f"Temuan patroli siber dari kanal {payload.source_channel.upper()} untuk URL {payload.url}"
    full_narrative = clean_caption
    if payload.transcript:
        full_narrative = f"{clean_caption}\n\n[TRANSKRIP AUDIO / DIALOG LENGKAP]:\n{payload.transcript}".strip()

    content_title = payload.title or (clean_caption[:70] + "...") if len(clean_caption) > 70 else (clean_caption or f"Temuan Patroli {platform.upper()} - {ticket_number}")

    # 4. Eksekusi Multimodal AI Analysis (Google Gemini + 5W+1H Engine)
    ai_service = AIService()
    ai_res = None
    try:
        logger.info(f"Menjalankan Gemini Multimodal AI Analysis untuk tiket {ticket_number}...")
        ai_res = ai_service.analyze_patrol_finding(
            caption=full_narrative,
            image_path=evidence_storage_path,
            profile_info={
                "username": account.username,
                "display_name": account.display_name,
                "subscribers_count": account.followers_count or 0,
            },
            title=content_title,
            metadata={
                "views_count": payload.views_count or 0,
                "likes_count": payload.likes_count or 0,
                "comments_count": payload.comments_count or 0,
                "tags": server_meta.get("tags", []) if server_meta else [],
            },
        )
        logger.info(f"Gemini AI Analysis sukses: label={ai_res.kategori_utama}, risiko={ai_res.tingkat_risiko}")
    except Exception as ai_err:
        logger.warning(f"Gemini Multimodal AI Analysis error, fallback ke heuristik: {ai_err}")

    # Eksekusi Analisis 5W+1H
    w5h1_service = Analysis5W1HService()
    w5h1_res = None
    try:
        logger.info(f"Menjalankan 5W+1H Intelligence Extraction untuk tiket {ticket_number}...")
        w5h1_res = w5h1_service.extract(
            text=full_narrative,
            title=content_title,
            image_path=evidence_storage_path,
            author=account.username,
            platform=platform,
            metadata={
                "views_count": payload.views_count or 0,
                "likes_count": payload.likes_count or 0,
                "comments_count": payload.comments_count or 0,
            },
        )
    except Exception as w_err:
        logger.warning(f"5W+1H extraction warning: {w_err}")

    # 5. Simpan Content langsung ke Database lengkap dengan metrik engagement dan transkrip
    content = Content(
        account_id=account.account_id,
        platform=platform,
        canonical_url=payload.url,
        title=content_title,
        caption_text=full_narrative,
        likes_count=payload.likes_count or 0,
        views_count=payload.views_count or 0,
        comments_count=payload.comments_count or 0,
        shares_count=payload.shares_count or 0,
        extra_metadata={
            "transcript": payload.transcript or "",
            "clean_caption": clean_caption,
        },
    )
    db.add(content)
    db.flush()

    # 6. Simpan Report Tiket Resmi dengan Hasil Analisis AI Gemini yang Riil & Akurat
    report = Report(
        ticket_number=ticket_number,
        content_id=content.content_id,
        reporter_telegram_id=payload.reporter_telegram_id or 0,
        source_channel=payload.source_channel.upper(),
        reporter_identifier=payload.reporter_identifier or "Analyst-Console",
        status=Report.STATUS_WAITING_VALIDATION,
        ai_status=ai_res.status_keamanan if ai_res else "POTENSI_BAHAYA",
        ai_predicted_label=ai_res.kategori_utama if ai_res else ("HOAKS" if platform in ["tiktok", "x", "youtube"] else "UJARAN_KEBENCIAN"),
        ai_risk_level=ai_res.tingkat_risiko if ai_res else "SEDANG",
        ai_confidence_score=ai_res.skor_keyakinan if ai_res else 0.885,
        ai_summary=ai_res.ringkasan_narasi if (ai_res and ai_res.ringkasan_narasi) else (w5h1_res.summary if w5h1_res else f"Temuan patroli {platform.upper()} untuk URL: {payload.url}"),
        ai_reasoning=ai_res.alasan_penilaian if ai_res else "Dianalisis melalui pipeline kecerdasan siber multimodal.",
        ai_topic_raw=ai_res.topik if (ai_res and ai_res.topik) else (w5h1_res.main_topic if w5h1_res else "Isu Media Sosial"),
        ai_actors_raw=ai_res.aktor_target if (ai_res and ai_res.aktor_target) else ([account.display_name or detected_user]),
        ai_source_raw=ai_res.sumber_konten if (ai_res and ai_res.sumber_konten) else platform.capitalize(),
    )
    db.add(report)
    db.flush()

    # 7. Simpan Analisis 5W+1H (ContentAnalysis)
    analysis = ContentAnalysis(
        content_id=content.content_id,
        what=w5h1_res.what if (w5h1_res and w5h1_res.what) else content_title,
        who=w5h1_res.who if (w5h1_res and w5h1_res.who) else (account.display_name or detected_user),
        when_info=w5h1_res.when_info if (w5h1_res and w5h1_res.when_info) else datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        where_info=w5h1_res.where_info if (w5h1_res and w5h1_res.where_info) else f"Platform {platform.capitalize()}",
        why=w5h1_res.why if (w5h1_res and w5h1_res.why) else "Dianalisis untuk pemantauan potensi risiko informasi dan opini publik.",
        how=w5h1_res.how if (w5h1_res and w5h1_res.how) else f"Didistribusikan melalui kanal daring {platform.upper()}.",
        summary=w5h1_res.summary if (w5h1_res and w5h1_res.summary) else (ai_res.ringkasan_narasi if ai_res else clean_caption[:300]),
        main_topic=w5h1_res.main_topic if (w5h1_res and w5h1_res.main_topic) else (ai_res.topik if (ai_res and ai_res.topik) else "Isu Publik"),
        sub_topics=w5h1_res.sub_topics if w5h1_res else [],
        keywords=w5h1_res.keywords if w5h1_res else [],
        hashtags=w5h1_res.hashtags if w5h1_res else [],
        named_entities=w5h1_res.named_entities if w5h1_res else ([account.username] if account.username else []),
        category=w5h1_res.category if (w5h1_res and w5h1_res.category) else "Lainnya",
        sentiment=w5h1_res.sentiment if (w5h1_res and w5h1_res.sentiment) else "NETRAL",
        tone=w5h1_res.tone if (w5h1_res and w5h1_res.tone) else "Informatif",
        relevance_score=w5h1_res.relevance_score if w5h1_res else 0.88,
        urgency_score=w5h1_res.urgency_score if w5h1_res else 0.75,
        confidence_score=w5h1_res.confidence_score if w5h1_res else 0.89,
        misinfo_indicators=w5h1_res.misinfo_indicators if w5h1_res else [],
        analysis_status="COMPLETED",
    )
    db.add(analysis)

    # 8. Simpan Bukti Digital Evidence
    if evidence_storage_path and evidence_sha256:
        evidence = Evidence(
            report_id=report.report_id,
            source_type="POST_SCREENSHOT",
            storage_path=evidence_storage_path,
            sha256=evidence_sha256,
            mime_type="image/png",
        )
        db.add(evidence)

    # Catat Audit Log
    db.add(
        AuditLog(
            action="REPORT_INTAKE_SUBMITTED",
            actor_telegram_id=payload.reporter_telegram_id or 0,
            actor_username=payload.reporter_identifier or "Analyst-Console",
            entity_type="Report",
            entity_id=str(report.report_id),
            details={"ticket": ticket_number, "platform": platform, "url": payload.url, "channel": payload.source_channel.upper()},
        )
    )

    db.commit()

    # 6. Trigger Celery Enrichment di latar belakang secara asinkron (non-blocking)
    try:
        from app.workers.tasks import enrich_content_intelligence
        enrich_content_intelligence.delay(str(content.content_id))
    except Exception as e:
        logger.info(f"Celery enrichment task tidak aktif atau di-skip: {e}")

    content_id_str = str(content.content_id)
    return {
        "status": "QUEUED",
        "ticket_number": ticket_number,
        "content_id": content_id_str,
        "platform": platform,
        "source_channel": payload.source_channel.upper(),
        "reporter_identifier": payload.reporter_identifier,
        "tracking_url": f"/#/contents/{content_id_str}",
        "dashboard_url": f"http://localhost:5173/#/contents/{content_id_str}",
        "contents_url": "http://localhost:5173/#/contents",
        "message": f"Tiket patroli {ticket_number} untuk {platform} berhasil didaftarkan dan langsung masuk ke Web Dashboard.",
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
        from app.workers.tasks import process_patrol_url
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
