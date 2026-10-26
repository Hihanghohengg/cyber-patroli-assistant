import asyncio
import logging
import os
import re
import uuid
from datetime import datetime, date

from telegram import Update, InputFile
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models.report import Account, Content, Report
from app.models.evidence import Evidence
from app.models.audit import AuditLog
from app.services.scraper.base import BaseScraper
from app.services.scraper.youtube import YouTubeScraper
from app.services.scraper.tiktok import TikTokScraper
from app.services.scraper.instagram import InstagramScraper
from app.services.ai_service import AIService
from app.services.report_service import ReportService
from app.services.rag_service import RAGService
from app.services.entity_service import EntityService
from app.bot.keyboards import (
    get_validation_keyboard,
    get_category_correction_keyboard,
    get_risk_correction_keyboard,
)

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────
#  Scraper factory
# ────────────────────────────────────────────

SCRAPERS: dict[str, BaseScraper] = {
    "youtube": YouTubeScraper(),
    "tiktok": TikTokScraper(),
    "instagram": InstagramScraper(),
}


# ────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────

def _get_patrol_user_role(user_id: int) -> str | None:
    """Retrieve role ('OPERATOR', 'ANALYST', 'ADMIN') from patrol_users table or config."""
    db = SessionLocal()
    try:
        from app.models.user import PatrolUser
        u = db.query(PatrolUser).filter(PatrolUser.telegram_id == user_id, PatrolUser.is_active.is_(True)).first()
        if u and u.role:
            return u.role.upper()
    except Exception as e:
        logger.warning("Error fetching PatrolUser role: %s", e)
    finally:
        db.close()

    if settings.whitelisted_user_ids:
        if user_id in settings.whitelisted_user_ids:
            return "ADMIN"
        return None
    # If no whitelist configured at all, grant ADMIN for local dev
    return "ADMIN"


def _is_authorised(user_id: int, allowed_roles: list[str] = None) -> bool:
    """Verify if user has active authorization, optionally filtering by roles."""
    role = _get_patrol_user_role(user_id)
    if not role:
        return False
    if allowed_roles:
        return role in [r.upper() for r in allowed_roles]
    return True


def _generate_ticket() -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    seq = uuid.uuid4().hex[:4].upper()
    return f"PS-{today}-{seq}"


def _format_analyst_card(
    report: Report,
    content: Content,
    account: Account,
    ai_result,
    evidence_post: Evidence | None,
) -> str:
    """Build the clean, compact analyst evaluation card fitting on a single mobile screen."""
    subs_count = account.followers_count or 0
    if subs_count >= 1_000_000:
        subs_fmt = f"{subs_count / 1_000_000:.2f}M"
    elif subs_count >= 1_000:
        subs_fmt = f"{subs_count / 1_000:.1f}K"
    else:
        subs_fmt = f"{subs_count:,}"

    kategori = (
        getattr(ai_result, "kategori_utama", None)
        or getattr(ai_result, "kategori_isu", None)
        or report.ai_predicted_label
        or "NETRAL"
    )
    risiko = (
        getattr(ai_result, "tingkat_risiko", None)
        or report.ai_risk_level
        or "RENDAH"
    )
    confidence = int((getattr(ai_result, "skor_keyakinan", 0) or 0) * 100)
    narasi = getattr(ai_result, "ringkasan_narasi", None) or report.ai_summary or "-"
    sha_full = evidence_post.sha256 if evidence_post else "N/A"

    title_display = content.title or (
        content.caption_text[:80] + "…"
        if content.caption_text and len(content.caption_text) > 80
        else (content.caption_text or "Konten Postingan")
    )

    return (
        f"🎯 *ID Tiket*: `{report.ticket_number}`\n"
        f"👤 *Akun*: `{account.username}` (Platform: {content.platform.upper()}) | Subs: {subs_fmt}\n"
        f"📌 *Judul/Konten*: {title_display}\n"
        f"🔗 *URL*: [Buka Postingan]({content.canonical_url})\n\n"
        f"🔍 *Analisis AI*: *{kategori}* | Risiko: *{risiko}* (Keyakinan: {confidence}%)\n"
        f"📝 *Ringkasan Narasi*: _{narasi}_\n\n"
        f"🔐 *Integritas Bukti*: SHA-256:\n`{sha_full}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Silakan Validator meninjau dan menetapkan keputusan:"
    )


# ────────────────────────────────────────────
#  Command: /start
# ────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command with a welcome message and role info."""
    user_id = update.effective_user.id
    role = _get_patrol_user_role(user_id) or "OPERATOR"

    role_lines = [
        f"🛡️ *Asisten Patroli Siber & Profiling Akun* (v2.2)\n",
        f"Peran Anda saat ini: *{role}*\n",
        "Metode input patroli:",
        "1. 🔗 *Kirim Tautan*: Kirim URL postingan YouTube, TikTok, atau Instagram.",
        "2. 📸 *Kirim Foto Bukti*: Kirimkan tangkapan layar langsung ke bot (Human-in-the-Loop Fallback).\n",
        "Perintah operasional:",
        "• `/status` — Cek daftar tiket aktif atau status laporan spesifik (contoh: `/status PS-20261026-ABCD`)",
    ]

    if role in ["ANALYST", "ADMIN"]:
        role_lines.append("• `/rekap_harian` — Unduh rekapitulasi harian resmi (DOCX) untuk temuan tervalidasi")

    if role == "ADMIN":
        role_lines.append("• `/whitelist` — Kelola daftar pengguna patroli siber (list/add/remove)")

    await _safe_reply(update, "\n".join(role_lines))


# ────────────────────────────────────────────
#  URL handler: full patrol pipeline
# ────────────────────────────────────────────

async def _safe_reply(update: Update, text: str, parse_mode: str = "Markdown"):
    """Safely reply with retry logic against connection glitches."""
    for attempt in range(3):
        try:
            return await update.message.reply_text(text, parse_mode=parse_mode)
        except Exception as err:
            logger.warning("Attempt %s/3 _safe_reply failed: %s", attempt + 1, err)
            await asyncio.sleep(1)
    return None


async def _safe_edit(msg, text: str, parse_mode: str = "Markdown"):
    """Safely edit a progress message with retry logic."""
    if not msg:
        return None
    for attempt in range(3):
        try:
            return await msg.edit_text(text, parse_mode=parse_mode)
        except Exception:
            await asyncio.sleep(0.5)
    return msg


async def url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main pipeline: receive URL → scrape → hash → AI → send to analysts."""
    user_id = update.effective_user.id
    if not _is_authorised(user_id):
        await _safe_reply(update, "⛔ Anda tidak memiliki akses ke sistem ini.")
        return

    text = update.message.text.strip()
    url_match = re.search(r"https?://\S+", text)
    if not url_match:
        await _safe_reply(update, "⚠️ Tidak ditemukan URL valid dalam pesan.")
        return

    url = url_match.group(0)

    try:
        platform = BaseScraper.detect_platform(url)
    except ValueError as e:
        await _safe_reply(update, f"❌ {e}")
        return

    scraper = SCRAPERS[platform]
    ticket = _generate_ticket()
    db = SessionLocal()

    # Step 0: Immediate interactive progress card
    status_card = await _safe_reply(
        update,
        f"🚨 *MEMULAI INVESTIGASI PATROLI SIBER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 *Tiket*: `{ticket}`\n"
        f"🌐 *Platform*: {platform.upper()}\n"
        f"🔗 *URL*: `{url}`\n\n"
        f"⏳ `[1/4]` 📡 *Mengekstrak metadata postingan & channel via yt-dlp…*",
    )

    try:
        # ── Step 1: Extract metadata in background thread ──
        meta = await asyncio.to_thread(scraper.extract_metadata, url)

        # ── Step 2: Upsert Account & Content ──
        account = (
            db.query(Account)
            .filter_by(
                platform=platform,
                username=meta["account"]["username"],
            )
            .first()
        )
        if not account:
            account = Account(
                platform=platform,
                username=meta["account"]["username"],
                display_name=meta["account"].get("display_name"),
                profile_url=meta["account"].get("profile_url", ""),
                followers_count=meta["account"].get("subscribers_count", 0),
                total_posts=meta["account"].get("total_posts", 0),
                is_verified=meta["account"].get("is_verified", False),
            )
            db.add(account)
            db.flush()
        else:
            account.display_name = meta["account"].get("display_name") or account.display_name
            account.followers_count = meta["account"].get("subscribers_count", 0)
            if meta["account"].get("is_verified") is not None:
                account.is_verified = meta["account"].get("is_verified")

        content = (
            db.query(Content)
            .filter_by(canonical_url=meta["canonical_url"])
            .first()
        )
        extra_data = {
            "duration": meta.get("duration"),
            "duration_seconds": meta.get("duration_seconds", 0),
            "tags": meta.get("tags", []),
            "categories": meta.get("categories", []),
        }
        if not content:
            content = Content(
                account_id=account.account_id,
                platform=platform,
                canonical_url=meta["canonical_url"],
                platform_content_id=meta.get("platform_content_id"),
                title=meta.get("title", ""),
                caption_text=meta.get("caption", ""),
                likes_count=meta.get("likes_count", 0),
                views_count=meta.get("views_count", 0),
                comments_count=meta.get("comments_count", 0),
                extra_metadata=extra_data,
                posted_at=meta.get("posted_at"),
            )
            db.add(content)
            db.flush()
        else:
            content.title = meta.get("title", "") or content.title
            content.likes_count = meta.get("likes_count", 0)
            content.views_count = meta.get("views_count", 0)
            content.comments_count = meta.get("comments_count", 0)
            content.extra_metadata = extra_data

        # Update progress card
        await _safe_edit(
            status_card,
            f"🚨 *INVESTIGASI PATROLI SIBER* | `{ticket}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 *Platform*: {platform.upper()}\n"
            f"👤 *Akun*: {account.display_name or 'N/A'} (`@{account.username}`)\n"
            f"👥 *Followers/Subs*: {account.followers_count:,}\n\n"
            f"⏳ `[2/4]` 📸 *Mengambil screenshot Full HD Playwright & Verifikasi SHA-256…*",
        )

        # ── Step 3: Initialize Report ──
        report = Report(
            ticket_number=ticket,
            reporter_telegram_id=user_id,
            content_id=content.content_id,
            intake_type="LINK",
            status="PENDING_ANALYSIS",
        )
        db.add(report)
        db.flush()

        # ── Step 4: Capture visual evidence with > 20 KB validation ──
        evidence_data = {}
        try:
            evidence_data = await scraper.capture_visual_evidence(
                post_url=meta["canonical_url"],
                profile_url=meta["account"].get("profile_url", ""),
                ticket_number=ticket,
                video_url=meta["canonical_url"],
                channel_url=meta["account"].get("profile_url", ""),
            )
            post_p = evidence_data.get("post_screenshot_path")
            if not post_p or not os.path.exists(post_p) or os.path.getsize(post_p) <= 20 * 1024:
                raise ValueError("Tangkapan layar visual berukuran <= 20 KB atau gagal tersimpan")
        except Exception as scrap_err:
            logger.warning("[%s] Scraper failed or <= 20KB, switching to MANUAL_FALLBACK: %s", ticket, scrap_err)
            report.status = "MANUAL_FALLBACK"
            db.add(
                AuditLog(
                    action="MANUAL_FALLBACK",
                    actor_telegram_id=user_id,
                    entity_type="Report",
                    entity_id=str(report.report_id),
                    details={"error": str(scrap_err), "url": url},
                )
            )
            db.commit()

            await _safe_edit(
                status_card,
                f"⚠️ *KENDALA PENANGKAPAN BUKTI VISUAL (Status: MANUAL_FALLBACK)*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎫 *Tiket*: `{ticket}`\n"
                f"🌐 *Platform*: {platform.upper()}\n"
                f"🔗 *URL*: `{url}`\n\n"
                f"Tangkapan layar otomatis gagal atau berukuran <= 20 KB (terhalang login-wall/antibot).\n\n"
                f"👉 *Silakan unggah foto/screenshot bukti secara manual* ke bot ini (kirim sebagai gambar dengan caption menyertakan nomor tiket `{ticket}`) untuk melanjutkan proses patroli.",
            )
            return

        evidence_post = None
        if evidence_data.get("post_screenshot_path"):
            evidence_post = Evidence(
                report_id=report.report_id,
                source_type="SCRAPER_SCREENSHOT",
                storage_path=evidence_data["post_screenshot_path"],
                sha256=evidence_data["post_screenshot_hash"],
            )
            db.add(evidence_post)

        if evidence_data.get("profile_screenshot_path"):
            evidence_profile = Evidence(
                report_id=report.report_id,
                source_type="SCRAPER_SCREENSHOT",
                storage_path=evidence_data["profile_screenshot_path"],
                sha256=evidence_data["profile_screenshot_hash"],
            )
            db.add(evidence_profile)
            account.profile_screenshot_path = evidence_data["profile_screenshot_path"]
            account.profile_screenshot_sha256 = evidence_data["profile_screenshot_hash"]

        db.flush()

        # Update progress card
        sha_str = (evidence_data.get("post_screenshot_hash") or "")[:16]
        await _safe_edit(
            status_card,
            f"🚨 *INVESTIGASI PATROLI SIBER* | `{ticket}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 *Platform*: {platform.upper()}\n"
            f"👤 *Akun*: {account.display_name or 'N/A'} (`@{account.username}`)\n"
            f"🔐 *SHA-256 Bukti*: `{sha_str}…`\n\n"
            f"⏳ `[3/4]` 🤖 *Menjalankan analisis AI Multimodal (Gemini 2.5 Flash)…*",
        )

        # ── Step 5: AI Analysis with RAG in background thread ──
        rag_svc = RAGService()
        entity_svc = EntityService()
        rag_context = ""
        try:
            rag_context = await asyncio.to_thread(
                rag_svc.retrieve_similar_cases,
                db=db,
                text=meta.get("caption", "") or meta.get("title", ""),
                top_k=5,
                threshold=0.75,
            )
        except Exception as rag_err:
            logger.warning("RAG retrieval failed (fail-open): %s", rag_err)

        ai_service = AIService()
        ai_result = None
        try:
            ai_result = await asyncio.to_thread(
                ai_service.analyze_patrol_finding,
                caption=meta.get("caption", ""),
                image_path=evidence_data.get("post_screenshot_path"),
                profile_info=meta.get("account", {}),
                title=meta.get("title", ""),
                metadata=meta,
                rag_context=rag_context,
            )

            report.ai_status = ai_result.status_keamanan
            report.ai_predicted_label = ai_result.kategori_utama
            report.ai_risk_level = ai_result.tingkat_risiko
            report.ai_confidence_score = ai_result.skor_keyakinan
            report.ai_summary = ai_result.ringkasan_narasi
            report.ai_reasoning = {
                "poin_pengamatan": ai_result.poin_pengamatan,
                "alasan_penilaian": ai_result.alasan_penilaian,
                "indikasi_pelanggaran": ai_result.indikasi_pelanggaran,
                "rekomendasi_tindak_lanjut": ai_result.rekomendasi_tindak_lanjut,
            }
            report.ai_needs_deep_check = ai_result.butuh_verifikasi_mendalam
            report.ai_topic_raw = ai_result.topik
            report.ai_actors_raw = ai_result.aktor_target
            report.ai_source_raw = ai_result.sumber_konten
            report.ai_source_type = ai_result.tipe_sumber
            report.status = "WAITING_VALIDATION"

            # Entity linking
            try:
                if ai_result.topik:
                    topic_ent = entity_svc.get_or_create_topic(db, ai_result.topik)
                    report.topic_id = topic_ent.entity_id
                if ai_result.sumber_konten:
                    source_ent = entity_svc.get_or_create_source(db, ai_result.sumber_konten, ai_result.tipe_sumber)
                    report.source_id = source_ent.entity_id
                if ai_result.aktor_target:
                    for act in ai_result.aktor_target:
                        actor_ent = entity_svc.get_or_create_actor(db, act)
                        entity_svc.link_report_actor(db, report.report_id, actor_ent.entity_id, role="TARGET")
            except Exception as ent_err:
                logger.warning("Entity linking failed: %s", ent_err)

        except Exception as ai_err:
            logger.error("AI analysis failed: %s", ai_err)
            report.status = "WAITING_VALIDATION"
            report.ai_summary = f"AI analysis failed: {ai_err}"

        db.commit()

        # Audit log
        audit = AuditLog(
            action="REPORT_CREATED",
            actor_telegram_id=user_id,
            entity_type="Report",
            entity_id=str(report.report_id),
            details={"ticket": ticket, "platform": platform, "url": url},
        )
        db.add(audit)
        db.commit()

        # Enqueue enrichment for Social Intelligence dashboard (non-blocking)
        try:
            from app.workers.tasks import enrich_content_intelligence
            enrich_content_intelligence.delay(str(content.content_id))
        except Exception as q_err:
            logger.warning("Could not enqueue intelligence enrichment: %s", q_err)

        # Update progress card
        await _safe_edit(
            status_card,
            f"🚨 *INVESTIGASI PATROLI SIBER* | `{ticket}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 *Platform*: {platform.upper()}\n"
            f"👤 *Akun*: {account.display_name or 'N/A'} (`@{account.username}`)\n"
            f"🏷️ *Indikasi AI*: {report.ai_predicted_label or 'N/A'} ({report.ai_risk_level or 'N/A'})\n\n"
            f"⏳ `[4/4]` 📨 *Menyajikan bukti visual dan kartu evaluasi…*",
        )

        # ── Step 6: Dispatch visual evidence & analyst card ──
        # Route to analyst group if configured, otherwise send to user chat
        target_chat_id = (
            settings.analyst_group_id
            if settings.analyst_group_id
            else update.effective_chat.id
        )

        # 1. Send post / video screenshot
        if evidence_data.get("post_screenshot_path") and os.path.exists(evidence_data["post_screenshot_path"]):
            try:
                with open(evidence_data["post_screenshot_path"], "rb") as img_file:
                    await context.bot.send_photo(
                        chat_id=target_chat_id,
                        photo=InputFile(img_file),
                        caption=f"📸 Bukti Visual Terverifikasi — `{ticket}`\n🔐 SHA-256: `{sha_str}…`",
                        parse_mode="Markdown",
                    )
            except Exception as img_err:
                logger.warning("Failed to send screenshot to target chat: %s", img_err)

        # 2. Send channel / profile screenshot if available
        if evidence_data.get("profile_screenshot_path") and os.path.exists(evidence_data["profile_screenshot_path"]):
            try:
                prof_sha = (evidence_data.get("profile_screenshot_hash") or "")[:16]
                with open(evidence_data["profile_screenshot_path"], "rb") as prof_file:
                    await context.bot.send_photo(
                        chat_id=target_chat_id,
                        photo=InputFile(prof_file),
                        caption=f"👤 Profil Akun Pembuat — `{account.username}`\n🔐 SHA-256: `{prof_sha}…`",
                        parse_mode="Markdown",
                    )
            except Exception as prof_err:
                logger.warning("Failed to send profile screenshot to target chat: %s", prof_err)

        # 3. Send analyst card with 3 interactive action buttons
        try:
            card_text = _format_analyst_card(
                report=report,
                content=content,
                account=account,
                ai_result=ai_result,
                evidence_post=evidence_post,
            )
            keyboard = get_validation_keyboard(str(report.report_id))
            await context.bot.send_message(
                chat_id=target_chat_id,
                text=card_text,
                parse_mode="Markdown",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except Exception as card_err:
            logger.error("Failed to send analyst card to target chat: %s", card_err)

        # Final update to the progress card in the requester's chat
        if target_chat_id != update.effective_chat.id:
            await _safe_edit(
                status_card,
                f"✅ *INVESTIGASI SELESAI* | `{ticket}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"Bukti visual dan kartu evaluasi telah diteruskan ke Grup Analis.\n"
                f"Menunggu konfirmasi validasi tim patroli.",
            )
        else:
            await _safe_edit(
                status_card,
                f"✅ *INVESTIGASI SELESAI* | `{ticket}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"Bukti visual Full HD dan kartu evaluasi telah disajikan di bawah.\n"
                f"Silakan klik tombol keputusan untuk memvalidasi temuan.",
            )

    except Exception as e:
        db.rollback()
        logger.exception("Pipeline failed for URL: %s", url)
        err_msg = str(e)

        # Anti-blank / capture failure fallback: prompt manual upload
        if "rusak/blank" in err_msg or "20 KB" in err_msg or "< 20" in err_msg:
            await _safe_edit(
                status_card,
                f"⚠️ *KENDALA PENANGKAPAN BUKTI VISUAL*\n\n"
                f"Tiket: `{ticket}`\n"
                f"Sistem mendeteksi tangkapan layar otomatis blank / terhalang overlay ({err_msg}).\n\n"
                f"👉 *Silakan unggah screenshot bukti manual* secara langsung ke chat bot ini (kirim sebagai gambar/foto) untuk melengkapi tiket `{ticket}`.",
            )
        elif "timeout" in err_msg.lower() or "terputus" in err_msg.lower() or "connection" in err_msg.lower():
            await _safe_edit(
                status_card,
                f"⚠️ *KENDALA AKSES JARINGAN SIBER* | `{ticket}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌐 Platform: *{platform.upper()}*\n"
                f"Koneksi scraping ke server {platform.title()} mengalami timeout atau pemblokiran oleh firewall jaringan lokal.\n\n"
                f"👉 *Solusi Handal (Piket Lapangan)*:\n"
                f"Silakan ambil tangkapan layar (screenshot) postingan ini di HP atau komputer Anda, lalu **kirimkan fotonya langsung ke chat bot ini** (bisa sertakan link postingan di caption foto). Sistem akan memproses dan memvalidasi temuan secara otomatis.",
            )
        else:
            await _safe_edit(
                status_card,
                f"❌ *Gagal Memproses Patroli*\n\n"
                f"Tiket: `{ticket}`\n"
                f"Error: `{err_msg}`\n"
                f"Silakan coba kirim ulang tautan atau unggah screenshot manual.",
            )
    finally:
        db.close()


# ────────────────────────────────────────────
#  Photo Handler: Direct Manual Evidence Ingestion
# ────────────────────────────────────────────

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct screenshot upload from patrol officer (Human-in-the-Loop fallback)."""
    user_id = update.effective_user.id
    if not _is_authorised(user_id, ["OPERATOR", "ANALYST", "ADMIN"]):
        await _safe_reply(update, "⛔ Anda tidak memiliki akses ke sistem ini.")
        return

    if not update.message.photo:
        return

    caption_text = (update.message.caption or "").strip()

    # Detect if caption mentions an existing ticket (e.g. from MANUAL_FALLBACK)
    existing_ticket_match = re.search(r"PS-\d{8}-[A-F0-9]{4}", caption_text)
    ticket = existing_ticket_match.group(0) if existing_ticket_match else _generate_ticket()

    # Detect if an original URL was included in the caption
    url_match = re.search(r"https?://\S+", caption_text)
    canonical_url = url_match.group(0) if url_match else f"manual://upload/{ticket}"

    platform = "manual"
    if url_match:
        try:
            platform = BaseScraper.detect_platform(canonical_url)
        except Exception:
            platform = "manual"

    status_card = await _safe_reply(
        update,
        f"🚨 *PENERIMAAN BUKTI VISUAL MANUAL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 *Tiket*: `{ticket}`\n"
        f"🌐 *Platform*: {platform.upper()}\n"
        f"⏳ `[1/3]` 💾 *Menyimpan file bukti dan menghitung integritas SHA-256…*",
    )

    db = SessionLocal()
    try:
        # Check if this ticket already exists in DB (e.g. from MANUAL_FALLBACK)
        existing_report = db.query(Report).filter(Report.ticket_number == ticket).first()

        # 1. Download highest-resolution photo
        photo_obj = update.message.photo[-1]
        photo_file = await photo_obj.get_file()

        filename = f"{ticket}_manual.png"
        file_path = os.path.join(settings.EVIDENCE_DIR, filename)
        os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
        await photo_file.download_to_drive(custom_path=file_path)

        file_size = os.path.getsize(file_path)
        sha_hash = CryptoService.calculate_sha256(file_path)
        sha_str = sha_hash[:16]

        await _safe_edit(
            status_card,
            f"🚨 *PENERIMAAN BUKTI VISUAL MANUAL* | `{ticket}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔐 *SHA-256 Bukti*: `{sha_str}…`\n"
            f"📦 *Ukuran*: {file_size:,} bytes\n\n"
            f"⏳ `[2/3]` 🤖 *Menjalankan analisis AI Multimodal (Gemini Vision)…*",
        )

        if existing_report and existing_report.content:
            report = existing_report
            content = report.content
            account = content.account
            report.status = "PENDING_ANALYSIS"
        else:
            # 2. Upsert Account & Content
            account = (
                db.query(Account)
                .filter_by(platform=platform, username=f"operator_{user_id}")
                .first()
            )
            if not account:
                account = Account(
                    platform=platform,
                    username=f"operator_{user_id}",
                    display_name="Pelapor Patroli Manual",
                    profile_url=canonical_url,
                )
                db.add(account)
                db.flush()

            content = (
                db.query(Content)
                .filter_by(canonical_url=canonical_url)
                .first()
            )
            if not content:
                content = Content(
                    account_id=account.account_id,
                    platform=platform,
                    canonical_url=canonical_url,
                    title="Bukti Screenshot Lapangan",
                    caption_text=caption_text or "Unggahan tangkapan layar bukti visual langsung dari pelapor patroli siber.",
                    extra_metadata={"intake_mode": "manual_upload", "file_size": file_size},
                )
                db.add(content)
                db.flush()

            # 3. Create Report
            report = Report(
                ticket_number=ticket,
                reporter_telegram_id=user_id,
                content_id=content.content_id,
                intake_type="MANUAL_SCREENSHOT",
                status="PENDING_ANALYSIS",
            )
            db.add(report)
            db.flush()

        evidence_post = Evidence(
            report_id=report.report_id,
            source_type="MANUAL_UPLOAD",
            storage_path=file_path,
            sha256=sha_hash,
        )
        db.add(evidence_post)
        db.flush()

        # 4. AI Vision Analysis with RAG
        rag_svc = RAGService()
        entity_svc = EntityService()
        rag_context = ""
        try:
            rag_context = await asyncio.to_thread(
                rag_svc.retrieve_similar_cases,
                db=db,
                text=caption_text or "Bukti visual postingan/konten media sosial hasil tangkapan layar manual.",
                top_k=5,
                threshold=0.75,
            )
        except Exception as rag_err:
            logger.warning("RAG retrieval failed in photo_handler (fail-open): %s", rag_err)

        ai_service = AIService()
        ai_result = await asyncio.to_thread(
            ai_service.analyze_patrol_finding,
            caption=caption_text or "Bukti visual postingan/konten media sosial hasil tangkapan layar manual.",
            image_path=file_path,
            profile_info={"username": account.username, "display_name": account.display_name, "subscribers_count": 0},
            title="Bukti Tangkapan Layar Manual",
            metadata={"views_count": 0, "likes_count": 0, "comments_count": 0},
            rag_context=rag_context,
        )

        report.ai_status = ai_result.status_keamanan
        report.ai_predicted_label = ai_result.kategori_utama
        report.ai_risk_level = ai_result.tingkat_risiko
        report.ai_confidence_score = ai_result.skor_keyakinan
        report.ai_summary = ai_result.ringkasan_narasi
        report.ai_reasoning = {
            "poin_pengamatan": ai_result.poin_pengamatan,
            "alasan_penilaian": ai_result.alasan_penilaian,
            "indikasi_pelanggaran": ai_result.indikasi_pelanggaran,
            "rekomendasi_tindak_lanjut": ai_result.rekomendasi_tindak_lanjut,
        }
        report.ai_needs_deep_check = ai_result.butuh_verifikasi_mendalam
        report.ai_topic_raw = ai_result.topik
        report.ai_actors_raw = ai_result.aktor_target
        report.ai_source_raw = ai_result.sumber_konten
        report.ai_source_type = ai_result.tipe_sumber
        report.status = "WAITING_VALIDATION"

        # Entity linking
        try:
            if ai_result.topik:
                topic_ent = entity_svc.get_or_create_topic(db, ai_result.topik)
                report.topic_id = topic_ent.entity_id
            if ai_result.sumber_konten:
                source_ent = entity_svc.get_or_create_source(db, ai_result.sumber_konten, ai_result.tipe_sumber)
                report.source_id = source_ent.entity_id
            if ai_result.aktor_target:
                for act in ai_result.aktor_target:
                    actor_ent = entity_svc.get_or_create_actor(db, act)
                    entity_svc.link_report_actor(db, report.report_id, actor_ent.entity_id, role="TARGET")
        except Exception as ent_err:
            logger.warning("Entity linking failed in photo_handler: %s", ent_err)

        db.commit()

        # Audit
        audit = AuditLog(
            action="REPORT_CREATED",
            actor_telegram_id=user_id,
            entity_type="Report",
            entity_id=str(report.report_id),
            details={"ticket": ticket, "intake": "MANUAL_SCREENSHOT", "url": canonical_url},
        )
        db.add(audit)
        db.commit()

        # Enqueue enrichment for Social Intelligence dashboard (non-blocking)
        try:
            from app.workers.tasks import enrich_content_intelligence
            enrich_content_intelligence.delay(str(content.content_id))
        except Exception as q_err:
            logger.warning("Could not enqueue intelligence enrichment: %s", q_err)

        # 5. Dispatch analyst card
        target_chat_id = (
            settings.analyst_group_id
            if settings.analyst_group_id
            else update.effective_chat.id
        )

        card_text = _format_analyst_card(
            report=report,
            content=content,
            account=account,
            ai_result=ai_result,
            evidence_post=evidence_post,
        )
        keyboard = get_validation_keyboard(str(report.report_id))
        await context.bot.send_message(
            chat_id=target_chat_id,
            text=card_text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

        await _safe_edit(
            status_card,
            f"✅ *ANALISIS BUKTI SELESAI* | `{ticket}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Bukti visual tersimpan secara forensik (SHA-256).\n"
            f"Kartu evaluasi analis telah diterbitkan di bawah.\n"
            f"Silakan klik tombol keputusan untuk memvalidasi temuan.",
        )
    except Exception as e:
        db.rollback()
        logger.exception("Manual photo intake error: %s", e)
        await _safe_edit(
            status_card,
            f"❌ *Gagal Memproses Bukti Manual*\n\n"
            f"Tiket: `{ticket}`\n"
            f"Error: `{e}`",
        )
    finally:
        db.close()


# ────────────────────────────────────────────
#  Callback: Validation buttons
# ────────────────────────────────────────────

async def validation_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle the 3 inline validation buttons (approve / reject / edit)."""
    query = update.callback_query
    await query.answer()

    reviewer_id = query.from_user.id
    if not _is_authorised(reviewer_id, ["ANALYST", "ADMIN"]):
        await query.answer("⛔ Akses ditolak: Hanya peran ANALYST atau ADMIN yang berwenang memvalidasi temuan.", show_alert=True)
        return

    data = query.data  # e.g. "val:approve:<report_id>"
    parts = data.split(":")
    if len(parts) != 3:
        return

    action = parts[1]
    report_id = parts[2]

    db = SessionLocal()
    try:
        report = db.query(Report).filter_by(report_id=report_id).first()
        if not report:
            await query.edit_message_text("⚠️ Laporan tidak ditemukan.")
            return

        if action == "approve":
            report.review_decision = "APPROVED"
            report.final_label = report.ai_predicted_label
            report.final_risk = report.ai_risk_level
            report.reviewer_telegram_id = reviewer_id
            report.validated_at = datetime.utcnow()
            report.status = "VALIDATED"
            report.analyst_notes = report.analyst_notes or "Disetujui sesuai rekomendasi AI"
            db.commit()

            audit = AuditLog(
                action="VALIDATION_APPROVED",
                actor_telegram_id=reviewer_id,
                entity_type="Report",
                entity_id=report_id,
            )
            db.add(audit)
            db.commit()

            # Asynchronously write to RAG knowledge base
            try:
                rag_svc = RAGService()
                await asyncio.to_thread(rag_svc.create_knowledge_entry, db, report)
            except Exception as rag_err:
                logger.error("Failed to write RAG knowledge entry on approve: %s", rag_err)

            await query.edit_message_text(
                f"✅ Laporan `{report.ticket_number}` telah *DISETUJUI* oleh validator.\n"
                f"Label: {report.final_label} | Risiko: {report.final_risk}\n"
                f"📚 *RAG*: Keputusan otomatis masuk ke Knowledge Base.",
                parse_mode="Markdown",
            )

        elif action == "reject":
            report.review_decision = "FALSE_POSITIVE"
            report.reviewer_telegram_id = reviewer_id
            report.validated_at = datetime.utcnow()
            report.status = "REJECTED"
            report.final_risk = None  # Wajib NULL/None per Proposal FR-06
            report.analyst_notes = report.analyst_notes or "Bukan Pelanggaran / False Positive"
            db.commit()

            audit = AuditLog(
                action="VALIDATION_REJECTED",
                actor_telegram_id=reviewer_id,
                entity_type="Report",
                entity_id=report_id,
            )
            db.add(audit)
            db.commit()

            # Deactivate active KB entry if exists (NFR-07: Versioning Berjejak tanpa hard-delete)
            try:
                rag_svc = RAGService()
                rag_svc.deactivate_knowledge_entry(db, report.report_id)
            except Exception as rag_err:
                logger.error("Failed to deactivate RAG knowledge entry on reject: %s", rag_err)

            # Store awaiting note in user_data so the next text reply attaches as analyst notes
            context.user_data["awaiting_note_for_report"] = str(report.report_id)

            await query.edit_message_text(
                f"✕ Laporan `{report.ticket_number}` ditandai sebagai *BUKAN PELANGGARAN* (Risiko diset: Nihil).\n"
                f"📚 *RAG*: Entri KB dinonaktifkan.\n\n"
                f"💡 *Catatan Analis*: Balas pesan ini jika ingin menambahkan rincian alasan penolakan.",
                parse_mode="Markdown",
            )

        elif action == "edit":
            keyboard = get_category_correction_keyboard(report_id)
            await query.edit_message_text(
                f"✏ Pilih kategori yang benar untuk `{report.ticket_number}`:",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

    except Exception as e:
        db.rollback()
        logger.exception("Validation callback error: %s", e)
    finally:
        db.close()


# ────────────────────────────────────────────
#  Callback: Category correction
# ────────────────────────────────────────────

async def category_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle category correction selection."""
    query = update.callback_query
    await query.answer()

    reviewer_id = query.from_user.id
    if not _is_authorised(reviewer_id, ["ANALYST", "ADMIN"]):
        await query.answer("⛔ Akses ditolak: Hanya peran ANALYST atau ADMIN yang berwenang memvalidasi temuan.", show_alert=True)
        return

    data = query.data  # e.g. "setcat:HOAKS:<report_id>"
    parts = data.split(":")
    if len(parts) != 3:
        return

    new_category = parts[1]
    report_id = parts[2]

    db = SessionLocal()
    try:
        report = db.query(Report).filter_by(report_id=report_id).first()
        if not report:
            await query.edit_message_text("⚠️ Laporan tidak ditemukan.")
            return

        report.final_label = new_category
        report.reviewer_telegram_id = reviewer_id
        report.review_decision = "MODIFIED"
        db.commit()

        # Now ask for risk level
        keyboard = get_risk_correction_keyboard(report_id)
        await query.edit_message_text(
            f"✏ Kategori diubah ke *{new_category}*.\n"
            f"Sekarang pilih tingkat risiko untuk `{report.ticket_number}`:",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    except Exception as e:
        db.rollback()
        logger.exception("Category callback error: %s", e)
    finally:
        db.close()


# ────────────────────────────────────────────
#  Callback: Risk level correction
# ────────────────────────────────────────────

async def risk_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle risk level correction — final step of the edit flow."""
    query = update.callback_query
    await query.answer()

    reviewer_id = query.from_user.id
    if not _is_authorised(reviewer_id, ["ANALYST", "ADMIN"]):
        await query.answer("⛔ Akses ditolak: Hanya peran ANALYST atau ADMIN yang berwenang memvalidasi temuan.", show_alert=True)
        return

    data = query.data  # e.g. "setrisk:TINGGI:<report_id>"
    parts = data.split(":")
    if len(parts) != 3:
        return

    new_risk = parts[1]
    report_id = parts[2]

    db = SessionLocal()
    try:
        report = db.query(Report).filter_by(report_id=report_id).first()
        if not report:
            await query.edit_message_text("⚠️ Laporan tidak ditemukan.")
            return

        report.final_risk = new_risk
        report.validated_at = datetime.utcnow()
        report.status = "MODIFIED"
        report.analyst_notes = report.analyst_notes or f"Koreksi analis: Kategori {report.final_label}, Risiko {new_risk}"
        db.commit()

        audit = AuditLog(
            action="VALIDATION_MODIFIED",
            actor_telegram_id=reviewer_id,
            entity_type="Report",
            entity_id=report_id,
            details={
                "final_label": report.final_label,
                "final_risk": new_risk,
            },
        )
        db.add(audit)
        db.commit()

        # Asynchronously write to RAG knowledge base
        try:
            rag_svc = RAGService()
            await asyncio.to_thread(rag_svc.create_knowledge_entry, db, report)
        except Exception as rag_err:
            logger.error("Failed to write RAG knowledge entry on modify: %s", rag_err)

        context.user_data["awaiting_note_for_report"] = str(report.report_id)

        await query.edit_message_text(
            f"✅ Laporan `{report.ticket_number}` telah *DIMODIFIKASI* oleh validator.\n"
            f"Label Baru: {report.final_label} | Risiko: {new_risk}\n"
            f"📚 *RAG*: Keputusan koreksi otomatis disimpan ke Knowledge Base.\n\n"
            f"💡 *Catatan Analis*: Balas pesan ini jika ingin menambahkan catatan alasan spesifik.",
            parse_mode="Markdown",
        )

    except Exception as e:
        db.rollback()
        logger.exception("Risk callback error: %s", e)
    finally:
        db.close()


# ────────────────────────────────────────────
#  Command: /rekap_harian
# ────────────────────────────────────────────

async def rekap_harian_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Export today's validated reports as an official DOCX and send to the requester."""
    user_id = update.effective_user.id
    if not _is_authorised(user_id, ["ANALYST", "ADMIN"]):
        await _safe_reply(update, "⛔ Akses ditolak: Perintah /rekap_harian hanya dapat diakses oleh peran ANALYST atau ADMIN.")
        return

    progress_msg = await _safe_reply(update, "📄 *Menyiapkan rekapitulasi harian resmi (DOCX)…*")

    db = SessionLocal()
    try:
        today_str = date.today().strftime("%Y-%m-%d")
        reports = (
            db.query(Report)
            .options(
                joinedload(Report.content).joinedload(Content.account),
                joinedload(Report.evidences),
            )
            .filter(
                Report.created_at >= datetime.strptime(today_str, "%Y-%m-%d"),
                Report.status.in_(["VALIDATED", "MODIFIED"]),
            )
            .order_by(Report.created_at.asc())
            .all()
        )

        if not reports:
            # Fallback to recent validated reports if none today yet
            all_reports = (
                db.query(Report)
                .options(
                    joinedload(Report.content).joinedload(Content.account),
                    joinedload(Report.evidences),
                )
                .filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
                .order_by(Report.created_at.desc())
                .limit(10)
                .all()
            )
            if not all_reports:
                await _safe_edit(
                    progress_msg,
                    "ℹ️ *Belum ada temuan patroli tervalidasi (VALIDATED / MODIFIED) dalam database.*\n"
                    "Laporan harian hanya merekap temuan yang telah disetujui atau dimodifikasi oleh analis.",
                )
                return
            reports = all_reports

        report_service = ReportService()
        filepath = report_service.generate_daily_docx(reports, today_str)

        # Audit log
        audit = AuditLog(
            action="REPORT_EXPORTED",
            actor_telegram_id=user_id,
            entity_type="Report",
            details={"date": today_str, "count": len(reports)},
        )
        db.add(audit)
        db.commit()

        # Send document directly via context.bot.send_document with retry
        chat_id = update.effective_chat.id
        doc_filename = os.path.basename(filepath)
        sent = False
        for attempt in range(3):
            try:
                with open(filepath, "rb") as doc_file:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=doc_file,
                        filename=doc_filename,
                        caption=(
                            f"📋 *Laporan Operasional Patroli Siber*\n"
                            f"📅 Periode Shift: `{today_str}`\n"
                            f"📊 Total Temuan: `{len(reports)} konten`\n\n"
                            f"Dokumen resmi DOCX terlampir siap serah ke Pimpinan."
                        ),
                        parse_mode="Markdown",
                    )
                sent = True
                break
            except Exception as send_err:
                logger.warning("Attempt %s/3 send_document failed: %s", attempt + 1, send_err)
                await asyncio.sleep(1)

        if sent:
            await _safe_edit(progress_msg, "✅ *Dokumen Rekapitulasi Berhasil Diterbitkan dan Dikirim.*")
        else:
            await _safe_edit(progress_msg, "❌ Gagal mengirim dokumen laporan. Silakan coba kembali.")

    except Exception as e:
        logger.exception("Recap generation failed: %s", e)
        await _safe_reply(update, f"❌ Gagal membuat rekapitulasi:\n`{e}`")
    finally:
        db.close()


# ────────────────────────────────────────────
#  Command: /status [ticket]
# ────────────────────────────────────────────

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check the status of a specific patrol ticket, or list active tickets."""
    user_id = update.effective_user.id
    if not _is_authorised(user_id):
        await _safe_reply(update, "⛔ Anda tidak memiliki akses ke sistem ini.")
        return

    db = SessionLocal()
    try:
        raw_ticket = context.args[0] if context.args else ""
        clean_ticket = raw_ticket.strip("<> ").upper()

        # If user typed /status without args or placeholder "<tiket>"
        if not clean_ticket or clean_ticket in ["TIKET", "<TIKET>", "HELP", "LIST"]:
            recent_reports = (
                db.query(Report)
                .options(joinedload(Report.content))
                .order_by(Report.created_at.desc())
                .limit(6)
                .all()
            )
            if not recent_reports:
                await _safe_reply(
                    update,
                    "ℹ️ *Belum ada tiket patroli dalam sistem.*\n\n"
                    "Kirimkan URL postingan atau unggah tangkapan layar untuk membuat tiket investigasi pertama Anda.",
                )
                return

            status_icons = {
                "PENDING_ANALYSIS": "⏳ PENDING",
                "WAITING_VALIDATION": "🔍 MENUNGGU VALIDASI",
                "MANUAL_FALLBACK": "⚠️ MANUAL FALLBACK",
                "FAILED": "❌ GAGAL",
                "VALIDATED": "✅ DISETUJUI",
                "MODIFIED": "✏️ DISESUAIKAN",
                "REJECTED": "✕ BUKAN PELANGGARAN",
            }

            lines = []
            for r in recent_reports:
                st = status_icons.get(r.status, r.status)
                plat = r.content.platform.upper() if r.content else "SIBER"
                lines.append(f"• `/status {r.ticket_number}`\n  Platform: *{plat}* | Status: {st}")

            list_text = "\n\n".join(lines)
            await _safe_reply(
                update,
                f"📋 *DAFTAR TIKET PATROLI TERKINI*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"{list_text}\n\n"
                f"👉 *Cara Cek*: Klik atau ketik salah satu perintah tiket di atas (misal: `/status {recent_reports[0].ticket_number}`).",
            )
            return

        # Query specific ticket (case-insensitive substring)
        report = (
            db.query(Report)
            .options(
                joinedload(Report.content).joinedload(Content.account),
                joinedload(Report.evidences),
            )
            .filter(Report.ticket_number.ilike(f"%{clean_ticket}%"))
            .first()
        )

        if not report:
            recent = db.query(Report).order_by(Report.created_at.desc()).limit(3).all()
            sugg_text = "\n".join([f"• `/status {r.ticket_number}`" for r in recent])
            await _safe_reply(
                update,
                f"⚠️ *Tiket `{clean_ticket}` tidak ditemukan.*\n\n"
                f"Contoh tiket yang tersedia saat ini:\n"
                f"{sugg_text}\n\n"
                f"Ketik `/status` untuk melihat seluruh tiket aktif.",
            )
            return

        status_emoji = {
            "PENDING_ANALYSIS": "⏳ PENDING (Sedang Diproses)",
            "WAITING_VALIDATION": "🔍 WAITING VALIDATION (Menunggu Validasi Analis)",
            "MANUAL_FALLBACK": "⚠️ MANUAL FALLBACK (Menunggu Foto Manual)",
            "FAILED": "❌ FAILED (Gagal Pemrosesan)",
            "VALIDATED": "✅ VALIDATED (Telah Disetujui)",
            "MODIFIED": "✏️ MODIFIED (Telah Dimodifikasi Validator)",
            "REJECTED": "✕ BUKAN PELANGGARAN (Ditolak/False Positive)",
        }
        status_label = status_emoji.get(report.status, report.status)

        acct_name = "N/A"
        acct_user = "N/A"
        platform = "SIBER"
        title = "N/A"
        canonical_url = ""

        if report.content:
            platform = report.content.platform.upper()
            canonical_url = report.content.canonical_url
            title = report.content.title or (report.content.caption_text[:60] if report.content.caption_text else "N/A")
            if report.content.account:
                acct_name = report.content.account.display_name or "N/A"
                acct_user = report.content.account.username or "N/A"

        sha_text = report.evidences[0].sha256 if report.evidences else "N/A"
        created_str = report.created_at.strftime("%Y-%m-%d %H:%M:%S") if report.created_at else "-"
        validated_str = report.validated_at.strftime("%Y-%m-%d %H:%M:%S") if report.validated_at else "Belum divalidasi"

        kategori = report.final_label or report.ai_predicted_label or "NETRAL"
        risiko = report.final_risk or report.ai_risk_level or "RENDAH"

        await _safe_reply(
            update,
            f"🎫 *STATUS TIKET PATROLI* | `{report.ticket_number}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 *Platform*: {platform}\n"
            f"👤 *Akun*: {acct_name} (`@{acct_user}`)\n"
            f"📌 *Judul*: {title}\n"
            f"🔗 *URL*: [Buka Konten]({canonical_url})\n\n"
            f"📊 *Status*: *{status_label}*\n"
            f"🏷️ *Kategori*: *{kategori}*\n"
            f"⚠️ *Tingkat Risiko*: *{risiko}*\n"
            f"📝 *Ringkasan*: _{report.ai_summary or '-'}_{' '}\n\n"
            f"🕒 *Waktu Temuan*: {created_str} UTC\n"
            f"⚖️ *Waktu Validasi*: {validated_str}\n"
            f"🔐 *SHA-256 Bukti*: `{sha_text}`",
        )
    finally:
        db.close()


# ────────────────────────────────────────────
#  Command: /whitelist (ADMIN)
# ────────────────────────────────────────────

async def whitelist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to inspect and manage patrol_users whitelist."""
    user_id = update.effective_user.id
    if not _is_authorised(user_id, ["ADMIN"]):
        await _safe_reply(update, "⛔ Akses ditolak: Perintah /whitelist hanya dapat diakses oleh peran ADMIN.")
        return

    args = context.args or []
    subcmd = args[0].lower() if args else "list"

    db = SessionLocal()
    try:
        from app.models.user import PatrolUser
        if subcmd == "list":
            users = db.query(PatrolUser).order_by(PatrolUser.created_at.desc()).all()
            if not users:
                await _safe_reply(update, "ℹ️ Belum ada pengguna terdaftar di tabel `patrol_users`.")
                return
            lines = ["👥 *DAFTAR WHITELIST PATROL USERS*\n━━━━━━━━━━━━━━━━━━━━━"]
            for u in users:
                status_icon = "🟢" if u.is_active else "🔴"
                lines.append(f"{status_icon} `{u.telegram_id}` — *{u.full_name}* (`{u.role}`)")
            await _safe_reply(update, "\n".join(lines))

        elif subcmd == "add" and len(args) >= 4:
            target_id = int(args[1])
            role_arg = args[2].upper()
            if role_arg not in ["OPERATOR", "ANALYST", "ADMIN"]:
                await _safe_reply(update, "⚠️ Role harus salah satu dari: `OPERATOR`, `ANALYST`, `ADMIN`.")
                return
            name_arg = " ".join(args[3:])
            user = db.query(PatrolUser).filter(PatrolUser.telegram_id == target_id).first()
            if user:
                user.role = role_arg
                user.full_name = name_arg
                user.is_active = True
            else:
                user = PatrolUser(
                    telegram_id=target_id,
                    full_name=name_arg,
                    role=role_arg,
                    is_active=True,
                )
                db.add(user)
            db.commit()
            await _safe_reply(update, f"✅ Pengguna `{target_id}` (*{name_arg}*) berhasil didaftarkan sebagai *{role_arg}*.")

        elif subcmd == "remove" and len(args) >= 2:
            target_id = int(args[1])
            user = db.query(PatrolUser).filter(PatrolUser.telegram_id == target_id).first()
            if user:
                user.is_active = False
                db.commit()
                await _safe_reply(update, f"✅ Pengguna `{target_id}` dinonaktifkan dari whitelist.")
            else:
                await _safe_reply(update, f"⚠️ Pengguna `{target_id}` tidak ditemukan.")
        else:
            await _safe_reply(
                update,
                "📖 *Panduan Perintah Whitelist (ADMIN)*:\n\n"
                "• `/whitelist list` — Tampilkan seluruh pengguna\n"
                "• `/whitelist add <id> <OPERATOR|ANALYST|ADMIN> <Nama>` — Tambah/ubah pengguna\n"
                "• `/whitelist remove <id>` — Nonaktifkan pengguna",
            )
    except Exception as e:
        logger.exception("Whitelist command error: %s", e)
        await _safe_reply(update, f"❌ Terjadi kesalahan: `{e}`")
    finally:
        db.close()


# ────────────────────────────────────────────
#  Build the Telegram Application
# ────────────────────────────────────────────

async def analyst_notes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text responses when an analyst provides notes for a validated/modified/rejected report."""
    report_id_str = context.user_data.get("awaiting_note_for_report")
    if not report_id_str or not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if text.startswith("http://") or text.startswith("https://") or text.startswith("/"):
        return

    db = SessionLocal()
    try:
        from uuid import UUID
        report = db.query(Report).filter(Report.report_id == UUID(report_id_str)).first()
        if report:
            report.analyst_notes = text
            db.commit()
            # Update knowledge entry with the custom notes
            rag_svc = RAGService()
            await asyncio.to_thread(rag_svc.create_knowledge_entry, db, report)
            context.user_data.pop("awaiting_note_for_report", None)
            await update.message.reply_text(
                f"📝 *Catatan analis berhasil disimpan untuk tiket* `{report.ticket_number}`:\n\n"
                f"_{text}_\n\n"
                f"📚 *Knowledge Base*: Entri RAG telah diperbarui dengan catatan analis.",
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error("Failed to save analyst note: %s", e)
    finally:
        db.close()


def build_bot_application() -> Application:
    """Construct and configure the Telegram bot application."""
    request = HTTPXRequest(
        connection_pool_size=16,
        connect_timeout=60.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=30.0,
        http_version="1.1",
    )
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).request(request).build()

    # Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("rekap_harian", rekap_harian_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("whitelist", whitelist_handler))

    # URL messages (any message containing a URL)
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"https?://"),
            url_handler,
        )
    )

    # Analyst note replies (text without URL or command when awaiting note)
    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND) & (~filters.Regex(r"https?://")),
            analyst_notes_handler,
        )
    )

    # Manual evidence photo upload (Human-in-the-Loop fallback)
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler,
        )
    )

    # Validation callbacks
    app.add_handler(
        CallbackQueryHandler(validation_callback_handler, pattern=r"^val:")
    )
    app.add_handler(
        CallbackQueryHandler(category_callback_handler, pattern=r"^setcat:")
    )
    app.add_handler(
        CallbackQueryHandler(risk_callback_handler, pattern=r"^setrisk:")
    )

    return app
