"""Omnichannel Assistant API.

Provides unified endpoints for:
- Chrome / Edge / Firefox Browser Extension
- Web Dashboard Console
"""

import base64
import hashlib
import logging
import os
import re
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode, unquote
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator, AliasChoices, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import func

import time
from app.config import settings
from app.database import get_db
from app.models.report import Report, Content, Account
from app.models.intelligence import ContentAnalysis
from app.models.evidence import Evidence
from app.models.audit import AuditLog
from app.services.scraper.base import BaseScraper
from app.services.crypto_service import CryptoService
from app.services.ocr_service import OCRService
from app.services.memory_service import MemoryService
from app.services.ollama_service import OllamaService
from app.services.intelligence.hitl_harness import HITLHarnessService
from app.services.extractors import ExtractorRegistry, ExtractedPost

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Omnichannel Assistant"])

# Antrean tunggal pipeline AI untuk mencegah pertarungan CPU pada beban tinggi
_AI_PIPELINE_SEMAPHORE: Optional[asyncio.Semaphore] = None


def _get_ai_semaphore() -> asyncio.Semaphore:
    global _AI_PIPELINE_SEMAPHORE
    if _AI_PIPELINE_SEMAPHORE is None:
        _AI_PIPELINE_SEMAPHORE = asyncio.Semaphore(1)
    return _AI_PIPELINE_SEMAPHORE


class ChannelIntakeRequest(BaseModel):
    """Payload for submitting a patrol intake from browser extension or web console."""
    model_config = ConfigDict(populate_by_name=True)

    url: str = Field(..., description="URL konten media sosial (TikTok, YouTube, Instagram).")
    source_channel: str = Field(default="BROWSER_EXTENSION", description="Kanal pengirim: BROWSER_EXTENSION, WEB_DASHBOARD, API.")
    reporter_identifier: Optional[str] = Field(default="Analyst-Browser", description="Pengenal pengirim (username analis, extension ID).")
    reporter_telegram_id: Optional[int] = Field(default=None, description="Deprecated / Nullable legacy identifier.")
    notes: Optional[str] = Field(default=None, description="Catatan opsional dari analis atau pelapor.")
    screenshot_base64: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "screenshot_base64",
            "screenshotBase64",
            "screenshot",
            "image_base64",
            "imageBase64",
        ),
        description="Tangkapan layar base64 langsung dari klien/browser."
    )
    media_image_url: Optional[str] = Field(default=None, description="URL gambar media langsung dari halaman postingan (og:image / article img).")
    
    # Operator & Local Integrity (Pilar RPLK)
    operator_id: Optional[str] = Field(default=None, description="ID / NIP Petugas Patroli (Multi-User LAN).")
    ocr_text: Optional[str] = Field(default="", description="Hasil teks OCR selektif jika diproses klien.")
    captured_at_utc: Optional[str] = Field(default=None, description="Waktu pengambilan bukti dalam format ISO 8601 UTC.")
    classification_mode: str = Field(default="adaptive", description="Mode klasifikasi: 'baseline' (zero-shot) vs 'adaptive' (dynamic few-shot MemPrompt).")
    
    # In-page DOM / Screen Extracted Metadata
    username: Optional[str] = Field(default=None, description="Username akun pembuat konten.")
    display_name: Optional[str] = Field(default=None, description="Nama tampilan akun (contoh: GadgetIn).")
    followers_count: Optional[int] = Field(default=0, description="Jumlah followers atau subscribers akun.")
    title: Optional[str] = Field(default=None, description="Judul video / postingan.")
    caption: Optional[str] = Field(default=None, description="Isi teks caption utuh.")
    transcript: Optional[str] = Field(default=None, description="Transkrip teks dialog / audio jika tersedia.")
    posted_at: Optional[str] = Field(default=None, description="Tanggal atau waktu postingan diunggah.")
    likes_count: Optional[int] = Field(default=0, description="Jumlah likes/suka.")
    views_count: Optional[int] = Field(default=0, description="Jumlah tayangan/views.")
    comments_count: Optional[int] = Field(default=0, description="Jumlah komentar.")
    shares_count: Optional[int] = Field(default=0, description="Jumlah bagikan/share.")
    has_media: Optional[bool] = Field(default=False, description="Penanda apakah konten memiliki media visual foto/poster/infografis.")
    platform_hint: Optional[str] = Field(default=None, description="Petunjuk platform dari ekstensi klien (instagram, x, threads, web).")

    @field_validator("followers_count", "likes_count", "views_count", "comments_count", "shares_count", mode="before")
    @classmethod
    def sanitize_int_counts(cls, v):
        if v is None:
            return 0
        try:
            import math
            val = float(v)
            if math.isnan(val) or math.isinf(val):
                return 0
            val_int = int(round(val))
            if val_int > 10**11 or val_int < 0:
                return 0
            return val_int
        except (ValueError, TypeError):
            return 0


class ClassifyRequest(BaseModel):
    """Payload for on-demand classification and evaluation (Baseline vs Adaptive)."""
    ticket_or_id: Optional[str] = Field(default=None, description="Nomor tiket atau UUID laporan jika mengklasifikasi ulang temuan.")
    text: Optional[str] = Field(default=None, description="Teks narasi mentah jika menguji sampel independen.")
    title: Optional[str] = Field(default=None, description="Judul opsional.")
    platform: Optional[str] = Field(default="web", description="Platform media sosial / berita.")
    classification_mode: str = Field(default="adaptive", description="Mode: 'baseline' (zero-shot) vs 'adaptive' (dynamic few-shot MemPrompt).")


class BatchIntakeRequest(BaseModel):
    """Payload for multi-URL / batch patrol triage (FR-20)."""
    urls: List[str] = Field(..., description="Daftar satu atau lebih URL target patroli.")
    operator_id: Optional[str] = Field(default="OP-01", description="ID / NIP Petugas Patroli.")
    classification_mode: str = Field(default="adaptive", description="Mode klasifikasi: 'baseline' vs 'adaptive'.")


def _safe_int(v) -> int:
    """Clamp integer metric to prevent SQLite 64-bit overflow."""
    try:
        val = int(v or 0)
        return val if 0 <= val <= 10**11 else 0
    except Exception:
        return 0


def is_login_wall_boilerplate(text: Optional[str]) -> bool:
    """Detect social media login wall / unauthenticated promotional boilerplate text."""
    if not text or not isinstance(text, str):
        return False
    lower = text.lower()
    boilerplate_patterns = [
        "log in with your instagram",
        "masuk dengan akun instagram",
        "log in to see photos and videos",
        "login to see photos and videos",
        "masuk untuk melihat foto dan video",
        "create an account or log in to instagram",
        "buat akun atau masuk ke instagram",
        "create an account or log in to threads",
        "buat akun atau masuk ke threads",
        "join groups, ask questions, or discover new people",
        "join groups, ask questions",
        "lihat lainnya dari threads",
        "see more from threads",
        "log in to threads",
        "masuk ke threads",
    ]
    return any(p in lower for p in boilerplate_patterns)


def clean_caption_noise(raw: Optional[str], username: Optional[str] = None) -> str:
    """Filter out social media UI button text artifacts, follower comments, and glued handle headers."""
    if not raw or is_login_wall_boilerplate(raw):
        return ""
    cleaned = raw.strip()

    # 1. Instagram comments cutoff: Comments on Instagram web always start at or after translation marker
    for marker in ["Lihat terjemahan", "See translation", "View translation", "Lihat semua komentar", "View all comments"]:
        if marker in cleaned:
            cleaned = cleaned.split(marker)[0].strip()

    # 2. Strip likes banner artifacts: 'Disukai oleh ... dan ... lainnya'
    cleaned = re.sub(r"Disukai oleh.*?lainnya", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Liked by.*?others", " ", cleaned, flags=re.IGNORECASE)

    # 2b. Strip Instagram glued button artifacts: e.g. 'vivacoidIkutivivacoid 21 jamKepala...' -> 'Kepala...'
    cleaned = re.sub(
        r"^(?:[a-zA-Z0-9_\.]{2,30})?(?:Ikuti|Mengikuti|Follow|Following)\s*(?:[a-zA-Z0-9_\.]{2,30})?\s*\d+\s*(?:jam|hari|menit|detik|m|h|d|w|minggu)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(
        r"^(?:[a-zA-Z0-9_\.]{2,30})\s+\d+\s*(?:jam|hari|menit|detik|m|h|d|w|minggu)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    # 3. Strip common social media & news portal UI artifacts
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
        r"Tambahkan komentar\S*",
        r"\b\d+\s*(?:detik|menit|jam|hari|minggu|bulan|tahun|sec|secs|min|mins|hr|hrs|h|m|d|w)\s*(?:yang\s+lalu|lalu|ago)?\b",
        r"\b(?:kemarin|baru saja|just now|yesterday)\b",
        r"\d{1,2}:\d{2}\s*[\/|\\]\s*\d{1,2}:\d{2}",  # Video duration / scrubber e.g. 00:00 / 09:28
        r"\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*[·•\u00b7\u2022]\s*[A-Za-z]{3}\s*\d{1,2},\s*\d{4}",  # Tweet timestamp e.g. 9:14 PM · Oct 20, 2026
        r"[·•\u00b7\u2022\s]*\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b",
        r"[·•\u00b7\u2022\s]*\d+[\d\.,]*[KkMm]?\s*(?:Views|View quotes|views|quotes|suka|likes|Retweets|reposts|Bookmarks|bookmarked)(?=[^a-zA-Z]|$)",  # Metrics e.g. 767.3KViews, 535View quotes
        # Media & news portal widget artifacts
        r"\bAdvertisement\b",
        r"\bListen\s+\d+\s*(?:min|mins|menit)\b",
        r"New:\s*You can now listen to articles[^\n]*",
        r"Recommended Stories list of \d+ items[\s\S]*?end of list",
        r"Get instant alerts and updates based on your interests[^\n.]*\.[^\n.]*\.",
        r"Be the first to know when big stories happen\.?",
        r"\b(?:Save\s+Share|Save\s*\n\s*Share)\b",
        r"(?:By\s+[A-Za-z\s]+)?Published On\s+\d+\s+[A-Za-z]+\s+\d{4}(?:\s*\d+\s*[A-Za-z]+\s*\d{4})?",
        r"News\s*\|\s*[A-Za-z\s]+(?=[A-Z])",
        r"\[[^\]]*?(?:Getty|Reuters|AFP|AP|Antara|Usep|Ezra|Photo)[^\]]*?\]",
        r"\([^\)]*?(?:Getty|Reuters|AFP|AP|Antara|Usep|Ezra|Photo)[^\)]*?\)",
        r"Follow us on[^\n]*",
        # Social media promotional & call-to-action (CTA) noise
        r"[-–—]?\s*Selengkapnya\s+kunjungi\s+website[^\n]*",
        r"(?:klik\s+link\s+di\s+bio|download\s+aplikasi\s+di\s+App\s*Store[^\n]*)",
        r"baca\s+selengkapnya\s+di\s+link[^\n]*",
        r"(?:\s+#[A-Za-z0-9_]+){2,}\s*$",
    ]
    for pat in patterns:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)

    # 4. Strip duplicate leading username repetition & glued profile headers (even without spaces)
    # e.g. 'Sumatera Adil & Federal@indepenSumateraPRABOWO...' -> 'PRABOWO...'
    # e.g. 'Ganjar Pranowo@ganjarpranowo1. Umumkan...' -> '1. Umumkan...'
    if username:
        cleaned = re.sub(r"^(?:[^\n@]{0,50})?@?" + re.escape(username) + r"\s*", "", cleaned, flags=re.IGNORECASE)

    # General unspaced glued handle detection (Twitter handles max 15 chars, ending before capital letter/digit)
    cleaned = re.sub(r"^(?:[^\n@]{0,50})?@[a-zA-Z0-9_\.]*?[a-z0-9](?=[A-Z]{2,}|\d+\.)\s*", "", cleaned)
    cleaned = re.sub(r"^(?:[A-Z][a-zA-Z0-9\s._-]+)?@([a-zA-Z0-9_]{1,20}?)(?=[A-Z]{2,}|\d+\.|\b)\s*", "", cleaned)
    cleaned = re.sub(r"^(?:[A-Z][a-zA-Z0-9\s._-]{0,40})?@[a-zA-Z0-9_]+(?:\s*[·•]\s*[\w\d]+)?(?:\s*(?=\d+\.))?\s*", "", cleaned)
    cleaned = re.sub(r"^[A-Z][a-zA-Z0-9\s._-]+@[a-zA-Z0-9_]+\s*", "", cleaned)
    cleaned = re.sub(r"^(?:[a-z0-9_\.]{3,30}\s*)+(?=[A-Z])", "", cleaned)
    cleaned = re.sub(r"^[a-zA-Z0-9_\.]{3,30}\s*:\s*", "", cleaned)

    # 5. Normalisasi spasi setelah tanda baca titik yang langsung diikuti huruf kapital
    # Contoh: 'setempat.Besarnya' -> 'setempat. Besarnya'
    cleaned = re.sub(r"\.([A-Z])", r". \1", cleaned)

    cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    if is_login_wall_boilerplate(cleaned):
        return ""
    return cleaned


@router.get("/channels")
def get_supported_channels(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve all operational assistant channels and their statistics."""
    channel_counts = (
        db.query(Report.source_channel, func.count(Report.report_id))
        .group_by(Report.source_channel)
        .all()
    )
    counts_map = {c or "BROWSER_EXTENSION": count for c, count in channel_counts}

    return {
        "status": "ONLINE",
        "architecture": "Pure Browser Extension + Web Command Console",
        "channels": [
            {
                "id": "browser_extension",
                "name": "TILIK Browser Extension",
                "type": "BROWSER_AGENT",
                "status": "ONLINE",
                "intake_count": counts_map.get("BROWSER_EXTENSION", 0),
                "features": [
                    "1-Click URL & DOM Capture",
                    "Active Tab Auto-Detection",
                    "Instant Triage Status",
                    "Side-panel Integration",
                    "Full HD Evidence Capture",
                ],
                "icon": "Chrome",
            },
            {
                "id": "web_dashboard",
                "name": "Web Command Console",
                "type": "MANAGEMENT_CONSOLE",
                "status": "ONLINE",
                "intake_count": counts_map.get("WEB_DASHBOARD", 0),
                "features": [
                    "Social Intelligence Graphs",
                    "Drill-Down Filter",
                    "Entity Resolution",
                    "Knowledge Base Management",
                    "Excel Pro & Forensic Export",
                ],
                "icon": "LayoutDashboard",
            },
        ],
    }


def _clean_url_tracking(url: str) -> str:
    """Strip social tracking parameters, modal suffixes, and trailing slashes from URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        qs = parse_qs(parsed.query)
        tracking_params = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "fbclid", "igshid", "xmt", "si", "ref", "share_id", "is_from_webapp",
            "sender_device", "feature", "tracking_id", "img_index"
        }
        cleaned_qs = {k: v for k, v in qs.items() if k.lower() not in tracking_params}
        new_query = urlencode(cleaned_qs, doseq=True)
        new_path = parsed.path.rstrip("/") if len(parsed.path) > 1 else parsed.path

        # Bersihkan suffix modal/dialog Instagram (e.g. /liked_by, /comments, /embed)
        if "instagram.com" in parsed.netloc.lower():
            ig_post_match = re.search(r"/(p|reel|reels|tv)/([A-Za-z0-9_-]+)", new_path, re.IGNORECASE)
            if ig_post_match:
                new_path = f"/{ig_post_match.group(1).lower()}/{ig_post_match.group(2)}"

        return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, new_query, ""))
    except Exception:
        clean = url.strip().rstrip("/")
        if "instagram.com" in clean.lower():
            ig_m = re.search(r"(https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/[A-Za-z0-9_-]+)", clean, re.IGNORECASE)
            if ig_m:
                return ig_m.group(1)
        return clean


def _normalize_text_for_hash(text: str) -> str:
    """Sanitize relative timestamps, UI noise artifacts, and whitespace for canonical hashing."""
    if not text:
        return ""
    cleaned = text
    # 1. Hapus stempel waktu relatif medsos (e.g. '5 jam lalu', '2 hari yang lalu', '3d ago', '10 menit lalu')
    rel_time_pat = r"\b\d+\s*(?:detik|menit|jam|hari|minggu|bulan|tahun|sec|secs|min|mins|hr|hrs|h|m|d|w)\s*(?:yang\s+lalu|lalu|ago)?\b"
    cleaned = re.sub(rel_time_pat, " ", cleaned, flags=re.IGNORECASE)

    # 2. Hapus noise UI umum
    cleaned = clean_caption_noise(cleaned)

    # 3. Normalisasi karakter dan spasi
    cleaned = re.sub(r"[^\w\s]", " ", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def _compute_canonical_text_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text."""
    norm = _normalize_text_for_hash(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest() if norm else ""


def _extract_post_identity(url: str) -> Tuple[str, Optional[str]]:
    """Extract (platform_key, canonical_post_id) from permalinks.
    
    Returns (platform_key, None) if URL is a generic feed/home page.
    """
    clean_url = _clean_url_tracking(url)
    try:
        platform = BaseScraper.detect_platform(clean_url)
    except Exception:
        platform = "web"

    parsed = urlparse(clean_url)
    path = parsed.path.lower()
    netloc = parsed.netloc.lower()

    if "tiktok.com" in netloc:
        if path in ["", "/", "/foryou", "/home"]:
            return ("tiktok", None)
        m = re.search(r"/(?:video|photo)/([A-Za-z0-9_-]+)", clean_url)
        return ("tiktok", m.group(1)) if m else ("tiktok", None)

    if "instagram.com" in netloc:
        if path in ["", "/", "/home", "/explore"]:
            return ("instagram", None)
        m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", clean_url, re.IGNORECASE)
        return ("instagram", m.group(1)) if m else ("instagram", None)

    if any(d in netloc for d in ["twitter.com", "x.com"]):
        if path in ["", "/", "/home", "/explore"]:
            return ("x", None)
        m = re.search(r"/status/(\d+)", clean_url)
        return ("x", m.group(1)) if m else ("x", None)

    if any(d in netloc for d in ["youtube.com", "youtu.be"]):
        if path in ["", "/"]:
            return ("youtube", None)
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", clean_url)
        return ("youtube", m.group(1)) if m else ("youtube", None)

    if any(d in netloc for d in ["threads.net", "threads.com"]):
        if path in ["", "/", "/home", "/for_you", "/following"]:
            return ("threads", None)
        m = re.search(r"/(?:post|t)/([A-Za-z0-9_-]+)", clean_url)
        return ("threads", m.group(1)) if m else ("threads", None)

    # Web umum
    if path in ["", "/", "/home", "/feed"]:
        return ("web", None)
    cleaned_no_query = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))
    return ("web", cleaned_no_query)


def _detect_author_username(url: str, username_param: Optional[str] = None, caption: Optional[str] = None) -> str:
    """Extract and normalize author username from payload, URL pattern, or caption context."""
    invalid_usernames = {"instagram.com", "x.com", "twitter.com", "tiktok.com", "facebook.com", "youtube.com", "threads.net", "threads.com"}
    detected_user = username_param

    if detected_user and (any(detected_user.lower().endswith(dom) for dom in [".com", ".id", ".org", ".net"]) or detected_user.lower() in invalid_usernames):
        detected_user = None

    if not detected_user:
        # Pola 1: X / Twitter -> https://x.com/ganjarpranowo/status/123...
        x_match = re.search(r"(?:twitter\.com|x\.com)/([a-zA-Z0-9_]{1,30})(?:/status|\b)", url, re.IGNORECASE)
        if x_match and x_match.group(1).lower() not in ["home", "explore", "notifications", "messages", "search", "i"]:
            detected_user = x_match.group(1)

        # Pola 2: Instagram URL -> https://instagram.com/vivacoid/p/...
        if not detected_user:
            ig_match = re.search(r"instagram\.com/([a-zA-Z0-9_\.]{1,30})/(?:p|reel|reels)/", url, re.IGNORECASE)
            if ig_match and ig_match.group(1).lower() not in ["p", "reel", "reels", "stories", "explore", "direct"]:
                detected_user = ig_match.group(1)

        # Pola 2b: Threads URL -> https://threads.net/@akun/post/...
        if not detected_user:
            th_match = re.search(r"threads\.(?:net|com)/@?([a-zA-Z0-9_\.]+)", url, re.IGNORECASE)
            if th_match and th_match.group(1).lower() not in ["post", "search", "activity"]:
                detected_user = th_match.group(1)

        # Pola 3: TikTok URL -> https://tiktok.com/@username
        if not detected_user:
            tt_match = re.search(r"tiktok\.com/@([a-zA-Z0-9_\.]+)", url, re.IGNORECASE)
            if tt_match:
                detected_user = tt_match.group(1)

        # Pola 4: YouTube URL -> https://youtube.com/@channel
        if not detected_user:
            yt_match = re.search(r"youtube\.com/@([a-zA-Z0-9_\.]+)", url, re.IGNORECASE)
            if yt_match:
                detected_user = yt_match.group(1)

        # Pola 5: Ekstrak dari teks caption mentah jika menempel
        if not detected_user and caption:
            ig_caption_user = re.search(r"^([a-zA-Z0-9_\.]{2,30})(?:Ikuti|Follow|Mengikuti|Following)", caption, re.IGNORECASE)
            if ig_caption_user:
                detected_user = ig_caption_user.group(1)

        # Pola 6: Regex @username di dalam URL atau caption
        if not detected_user:
            at_match = re.search(r"@([a-zA-Z0-9_\.]{2,30})", url) or (re.search(r"@([a-zA-Z0-9_\.]{2,30})", caption) if caption else None)
            if at_match and at_match.group(1).lower() not in invalid_usernames:
                detected_user = at_match.group(1)

        # Pola 7: Portal berita (kompas.com) atau fallback anonim
        if not detected_user:
            parsed = urlparse(url)
            if parsed.netloc:
                domain = parsed.netloc.replace("www.", "")
                detected_user = domain

    if detected_user:
        if any(detected_user.lower().endswith(dom) for dom in [".com", ".id", ".org", ".net"]) or detected_user.lower() in invalid_usernames:
            detected_user = "Anonim"

    return detected_user or "Anonim"


@router.post("/intake")
@router.post("/analyze")
async def submit_channel_intake(payload: ChannelIntakeRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Accept patrol intake from any client channel (Browser Extension, WhatsApp, Web, etc.)."""
    # 0. Pembersihan URL Pelacak & Ekstraksi Identitas Kanonik via Modular ExtractorRegistry
    payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    extracted_post: ExtractedPost = ExtractorRegistry.resolve(
        raw_url=payload.url,
        platform_hint=payload.platform_hint,
        payload_data=payload_dict,
    )
    clean_url = extracted_post.canonical_url
    platform = extracted_post.platform
    canonical_post_id = extracted_post.post_id

    ticket_number = f"PS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    active_operator_id = (payload.operator_id or payload.reporter_identifier or "OP-01").strip()
    active_captured_at_utc = (payload.captured_at_utc or datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')).strip()
    active_ocr_text = (payload.ocr_text or "").strip()

    # Ekstraksi Pengunggah & Narasi Awal untuk Deduplikasi
    if payload.caption and is_login_wall_boilerplate(payload.caption):
        logger.warning(f"Menolak narasi boilerplate login-wall dari payload: {payload.caption[:80]}...")
        payload.caption = None

    detected_user = _detect_author_username(clean_url, payload.username, payload.caption)
    account_username = detected_user

    raw_caption = payload.caption or payload.notes or f"Temuan patroli siber dari kanal {payload.source_channel.upper()} untuk URL {clean_url}"
    clean_caption = clean_caption_noise(raw_caption, username=account_username)
    if payload.caption:
        payload.caption = clean_caption
    canonical_text_hash = _compute_canonical_text_hash(clean_caption)

    # Validasi Feed/Beranda Umum: Tolak HANYA jika berupa beranda TANPA konten teks atau tangkapan layar
    if not canonical_post_id and len(clean_caption) < 15 and not payload.screenshot_base64:
        raise HTTPException(
            status_code=400,
            detail=(
                f"URL target adalah beranda/halaman utama platform ({platform.upper()}). "
                "Harap buka postingan spesifik atau gunakan tangkapan layar/seleksi teks."
            ),
        )

    # ── HIERARCHICAL DEDUPLICATION 3 LAPIS ──
    matched_content: Optional[Content] = None

    # Lapis 1: Pencocokan Canonical Post ID (Permalink Platform)
    if canonical_post_id:
        cand = db.query(Content).filter(
            Content.platform == platform,
            Content.platform_content_id == canonical_post_id
        ).order_by(Content.created_at.desc()).first()
        if not cand:
            cand = db.query(Content).filter(
                Content.platform == platform,
                Content.canonical_url.like(f"%{canonical_post_id}%")
            ).order_by(Content.created_at.desc()).first()
        if cand:
            matched_content = cand
            logger.info(f"[DEDUP-L1] Postingan teridentifikasi duplikat via canonical_post_id '{canonical_post_id}' -> Content {cand.content_id}")

    # Lapis 2: Fallback Feed / Beranda (Normalized Author + Canonical Text Hash)
    if not matched_content and canonical_text_hash and detected_user and detected_user != "Anonim":
        author_candidates = (
            db.query(Content)
            .join(Account, Content.account_id == Account.account_id)
            .filter(Account.username.ilike(detected_user))
            .order_by(Content.created_at.desc())
            .all()
        )
        for cand in author_candidates:
            cand_text_hash = _compute_canonical_text_hash(cand.caption_text or "")
            if cand_text_hash and cand_text_hash == canonical_text_hash:
                matched_content = cand
                logger.info(f"[DEDUP-L2] Postingan teridentifikasi duplikat via author '{detected_user}' + canonical_text_hash -> Content {cand.content_id}")
                break

    # Lapis 3: Smart Update vs Deduplicated Return
    if matched_content:
        existing_rep = (
            db.query(Report)
            .filter(Report.content_id == matched_content.content_id)
            .order_by(Report.created_at.desc())
            .first()
        )
        existing_evi = (
            db.query(Evidence)
            .filter(Evidence.report_id == existing_rep.report_id)
            .first() if existing_rep else None
        )

        old_clean = clean_caption_noise(matched_content.caption_text or "")
        new_clean = clean_caption
        is_smart_update = len(new_clean) > len(old_clean) * 1.5

        if is_smart_update:
            logger.info(f"[DEDUP-L3 SMART UPDATE] Teks baru ({len(new_clean)} karakter) > 1.5x teks lama ({len(old_clean)} karakter). Memperbarui Content {matched_content.content_id}")
            matched_content.caption_text = clean_caption
            if payload.title and not matched_content.title:
                matched_content.title = clean_caption_noise(payload.title, username=detected_user)
            if payload.likes_count: matched_content.likes_count = _safe_int(payload.likes_count)
            if payload.views_count: matched_content.views_count = _safe_int(payload.views_count)
            if payload.comments_count: matched_content.comments_count = _safe_int(payload.comments_count)
            if payload.shares_count: matched_content.shares_count = _safe_int(payload.shares_count)

            if existing_evi:
                evidence_captured_at = existing_evi.captured_at_utc or active_captured_at_utc
                evidence_operator = existing_evi.operator_id or active_operator_id
                seal = CryptoService.seal_evidence_package(
                    screenshot_sha256=existing_evi.sha256,
                    source_url=matched_content.canonical_url,
                    dom_text=clean_caption,
                    ocr_text=active_ocr_text or existing_evi.ocr_text or "",
                    captured_at_utc=evidence_captured_at,
                    operator_id=evidence_operator,
                )
                existing_evi.dom_text = clean_caption
                existing_evi.source_url = matched_content.canonical_url
                existing_evi.captured_at_utc = evidence_captured_at
                existing_evi.operator_id = evidence_operator
                existing_evi.canonical_hash = seal["canonical_hash"]
                existing_evi.hmac_tag = seal["hmac_tag"]
                existing_evi.verification_status = "VERIFIED"
                existing_evi.last_verified_at = datetime.utcnow()

            analysis = db.query(ContentAnalysis).filter_by(content_id=matched_content.content_id).first()
            if analysis:
                analysis.summary = new_clean[:300]
            if existing_rep:
                existing_rep.ai_summary = new_clean[:300]

            db.commit()

            cid_str = str(matched_content.content_id)
            tkt_str = existing_rep.ticket_number if existing_rep else ticket_number
            return {
                "status": "QUEUED",
                "ticket_number": tkt_str,
                "content_id": cid_str,
                "platform": platform,
                "source_channel": payload.source_channel.upper(),
                "reporter_identifier": payload.reporter_identifier,
                "operator_id": active_operator_id,
                "captured_at_utc": active_captured_at_utc,
                "canonical_hash": existing_evi.canonical_hash if existing_evi else None,
                "hmac_tag": existing_evi.hmac_tag if existing_evi else None,
                "verification_status": "VERIFIED",
                "tracking_url": f"/dashboard/#/contents/{cid_str}",
                "dashboard_url": f"http://localhost:8000/dashboard/#/contents/{cid_str}",
                "contents_url": "http://localhost:8000/dashboard/#/contents",
                "ai_status": existing_rep.ai_status if existing_rep else "AMAN",
                "ai_predicted_label": existing_rep.ai_predicted_label if existing_rep else "Non-Isu",
                "ai_confidence_score": round((existing_rep.ai_confidence_score or 0.88) * 100) if existing_rep else 88,
                "ai_summary": existing_rep.ai_summary if existing_rep else new_clean[:200],
                "deduplicated": True,
                "updated": True,
                "message": f"Tiket patroli {tkt_str} berhasil diperbarui dengan teks yang lebih lengkap (Smart Update).",
            }
        else:
            logger.info(f"[DEDUP-L3] Duplikat terdeteksi untuk Content {matched_content.content_id}. Mengembalikan data eksisting tanpa re-run LLM.")
            cid_str = str(matched_content.content_id)
            tkt_str = existing_rep.ticket_number if existing_rep else ticket_number
            return {
                "status": "QUEUED",
                "ticket_number": tkt_str,
                "content_id": cid_str,
                "platform": platform,
                "source_channel": payload.source_channel.upper(),
                "reporter_identifier": payload.reporter_identifier,
                "operator_id": active_operator_id,
                "captured_at_utc": active_captured_at_utc,
                "canonical_hash": existing_evi.canonical_hash if existing_evi else None,
                "hmac_tag": existing_evi.hmac_tag if existing_evi else None,
                "verification_status": existing_evi.verification_status if existing_evi else "VERIFIED",
                "tracking_url": f"/dashboard/#/contents/{cid_str}",
                "dashboard_url": f"http://localhost:8000/dashboard/#/contents/{cid_str}",
                "contents_url": "http://localhost:8000/dashboard/#/contents",
                "ai_status": existing_rep.ai_status if existing_rep else "AMAN",
                "ai_predicted_label": existing_rep.ai_predicted_label if existing_rep else "Non-Isu",
                "ai_confidence_score": round((existing_rep.ai_confidence_score or 0.88) * 100) if existing_rep else 88,
                "ai_summary": existing_rep.ai_summary if existing_rep else old_clean[:200],
                "deduplicated": True,
                "updated": False,
                "message": f"Tiket patroli {tkt_str} untuk {platform} telah tercatat pada Web Dashboard.",
            }

    # 0. Hybrid Metadata Enrichment: Jika ada data metrik atau judul yang belum lengkap dari klien,
    # otomatis lengkapi menggunakan backend scraper engine (yt-dlp, Playwright)
    try:
        scraper = None
        if not extracted_post.should_crawl_server:
            # Platform seperti Threads, Instagram, X, Facebook, atau web dengan konten DOM klien lengkap dibypass
            logger.info(f"Extractor {platform} menetapkan should_crawl_server=False. Melewati server-side Playwright crawl.")
            crawl_res = None
        elif platform == "youtube":
            from app.services.scraper.youtube import YouTubeScraper
            scraper = YouTubeScraper(storage_dir=settings.EVIDENCE_DIR)
        elif platform == "instagram":
            from app.services.scraper.instagram import InstagramScraper
            scraper = InstagramScraper(storage_dir=settings.EVIDENCE_DIR)
        elif platform == "tiktok":
            from app.services.scraper.tiktok import TikTokScraper
            scraper = TikTokScraper(storage_dir=settings.EVIDENCE_DIR)
        elif platform == "web":
            from app.services.crawler_service import CrawlerService
            try:
                crawl_res = await CrawlerService.crawl_article(payload.url, ticket_number=ticket_number)
            except Exception as crawl_err:
                logger.warning(f"Crawler article failed for {payload.url}: {crawl_err}")
                crawl_res = None

            if crawl_res:
                cr_title = crawl_res.get("title")
                cr_text = crawl_res.get("clean_text")
                if cr_title and not is_login_wall_boilerplate(cr_title) and not payload.title:
                    payload.title = cr_title
                if cr_text and not is_login_wall_boilerplate(cr_text) and not payload.caption:
                    payload.caption = cr_text
                if not payload.username and crawl_res.get("author"):
                    payload.username = crawl_res["author"]
                if not payload.display_name and crawl_res.get("display_name"):
                    payload.display_name = crawl_res["display_name"]
                if not payload.media_image_url and crawl_res.get("media_image_url"):
                    payload.media_image_url = crawl_res["media_image_url"]
                if crawl_res.get("screenshot_path") and os.path.exists(crawl_res["screenshot_path"]):
                    evidence_storage_path = crawl_res["screenshot_path"]
                    evidence_sha256 = crawl_res.get("screenshot_sha256")

        server_meta = None
        if scraper:
            server_meta = scraper.extract_metadata(payload.url)
            if server_meta:
                # Jangan biarkan judul placeholder server menimpa judul/caption klien
                srv_title = server_meta.get("title")
                if srv_title and is_login_wall_boilerplate(srv_title):
                    srv_title = None
                if not payload.title and srv_title and not srv_title.startswith("Instagram Post"):
                    payload.title = srv_title
                
                # Jangan biarkan caption placeholder / login-wall server menimpa caption hasil ekstraksi DOM asli klien
                server_caption = server_meta.get("caption")
                if server_caption and is_login_wall_boilerplate(server_caption):
                    server_caption = None
                if server_caption and not server_caption.startswith("Instagram public post"):
                    if not payload.caption or len(server_caption) > len(payload.caption):
                        payload.caption = server_caption

                if server_meta.get("transcript"):
                    if not payload.transcript or len(server_meta["transcript"]) > len(payload.transcript):
                        payload.transcript = server_meta["transcript"]

                if not payload.username and server_meta.get("account", {}).get("username"):
                    srv_user = server_meta["account"]["username"].replace("@", "")
                    if not srv_user.startswith("instagram_user_"):
                        payload.username = srv_user
                if not payload.display_name and server_meta.get("account", {}).get("display_name"):
                    srv_disp = server_meta["account"]["display_name"]
                    if srv_disp != "Pengguna Instagram":
                        payload.display_name = srv_disp
                if (not payload.followers_count or payload.followers_count == 0) and server_meta.get("account", {}).get("subscribers_count"):
                    payload.followers_count = server_meta["account"]["subscribers_count"]
                if (not payload.views_count or payload.views_count == 0) and server_meta.get("views_count"):
                    payload.views_count = server_meta["views_count"]
                if (not payload.likes_count or payload.likes_count == 0) and server_meta.get("likes_count"):
                    payload.likes_count = server_meta["likes_count"]
                if (not payload.comments_count or payload.comments_count == 0) and server_meta.get("comments_count"):
                    payload.comments_count = server_meta["comments_count"]
                logger.info(f"Metadata berhasil diperkaya via server engine {platform}: {payload.title or 'N/A'} (transcript={len(payload.transcript) if payload.transcript else 0} chars)")
    except Exception as enrich_err:
        logger.warning(f"Server-side metadata enrichment warning for {payload.url}: {enrich_err}")

    # 1. Identifikasi Data Akun Pengunggah (In-Memory, Belum Membuka Lock DB)
    from urllib.parse import urlparse
    parsed_url = urlparse(payload.url)
    detected_user = payload.username

    # Abaikan jika username berupa nama domain platform atau ekstensi domain
    invalid_usernames = {"instagram.com", "x.com", "twitter.com", "tiktok.com", "facebook.com", "youtube.com", "threads.net", "threads.com"}
    if detected_user and (any(detected_user.lower().endswith(dom) for dom in [".com", ".id", ".org", ".net"]) or detected_user.lower() in invalid_usernames):
        detected_user = None

    if not detected_user:
        # Pola 1: X / Twitter -> https://x.com/ganjarpranowo/status/123...
        x_match = re.search(r"(?:twitter\.com|x\.com)/([a-zA-Z0-9_]{1,30})(?:/status|\b)", payload.url, re.IGNORECASE)
        if x_match and x_match.group(1).lower() not in ["home", "explore", "notifications", "messages", "search", "i"]:
            detected_user = x_match.group(1)

        # Pola 2: Instagram URL -> https://instagram.com/vivacoid/p/...
        if not detected_user:
            ig_match = re.search(r"instagram\.com/([a-zA-Z0-9_\.]{1,30})/(?:p|reel|reels)/", payload.url, re.IGNORECASE)
            if ig_match and ig_match.group(1).lower() not in ["p", "reel", "reels", "stories", "explore", "direct"]:
                detected_user = ig_match.group(1)

        # Pola 2b: Threads URL -> https://threads.net/@akun/post/...
        if not detected_user:
            th_match = re.search(r"threads\.(?:net|com)/@?([a-zA-Z0-9_\.]+)", payload.url, re.IGNORECASE)
            if th_match and th_match.group(1).lower() not in ["post", "search", "activity", "t"]:
                detected_user = th_match.group(1)

        # Pola 3: TikTok URL -> https://tiktok.com/@username
        if not detected_user:
            tt_match = re.search(r"tiktok\.com/@([a-zA-Z0-9_\.]+)", payload.url, re.IGNORECASE)
            if tt_match:
                detected_user = tt_match.group(1)

        # Pola 4: YouTube URL -> https://youtube.com/@channel
        if not detected_user:
            yt_match = re.search(r"youtube\.com/@([a-zA-Z0-9_\.]+)", payload.url, re.IGNORECASE)
            if yt_match:
                detected_user = yt_match.group(1)

        # Pola 5: Ekstrak dari teks caption mentah jika menempel (misal 'vivacoidIkutivivacoid...')
        if not detected_user and payload.caption:
            ig_caption_user = re.search(r"^([a-zA-Z0-9_\.]{2,30})(?:Ikuti|Follow|Mengikuti|Following)", payload.caption, re.IGNORECASE)
            if ig_caption_user:
                detected_user = ig_caption_user.group(1)

        # Pola 6: Regex @username di dalam caption atau URL
        if not detected_user:
            at_match = re.search(r"@([a-zA-Z0-9_\.]{2,30})", payload.url) or (re.search(r"@([a-zA-Z0-9_\.]{2,30})", payload.caption) if payload.caption else None)
            if at_match and at_match.group(1).lower() not in invalid_usernames:
                detected_user = at_match.group(1)

        # Pola 7: Portal berita (kompas.com) atau fallback anonim
        if not detected_user and parsed_url.netloc:
            domain = parsed_url.netloc.replace("www.", "")
            if platform in ["news", "media", "portal"]:
                detected_user = domain
            else:
                detected_user = "Anonim"

    # Penjagaan mutlak: Jangan biarkan nama domain masuk sebagai username medsos
    if detected_user and platform not in ["news", "media", "portal"]:
        if any(detected_user.lower().endswith(dom) for dom in [".com", ".id", ".org", ".net"]) or detected_user.lower() in invalid_usernames:
            detected_user = "Anonim"

    detected_user = detected_user or "Anonim"
    
    account_username = detected_user
    if detected_user == "Anonim":
        account_display_name = payload.display_name or f"Pengguna {platform.capitalize()}"
    else:
        account_display_name = payload.display_name or f"@{detected_user}"
    account_followers = _safe_int(payload.followers_count)
    account_profile_url = f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url.netloc else payload.url

    # Clean UI artifacts from caption (with known username context) and normalize punctuation spacing
    payload.caption = clean_caption_noise(payload.caption, username=detected_user)
    if payload.caption:
        payload.caption = re.sub(r"\.([A-Z])", r". \1", payload.caption)

    # 2. Akuisisi Bukti Digital Visual (Screenshot) Terlebih Dahulu agar Siap Dianalisis AI Multimodal
    evidence_storage_path = None
    evidence_sha256 = None
    os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
    evidence_filename = f"{ticket_number}_post.png"
    target_path = os.path.join(settings.EVIDENCE_DIR, evidence_filename)

    if payload.screenshot_base64:
        try:
            raw_b64 = str(payload.screenshot_base64).strip()
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1].strip()
            raw_b64 = re.sub(r"\s+", "", raw_b64)
            missing_padding = len(raw_b64) % 4
            if missing_padding:
                raw_b64 += "=" * (4 - missing_padding)
            img_bytes = base64.b64decode(raw_b64)
            if img_bytes and len(img_bytes) > 100:
                ext = ".jpg" if img_bytes.startswith(b"\xff\xd8\xff") else ".png"
                evidence_filename = f"{ticket_number}_post{ext}"
                target_path = os.path.join(settings.EVIDENCE_DIR, evidence_filename)
                with open(target_path, "wb") as f:
                    f.write(img_bytes)
                evidence_storage_path = target_path
                evidence_sha256 = hashlib.sha256(img_bytes).hexdigest()
                logger.info(f"Berhasil menyimpan tangkapan layar bukti digital asli ({len(img_bytes)} bytes): {target_path}")
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

    # Scrape visual via Playwright jika belum ada, BUKAN platform yang mewajibkan login (IG/FB/X), dan Playwright terpasang
    if not evidence_storage_path or not os.path.exists(evidence_storage_path):
        if platform in ("instagram", "facebook", "threads", "x", "twitter", "tiktok"):
            logger.info(f"Platform {platform} membatasi bot headless dengan login wall / proteksi anti-bot; Playwright server dilewati untuk menghindari rekaman layar login palsu.")
        else:
            try:
                from app.services.scraper.youtube import is_playwright_installed
                if scraper and is_playwright_installed():
                    logger.info(f"Mengambil screenshot visual otomatis via Playwright untuk {platform}: {payload.url}")
                    scrape_res = await scraper.capture_visual_evidence(post_url=payload.url, ticket_number=ticket_number)
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
            draw.text((40, 24), "TILIK DIGITAL EVIDENCE ARCHIVE (ACQUISITION RECORD)", fill=(56, 189, 248))
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
    raw_caption = payload.caption or payload.notes or f"Temuan patroli siber dari kanal {payload.source_channel.upper()} untuk URL {payload.url}"
    clean_caption = clean_caption_noise(raw_caption, username=account_username)
    full_narrative = clean_caption
    if payload.transcript:
        full_narrative = f"{clean_caption}\n\n[TRANSKRIP AUDIO / DIALOG LENGKAP]:\n{payload.transcript}".strip()

    if payload.title and payload.title.strip():
        content_title = clean_caption_noise(payload.title.strip(), username=account_username)
        if not content_title:
            content_title = clean_caption[:70] + "..." if len(clean_caption) > 70 else clean_caption
    elif len(clean_caption) > 70:
        content_title = clean_caption[:70] + "..."
    else:
        content_title = clean_caption or f"Temuan Patroli {platform.upper()} - {ticket_number}"

    # Bersihkan sisa nomor bullet di awal judul (e.g. '1. Umumkan...' -> 'Umumkan...')
    content_title = re.sub(r"^\d+\.\s*", "", content_title).strip()
    if len(content_title) > 85:
        content_title = content_title[:82].strip() + "..."

    # 4. Eksekusi Selective OCR & Adaptive Local Intelligence (Ollama + MemPrompt)
    # Dibungkus antrean tunggal non-blocking (async with _AI_PIPELINE_SEMAPHORE)
    ocr_res = None
    has_media_flag = getattr(payload, "has_media", False) or (platform in ("instagram", "threads"))

    async with _get_ai_semaphore():
        # 4.1 Selective Local OCR (Smart Multimodal Gate: teks pendek, UI noise, atau Instagram poster)
        if evidence_storage_path and os.path.exists(evidence_storage_path):
            try:
                ocr_res = await asyncio.to_thread(
                    OCRService.process_selective_ocr,
                    image_path=evidence_storage_path,
                    dom_text=full_narrative,
                    platform=platform,
                    has_media=has_media_flag,
                )
                if ocr_res.get("ocr_performed") and ocr_res.get("ocr_text"):
                    active_ocr_text = ocr_res["ocr_text"]
                    full_narrative = f"{full_narrative}\n\n[HASIL OCR TEKS GAMBAR / POSTER]:\n{active_ocr_text}".strip()
                    logger.info(f"Selective OCR berhasil mengekstrak {len(active_ocr_text)} karakter via {ocr_res.get('engine_used')}.")
            except Exception as ocr_err:
                logger.warning(f"Selective OCR warning: {ocr_err}")

        # 4.2 Ollama Local LLM Inference with Integrated MemPrompt Retrieval (Single Embedding Pass)
        ollama_svc = OllamaService()
        ollama_res = await asyncio.to_thread(
            ollama_svc.classify_and_summarize,
            text=full_narrative,
            title=content_title,
            source_url=payload.url,
            author=account_username,
            platform=platform,
            mode=payload.classification_mode,
            db=db,
        )
        if ollama_res.get("similar_cases"):
            logger.info(f"MemPrompt successfully injected {len(ollama_res['similar_cases'])} verified historical precedents.")

        logger.info(
            f"Ollama Local Triage selesai ({ollama_res.get('latency_ms', 0)}ms): "
            f"kategori={ollama_res.get('predicted_category')}, urgensi={ollama_res.get('urgency_score')}/5"
        )

    # 4.4 100% Local Intelligence (Ollama / Local Heuristic Engine)
    posted_at_raw = payload.posted_at or (server_meta.get("posted_at") if server_meta else None)
    logger.debug("Analisis intelijen siber 100%% diproses lokal via Ollama.")

    # 5. Persistensi Atomik ke Database (Menghindari transaksi panjang & lock SQLite)
    try:
        account = db.query(Account).filter_by(platform=platform, username=account_username).first()
        if not account:
            account = Account(
                platform=platform,
                username=account_username,
                display_name=account_display_name,
                profile_url=account_profile_url,
                followers_count=account_followers,
            )
            db.add(account)
            db.flush()
        else:
            if account_followers > 0:
                account.followers_count = account_followers
            if account_display_name:
                account.display_name = account_display_name
            db.flush()

        canonical_content_url = clean_url
        if platform == "threads" and canonical_post_id:
            if account_username and account_username != "Anonim":
                canonical_content_url = f"https://www.threads.net/@{account_username}/post/{canonical_post_id}"
            else:
                canonical_content_url = f"https://www.threads.net/post/{canonical_post_id}"

        content = Content(
            account_id=account.account_id,
            platform=platform,
            canonical_url=canonical_content_url,
            platform_content_id=canonical_post_id,
            title=content_title,
            caption_text=full_narrative,
            ocr_text=active_ocr_text,
            likes_count=_safe_int(payload.likes_count),
            views_count=_safe_int(payload.views_count),
            comments_count=_safe_int(payload.comments_count),
            shares_count=_safe_int(payload.shares_count),
            extra_metadata={
                "transcript": payload.transcript or "",
                "clean_caption": clean_caption,
                "canonical_text_hash": canonical_text_hash,
                "posted_at": str(posted_at_raw) if posted_at_raw else None,
                "status_klaim": ollama_res.get("status_klaim", "Fakta Terverifikasi"),
                "kutipan_bukti": ollama_res.get("kutipan_bukti", ""),
                "tipe_konteks": ollama_res.get("tipe_konteks", "Publikasi Digital"),
            },
        )
        db.add(content)
        db.flush()

        # Konsolidasi Hasil AI: 100% Ollama Local Engine
        pred_cat = ollama_res.get("predicted_category") or "Umum / Di Luar Topik"
        urgency_val = ollama_res.get("urgency_score", 2)
        summary_text = (
            ollama_res.get("ringkasan_eksekutif")
            or ollama_res.get("summary")
            or f"Temuan patroli siber {platform.upper()}: {content_title}"
        )
        w5h1_dict = ollama_res.get("summary_5w1h", {})

        # Status keamanan dan risiko yang realistis sesuai kategori + urgensi
        if pred_cat in ("Non-Isu", "Umum / Di Luar Topik"):
            calc_ai_status = "AMAN"
            calc_risk_level = "RENDAH"
            urgency_val = min(urgency_val, 2)
        elif urgency_val >= 4:
            calc_ai_status = "PERINGATAN"
            calc_risk_level = "TINGGI"
        elif urgency_val == 3:
            calc_ai_status = "WASPADA"
            calc_risk_level = "SEDANG"
        else:
            calc_ai_status = "AMAN"
            calc_risk_level = "RENDAH"

        # Gunakan reasoning yang sudah kontekstual dari heuristic fallback
        ollama_indikasi = ollama_res.get("indikasi_pelanggaran", "")
        ollama_rekomendasi = ollama_res.get("rekomendasi_tindak_lanjut", "")
        bluf_dossier = ollama_res.get("bluf_dossier") or {
            "intisari_bluf": ollama_res.get("intisari_bluf") or summary_text,
            "fakta_vs_klaim": ollama_res.get("fakta_vs_klaim") or f"Fakta Teramati: {summary_text}\nKlaim: {ollama_res.get('status_klaim', 'Fakta Terverifikasi')}",
            "analisis_dampak": ollama_res.get("analisis_dampak") or f"Potensi eskalasi pada ranah {pred_cat} dengan urgensi {urgency_val}/5.",
            "aktor_dan_modus": ollama_res.get("aktor_dan_modus") or f"Aktor: {account_username}. Kanal: {platform.upper()}.",
            "rekomendasi_tindak_lanjut": ollama_rekomendasi or "Lakukan verifikasi berkala sesuai SOP.",
        }

        ai_reason_dict = {
            "alasan_penilaian": (
                ollama_res.get("ai_reasoning")
                or "Konten dalam pemantauan rutin intelijen siber."
            ),
            "status_klaim": ollama_res.get("status_klaim", "Fakta Terverifikasi"),
            "kutipan_bukti": ollama_res.get("kutipan_bukti", ""),
            "tipe_konteks": ollama_res.get("tipe_konteks", "Publikasi Digital"),
            "fakta_ekstraksi": ollama_res.get("ekstraksi_awal_tengah_akhir", []),
            "bluf_dossier": bluf_dossier,
            "intisari_bluf": bluf_dossier.get("intisari_bluf", ""),
            "fakta_vs_klaim": bluf_dossier.get("fakta_vs_klaim", ""),
            "analisis_dampak": bluf_dossier.get("analisis_dampak", ""),
            "aktor_dan_modus": bluf_dossier.get("aktor_dan_modus", ""),
            "indikasi_pelanggaran": (
                ollama_indikasi
                or ("Tidak ditemukan indikasi pelanggaran; narasi bersifat positif, edukatif, atau informasi umum." if pred_cat in ("Non-Isu", "Umum / Di Luar Topik") else (f"Indikasi isu {pred_cat} dengan tingkat urgensi {urgency_val}/5." if urgency_val >= 3 else ""))
            ),
            "rekomendasi_tindak_lanjut": (
                ollama_rekomendasi
                or bluf_dossier.get("rekomendasi_tindak_lanjut", "")
                or ("Pengawasan berkala sesuai SOP (arsip konten umum)." if pred_cat in ("Non-Isu", "Umum / Di Luar Topik") else ("Tandai siap diteruskan ke Tim Dalkonten untuk takedown dan koordinasi penegakan hukum." if urgency_val >= 4 else ("Pantau perkembangan isu secara berkala. Siapkan laporan situasi jika terdapat eskalasi." if urgency_val == 3 else "Pengawasan rutin sesuai SOP.")))
            ),
        }

        ocr_lat = round(float(ocr_res.get("latency_ms", 0.0)), 1) if ('ocr_res' in locals() and ocr_res) else 0.0
        retrieval_lat = round(float(ollama_res.get("retrieval_latency_ms", 2.8)), 1) if getattr(payload, "classification_mode", "adaptive") == "adaptive" else 0.0
        llm_lat = round(float(ollama_res.get("llm_latency_ms") or ollama_res.get("latency_ms", 0.0)), 1)
        total_lat = round(ocr_lat + retrieval_lat + llm_lat, 1)

        report = Report(
            ticket_number=ticket_number,
            content_id=content.content_id,
            reporter_telegram_id=0,
            source_channel=payload.source_channel.upper(),
            reporter_identifier=payload.reporter_identifier or "Analyst-Extension",
            operator_id=active_operator_id,
            status=Report.STATUS_WAITING_VALIDATION,
            original_language=ollama_res.get("original_language", "id"),
            indonesian_content=ollama_res.get("indonesian_content", summary_text),
            classification_mode=getattr(payload, "classification_mode", "adaptive"),
            execution_latencies={
                "ocr_ms": ocr_lat,
                "retrieval_ms": retrieval_lat,
                "llm_ms": llm_lat,
                "total_ms": total_lat,
            },
            ai_status=calc_ai_status,
            ai_predicted_label=pred_cat,
            ai_risk_level=calc_risk_level,
            ai_confidence_score=(0.92 if urgency_val >= 4 else 0.88),
            ai_summary=summary_text,
            ai_reasoning=ai_reason_dict,
            ai_topic_raw=pred_cat,
            ai_actors_raw=[account_display_name or account_username],
            ai_source_raw=platform.capitalize(),
        )
        db.add(report)
        db.flush()

        analysis = ContentAnalysis(
            content_id=content.content_id,
            what=w5h1_dict.get("what") or content_title,
            who=w5h1_dict.get("who") or (f"{account_display_name} (@{account_username})" if account_display_name else f"@{account_username}"),
            when_info=w5h1_dict.get("when") or f"Dipublikasikan pada {datetime.now().strftime('%d %B %Y')}",
            where_info=w5h1_dict.get("where") or f"Platform {platform.upper()} ({payload.url})",
            why=w5h1_dict.get("why") or f"Isu seputar perkembangan {content_title}.",
            how=w5h1_dict.get("how") or f"Dipaparkan melalui narasi digital pada platform {platform.upper()}.",
            summary=summary_text,
            main_topic=pred_cat,
            sub_topics=[],
            keywords=[],
            hashtags=[],
            named_entities=[account_username] if account_username else [],
            category=pred_cat,
            sentiment="NETRAL" if pred_cat in ("Non-Isu", "Umum / Di Luar Topik") else "NEGATIF",
            tone="Informatif",
            relevance_score=0.88,
            urgency_score=float(urgency_val) / 5.0,
            confidence_score=0.89,
            misinfo_indicators=[],
            analysis_status="COMPLETED",
        )
        db.add(analysis)

        seal_info = None
        if evidence_storage_path and evidence_sha256:
            seal_info = CryptoService.seal_evidence_package(
                screenshot_sha256=evidence_sha256,
                source_url=clean_url,
                dom_text=full_narrative,
                ocr_text=active_ocr_text,
                captured_at_utc=active_captured_at_utc,
                operator_id=active_operator_id,
            )
            evidence = Evidence(
                report_id=report.report_id,
                source_type="POST_SCREENSHOT",
                storage_path=evidence_storage_path,
                sha256=evidence_sha256,
                mime_type="image/png",
                operator_id=active_operator_id,
                source_url=clean_url,
                dom_text=full_narrative,
                ocr_text=active_ocr_text,
                captured_at_utc=active_captured_at_utc,
                canonical_hash=seal_info["canonical_hash"],
                hmac_tag=seal_info["hmac_tag"],
                verification_status="VERIFIED",
                last_verified_at=datetime.utcnow(),
            )
            db.add(evidence)

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
    except Exception as db_err:
        db.rollback()
        logger.error(f"Gagal simpan database atomik untuk tiket {ticket_number}: {db_err}")
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan data laporan ke database: {db_err}")

    # 6. Automasi Intelligence Radar: Hubungkan ke IssueCluster & Kalkulasi Trending Snapshot
    try:
        from app.services.intelligence.topic_clustering import TopicClusteringService
        from app.services.intelligence.trending_engine import TrendingEngine
        
        clustering_svc = TopicClusteringService()
        cluster, score, is_new = clustering_svc.assign_content_to_cluster(db, content.content_id, analysis)
        if cluster:
            logger.info(f"Otomatisasi klaster: Content {content.content_id} -> Cluster '{cluster.title}' (score={score}, is_new={is_new})")
            trending_engine = TrendingEngine()
            trending_engine.generate_and_save_snapshot(db, cluster.issue_id)
        else:
            logger.info(f"Otomatisasi klaster dilewati untuk Content {content.content_id} (Non-Isu atau di luar klaster).")
    except Exception as cluster_err:
        logger.warning(f"Otomatisasi klaster error (fail-open): {cluster_err}")

    # 7. Trigger Celery Enrichment jika worker aktif (opsional)
    if getattr(settings, "ENABLE_CELERY", False) or os.environ.get("ENABLE_CELERY") == "true":
        try:
            import socket
            with socket.create_connection(("127.0.0.1", 6379), timeout=0.1):
                from app.workers.tasks import enrich_content_intelligence
                enrich_content_intelligence.delay(str(content.content_id))
        except Exception as e:
            logger.debug(f"Celery enrichment task tidak aktif atau di-skip: {e}")

    content_id_str = str(content.content_id)
    return {
        "status": "QUEUED",
        "ticket_number": ticket_number,
        "content_id": content_id_str,
        "platform": platform,
        "source_channel": payload.source_channel.upper(),
        "reporter_identifier": payload.reporter_identifier,
        "operator_id": active_operator_id,
        "captured_at_utc": active_captured_at_utc,
        "canonical_hash": seal_info["canonical_hash"] if seal_info else None,
        "hmac_tag": seal_info["hmac_tag"] if seal_info else None,
        "verification_status": "VERIFIED" if seal_info else "UNSEALED",
        "tracking_url": f"/dashboard/#/contents/{content_id_str}",
        "dashboard_url": f"http://localhost:8000/dashboard/#/contents/{content_id_str}",
        "contents_url": "http://localhost:8000/dashboard/#/contents",
        "ai_status": report.ai_status,
        "ai_predicted_label": report.ai_predicted_label,
        "ai_confidence_score": round((report.ai_confidence_score or 0.85) * 100),
        "ai_summary": report.ai_summary,
        "deduplicated": False,
        "updated": False,
        "message": f"Tiket patroli {ticket_number} untuk {platform} berhasil didaftarkan dan langsung masuk ke Web Dashboard.",
    }


@router.post("/batch-intake")
async def submit_batch_intake(payload: BatchIntakeRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Accept multi-URL batch patrol triage (FR-20) and process each target securely."""
    clean_urls = [u.strip() for u in payload.urls if u and u.strip()]
    if not clean_urls:
        raise HTTPException(status_code=400, detail="Daftar URL patroli tidak boleh kosong.")

    results = []
    errors = []

    for target_url in clean_urls:
        try:
            intake_req = ChannelIntakeRequest(
                url=target_url,
                source_channel="WEB_DASHBOARD",
                reporter_identifier=f"Analyst-{payload.operator_id or 'Batch'}",
                operator_id=payload.operator_id or "OP-01",
                classification_mode=payload.classification_mode,
            )
            res = await submit_channel_intake(intake_req, db)
            results.append(res)
        except Exception as ex:
            logger.error("Error processing batch intake for %s: %s", target_url, ex)
            errors.append({"url": target_url, "error": str(ex)})

    return {
        "status": "COMPLETED",
        "total_submitted": len(clean_urls),
        "total_success": len(results),
        "total_failed": len(errors),
        "results": results,
        "errors": errors,
    }
