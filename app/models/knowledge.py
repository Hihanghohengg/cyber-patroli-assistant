"""Knowledge Base models for RAG system (PRD v2).

Stores past analyst decisions with vector embeddings to augment future
AI triages with verified institutional context.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, BigInteger, Boolean, DateTime, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

import json
from sqlalchemy.types import TypeDecorator, Text as SqlText

# Gracefully support pgvector or fallback type with SQLite JSON serialization
try:
    from pgvector.sqlalchemy import Vector as PgVector  # type: ignore
except ImportError:
    PgVector = None

class Vector(TypeDecorator):
    impl = SqlText
    cache_ok = True

    def __init__(self, dim=768):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite" or PgVector is None:
            return dialect.type_descriptor(SqlText())
        return dialect.type_descriptor(PgVector(self.dim))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite" or PgVector is None:
            if isinstance(value, (list, tuple)):
                return json.dumps(list(value))
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if (dialect.name == "sqlite" or PgVector is None) and isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value


class KnowledgeEntry(Base):
    """A verified case in the RAG Knowledge Base (NFR-07 - Versioning Berjejak).

    Strict rule: Never overwrite or hard-delete entries.
    When a report is re-validated, previous active entries are set to is_active=False
    with deactivated_at=utcnow, and a new version is inserted.
    """
    __tablename__ = "knowledge_entries"

    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.report_id", ondelete="CASCADE"), nullable=True)
    ticket_number = Column(String(100), nullable=True)
    source_platform = Column(String(50), nullable=True)
    account_username = Column(String(100), nullable=True)
    decision = Column(String(50), nullable=True)  # VALIDATED, MODIFIED, REJECTED
    final_label = Column(String(100), nullable=False)  # HOAKS, UJARAN_KEBENCIAN, PROVOKASI_SARA, etc.
    final_risk = Column(String(50), nullable=True)   # RENDAH, SEDANG, TINGGI (or None for REJECTED)
    notes = Column(Text, nullable=True)               # Mandatory notes from analyst
    reasoning = Column(Text, nullable=True)           # Justification or correction reasons
    summary_text = Column(Text, nullable=True)        # Narrative summary
    topic_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=True)

    embed_text = Column(Text, nullable=True)          # Title + Caption + OCR + Summary
    embedding = Column(Vector(768), nullable=True)    # Gemini text-embedding-004 is 768 dimensions

    decided_by = Column(BigInteger, nullable=True)    # Telegram ID of the analyst
    is_active = Column(Boolean, default=True, nullable=False)  # Active version flag
    deactivated_by = Column(BigInteger, nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    report = relationship("Report")
    topic = relationship("Entity", foreign_keys=[topic_id])
    source = relationship("Entity", foreign_keys=[source_id])

    @property
    def analyst_notes(self) -> str:
        return self.notes or ""

    @analyst_notes.setter
    def analyst_notes(self, val: str):
        self.notes = val

    @property
    def verified_category(self):
        return self.final_label

    @verified_category.setter
    def verified_category(self, val):
        self.final_label = val

    @property
    def verified_risk(self):
        return self.final_risk

    @verified_risk.setter
    def verified_risk(self, val):
        self.final_risk = val

    @property
    def analyst_decision(self):
        return self.decision

    @analyst_decision.setter
    def analyst_decision(self, val):
        self.decision = val

    @property
    def content_text(self):
        return self.embed_text or self.summary_text or ""

    @content_text.setter
    def content_text(self, val):
        self.embed_text = val

    @property
    def extra_metadata(self):
        return {}

    __table_args__ = (
        Index("ix_knowledge_entries_report_id", "report_id"),
        Index("ix_knowledge_entries_active", "is_active"),
        Index("ix_knowledge_entries_decision", "decision"),
        Index("ix_knowledge_entries_final_label", "final_label"),
        Index("uq_active_knowledge_report", "report_id", unique=True, postgresql_where=(is_active == True)),
    )
