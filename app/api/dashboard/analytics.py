"""Analytics and Charts API endpoints for Web Dashboard."""

from datetime import datetime, timedelta
from typing import Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.report import Content
from app.models.intelligence import ContentAnalysis
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/analytics", tags=["Dashboard Analytics"])


@router.get("/timeseries")
def get_content_timeseries(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retrieve daily content discovery volume over the last N days."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    contents = (
        db.query(func.date(Content.created_at).label("day"), Content.platform, func.count(Content.content_id))
        .filter(Content.created_at >= start_date)
        .group_by(func.date(Content.created_at), Content.platform)
        .all()
    )

    day_map: Dict[str, Dict[str, int]] = {}
    for i in range(days + 1):
        d_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        day_map[d_str] = {"total": 0, "youtube": 0, "tiktok": 0, "instagram": 0}

    for d, plat, cnt in contents:
        d_str = str(d)
        if d_str in day_map:
            p = (plat or "other").lower()
            if p in day_map[d_str]:
                day_map[d_str][p] += cnt
            day_map[d_str]["total"] += cnt

    return [
        {"date": date_key, **metrics}
        for date_key, metrics in sorted(day_map.items())
    ]


@router.get("/platforms")
def get_platform_analytics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Detailed platform distribution with engagement sums."""
    results = (
        db.query(
            Content.platform,
            func.count(Content.content_id).label("count"),
            func.sum(Content.views_count).label("total_views"),
            func.sum(Content.likes_count).label("total_likes"),
            func.sum(Content.comments_count).label("total_comments"),
        )
        .group_by(Content.platform)
        .all()
    )

    return [
        {
            "platform": (row[0] or "other").lower(),
            "content_count": row[1],
            "total_views": int(row[2] or 0),
            "total_likes": int(row[3] or 0),
            "total_comments": int(row[4] or 0),
        }
        for row in results
    ]


@router.get("/sentiments")
def get_sentiment_analytics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Sentiment distribution across categories."""
    results = (
        db.query(
            ContentAnalysis.sentiment,
            ContentAnalysis.category,
            func.count(ContentAnalysis.analysis_id),
        )
        .group_by(ContentAnalysis.sentiment, ContentAnalysis.category)
        .all()
    )

    return [
        {
            "sentiment": (row[0] or "NETRAL").upper(),
            "category": row[1] or "Lainnya",
            "count": row[2],
        }
        for row in results
    ]
