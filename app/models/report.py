import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, BigInteger, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Account(Base):
    """Social media account discovered during patrol."""
    __tablename__ = "accounts"

    account_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(50), nullable=False)  # youtube, tiktok, instagram
    platform_account_id = Column(String(255), nullable=True)
    username = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    profile_url = Column(Text, nullable=False)
    followers_count = Column(BigInteger, default=0)
    following_count = Column(BigInteger, default=0)
    total_posts = Column(BigInteger, default=0)
    bio = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    profile_screenshot_path = Column(Text, nullable=True)
    profile_screenshot_sha256 = Column(String(64), nullable=True)
    account_created_at = Column(DateTime, nullable=True)  # Added per proposal ERD
    discovered_at = Column(DateTime, default=datetime.utcnow)

    contents = relationship("Content", back_populates="account")


class Content(Base):
    """Individual post / video / story captured during patrol."""
    __tablename__ = "contents"

    content_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.account_id"), nullable=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    canonical_url = Column(Text, unique=False, nullable=True, index=True)  # Nullable for manual photo uploads
    platform_content_id = Column(String(255), nullable=True, index=True)
    title = Column(Text, nullable=True)
    caption_text = Column(Text, nullable=True)
    ocr_text = Column(Text, nullable=True, default="")
    likes_count = Column(BigInteger, default=0)
    views_count = Column(BigInteger, default=0)
    comments_count = Column(BigInteger, default=0)
    shares_count = Column(BigInteger, default=0)
    extra_metadata = Column("metadata", JSONB, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    account = relationship("Account", back_populates="contents")
    reports = relationship("Report", back_populates="content")

    @property
    def caption(self) -> str:
        return self.caption_text or ""


class Report(Base):
    """Patrol report tying content to AI analysis and human validation (FR-05 & FR-06)."""
    __tablename__ = "reports"

    # 7 Lifecycle Statuses (Proposal FR-05 & FR-06)
    STATUS_PENDING_ANALYSIS = "PENDING_ANALYSIS"
    STATUS_WAITING_VALIDATION = "WAITING_VALIDATION"
    STATUS_MANUAL_FALLBACK = "MANUAL_FALLBACK"
    STATUS_FAILED = "FAILED"
    STATUS_VALIDATED = "VALIDATED"
    STATUS_MODIFIED = "MODIFIED"
    STATUS_REJECTED = "REJECTED"

    VALID_STATUSES = {
        STATUS_PENDING_ANALYSIS,
        STATUS_WAITING_VALIDATION,
        STATUS_MANUAL_FALLBACK,
        STATUS_FAILED,
        STATUS_VALIDATED,
        STATUS_MODIFIED,
        STATUS_REJECTED,
    }

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number = Column(String(50), unique=True, index=True, nullable=False)  # e.g. PS-20261022-001
    reporter_telegram_id = Column(BigInteger, nullable=True)  # Deprecated
    source_channel = Column(String(50), default="BROWSER_EXTENSION", index=True)  # BROWSER_EXTENSION, WEB_DASHBOARD, API
    reporter_identifier = Column(String(255), nullable=True)  # Phone number, extension ID, or username
    operator_id = Column(String(100), default="OP-DEFAULT", index=True)  # Operator ID / NIP for Multi-User LAN
    content_id = Column(UUID(as_uuid=True), ForeignKey("contents.content_id"), nullable=False, index=True)
    intake_type = Column(String(50), default="LINK")  # LINK or MANUAL_SCREENSHOT
    status = Column(String(50), default="PENDING_ANALYSIS", index=True)

    # --- AI Classification Fields ---
    ai_status = Column(String(50), nullable=True)  # AMAN, BERPOTENSI_BAHAYA
    ai_predicted_label = Column(String(100), nullable=True, index=True)
    # Labels: HOAKS, SARA, UJARAN_KEBENCIAN, PENIPUAN_FINANSIAL, DI_LUAR_KONTEKS, NETRAL
    ai_risk_level = Column(String(50), nullable=True, index=True)  # RENDAH, SEDANG, TINGGI
    ai_confidence_score = Column(Numeric(4, 3), nullable=True)
    ai_summary = Column(Text, nullable=True)
    ai_reasoning = Column(JSONB, nullable=True)
    ai_output = Column(JSONB, nullable=True)  # Full raw AI output dictionary

    # --- TILIK Adaptive Learning & Latency Metrics ---
    classification_mode = Column(String(50), default="adaptive", nullable=True)  # baseline vs adaptive
    original_language = Column(String(10), default="id", nullable=True)  # e.g. "id", "en", "jv"
    indonesian_content = Column(Text, nullable=True)  # Clean narrative in formal Indonesian
    is_potential_duplicate = Column(Boolean, default=False, nullable=True)
    duplicate_of_ticket = Column(String(50), nullable=True)
    duplicate_similarity = Column(Numeric(4, 3), nullable=True)
    execution_latencies = Column(JSONB, default=dict)  # {"ocr_ms": 0, "retrieval_ms": 0, "llm_ms": 0, "total_ms": 0}

    # --- Extended AI Fields (PRD v3.0) ---
    ai_topic_raw = Column(String(255), nullable=True)
    ai_actors_raw = Column(JSONB, default=list)
    ai_source_raw = Column(String(255), nullable=True)
    ai_source_type = Column(String(50), nullable=True)
    # Types: MEDIA_ONLINE, MEDIA_TV, AKUN_INDIVIDU, KOMUNITAS, LAINNYA
    topic_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=True)

    # --- Human Review Fields ---
    reviewer_telegram_id = Column(BigInteger, nullable=True)
    review_decision = Column(String(50), nullable=True)
    # Decisions: APPROVED, MODIFIED, FALSE_POSITIVE
    final_label = Column(String(100), nullable=True)
    final_risk = Column(String(50), nullable=True)
    correction_notes = Column(Text, nullable=True)
    analyst_notes = Column(Text, nullable=True)  # Mandatory note for Ubah / Bukan Pelanggaran
    validated_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    content = relationship("Content", back_populates="reports")
    evidences = relationship("Evidence", back_populates="report")
    topic = relationship("Entity", foreign_keys=[topic_id])
    source = relationship("Entity", foreign_keys=[source_id])
    topic_entity = relationship("Entity", foreign_keys=[topic_id], overlaps="topic")
    source_entity = relationship("Entity", foreign_keys=[source_id], overlaps="source")
    target_actors = relationship("ReportActor", foreign_keys="ReportActor.report_id")

