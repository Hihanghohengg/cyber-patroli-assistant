"""Trending topic calculation engine for Social Intelligence.

Calculates multi-factor weighted trending scores based on volume, growth rate,
velocity, platform/source diversity, recency decay, and analyst relevance.
Stores historical snapshots in TopicSnapshot for timeline visualization.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.intelligence import IssueCluster, IssueContent, TopicSnapshot, ContentAnalysis
from app.models.report import Content

logger = logging.getLogger(__name__)


class TrendingEngine:
    """Calculates weighted trending scores and generates periodic snapshots."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or getattr(settings, "TRENDING_WEIGHTS", {
            "volume": 0.30,
            "growth": 0.30,
            "velocity": 0.15,
            "source_diversity": 0.10,
            "recency": 0.10,
            "relevance": 0.05,
        })

    def calculate_issue_metrics(
        self,
        db: Session,
        issue_id: uuid.UUID,
        window_hours: int = 24,
    ) -> Dict:
        """Compute all component metrics for an IssueCluster over a time window."""
        now = datetime.utcnow()
        current_window_start = now - timedelta(hours=window_hours)
        previous_window_start = now - timedelta(hours=window_hours * 2)

        # 1. Seluruh temuan yang terhubung dalam klaster isu
        all_links = (
            db.query(IssueContent, Content)
            .join(Content, IssueContent.content_id == Content.content_id)
            .filter(IssueContent.issue_id == issue_id)
            .all()
        )
        total_count = len(all_links)

        # 2. Temuan baru dalam rentang jendela waktu aktif (24 jam terakhir)
        current_links = [
            (link, content)
            for link, content in all_links
            if content.created_at and content.created_at >= current_window_start
        ]
        current_count = len(current_links)

        # 3. Temuan pada jendela waktu sebelumnya (untuk menghitung laju pertumbuhan)
        prev_count = (
            db.query(func.count(IssueContent.id))
            .join(Content, IssueContent.content_id == Content.content_id)
            .filter(IssueContent.issue_id == issue_id)
            .filter(Content.created_at >= previous_window_start)
            .filter(Content.created_at < current_window_start)
            .scalar() or 0
        )

        if prev_count > 0:
            growth_rate = ((current_count - prev_count) / float(prev_count)) * 100.0
        else:
            growth_rate = 100.0 if current_count > 0 else 0.0

        # Kecepatan temuan per jam
        velocity = round(current_count / float(max(1, window_hours)), 2)

        # 4. Sebaran Platform & Akun Unik
        platform_dist: Dict[str, int] = {}
        unique_authors = set()
        total_interactions = 0

        for _, content in all_links:
            plat = (content.platform or "other").lower()
            platform_dist[plat] = platform_dist.get(plat, 0) + 1
            if content.account_id:
                unique_authors.add(content.account_id)
            
            # Hitung total interaksi digital
            total_interactions += (
                (content.likes_count or 0)
                + (content.views_count or 0)
                + (content.shares_count or 0)
                + (content.comments_count or 0)
            )

        unique_sources_count = len(unique_authors)
        platform_count = len(platform_dist)

        # 5. Distribusi Sentimen
        sentiments: Dict[str, int] = {"POSITIF": 0, "NEGATIF": 0, "NETRAL": 0, "CAMPURAN": 0}
        content_ids = [c.content_id for _, c in all_links]

        # -------------------------------------------------------------------------
        # FORMULA SKOR ISU HANGAT (HotScore 0-100) — 4 SINYAL OPERASIONAL NYATA
        # -------------------------------------------------------------------------
        from app.models.report import Report

        reports_map = {}
        analyses_map = {}
        if content_ids:
            rep_list = db.query(Report).filter(Report.content_id.in_(content_ids)).all()
            reports_map = {r.content_id: r for r in rep_list}

            ana_list = db.query(ContentAnalysis).filter(ContentAnalysis.content_id.in_(content_ids)).all()
            analyses_map = {a.content_id: a for a in ana_list}
            for a in ana_list:
                s = (a.sentiment or "NETRAL").upper()
                sentiments[s] = sentiments.get(s, 0) + 1

        # Sinyal 1: Urgensi Tervalidasi (35%)
        # Rata-rata urgency_score (1-5) dengan pembobotan 1.5x untuk konten HITL APPROVED/VALIDATED
        weighted_urgency_sum = 0.0
        weight_sum = 0.0
        for cid in content_ids:
            rep = reports_map.get(cid)
            ana = analyses_map.get(cid)

            # Ekstraksi urgensi 1-5
            u = 2.0
            if ana and ana.urgency_score is not None:
                raw_u = float(ana.urgency_score)
                u = (raw_u * 5.0) if raw_u <= 1.0 else raw_u
            elif rep and rep.ai_output and isinstance(rep.ai_output, dict) and rep.ai_output.get("urgency_score"):
                u = float(rep.ai_output["urgency_score"])
            elif rep and rep.ai_risk_level:
                u = 4.0 if rep.ai_risk_level == "TINGGI" else (3.0 if rep.ai_risk_level == "SEDANG" else 2.0)
            
            u = max(1.0, min(5.0, u))

            # Bobot 1.5x untuk konten yang tervalidasi analis manusia
            w = 1.0
            if rep and (rep.review_decision in ["APPROVED", "VALIDATED"] or rep.status == Report.STATUS_VALIDATED):
                w = 1.5

            weighted_urgency_sum += (u * w)
            weight_sum += w

        avg_urgency = (weighted_urgency_sum / max(1.0, weight_sum)) if weight_sum > 0 else 2.5
        score_urgency = min(100.0, max(0.0, (avg_urgency / 5.0) * 100.0))

        # Sinyal 2: Sebaran Lintas Platform (25%)
        # Jumlah platform unik dibagi 5 kanal target (X, Instagram, YouTube, Threads, Media)
        score_platform = min(100.0, max(0.0, (platform_count / 5.0) * 100.0))

        # Sinyal 3: Laju Tangkapan Baru / Velocity (25%)
        # Rasio temuan baru 24 jam terakhir terhadap total temuan dalam klaster
        score_velocity = min(100.0, max(0.0, (float(current_count) / float(max(1, total_count))) * 100.0))

        # Sinyal 4: Otoritas Sumber & Interaksi (15%)
        # Bonus +30 jika terdapat sumber media nasional + normalisasi logaritmik interaksi (maks 70)
        has_media = any(p in ["media", "news", "kompas", "detik", "tribun", "tempo"] for p in platform_dist.keys())
        media_bonus = 30.0 if has_media else 0.0
        interaction_norm = min(70.0, math.log1p(total_interactions) * 7.0)
        score_authority = min(100.0, max(0.0, media_bonus + interaction_norm))

        # Total HotScore Tertimbang (0-100)
        hot_score = (
            (0.35 * score_urgency)
            + (0.25 * score_platform)
            + (0.25 * score_velocity)
            + (0.15 * score_authority)
        )
        final_score = round(max(0.0, min(100.0, hot_score)), 1)

        # Label Status Eskalasi Berdasarkan Ambang Batas
        if final_score >= 75.0:
            escalation_label = "ESKALASI TINGGI"
        elif final_score >= 50.0:
            escalation_label = "MENGHANGAT"
        else:
            escalation_label = "PANTAU"

        return {
            "issue_id": issue_id,
            "total_count": total_count,
            "current_count": current_count,
            "recent_count_24h": current_count,
            "unique_sources": unique_sources_count,
            "platform_count": platform_count,
            "growth_rate": round(growth_rate, 2),
            "velocity": velocity,
            "trending_score": final_score,
            "escalation_label": escalation_label,
            "avg_urgency": round(avg_urgency, 2),
            "total_interactions": total_interactions,
            "platform_distribution": platform_dist,
            "sentiment_distribution": sentiments,
            "recency_score": round(score_velocity, 2),
            "snapshot_time": now,
        }

    def generate_and_save_snapshot(
        self,
        db: Session,
        issue_id: uuid.UUID,
        window_hours: int = 24,
    ) -> TopicSnapshot:
        """Calculate metrics and record a TopicSnapshot entry in the database."""
        metrics = self.calculate_issue_metrics(db, issue_id, window_hours=window_hours)

        snapshot = TopicSnapshot(
            issue_id=issue_id,
            snapshot_time=metrics["snapshot_time"],
            content_count=metrics["current_count"],
            unique_sources=metrics["unique_sources"],
            platform_count=metrics["platform_count"],
            growth_rate=metrics["growth_rate"],
            velocity=metrics["velocity"],
            trending_score=metrics["trending_score"],
            platform_distribution=metrics["platform_distribution"],
            sentiment_distribution=metrics["sentiment_distribution"],
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    def recalculate_all_active_issues(
        self,
        db: Session,
        window_hours: int = 24,
    ) -> List[TopicSnapshot]:
        """Run batch recalculation for all active issue clusters and generate snapshots."""
        active_issues = (
            db.query(IssueCluster)
            .filter(IssueCluster.status == "ACTIVE")
            .all()
        )
        snapshots = []
        for issue in active_issues:
            try:
                snap = self.generate_and_save_snapshot(db, issue.issue_id, window_hours=window_hours)
                snapshots.append(snap)
            except Exception as e:
                logger.error("Failed to generate snapshot for issue %s: %s", issue.issue_id, e)
                db.rollback()

        logger.info("Successfully generated snapshots for %d issues.", len(snapshots))
        return snapshots
