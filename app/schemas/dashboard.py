"""Pydantic schemas for Web Dashboard API requests and responses."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ==========================================
# AUTH SCHEMAS
# ==========================================

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    user_id: UUID
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# ==========================================
# OVERVIEW SCHEMAS
# ==========================================

class PlatformStat(BaseModel):
    platform: str
    count: int
    percentage: float


class SentimentStat(BaseModel):
    sentiment: str
    count: int
    percentage: float


class CategoryStat(BaseModel):
    category: str
    count: int


class OverviewStatsResponse(BaseModel):
    total_contents: int
    contents_last_24h: int
    active_issues_count: int
    pending_validations_count: int
    high_risk_contents_count: int
    platforms: List[PlatformStat]
    sentiments: List[SentimentStat]
    top_categories: List[CategoryStat]
    latest_trending: List["TrendingTopicItem"]


# ==========================================
# TRENDING TOPIC SCHEMAS
# ==========================================

class TrendingTopicItem(BaseModel):
    issue_id: UUID
    title: str
    canonical_name: str
    category: str
    status: str
    trending_score: float
    content_count: int
    platform_count: int
    growth_rate: float
    velocity: float
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    top_keywords: List[str] = []
    top_hashtags: List[str] = []
    sentiment_dominant: str = "NETRAL"

    class Config:
        from_attributes = True


class TopicTimelinePoint(BaseModel):
    snapshot_time: datetime
    content_count: int
    trending_score: float
    growth_rate: float
    velocity: float
    platform_distribution: Dict[str, int] = {}
    sentiment_distribution: Dict[str, int] = {}


class KeywordCloudItem(BaseModel):
    text: str
    value: int


class SourceItem(BaseModel):
    source_name: str
    platform: str
    content_count: int
    url: Optional[str] = None


class TrendingDetailResponse(BaseModel):
    issue: TrendingTopicItem
    description: Optional[str] = None
    named_entities: List[str] = []
    w5h1_summary: Dict[str, Optional[str]] = {}
    platform_breakdown: Dict[str, int] = {}
    sentiment_breakdown: Dict[str, int] = {}
    timeline: List[TopicTimelinePoint] = []
    keywords: List[KeywordCloudItem] = []
    sources: List[SourceItem] = []


# ==========================================
# CONTENT SCHEMAS
# ==========================================

class Analysis5W1HData(BaseModel):
    what: Optional[str] = None
    who: Optional[str] = None
    when_info: Optional[str] = None
    where_info: Optional[str] = None
    why: Optional[str] = None
    how: Optional[str] = None
    summary: Optional[str] = None
    main_topic: Optional[str] = None
    sub_topics: List[str] = []
    keywords: List[str] = []
    hashtags: List[str] = []
    named_entities: List[str] = []
    sentiment: Optional[str] = None
    tone: Optional[str] = None
    category: Optional[str] = None
    relevance_score: float = 0.0
    urgency_score: float = 0.0
    confidence_score: float = 0.0
    misinfo_indicators: List[str] = []


class ContentListItem(BaseModel):
    content_id: UUID
    platform: str
    url: str
    title: Optional[str] = None
    caption_snippet: Optional[str] = None
    author_username: Optional[str] = None
    status: str
    category: Optional[str] = None
    sentiment: Optional[str] = None
    risk_level: Optional[str] = None
    created_at: datetime
    screenshot_url: Optional[str] = None
    issue_title: Optional[str] = None


class ContentDetailResponse(BaseModel):
    content_id: UUID
    platform: str
    url: str
    title: Optional[str] = None
    caption: Optional[str] = None
    author: Dict[str, Any] = {}
    interaction: Dict[str, Any] = {}
    created_at: datetime
    status: str
    report_id: Optional[UUID] = None
    ai_patrol: Optional[Dict[str, Any]] = None
    analysis_5w1h: Optional[Analysis5W1HData] = None
    evidences: List[Dict[str, Any]] = []
    assigned_issue: Optional[Dict[str, Any]] = None


class ValidationRequest(BaseModel):
    status: str = Field(..., description="VALIDATED or REJECTED")
    notes: Optional[str] = None
    risk_level_override: Optional[str] = None
    category_override: Optional[str] = None


class ReclassifyRequest(BaseModel):
    category: Optional[str] = None
    issue_id: Optional[UUID] = None
    new_issue_title: Optional[str] = None
