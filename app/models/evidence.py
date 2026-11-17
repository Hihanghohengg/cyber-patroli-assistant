import re
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from app.database import Base


class Evidence(Base):
    """Digital evidence artifact linked to a patrol report (FR-03 & NIST FIPS 198-1).

    Maintains cryptographic evidence integrity, deterministic canonicalization,
    and HMAC-SHA256 authentication tag for tamper-evident chain of custody.
    """
    __tablename__ = "evidences"

    evidence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.report_id"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    # Source types: POST_SCREENSHOT, SCRAPER_SCREENSHOT, MANUAL_UPLOAD, PROFILE_SCREENSHOT
    storage_path = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False)
    mime_type = Column(String(50), default="image/png")

    # --- Cryptographic Evidence Integrity (Pilar RPLK - NIST FIPS 198-1) ---
    operator_id = Column(String(100), nullable=False, default="OP-DEFAULT")
    source_url = Column(Text, nullable=True)
    dom_text = Column(Text, nullable=True)
    ocr_text = Column(Text, nullable=True, default="")
    captured_at_utc = Column(String(50), nullable=True)
    canonical_hash = Column(String(64), nullable=True)  # SHA-256(canonical JSON payload)
    hmac_tag = Column(String(64), nullable=True)        # HMAC-SHA256(SECRET_HMAC_KEY, canonical JSON)
    verification_status = Column(String(50), default="VERIFIED")  # VERIFIED, TAMPERED, UNVERIFIED
    last_verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="evidences")

    @validates("sha256")
    def validate_sha256(self, key, value):
        if not value or not re.match(r"^[a-fA-F0-9]{64}$", value.strip()):
            raise ValueError(f"Nilai SHA-256 tidak valid: harus tepat 64 karakter heksadesimal (diterima: '{value}')")
        return value.strip().lower()
