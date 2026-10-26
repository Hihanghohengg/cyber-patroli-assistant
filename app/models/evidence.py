import re
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from app.database import Base


class Evidence(Base):
    """Digital evidence artifact linked to a patrol report (FR-03).

    Each evidence has a SHA-256 hash computed at capture time so that
    file integrity can be verified later for legal/forensic purposes (Chain of Custody).
    """
    __tablename__ = "evidences"

    evidence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.report_id"), nullable=False)
    source_type = Column(String(50), nullable=False)
    # Source types: SCRAPER_SCREENSHOT, MANUAL_UPLOAD, POST_SCREENSHOT, PROFILE_SCREENSHOT
    storage_path = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False)
    mime_type = Column(String(50), default="image/png")
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="evidences")

    @validates("sha256")
    def validate_sha256(self, key, value):
        if not value or not re.match(r"^[a-fA-F0-9]{64}$", value.strip()):
            raise ValueError(f"Nilai SHA-256 tidak valid: harus tepat 64 karakter heksadesimal (diterima: '{value}')")
        return value.strip().lower()
