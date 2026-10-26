"""Trending Topics API endpoints.

Lists, inspects, and analyzes detected trending issues, their timelines,
keyword clouds, associated social contents, and accounts.
"""

from typing import List, Optional
from uuid import UUID
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.database import get_db
from app.models.intelligence import IssueCluster, IssueContent, TopicSnapshot, ContentAnalysis
from app.models.report import Content, Account
from app.auth.dependencies import get_current_user
from app.services.intelligence.trending_engine import TrendingEngine
from app.schemas.dashboard import (
    TrendingTopicItem,
    TrendingDetailResponse,
    TopicTimelinePoint,
    KeywordCloudItem,
    SourceItem,
    ContentListItem,
)

router = APIRouter(prefix="/trending", tags=["Dashboard Trending Topics"])


@router.get("", response_model=List[TrendingTopicItem])
def list_trending_topics(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title or keyword"),
    status: str = Query("ACTIVE", description="ACTIVE, ARCHIVED, or ALL"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List trending topics sorted by trending score and recency."""
    query = db.query(IssueCluster)

    if status != "ALL":
        query = query.filter(IssueCluster.status == status)

    if category:
        query = query.filter(IssueCluster.category == category)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (IssueCluster.title.ilike(search_pattern)) |
            (IssueCluster.canonical_name.ilike(search_pattern))
        )

    # Sort by last_seen_at desc
    issues = query.order_by(desc(IssueCluster.last_seen_at)).limit(limit).all()

    items: List[TrendingTopicItem] = []
    for issue in issues:
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

        dominant_sent = "NETRAL"
        if last_snap and last_snap.sentiment_distribution:
            dominant_sent = max(last_snap.sentiment_distribution, key=last_snap.sentiment_distribution.get)

        items.append(
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
                top_keywords=issue.keywords[:6] if issue.keywords else [],
                top_hashtags=issue.hashtags[:6] if issue.hashtags else [],
                sentiment_dominant=dominant_sent,
            )
        )

    # Sort by trending score descending
    items.sort(key=lambda x: x.trending_score, reverse=True)
    return items


@router.get("/{issue_id}", response_model=TrendingDetailResponse)
def get_trending_topic_detail(
    issue_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retrieve in-depth details of a specific issue topic with aggregated 5W+1H."""
    issue = db.query(IssueCluster).filter(IssueCluster.issue_id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Topik tidak ditemukan")

    # Fetch snapshots for timeline
    snapshots = (
        db.query(TopicSnapshot)
        .filter(TopicSnapshot.issue_id == issue_id)
        .order_by(TopicSnapshot.snapshot_time.asc())
        .limit(48)
        .all()
    )

    last_snap = snapshots[-1] if snapshots else None

    # Fetch connected contents and analyses for 5W+1H synthesis
    contents_junction = (
        db.query(IssueContent, Content)
        .join(Content, IssueContent.content_id == Content.content_id)
        .filter(IssueContent.issue_id == issue_id)
        .all()
    )

    content_ids = [c.content_id for _, c in contents_junction]
    analyses = (
        db.query(ContentAnalysis)
        .filter(ContentAnalysis.content_id.in_(content_ids))
        .all()
    ) if content_ids else []

    # Synthesize 5W+1H
    w5h1 = {
        "what": None,
        "who": None,
        "when_info": None,
        "where_info": None,
        "why": None,
        "how": None,
    }
    all_keywords: List[str] = []
    platform_counts: dict = {}
    sentiment_counts: dict = {"POSITIF": 0, "NEGATIF": 0, "NETRAL": 0, "CAMPURAN": 0}

    for _, c in contents_junction:
        p = (c.platform or "other").lower()
        platform_counts[p] = platform_counts.get(p, 0) + 1

    for a in analyses:
        for k in ["what", "who", "when_info", "where_info", "why", "how"]:
            val = getattr(a, k, None)
            if val and not w5h1[k]:
                w5h1[k] = val
        if a.keywords:
            all_keywords.extend(a.keywords)
        s = (a.sentiment or "NETRAL").upper()
        sentiment_counts[s] = sentiment_counts.get(s, 0) + 1

    # Fallback to issue description if what is empty
    if not w5h1["what"]:
        w5h1["what"] = issue.description or issue.title

    # Keyword cloud
    kw_counter = Counter(all_keywords)
    cloud_items = [
        KeywordCloudItem(text=k, value=v)
        for k, v in kw_counter.most_common(25)
    ]

    # Timeline points
    timeline_pts = [
        TopicTimelinePoint(
            snapshot_time=s.snapshot_time,
            content_count=s.content_count,
            trending_score=s.trending_score,
            growth_rate=s.growth_rate,
            velocity=s.velocity,
            platform_distribution=s.platform_distribution or {},
            sentiment_distribution=s.sentiment_distribution or {},
        )
        for s in snapshots
    ]

    # Top sources / accounts
    source_items: List[SourceItem] = []
    author_counts = Counter(c.account_id for _, c in contents_junction if c.account_id)
    for acc_id, count in author_counts.most_common(10):
        acc = db.query(Account).filter(Account.account_id == acc_id).first()
        if acc:
            source_items.append(
                SourceItem(
                    source_name=acc.username or acc.display_name or "Anonim",
                    platform=acc.platform,
                    content_count=count,
                    url=acc.url,
                )
            )

    issue_item = TrendingTopicItem(
        issue_id=issue.issue_id,
        title=issue.title,
        canonical_name=issue.canonical_name,
        category=issue.category or "Lainnya",
        status=issue.status,
        trending_score=last_snap.trending_score if last_snap else 50.0,
        content_count=len(contents_junction),
        platform_count=len(platform_counts),
        growth_rate=last_snap.growth_rate if last_snap else 0.0,
        velocity=last_snap.velocity if last_snap else 0.0,
        first_seen_at=issue.first_seen_at,
        last_seen_at=issue.last_seen_at,
        top_keywords=issue.keywords[:8] if issue.keywords else [],
        top_hashtags=issue.hashtags[:8] if issue.hashtags else [],
        sentiment_dominant="NETRAL",
    )

    return TrendingDetailResponse(
        issue=issue_item,
        description=issue.description,
        named_entities=issue.named_entities or [],
        w5h1_summary=w5h1,
        platform_breakdown=platform_counts,
        sentiment_breakdown=sentiment_counts,
        timeline=timeline_pts,
        keywords=cloud_items,
        sources=source_items,
    )


@router.get("/{issue_id}/contents", response_model=List[ContentListItem])
def get_contents_for_topic(
    issue_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Fetch all contents grouped under this issue cluster."""
    junctions = (
        db.query(IssueContent, Content)
        .join(Content, IssueContent.content_id == Content.content_id)
        .filter(IssueContent.issue_id == issue_id)
        .order_by(desc(Content.created_at))
        .all()
    )

    items: List[ContentListItem] = []
    for _, c in junctions:
        analysis = (
            db.query(ContentAnalysis)
            .filter(ContentAnalysis.content_id == c.content_id)
            .first()
        )
        author = db.query(Account).filter(Account.account_id == c.account_id).first() if c.account_id else None

        items.append(
            ContentListItem(
                content_id=c.content_id,
                platform=c.platform,
                url=c.url,
                title=c.title,
                caption_snippet=(c.caption[:150] + "...") if c.caption and len(c.caption) > 150 else c.caption,
                author_username=author.username if author else None,
                status="VALIDATED" if getattr(c, "status", None) == "VALIDATED" else "ACTIVE",
                category=analysis.category if analysis else "Lainnya",
                sentiment=analysis.sentiment if analysis else "NETRAL",
                risk_level="RENDAH",
                created_at=c.created_at,
                screenshot_url=f"/api/dashboard/contents/{c.content_id}/screenshot",
                issue_title=None,
            )
        )
    return items


@router.post("/recalculate")
def trigger_trending_recalculation(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manually trigger recalculation of trending scores across all active issues."""
    engine = TrendingEngine()
    snapshots = engine.recalculate_all_active_issues(db, window_hours=24)
    return {
        "status": "success",
        "message": f"Berhasil menghitung ulang skor trending untuk {len(snapshots)} isu aktif.",
        "snapshots_generated": len(snapshots),
    }
