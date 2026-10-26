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

        # 1. Contents in current window
        current_links = (
            db.query(IssueContent, Content)
            .join(Content, IssueContent.content_id == Content.content_id)
            .filter(IssueContent.issue_id == issue_id)
            .filter(Content.created_at >= current_window_start)
            .all()
        )
        current_count = len(current_links)

        # 2. Total contents ever linked
        total_count = (
            db.query(func.count(IssueContent.id))
            .filter(IssueContent.issue_id == issue_id)
            .scalar() or 0
        )

        # 3. Contents in previous window (for growth rate)
        prev_count = (
            db.query(func.count(IssueContent.id))
            .join(Content, IssueContent.content_id == Content.content_id)
            .filter(IssueContent.issue_id == issue_id)
            .filter(Content.created_at >= previous_window_start)
            .filter(Content.created_at < current_window_start)
            .scalar() or 0
        )

        # Growth calculation
        if prev_count > 0:
            growth_rate = ((current_count - prev_count) / float(prev_count)) * 100.0
        else:
            growth_rate = 100.0 if current_count > 0 else 0.0

        # Velocity (items per hour)
        velocity = round(current_count / float(window_hours), 2)

        # 4. Sources and Platforms distribution
        platform_dist: Dict[str, int] = {}
        unique_authors = set()
        for link, content in current_links:
            plat = (content.platform or "other").lower()
            platform_dist[plat] = platform_dist.get(plat, 0) + 1
            if content.account_id:
                unique_authors.add(content.account_id)

        unique_sources_count = len(unique_authors)
        platform_count = len(platform_dist)

        # 5. Sentiments distribution from ContentAnalysis
        sentiments: Dict[str, int] = {"POSITIF": 0, "NEGATIF": 0, "NETRAL": 0, "CAMPURAN": 0}
        relevance_scores: List[float] = []

        if current_links:
            content_ids = [c.content_id for _, c in current_links]
            analyses = (
                db.query(ContentAnalysis)
                .filter(ContentAnalysis.content_id.in_(content_ids))
                .all()
            )
            for a in analyses:
                s = (a.sentiment or "NETRAL").upper()
                sentiments[s] = sentiments.get(s, 0) + 1
                if a.relevance_score is not None:
                    relevance_scores.append(a.relevance_score)

        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.5

        # 6. Recency decay
        issue = db.query(IssueCluster).filter(IssueCluster.issue_id == issue_id).first()
        last_seen = issue.last_seen_at or issue.created_at or now
        hours_since_last = max(0.0, (now - last_seen).total_seconds() / 3600.0)
        # Half-life of 24 hours: decay = 2^(-hours/24)
        recency_score = math.pow(0.5, hours_since_last / 24.0)

        # 7. Normalize components for trending formula
        # Volume score (0-100 logarithmic scale)
        norm_volume = min(100.0, math.log1p(current_count) * 20.0)

        # Growth score (-50% to +200% mapped to 0-100)
        norm_growth = min(100.0, max(0.0, (growth_rate + 50.0) / 2.5))

        # Velocity score (0 to 10 items/hr mapped to 0-100)
        norm_velocity = min(100.0, velocity * 10.0)

        # Diversity score (1 to 3 platforms + authors)
        plat_factor = min(1.0, platform_count / 3.0)
        author_factor = min(1.0, unique_sources_count / 5.0) if unique_sources_count else 0.2
        norm_diversity = (plat_factor * 0.6 + author_factor * 0.4) * 100.0

        # Recency score (0-100)
        norm_recency = recency_score * 100.0

        # Relevance score (0-100)
        norm_relevance = avg_relevance * 100.0

        # Compute weighted sum
        final_score = (
            self.weights.get("volume", 0.30) * norm_volume
            + self.weights.get("growth", 0.30) * norm_growth
            + self.weights.get("velocity", 0.15) * norm_velocity
            + self.weights.get("source_diversity", 0.10) * norm_diversity
            + self.weights.get("recency", 0.10) * norm_recency
            + self.weights.get("relevance", 0.05) * norm_relevance
        )
        final_score = round(max(0.0, min(100.0, final_score)), 2)

        return {
            "issue_id": issue_id,
            "total_count": total_count,
            "current_count": current_count,
            "unique_sources": unique_sources_count,
            "platform_count": platform_count,
            "growth_rate": round(growth_rate, 2),
            "velocity": velocity,
            "trending_score": final_score,
            "platform_distribution": platform_dist,
            "sentiment_distribution": sentiments,
            "recency_score": round(norm_recency, 2),
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
