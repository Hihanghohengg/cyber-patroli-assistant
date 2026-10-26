import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class AuditLog(Base):
    """Immutable audit trail for every significant system action."""
    __tablename__ = "audit_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String(100), nullable=False)
    # Actions: REPORT_CREATED, AI_ANALYSIS_COMPLETED, VALIDATION_APPROVED,
    #          VALIDATION_MODIFIED, VALIDATION_REJECTED, REPORT_EXPORTED
    actor_telegram_id = Column(BigInteger, nullable=True)
    actor_username = Column(String(100), nullable=True)
    entity_type = Column(String(50), nullable=True)  # Report, Evidence, Account
    entity_id = Column(String(100), nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    @property
    def created_at(self):
        return self.timestamp

    @created_at.setter
    def created_at(self, val):
        self.timestamp = val
