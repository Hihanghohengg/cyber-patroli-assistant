from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    PENDING_ANALYSIS = "PENDING_ANALYSIS"
    WAITING_VALIDATION = "WAITING_VALIDATION"
    VALIDATED = "VALIDATED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class PatrolRequest(BaseModel):
    """Incoming patrol request — a URL submitted by an operator."""
    url: str = Field(..., description="URL postingan publik yang akan dianalisis.")
    reporter_telegram_id: int = Field(..., description="Telegram user ID pengirim laporan.")
    intake_type: str = Field(default="LINK", description="Tipe intake: LINK atau MANUAL_SCREENSHOT.")


class AccountSnapshot(BaseModel):
    """Summary of a social media account at the time of capture."""
    username: str
    display_name: Optional[str] = None
    profile_url: str
    followers_count: int = 0
    following_count: int = 0
    total_posts: int = 0
    bio: Optional[str] = None


class ContentSnapshot(BaseModel):
    """Summary of the captured content / post."""
    platform: str
    canonical_url: str
    platform_content_id: Optional[str] = None
    caption_text: Optional[str] = None
    likes_count: int = 0
    views_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    posted_at: Optional[datetime] = None


class EvidenceSnapshot(BaseModel):
    """Evidence file metadata."""
    source_type: str
    storage_path: str
    sha256: str
    mime_type: str = "image/png"


class PatrolResponse(BaseModel):
    """Full response payload after processing a patrol request."""
    ticket_number: str
    status: TicketStatus
    account: AccountSnapshot
    content: ContentSnapshot
    evidences: List[EvidenceSnapshot] = []
    ai_status: Optional[str] = None
    ai_predicted_label: Optional[str] = None
    ai_risk_level: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    ai_summary: Optional[str] = None
    ai_reasoning: Optional[List[str]] = None
    created_at: datetime
