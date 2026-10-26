"""Entity normalization and alias deduplication service (PRD v2).

Provides exact and fuzzy matching to canonicalize Topics, Target Actors,
and Content Sources into unified entities.
"""

import re
import uuid
import difflib
import logging
from typing import List, Optional, Any
from sqlalchemy.orm import Session

from app.models.entities import Entity, EntityAlias, ReportActor

logger = logging.getLogger(__name__)

FUZZY_MATCH_THRESHOLD = 0.85


class EntityService:
    """Service to normalize, resolve, merge, and manage canonical entities and aliases."""

    @staticmethod
    def normalize_string(text: str) -> str:
        """Standardize raw string: lowercase, remove special characters, trim."""
        if not text:
            return ""
        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    def resolve_or_create_entity(
        self,
        db: Session,
        entity_type: str,
        raw_name: str,
        source_kind: Optional[str] = None,
    ) -> Entity:
        """Resolve a raw name to an existing canonical Entity or create as PENDING_REVIEW.

        Steps:
        1. Exact match against entity_aliases.alias_normalized for this entity_type
        2. Exact match against entities.canonical_name
        3. Fuzzy match against existing entities/aliases (>0.85 similarity)
        4. If no match: Create new Entity with status PENDING_REVIEW and record alias
        """
        raw_name = (raw_name or "").strip()
        if not raw_name:
            raw_name = "Tidak Diketahui"

        norm = self.normalize_string(raw_name)

        # 1. Exact alias match
        alias_match = (
            db.query(EntityAlias)
            .join(Entity, EntityAlias.entity_id == Entity.entity_id)
            .filter(Entity.entity_type == entity_type)
            .filter(EntityAlias.alias_normalized == norm)
            .first()
        )
        if alias_match:
            logger.info("Exact alias match: '%s' -> Canonical '%s'", raw_name, alias_match.entity.canonical_name)
            return alias_match.entity

        # 2. Exact canonical match
        canon_match = (
            db.query(Entity)
            .filter(Entity.entity_type == entity_type)
            .filter(Entity.canonical_name.ilike(raw_name))
            .first()
        )
        if canon_match:
            # Register alias for faster future lookups
            self._register_alias_if_absent(db, canon_match.entity_id, raw_name, norm)
            return canon_match

        # 3. Fuzzy matching against active/pending entities of same type
        candidates = (
            db.query(Entity)
            .filter(Entity.entity_type == entity_type)
            .all()
        )
        best_candidate: Optional[Entity] = None
        best_ratio = 0.0

        for cand in candidates:
            cand_norm = self.normalize_string(cand.canonical_name)
            ratio = difflib.SequenceMatcher(None, norm, cand_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_candidate = cand

        if best_candidate and best_ratio >= FUZZY_MATCH_THRESHOLD:
            logger.info(
                "Fuzzy matched '%s' -> '%s' (similarity: %.2f)",
                raw_name,
                best_candidate.canonical_name,
                best_ratio,
            )
            self._register_alias_if_absent(db, best_candidate.entity_id, raw_name, norm)
            return best_candidate

        # 4. No match found: create new Entity with PENDING_REVIEW
        new_entity = Entity(
            entity_type=entity_type,
            canonical_name=raw_name,
            source_kind=source_kind,
            status="PENDING_REVIEW",
        )
        db.add(new_entity)
        db.flush()

        alias = EntityAlias(
            entity_id=new_entity.entity_id,
            alias_text=raw_name,
            alias_normalized=norm,
        )
        db.add(alias)
        db.commit()
        db.refresh(new_entity)
        logger.info("Spawned new PENDING_REVIEW entity: '%s' (%s)", raw_name, entity_type)
        return new_entity

    def _register_alias_if_absent(self, db: Session, entity_id: uuid.UUID, text: str, norm: str):
        """Record alias mapping if not already recorded."""
        existing = (
            db.query(EntityAlias)
            .filter(EntityAlias.entity_id == entity_id, EntityAlias.alias_normalized == norm)
            .first()
        )
        if not existing:
            alias = EntityAlias(
                entity_id=entity_id,
                alias_text=text,
                alias_normalized=norm,
            )
            db.add(alias)
            db.commit()

    normalize_name = normalize_string

    def get_or_create_topic(self, db: Session, topic_name: str, category: Optional[str] = None) -> Entity:
        """Resolve or create canonical Topic entity."""
        return self.resolve_or_create_entity(db, "TOPIC", topic_name)

    def get_or_create_actor(self, db: Session, actor_name: str, category: Optional[str] = None) -> Entity:
        """Resolve or create canonical Actor entity."""
        return self.resolve_or_create_entity(db, "ACTOR", actor_name)

    def get_or_create_source(self, db: Session, source_name: str, source_kind: Optional[str] = None) -> Entity:
        """Resolve or create canonical Source entity."""
        return self.resolve_or_create_entity(db, "SOURCE", source_name, source_kind=source_kind)

    def link_report_actor(
        self,
        db: Session,
        report_id: uuid.UUID,
        actor_id: uuid.UUID,
        role: str = "TARGET",
    ) -> ReportActor:
        """Link a canonical Actor entity to a Report."""
        exists = (
            db.query(ReportActor)
            .filter(ReportActor.report_id == report_id, ReportActor.entity_id == actor_id)
            .first()
        )
        if not exists:
            link = ReportActor(
                report_id=report_id,
                entity_id=actor_id,
                role=role,
            )
            db.add(link)
            db.commit()
            return link
        return exists

    def register_alias(self, db: Session, entity_id: uuid.UUID, alias_text: str) -> EntityAlias:
        """Register a new alias variation for an existing canonical entity."""
        alias_text = (alias_text or "").strip()
        norm = self.normalize_string(alias_text)
        return self._register_alias_if_absent(db, entity_id, alias_text, norm)

    def link_report_actors(
        self,
        db: Session,
        report_id: uuid.UUID,
        raw_actors: List[str],
    ) -> List[Entity]:
        """Resolve and link a list of raw target actors to a Report."""
        entities = []
        for raw in raw_actors:
            if not raw or not raw.strip():
                continue
            actor_entity = self.resolve_or_create_entity(db, "ACTOR", raw.strip())
            entities.append(actor_entity)
            self.link_report_actor(db, report_id, actor_entity.entity_id, role="TARGET")
        return entities

    def merge_entities(
        self,
        db: Session,
        source_id: Any = None,
        target_id: Any = None,
        target_entity_id: Any = None,
        source_entity_id: Any = None,
    ) -> Entity:
        """Admin operation: merge source entity into target entity and migrate all aliases & links."""
        effective_source = source_id or source_entity_id
        effective_target = target_id or target_entity_id

        target = db.query(Entity).filter(Entity.entity_id == effective_target).first()
        source = db.query(Entity).filter(Entity.entity_id == effective_source).first()
        if not target or not source:
            raise ValueError("Target or source entity not found")

        # Migrate aliases
        aliases = db.query(EntityAlias).filter(EntityAlias.entity_id == effective_source).all()
        for a in aliases:
            a.entity_id = effective_target

        # Also add source's canonical name as an alias of target
        source_norm = self.normalize_string(source.canonical_name)
        self._register_alias_if_absent(db, effective_target, source.canonical_name, source_norm)

        # Migrate report links
        from app.models.report import Report
        db.query(Report).filter(Report.topic_id == effective_source).update({"topic_id": effective_target})
        db.query(Report).filter(Report.source_id == effective_source).update({"source_id": effective_target})

        # Migrate report actors
        db.query(ReportActor).filter(ReportActor.entity_id == effective_source).update({"entity_id": effective_target})

        # Migrate knowledge entries
        from app.models.knowledge import KnowledgeEntry
        db.query(KnowledgeEntry).filter(KnowledgeEntry.topic_id == effective_source).update({"topic_id": effective_target})
        db.query(KnowledgeEntry).filter(KnowledgeEntry.source_id == effective_source).update({"source_id": effective_target})

        # Mark source as MERGED
        source.status = "MERGED"
        source.merged_into_id = effective_target

        db.commit()
        db.refresh(target)
        logger.info("Merged entity '%s' into '%s'", source.canonical_name, target.canonical_name)
        return target

    def approve_entity(self, db: Session, entity_id: uuid.UUID) -> Entity:
        """Admin operation: approve a PENDING_REVIEW entity to APPROVED/ACTIVE status."""
        entity = db.query(Entity).filter(Entity.entity_id == entity_id).first()
        if not entity:
            raise ValueError("Entity not found")
        entity.status = "APPROVED"
        db.commit()
        db.refresh(entity)
        return entity
