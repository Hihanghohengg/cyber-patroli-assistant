import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class PatrolUser(Base):
    """Registered patrol operator / analyst with Telegram identity."""
    __tablename__ = "patrol_users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="OPERATOR")  # OPERATOR, ANALYST, ADMIN
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, nullable=True)
