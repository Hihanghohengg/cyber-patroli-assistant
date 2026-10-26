"""Celery task definitions for background patrol processing.

These tasks allow the patrol pipeline to run asynchronously, enqueued
via Redis and processed by Celery workers outside the Telegram bot's
event loop.
"""

import asyncio
import logging

from celery import Celery  # type: ignore

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

logger = logging.getLogger(__name__)

# ── Celery app ──
celery_app = Celery(
    "patrol_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "refresh-trending-scores-every-5-min": {
            "task": "app.workers.tasks.periodic_refresh_trending_scores",
            "schedule": 300.0,
        },
    },
)

SCRAPERS = {
    "youtube": YouTubeScraper(),
    "tiktok": TikTokScraper(),
    "instagram": InstagramScraper(),
}


def _run_async(coro):
    """Run an async coroutine from synchronous Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_patrol_url(self, url: str, reporter_telegram_id: int, ticket_number: str):
    """Full async patrol pipeline executed in a Celery worker.

    Steps:
    1. Detect platform & extract metadata
    2. Capture visual evidence (screenshots)
    3. Run AI analysis
    4. Persist everything to PostgreSQL

    This task is enqueued by the FastAPI endpoint and can also be
    invoked directly for batch processing.
    """
    db = SessionLocal()
    try:
        platform = BaseScraper.detect_platform(url)
        scraper = SCRAPERS[platform]

        # ── Step 1: Metadata ──
        logger.info("[%s] Extracting metadata for %s", ticket_number, url)
        meta = scraper.extract_metadata(url)

        # ── Step 2: Upsert Account ──
        account = (
            db.query(Account)
            .filter_by(platform=platform, username=meta["account"]["username"])
            .first()
        )
        if not account:
            account = Account(
                platform=platform,
                username=meta["account"]["username"],
                display_name=meta["account"].get("display_name"),
                profile_url=meta["account"].get("profile_url", ""),
                followers_count=meta["account"].get("subscribers_count", 0),
            )
            db.add(account)
            db.flush()

        # ── Step 3: Upsert Content ──
        content = (
            db.query(Content)
            .filter_by(canonical_url=meta["canonical_url"])
            .first()
        )
        if not content:
            content = Content(
                account_id=account.account_id,
                platform=platform,
                canonical_url=meta["canonical_url"],
                platform_content_id=meta.get("platform_content_id"),
                caption_text=meta.get("caption", ""),
                likes_count=meta.get("likes_count", 0),
                views_count=meta.get("views_count", 0),
                comments_count=meta.get("comments_count", 0),
                posted_at=meta.get("posted_at"),
            )
            db.add(content)
            db.flush()

        # ── Step 4: Report ──
        report = Report(
            ticket_number=ticket_number,
            reporter_telegram_id=reporter_telegram_id,
            content_id=content.content_id,
            intake_type="LINK",
            status="PENDING_ANALYSIS",
        )
        db.add(report)
        db.flush()

        # ── Step 5: Screenshots with MANUAL_FALLBACK check ──
        logger.info("[%s] Capturing visual evidence", ticket_number)
        evidence_data = {}
        try:
            evidence_data = _run_async(
                scraper.capture_visual_evidence(
                    post_url=meta["canonical_url"],
                    profile_url=meta["account"].get("profile_url", ""),
                    ticket_number=ticket_number,
                )
            )
        except Exception as scrap_err:
            logger.warning("[%s] Scraper capture failed, switching to MANUAL_FALLBACK: %s", ticket_number, scrap_err)
            report.status = "MANUAL_FALLBACK"
            db.add(
                AuditLog(
                    action="MANUAL_FALLBACK",
                    actor_telegram_id=reporter_telegram_id,
                    entity_type="Report",
                    entity_id=str(report.report_id),
                    details={"error": str(scrap_err), "url": url},
                )
            )
            db.commit()
            return {"status": "MANUAL_FALLBACK", "ticket_number": ticket_number, "reason": str(scrap_err)}

        # ── Step 6: Evidence records ──
        if evidence_data.get("post_screenshot_path"):
            db.add(
                Evidence(
                    report_id=report.report_id,
                    source_type="POST_SCREENSHOT",
                    storage_path=evidence_data["post_screenshot_path"],
                    sha256=evidence_data["post_screenshot_hash"],
                )
            )
        if evidence_data.get("profile_screenshot_path"):
            db.add(
                Evidence(
                    report_id=report.report_id,
                    source_type="PROFILE_SCREENSHOT",
                    storage_path=evidence_data["profile_screenshot_path"],
                    sha256=evidence_data["profile_screenshot_hash"],
                )
            )
        db.flush()

        # ── Step 7: AI Analysis with RAG Fail-Open ──
        logger.info("[%s] Retrieving RAG reference cases & running AI analysis", ticket_number)
        from app.services.rag_service import RAGService
        from app.services.entity_service import EntityService

        rag_svc = RAGService()
        entity_svc = EntityService()
        rag_context = ""
        try:
            rag_context = rag_svc.retrieve_similar_cases(
                db=db,
                text=meta.get("caption", "") or meta.get("title", ""),
                top_k=5,
                threshold=0.75,
            )
        except Exception as rag_err:
            logger.warning("[%s] RAG retrieval failed (fail-open): %s", ticket_number, rag_err)

        ai_service = AIService()
        try:
            ai_result = ai_service.analyze_patrol_finding(
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

            # Entity canonicalization & linking
            try:
                if ai_result.topik:
                    topic_ent = entity_svc.get_or_create_topic(db, ai_result.topik)
                    report.topic_id = topic_ent.entity_id
                if ai_result.sumber_konten:
                    source_ent = entity_svc.get_or_create_source(db, ai_result.sumber_konten, ai_result.tipe_sumber)
                    report.source_id = source_ent.entity_id
                if ai_result.aktor_target:
                    for actor_name in ai_result.aktor_target:
                        actor_ent = entity_svc.get_or_create_actor(db, actor_name)
                        entity_svc.link_report_actor(db, report.report_id, actor_ent.entity_id, role="TARGET")
            except Exception as ent_err:
                logger.warning("[%s] Entity linking encountered error: %s", ticket_number, ent_err)

        except Exception as ai_err:
            logger.error("[%s] AI analysis failed: %s", ticket_number, ai_err)
            report.ai_summary = f"AI analysis failed: {ai_err}"

        report.status = "WAITING_VALIDATION"
        db.commit()

        # Audit
        db.add(
            AuditLog(
                action="REPORT_CREATED",
                actor_telegram_id=reporter_telegram_id,
                entity_type="Report",
                entity_id=str(report.report_id),
                details={"ticket": ticket_number, "platform": platform, "url": url},
            )
        )
        db.commit()

        # Enqueue intelligence extraction & clustering (non-blocking)
        try:
            enrich_content_intelligence.delay(str(content.content_id))
        except Exception as q_err:
            logger.warning("[%s] Could not enqueue intelligence extraction: %s", ticket_number, q_err)

        logger.info("[%s] Pipeline complete — WAITING_VALIDATION", ticket_number)
        return {"ticket": ticket_number, "status": "WAITING_VALIDATION"}

    except Exception as exc:
        db.rollback()
        logger.exception("[%s] Worker task failed", ticket_number)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=15)
def enrich_content_intelligence(self, content_id_str: str):
    """Run 5W+1H intelligence extraction and trigger cluster matching for a content item."""
    from uuid import UUID
    from app.models.intelligence import ContentAnalysis
    from app.services.intelligence.analysis_5w1h import Analysis5W1HService

    db = SessionLocal()
    try:
        content_id = UUID(content_id_str)
        content = db.query(Content).filter(Content.content_id == content_id).first()
        if not content:
            logger.warning("Content %s not found for intelligence enrichment", content_id_str)
            return

        # Check if already analyzed
        existing = db.query(ContentAnalysis).filter(ContentAnalysis.content_id == content_id).first()
        if existing and existing.analysis_status == "COMPLETED":
            logger.info("Content %s already has 5W+1H analysis; reclustering directly", content_id_str)
            cluster_content_to_issues.delay(content_id_str)
            return

        # Find post screenshot evidence if available
        report = db.query(Report).filter(Report.content_id == content_id).first()
        image_path = None
        if report:
            evidence = (
                db.query(Evidence)
                .filter(Evidence.report_id == report.report_id, Evidence.source_type == "POST_SCREENSHOT")
                .first()
            )
            if evidence:
                image_path = evidence.storage_path

        # Author username
        author_username = content.account.username if content.account else ""

        # Run extraction
        extractor = Analysis5W1HService()
        result = extractor.extract(
            text=content.caption_text or "",
            title=content.title or "",
            image_path=image_path,
            author=author_username,
            platform=content.platform,
            metadata=content.extra_metadata or {},
        )

        # Upsert ContentAnalysis
        if not existing:
            analysis_rec = ContentAnalysis(
                content_id=content_id,
                what=result.what,
                who=result.who,
                when_info=result.when_info,
                where_info=result.where_info,
                why=result.why,
                how=result.how,
                summary=result.summary,
                main_topic=result.main_topic,
                sub_topics=result.sub_topics,
                keywords=result.keywords,
                hashtags=result.hashtags,
                named_entities=result.named_entities,
                sentiment=result.sentiment,
                tone=result.tone,
                category=result.category,
                relevance_score=result.relevance_score,
                urgency_score=result.urgency_score,
                confidence_score=result.confidence_score,
                misinfo_indicators=result.misinfo_indicators,
                analysis_model="gemini",
                analysis_status="COMPLETED",
            )
            db.add(analysis_rec)
        else:
            existing.what = result.what
            existing.who = result.who
            existing.when_info = result.when_info
            existing.where_info = result.where_info
            existing.why = result.why
            existing.how = result.how
            existing.summary = result.summary
            existing.main_topic = result.main_topic
            existing.sub_topics = result.sub_topics
            existing.keywords = result.keywords
            existing.hashtags = result.hashtags
            existing.named_entities = result.named_entities
            existing.sentiment = result.sentiment
            existing.tone = result.tone
            existing.category = result.category
            existing.relevance_score = result.relevance_score
            existing.urgency_score = result.urgency_score
            existing.confidence_score = result.confidence_score
            existing.misinfo_indicators = result.misinfo_indicators
            existing.analysis_status = "COMPLETED"

        db.commit()
        logger.info("Successfully saved 5W+1H analysis for content %s", content_id_str)

        # Trigger cluster matching
        cluster_content_to_issues.delay(content_id_str)

    except Exception as e:
        db.rollback()
        logger.error("Failed to enrich content %s: %s", content_id_str, e)
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=15)
def cluster_content_to_issues(self, content_id_str: str):
    """Assign content to an existing issue cluster or create a new cluster."""
    from uuid import UUID
    from app.services.intelligence.topic_clustering import TopicClusteringService

    db = SessionLocal()
    try:
        content_id = UUID(content_id_str)
        clustering_svc = TopicClusteringService()
        cluster, score, is_new = clustering_svc.assign_content_to_cluster(db, content_id)
        logger.info(
            "Clustering completed for content %s -> Issue '%s' (score=%.2f, is_new=%s)",
            content_id_str,
            cluster.title,
            score,
            is_new,
        )
    except Exception as e:
        db.rollback()
        logger.error("Clustering failed for content %s: %s", content_id_str, e)
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task
def periodic_refresh_trending_scores():
    """Periodic Celery Beat task: recalculates trending scores for all active issues."""
    from app.services.intelligence.trending_engine import TrendingEngine

    db = SessionLocal()
    try:
        engine = TrendingEngine()
        snapshots = engine.recalculate_all_active_issues(db, window_hours=24)
        logger.info("Periodic trending calculation completed: %d snapshots generated", len(snapshots))
    except Exception as e:
        logger.error("Periodic trending calculation error: %s", e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=20)
def write_knowledge_entry_task(self, report_id_str: str):
    """Asynchronously compute embeddings and store validated decision in RAG knowledge base."""
    from uuid import UUID
    from app.services.rag_service import RAGService

    db = SessionLocal()
    try:
        report_id = UUID(report_id_str)
        report = db.query(Report).filter(Report.report_id == report_id).first()
        if not report:
            logger.warning("Report %s not found for knowledge entry write", report_id_str)
            return

        rag_svc = RAGService()
        entry = rag_svc.create_knowledge_entry(db, report)
        logger.info("Knowledge entry successfully written for report %s (entry_id: %s)", report_id_str, entry.entry_id)
        return {"report_id": report_id_str, "entry_id": str(entry.entry_id)}
    except Exception as e:
        db.rollback()
        logger.error("Failed to write knowledge entry for report %s: %s", report_id_str, e)
        raise self.retry(exc=e)
    finally:
        db.close()

