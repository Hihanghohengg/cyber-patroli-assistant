"""Intelligence & Trending Topic models.

These models power the Social Intelligence dashboard and are purely additive —
they reference existing tables (contents, reports) via foreign keys but never
alter them.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Integer, BigInteger, Float, Boolean,
    DateTime, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class IssueCluster(Base):
    """A grouped issue / trending topic identified from multiple content items."""
    __tablename__ = "issue_clusters"

    issue_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    canonical_name = Column(String(500), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="Lainnya")
    # Categories: Politik, Bencana Alam, Lingkungan, Keamanan, Ekonomi,
    #             Sosial, Teknologi, Kesehatan, Pendidikan, Hukum, Lainnya
    keywords = Column(JSONB, default=list)         # ["karhutla", "asap", ...]
    hashtags = Column(JSONB, default=list)          # ["#karhutla", ...]
    named_entities = Column(JSONB, default=list)    # ["BNPB", "Kalimantan", ...]
    status = Column(String(50), default="ACTIVE")   # ACTIVE, ARCHIVED, MERGED
    first_seen_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    issue_contents = relationship("IssueContent", back_populates="issue", cascade="all, delete-orphan")
    snapshots = relationship("TopicSnapshot", back_populates="issue", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_issue_clusters_category", "category"),
        Index("ix_issue_clusters_status", "status"),
        Index("ix_issue_clusters_first_seen", "first_seen_at"),
        Index("ix_issue_clusters_last_seen", "last_seen_at"),
    )


class IssueContent(Base):
    """Many-to-many junction between IssueCluster and Content."""
    __tablename__ = "issue_contents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issue_clusters.issue_id"), nullable=False)
    content_id = Column(UUID(as_uuid=True), ForeignKey("contents.content_id"), nullable=False)
    similarity_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    issue = relationship("IssueCluster", back_populates="issue_contents")
    content = relationship("Content")

    __table_args__ = (
        UniqueConstraint("issue_id", "content_id", name="uq_issue_content"),
        Index("ix_issue_contents_issue_id", "issue_id"),
        Index("ix_issue_contents_content_id", "content_id"),
    )


class TopicSnapshot(Base):
    """Periodic snapshot of trending metrics for an issue cluster."""
    __tablename__ = "topic_snapshots"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issue_clusters.issue_id"), nullable=False)
    snapshot_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    content_count = Column(Integer, default=0)
    unique_sources = Column(Integer, default=0)
    platform_count = Column(Integer, default=0)
    growth_rate = Column(Float, default=0.0)        # % change vs previous snapshot
    velocity = Column(Float, default=0.0)            # items per hour
    trending_score = Column(Float, default=0.0)      # 0-100 normalised
    platform_distribution = Column(JSONB, default=dict)  # {"youtube": 5, "tiktok": 3}
    sentiment_distribution = Column(JSONB, default=dict)  # {"positif": 2, "negatif": 5, "netral": 3}

    # Relationships
    issue = relationship("IssueCluster", back_populates="snapshots")

    __table_args__ = (
        Index("ix_topic_snapshots_issue_id", "issue_id"),
        Index("ix_topic_snapshots_time", "snapshot_time"),
    )


class ContentAnalysis(Base):
    """Structured 5W+1H analysis result for a single content item.

    Produced by Gemini AI extraction — stored separately from the original
    Report AI fields so both can coexist without altering existing data.
    """
    __tablename__ = "content_analyses"

    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("contents.content_id"), nullable=False, unique=True)

    # 5W+1H
    what = Column(Text, nullable=True)
    who = Column(Text, nullable=True)
    when_info = Column(Text, nullable=True)   # 'when' is reserved in Python
    where_info = Column(Text, nullable=True)  # 'where' is reserved in SQL
    why = Column(Text, nullable=True)
    how = Column(Text, nullable=True)

    # Extended intelligence
    summary = Column(Text, nullable=True)
    main_topic = Column(String(300), nullable=True)
    sub_topics = Column(JSONB, default=list)
    keywords = Column(JSONB, default=list)
    hashtags = Column(JSONB, default=list)
    named_entities = Column(JSONB, default=list)
    sentiment = Column(String(50), nullable=True)  # POSITIF, NEGATIF, NETRAL, CAMPURAN
    tone = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    relevance_score = Column(Float, default=0.0)   # 0.0 – 1.0
    urgency_score = Column(Float, default=0.0)     # 0.0 – 1.0
    confidence_score = Column(Float, default=0.0)  # 0.0 – 1.0
    misinfo_indicators = Column(JSONB, default=list)
    analysis_model = Column(String(100), nullable=True)
    analysis_status = Column(String(50), default="COMPLETED")  # COMPLETED, FAILED, PENDING

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    content = relationship("Content")

    __table_args__ = (
        Index("ix_content_analyses_content_id", "content_id"),
        Index("ix_content_analyses_main_topic", "main_topic"),
        Index("ix_content_analyses_category", "category"),
        Index("ix_content_analyses_sentiment", "sentiment"),
    )


class DashboardUser(Base):
    """Web dashboard authentication — independent from Telegram whitelist."""
    __tablename__ = "dashboard_users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="ANALYST")  # ANALYST, ADMIN
    is_active = Column(Boolean, default=True)
    telegram_id = Column(BigInteger, nullable=True)  # optional link
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
