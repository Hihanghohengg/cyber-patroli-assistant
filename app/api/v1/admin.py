"""Admin Management API Endpoints (v1).

Role: ADMIN only.
Provides curation tools for:
- RAG Knowledge Base entries
- Canonical Entities & Aliases (Merging, Approval, Alias Registration)
- Dashboard Users (Listing, Role Provisioning)
- Forensic Audit Logs
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_

from app.database import get_db
from app.models.knowledge import KnowledgeEntry
from app.models.entities import Entity, EntityAlias
from app.models.intelligence import DashboardUser
from app.models.user import PatrolUser
from app.models.audit import AuditLog
from app.auth.dependencies import require_role
from app.auth.jwt_handler import hash_password
from app.services.rag_service import RAGService
from app.services.entity_service import EntityService

router = APIRouter(prefix="/admin", tags=["Admin v1"])


# ────────────────────────────────────────────
# Pydantic Schemas
# ────────────────────────────────────────────

class KnowledgeCreateRequest(BaseModel):
    ticket_number: str
    content_text: str
    verified_category: str
    verified_risk: str
    analyst_decision: str = "APPROVED"
    analyst_notes: Optional[str] = None
    source_platform: Optional[str] = "MANUAL"
    account_username: Optional[str] = None


class KnowledgeUpdateRequest(BaseModel):
    verified_category: Optional[str] = None
    verified_risk: Optional[str] = None
    analyst_notes: Optional[str] = None
    analyst_decision: Optional[str] = None
    is_active: Optional[bool] = None


class EntityMergeRequest(BaseModel):
    source_id: UUID
    target_id: UUID


class EntityAliasCreateRequest(BaseModel):
    alias: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str = ""
    role: str = "ANALYST"


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None


class PatrolUserCreateRequest(BaseModel):
    telegram_id: int
    full_name: str
    role: str = "OPERATOR"  # OPERATOR, ANALYST, ADMIN


class PatrolUserUpdateRequest(BaseModel):
    role: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


# ────────────────────────────────────────────
# Knowledge Base Endpoints
# ────────────────────────────────────────────

@router.get("/knowledge")
def list_knowledge_entries(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """List curated RAG knowledge base entries."""
    query = db.query(KnowledgeEntry)

    if category:
        query = query.filter(KnowledgeEntry.verified_category.ilike(f"%{category}%"))
    if decision:
        query = query.filter(KnowledgeEntry.analyst_decision == decision)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                KnowledgeEntry.ticket_number.ilike(search_pattern),
                KnowledgeEntry.content_text.ilike(search_pattern),
                KnowledgeEntry.analyst_notes.ilike(search_pattern),
            )
        )

    total = query.count()
    offset = (page - 1) * limit
    entries = query.order_by(KnowledgeEntry.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for e in entries:
        has_emb = e.embedding is not None
        items.append({
            "entry_id": str(e.entry_id),
            "ticket_number": e.ticket_number,
            "content_summary": e.content_text[:200] + "..." if len(e.content_text) > 200 else e.content_text,
            "verified_category": e.verified_category,
            "verified_risk": e.verified_risk,
            "analyst_decision": e.analyst_decision,
            "analyst_notes": e.analyst_notes,
            "source_platform": e.source_platform,
            "has_embedding": has_emb,
            "is_active": e.is_active,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": items,
    }


@router.get("/knowledge/{entry_id}")
def get_knowledge_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Retrieve full details for a knowledge base entry."""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entri knowledge base tidak ditemukan")

    return {
        "entry_id": str(entry.entry_id),
        "ticket_number": entry.ticket_number,
        "content_text": entry.content_text,
        "verified_category": entry.verified_category,
        "verified_risk": entry.verified_risk,
        "analyst_decision": entry.analyst_decision,
        "analyst_notes": entry.analyst_notes,
        "source_platform": entry.source_platform,
        "account_username": entry.account_username,
        "extra_metadata": entry.extra_metadata,
        "is_active": entry.is_active,
        "has_embedding": entry.embedding is not None,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.post("/knowledge", status_code=status.HTTP_201_CREATED)
def create_knowledge_entry_manually(
    payload: KnowledgeCreateRequest,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Manually add an exemplar reference case to the RAG knowledge base."""
    rag_svc = RAGService()
    embedding = rag_svc.generate_embedding(payload.content_text)

    entry = KnowledgeEntry(
        ticket_number=payload.ticket_number,
        content_text=payload.content_text,
        verified_category=payload.verified_category,
        verified_risk=payload.verified_risk,
        analyst_decision=payload.analyst_decision,
        analyst_notes=payload.analyst_notes,
        source_platform=payload.source_platform,
        account_username=payload.account_username,
        embedding=embedding,
        is_active=True,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Audit
    db.add(
        AuditLog(
            action="KNOWLEDGE_CREATED",
            actor_telegram_id=0,
            entity_type="KnowledgeEntry",
            entity_id=str(entry.entry_id),
            details={"ticket": payload.ticket_number, "admin": admin.username},
        )
    )
    db.commit()

    return {"entry_id": str(entry.entry_id), "status": "created"}


@router.put("/knowledge/{entry_id}")
def update_knowledge_entry(
    entry_id: UUID,
    payload: KnowledgeUpdateRequest,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Update verified fields, notes, or active status of a knowledge entry."""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entri knowledge base tidak ditemukan")

    if payload.verified_category is not None:
        entry.verified_category = payload.verified_category
    if payload.verified_risk is not None:
        entry.verified_risk = payload.verified_risk
    if payload.analyst_notes is not None:
        entry.analyst_notes = payload.analyst_notes
    if payload.analyst_decision is not None:
        entry.analyst_decision = payload.analyst_decision
    if payload.is_active is not None:
        entry.is_active = payload.is_active
        if not payload.is_active:
            entry.deactivated_at = datetime.utcnow()
            entry.deactivated_by = getattr(admin, "telegram_id", 0)
        else:
            entry.deactivated_at = None

    db.commit()
    return {"entry_id": str(entry.entry_id), "status": "updated", "is_active": entry.is_active}


@router.delete("/knowledge/{entry_id}")
def deactivate_knowledge_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Deactivate knowledge base entry without hard-delete (NFR-07: Versioning Berjejak)."""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entri knowledge base tidak ditemukan")

    # Business rule: Never hard-delete
    entry.is_active = False
    entry.deactivated_at = datetime.utcnow()
    entry.deactivated_by = getattr(admin, "telegram_id", 0)

    # Audit log
    db.add(
        AuditLog(
            action="KNOWLEDGE_DEACTIVATED",
            actor_username=admin.username,
            entity_type="KnowledgeEntry",
            entity_id=str(entry.entry_id),
            details={"reason": "Admin dashboard soft-deactivation"},
        )
    )
    db.commit()
    return {"entry_id": str(entry_id), "status": "deactivated", "is_active": False}


# ────────────────────────────────────────────
# Entity Management Endpoints
# ────────────────────────────────────────────

@router.get("/entities")
def list_canonical_entities(
    entity_type: Optional[str] = Query(None, regex="^(TOPIC|ACTOR|SOURCE)$"),
    status_filter: Optional[str] = Query(None, alias="status", regex="^(APPROVED|PENDING_REVIEW|MERGED)$"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """List canonical entities with their alias count and curation status."""
    query = db.query(Entity).options(joinedload(Entity.aliases))

    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    if status_filter:
        query = query.filter(Entity.status == status_filter)
    if search:
        query = query.filter(Entity.canonical_name.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * limit
    entities = query.order_by(Entity.canonical_name.asc()).offset(offset).limit(limit).all()

    items = []
    for e in entities:
        items.append({
            "entity_id": str(e.entity_id),
            "canonical_name": e.canonical_name,
            "entity_type": e.entity_type,
            "category": e.category,
            "status": e.status,
            "merged_into_id": str(e.merged_into_id) if e.merged_into_id else None,
            "aliases": [a.alias for a in (e.aliases or [])],
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": items,
    }


@router.post("/entities/merge")
def merge_entities_endpoint(
    payload: EntityMergeRequest,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Merge duplicate source entity into canonical target entity."""
    entity_svc = EntityService()
    try:
        target = entity_svc.merge_entities(db, payload.source_id, payload.target_id)
        # Audit
        db.add(
            AuditLog(
                action="ENTITY_MERGED",
                actor_telegram_id=0,
                entity_type="Entity",
                entity_id=str(target.entity_id),
                details={
                    "source_id": str(payload.source_id),
                    "target_name": target.canonical_name,
                    "admin": admin.username,
                },
            )
        )
        db.commit()
        return {
            "status": "merged",
            "target_id": str(target.entity_id),
            "target_canonical_name": target.canonical_name,
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.put("/entities/{entity_id}/approve")
def approve_entity_endpoint(
    entity_id: UUID,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Approve a PENDING_REVIEW entity into APPROVED canonical status."""
    entity_svc = EntityService()
    try:
        ent = entity_svc.approve_entity(db, entity_id)
        return {
            "status": "approved",
            "entity_id": str(ent.entity_id),
            "canonical_name": ent.canonical_name,
        }
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))


@router.post("/entities/{entity_id}/aliases", status_code=status.HTTP_201_CREATED)
def add_entity_alias(
    entity_id: UUID,
    payload: EntityAliasCreateRequest,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Add a manual alias variant to an existing canonical entity."""
    entity_svc = EntityService()
    ent = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Entitas tidak ditemukan")

    alias_rec = entity_svc.register_alias(db, entity_id, payload.alias)
    return {
        "status": "created",
        "alias_id": str(alias_rec.alias_id),
        "alias": alias_rec.alias,
    }


# ────────────────────────────────────────────
# Users & Audit Endpoints
# ────────────────────────────────────────────

@router.get("/users")
def list_dashboard_users(
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """List all registered dashboard operators and administrators."""
    users = db.query(DashboardUser).order_by(DashboardUser.created_at.desc()).all()
    return [
        {
            "user_id": str(u.user_id),
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_dashboard_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Create new dashboard user account (Role: USER or ADMIN)."""
    if db.query(DashboardUser).filter(DashboardUser.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Nama pengguna sudah digunakan")

    user = DashboardUser(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role.upper(),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "user_id": str(user.user_id),
        "username": user.username,
        "role": user.role,
        "status": "created",
    }


@router.put("/users/{user_id}")
def update_dashboard_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Update role, active state, or display name of a user."""
    user = db.query(DashboardUser).filter(DashboardUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")

    if payload.role is not None:
        user.role = payload.role.upper()
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.full_name is not None:
        user.full_name = payload.full_name

    db.commit()
    return {"user_id": str(user.user_id), "status": "updated"}


@router.get("/audit")
def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Retrieve immutable audit logs of patrol creation, validations, and curation."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    total = query.count()
    offset = (page - 1) * limit
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": [
            {
                "log_id": str(l.log_id),
                "action": l.action,
                "actor_telegram_id": l.actor_telegram_id,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "details": l.details,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            }
            for l in logs
        ],
    }


# ────────────────────────────────────────────
# Patrol Users (Telegram Whitelist) Endpoints
# ────────────────────────────────────────────

@router.get("/patrol-users")
def list_patrol_users(
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """List all registered Telegram patrol operators, analysts, and admins."""
    users = db.query(PatrolUser).order_by(PatrolUser.created_at.desc()).all()
    return [
        {
            "user_id": str(u.user_id),
            "telegram_id": u.telegram_id,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "last_active_at": u.last_active_at.isoformat() if u.last_active_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/patrol-users", status_code=status.HTTP_201_CREATED)
def create_or_update_patrol_user(
    payload: PatrolUserCreateRequest,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Register or update a Telegram patrol user role."""
    existing = db.query(PatrolUser).filter(PatrolUser.telegram_id == payload.telegram_id).first()
    if existing:
        existing.role = payload.role.upper()
        existing.full_name = payload.full_name
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return {"user_id": str(existing.user_id), "status": "updated", "role": existing.role}

    user = PatrolUser(
        telegram_id=payload.telegram_id,
        full_name=payload.full_name,
        role=payload.role.upper(),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user_id": str(user.user_id), "status": "created", "role": user.role}


@router.put("/patrol-users/{user_id}")
def update_patrol_user(
    user_id: UUID,
    payload: PatrolUserUpdateRequest,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Update role, name, or active status of a patrol user."""
    user = db.query(PatrolUser).filter(PatrolUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Petugas patroli tidak ditemukan")

    if payload.role is not None:
        user.role = payload.role.upper()
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    return {"user_id": str(user.user_id), "status": "updated"}


@router.delete("/patrol-users/{user_id}")
def deactivate_patrol_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: DashboardUser = Depends(require_role("ADMIN")),
):
    """Soft-deactivate a patrol user from whitelist."""
    user = db.query(PatrolUser).filter(PatrolUser.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Petugas patroli tidak ditemukan")

    user.is_active = False
    db.commit()
    return {"user_id": str(user_id), "status": "deactivated"}
