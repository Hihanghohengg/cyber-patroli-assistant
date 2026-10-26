"""Entity and Alias normalization models for PRD v2.

Stores canonical topics, target actors, and content sources, along with
their alias mappings for exact and fuzzy normalization.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Entity(Base):
    """Canonical entity for Topics, Target Actors, or Content Sources."""
    __tablename__ = "entities"

    entity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)
    # Types: TOPIC, ACTOR, SOURCE
    canonical_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    source_kind = Column(String(50), nullable=True)
    # Kinds for SOURCE: MEDIA_ONLINE, MEDIA_TV, AKUN_INDIVIDU, KOMUNITAS, LAINNYA
    status = Column(String(50), default="ACTIVE")
    # Statuses: ACTIVE, APPROVED, PENDING_REVIEW, MERGED
    merged_into_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    aliases = relationship("EntityAlias", back_populates="entity", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("entity_type", "canonical_name", name="uq_entity_type_canonical"),
        Index("ix_entities_type_status", "entity_type", "status"),
        Index("ix_entities_canonical", "canonical_name"),
    )


class EntityAlias(Base):
    """Raw textual variations mapped to a canonical Entity."""
    __tablename__ = "entity_aliases"

    alias_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id", ondelete="CASCADE"), nullable=False)
    alias_text = Column(String(255), nullable=False)
    alias_normalized = Column(String(255), nullable=False)  # lowercase, alphanumeric-only for fast exact index
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity", back_populates="aliases")

    @property
    def alias(self) -> str:
        return self.alias_text

    @alias.setter
    def alias(self, val: str):
        self.alias_text = val

    __table_args__ = (
        Index("ix_entity_aliases_normalized", "alias_normalized"),
        Index("ix_entity_aliases_entity_id", "entity_id"),
    )


class ReportActor(Base):
    """Many-to-many relationship linking a Report to target Actor Entities (11th Physical Table)."""
    __tablename__ = "report_actors"

    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.report_id", ondelete="CASCADE"), primary_key=True)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), default="TARGET", nullable=False)  # e.g. TARGET, INSTITUSI_TERCATUT
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity")
    actor = relationship("Entity", foreign_keys=[entity_id], overlaps="entity")

    @property
    def id(self):
        return f"{self.report_id}:{self.entity_id}"

    @property
    def role_description(self) -> str:
        return self.role

    @role_description.setter
    def role_description(self, val: str):
        self.role = val

    __table_args__ = (
        Index("ix_report_actors_report_id", "report_id"),
        Index("ix_report_actors_entity_id", "entity_id"),
    )
