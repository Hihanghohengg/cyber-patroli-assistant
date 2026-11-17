"""Validated Case Memory Model for Human-in-the-Loop (HITL) Adaptive Learning (MemPrompt Pattern).

Stores verified ground-truth cases with analyst rationales and dense vector embeddings
to dynamically inject few-shot in-context examples into local LLM inference without retraining.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ValidatedMemory(Base):
    """Analyst-validated ground truth case memory for training-free adaptive classification."""
    __tablename__ = "validated_memory"

    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("contents.content_id"), nullable=True, index=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.report_id"), nullable=True, index=True)

    content_text = Column(Text, nullable=False)
    embedding_vector = Column(Text, nullable=True)  # JSON-encoded array of 384 float dimensions (SBERT)
    validated_category = Column(String(100), nullable=False, index=True)
    # Target categories: Ideologi, Politik, Ekonomi, Sosial, Budaya, Pertahanan, Keamanan, Non-Isu
    analyst_rationale = Column(Text, nullable=False)
    validated_by = Column(String(100), nullable=False, default="ANALYST")
    urgency_score = Column(Integer, default=3)  # Scale 1 - 5
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    content = relationship("Content")
    report = relationship("Report")

    __table_args__ = (
        Index("ix_validated_memory_category", "validated_category"),
        Index("ix_validated_memory_created", "created_at"),
    )

