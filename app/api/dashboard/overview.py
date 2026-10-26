"""Dashboard Overview API endpoint.

Provides aggregated KPIs, platform distributions, sentiment analysis breakdown,
and latest high-velocity trending issues for the main executive dashboard.
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models.intelligence import IssueCluster, IssueContent, TopicSnapshot, ContentAnalysis
from app.models.report import Content, Report
from app.auth.dependencies import get_current_user
from app.schemas.dashboard import (
    OverviewStatsResponse,
    PlatformStat,
    SentimentStat,
    CategoryStat,
    TrendingTopicItem,
)

router = APIRouter(prefix="/overview", tags=["Dashboard Overview"])


@router.get("", response_model=OverviewStatsResponse)
def get_dashboard_overview(
    db: Session = Depends(get_db),
    # Optional authentication or enabled auth
    current_user=Depends(get_current_user),
):
    """Fetch high-level overview metrics, KPI cards, and breakdowns."""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)

    # 1. KPIs
    total_contents = db.query(func.count(Content.content_id)).scalar() or 0
    contents_last_24h = (
        db.query(func.count(Content.content_id))
        .filter(Content.created_at >= last_24h)
        .scalar() or 0
    )
    active_issues_count = (
        db.query(func.count(IssueCluster.issue_id))
        .filter(IssueCluster.status == "ACTIVE")
        .scalar() or 0
    )
    pending_validations = (
        db.query(func.count(Report.report_id))
        .filter(Report.status == "PENDING")
        .scalar() or 0
    )
    high_risk_contents = (
        db.query(func.count(Report.report_id))
        .filter(Report.ai_risk_level == "TINGGI")
        .scalar() or 0
    )

    # 2. Platform distribution
    platform_rows = (
        db.query(Content.platform, func.count(Content.content_id))
        .group_by(Content.platform)
        .all()
    )
    platforms: List[PlatformStat] = []
    for plat, count in platform_rows:
        plat_name = plat.lower() if plat else "lainnya"
        pct = round((count / total_contents * 100.0), 1) if total_contents > 0 else 0.0
        platforms.append(PlatformStat(platform=plat_name, count=count, percentage=pct))

    # 3. Sentiment breakdown from ContentAnalysis
    sentiment_rows = (
        db.query(ContentAnalysis.sentiment, func.count(ContentAnalysis.analysis_id))
        .group_by(ContentAnalysis.sentiment)
        .all()
    )
    total_analyses = sum(cnt for _, cnt in sentiment_rows) or 1
    sentiments: List[SentimentStat] = []
    for sent, count in sentiment_rows:
        s_name = (sent or "NETRAL").upper()
        pct = round((count / total_analyses * 100.0), 1)
        sentiments.append(SentimentStat(sentiment=s_name, count=count, percentage=pct))

    # 4. Top categories from IssueClusters
    category_rows = (
        db.query(IssueCluster.category, func.count(IssueCluster.issue_id))
        .filter(IssueCluster.status == "ACTIVE")
        .group_by(IssueCluster.category)
        .order_by(desc(func.count(IssueCluster.issue_id)))
        .limit(6)
        .all()
    )
    categories = [
        CategoryStat(category=cat or "Lainnya", count=cnt)
        for cat, cnt in category_rows
    ]

    # 5. Top 5 trending issues
    # Join with latest snapshot or sort by last_seen_at
    latest_issues = (
        db.query(IssueCluster)
        .filter(IssueCluster.status == "ACTIVE")
        .order_by(desc(IssueCluster.last_seen_at))
        .limit(5)
        .all()
    )

    latest_trending: List[TrendingTopicItem] = []
    for issue in latest_issues:
        # Get latest snapshot if available
        last_snap = (
            db.query(TopicSnapshot)
            .filter(TopicSnapshot.issue_id == issue.issue_id)
            .order_by(desc(TopicSnapshot.snapshot_time))
            .first()
        )
        content_cnt = (
            db.query(func.count(IssueContent.id))
            .filter(IssueContent.issue_id == issue.issue_id)
            .scalar() or 0
        )

        latest_trending.append(
            TrendingTopicItem(
                issue_id=issue.issue_id,
                title=issue.title,
                canonical_name=issue.canonical_name,
                category=issue.category or "Lainnya",
                status=issue.status,
                trending_score=last_snap.trending_score if last_snap else 50.0,
                content_count=last_snap.content_count if last_snap else content_cnt,
                platform_count=last_snap.platform_count if last_snap else 1,
                growth_rate=last_snap.growth_rate if last_snap else 0.0,
                velocity=last_snap.velocity if last_snap else 0.0,
                first_seen_at=issue.first_seen_at,
                last_seen_at=issue.last_seen_at,
                top_keywords=issue.keywords[:5] if issue.keywords else [],
                top_hashtags=issue.hashtags[:5] if issue.hashtags else [],
                sentiment_dominant="NETRAL",
            )
        )

    return OverviewStatsResponse(
        total_contents=total_contents,
        contents_last_24h=contents_last_24h,
        active_issues_count=active_issues_count,
        pending_validations_count=pending_validations,
        high_risk_contents_count=high_risk_contents,
        platforms=platforms,
        sentiments=sentiments,
        top_categories=categories,
        latest_trending=latest_trending,
    )
