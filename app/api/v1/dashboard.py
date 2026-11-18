"""Web Dashboard Public API Endpoints (v1).

Role: USER and ADMIN.
Implements summary, timeseries, breakdown, top entities, reports explorer, and export.
Strictly surfaces VALIDATED and MODIFIED reports with final labels and neutral disclaimers.
"""

import csv
import io
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_

from app.database import get_db
from app.models.report import Report, Content, Account
from app.models.evidence import Evidence
from app.models.entities import Entity, ReportActor
from app.models.intelligence import DashboardUser, ContentAnalysis
from app.models.audit import AuditLog
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard v1"])


@router.get("/summary")
def get_dashboard_summary(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    platform: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: DashboardUser = Depends(get_current_user),
):
    """Aggregated patrol metrics: 4 KPIs, category, risk, platform distributions and AI agreement rate."""
    base_all_q = db.query(Report).join(Content, Report.content_id == Content.content_id, isouter=True)
    if date_from:
        base_all_q = base_all_q.filter(Report.created_at >= date_from)
    if date_to:
        base_all_q = base_all_q.filter(Report.created_at <= date_to)
    if platform:
        base_all_q = base_all_q.filter(Content.platform.ilike(platform))

    # 4 KPI Ringkasan (Proposal Gambar L3.18)
    total_laporan = base_all_q.count()
    temuan_tervalidasi = base_all_q.filter(Report.status.in_(["VALIDATED", "MODIFIED"])).count()
    koreksi_analis = base_all_q.filter(Report.status == "MODIFIED").count()
    bukan_pelanggaran = base_all_q.filter(Report.status == "REJECTED").count()

    # Query seluruh temuan aktif patroli (tidak ditolak) agar metrik live & langsung terlihat
    active_q = base_all_q.filter(Report.status != "REJECTED")
    if category:
        active_q = active_q.filter(
            or_(
                Report.final_label.ilike(category),
                Report.ai_predicted_label.ilike(category)
            )
        )
    if risk_level:
        active_q = active_q.filter(
            or_(
                Report.final_risk.ilike(risk_level),
                Report.ai_risk_level.ilike(risk_level)
            )
        )

    # Kategori (Gunakan final_label jika ada, atau fallback ke ai_predicted_label)
    eff_label = func.coalesce(Report.final_label, Report.ai_predicted_label, "Non-Isu")
    kategori_rows = (
        active_q.with_entities(eff_label, func.count(Report.report_id))
        .group_by(eff_label)
        .all()
    )
    distribusi_kategori = {cat: count for cat, count in kategori_rows if cat}

    # Risiko (Gunakan final_risk jika ada, atau fallback ke ai_risk_level)
    eff_risk = func.coalesce(Report.final_risk, Report.ai_risk_level, "SEDANG")
    risiko_rows = (
        active_q.with_entities(eff_risk, func.count(Report.report_id))
        .group_by(eff_risk)
        .all()
    )
    distribusi_risiko = {rsk: count for rsk, count in risiko_rows if rsk}

    # Platform (Dihitung dari seluruh temuan aktif postingan)
    platform_rows = (
        active_q.with_entities(Content.platform, func.count(Report.report_id))
        .group_by(Content.platform)
        .all()
    )
    distribusi_platform = {
        (plt.upper() if plt else "WEB"): count for plt, count in platform_rows
    }

    # Putusan Evaluasi AI vs Analis (Visual 8)
    validated_cnt = base_all_q.filter(Report.status == "VALIDATED").count()
    putusan_evaluasi = {
        "VALIDATED": validated_cnt,
        "MODIFIED": koreksi_analis,
        "REJECTED": bukan_pelanggaran,
    }

    # Rasio Persetujuan AI
    eval_query = db.query(Report).filter(Report.review_decision.isnot(None))
    if date_from:
        eval_query = eval_query.filter(Report.created_at >= date_from)
    if date_to:
        eval_query = eval_query.filter(Report.created_at <= date_to)

    total_eval = eval_query.count()
    if total_eval > 0:
        setuju_cnt = eval_query.filter(Report.review_decision == "APPROVED").count()
        ubah_cnt = eval_query.filter(Report.review_decision == "MODIFIED").count()
        tolak_cnt = eval_query.filter(Report.review_decision == "FALSE_POSITIVE").count()

        rasio_ai = {
            "setuju_pct": round((setuju_cnt / total_eval) * 100, 1),
            "ubah_pct": round((ubah_cnt / total_eval) * 100, 1),
            "tolak_pct": round((tolak_cnt / total_eval) * 100, 1),
            "total_dievaluasi": total_eval,
        }
    else:
        rasio_ai = {
            "setuju_pct": 100.0,
            "ubah_pct": 0.0,
            "tolak_pct": 0.0,
            "total_dievaluasi": 0,
        }

    return {
        "total_laporan": total_laporan,
        "temuan_tervalidasi": temuan_tervalidasi,
        "koreksi_analis": koreksi_analis,
        "bukan_pelanggaran": bukan_pelanggaran,
        "distribusi_kategori": distribusi_kategori,
        "distribusi_risiko": distribusi_risiko,
        "distribusi_platform": distribusi_platform,
        "putusan_evaluasi": putusan_evaluasi,
        "rasio_persetujuan_ai": rasio_ai,
    }


@router.get("/timeseries")
def get_dashboard_timeseries(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    interval: str = Query("day", pattern="^(hour|day|week)$"),
    metric: str = Query("total", pattern="^(total|by_category|by_risk)$"),
    db: Session = Depends(get_db),
    current_user: DashboardUser = Depends(get_current_user),
):
    """Time-series aggregation for dual-line volume trends (Laporan Masuk vs Tervalidasi)."""
    if not date_to:
        date_to = datetime.utcnow()
    if not date_from:
        date_from = date_to - timedelta(days=14)

    query = (
        db.query(Report)
        .filter(Report.created_at >= date_from, Report.created_at <= date_to)
        .order_by(Report.created_at.asc())
    )

    reports = query.all()

    # Bucketing logic
    buckets: Dict[str, Dict[str, Any]] = {}

    for r in reports:
        dt = r.created_at or datetime.utcnow()
        if interval == "hour":
            key = dt.strftime("%Y-%m-%dT%H:00:00Z")
        elif interval == "week":
            start_week = dt - timedelta(days=dt.weekday())
            key = start_week.strftime("%Y-%m-%dT00:00:00Z")
        else:
            key = dt.strftime("%Y-%m-%dT00:00:00Z")

        if key not in buckets:
            buckets[key] = {
                "timestamp": key,
                "total": 0,
                "total_masuk": 0,
                "tervalidasi": 0,
                "breakdown": {},
            }

        buckets[key]["total_masuk"] += 1
        if r.status in ["VALIDATED", "MODIFIED"]:
            buckets[key]["tervalidasi"] += 1
            buckets[key]["total"] += 1

            if metric == "by_category":
                cat = r.final_label or "LAINNYA"
                buckets[key]["breakdown"][cat] = buckets[key]["breakdown"].get(cat, 0) + 1
            elif metric == "by_risk":
                rsk = r.final_risk or "SEDANG"
                buckets[key]["breakdown"][rsk] = buckets[key]["breakdown"].get(rsk, 0) + 1

    series = sorted(buckets.values(), key=lambda x: x["timestamp"])

    return {
        "interval": interval,
        "metric": metric,
        "series": series,
    }


@router.get("/breakdown")
def get_dashboard_breakdown(
    dimension: str = Query("category", pattern="^(category|risk|platform|source_type)$"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: DashboardUser = Depends(get_current_user),
):
    """Categorical distribution breakdown with counts and percentages."""
    query = (
        db.query(Report)
        .join(Content, Report.content_id == Content.content_id, isouter=True)
        .filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
    )

    if date_from:
        query = query.filter(Report.created_at >= date_from)
    if date_to:
        query = query.filter(Report.created_at <= date_to)

    total = query.count()
    items = []

    if dimension == "category":
        rows = (
            query.with_entities(Report.final_label, func.count(Report.report_id))
            .group_by(Report.final_label)
            .order_by(desc(func.count(Report.report_id)))
            .all()
        )
        for name, cnt in rows:
            items.append({
                "label": name or "LAINNYA",
                "count": cnt,
                "percentage": round((cnt / total * 100), 1) if total > 0 else 0,
            })
    elif dimension == "risk":
        rows = (
            query.with_entities(Report.final_risk, func.count(Report.report_id))
            .group_by(Report.final_risk)
            .order_by(desc(func.count(Report.report_id)))
            .all()
        )
        for name, cnt in rows:
            items.append({
                "label": name or "BELUM_DITENTUKAN",
                "count": cnt,
                "percentage": round((cnt / total * 100), 1) if total > 0 else 0,
            })
    elif dimension == "platform":
        rows = (
            query.with_entities(Content.platform, func.count(Report.report_id))
            .group_by(Content.platform)
            .order_by(desc(func.count(Report.report_id)))
            .all()
        )
        for name, cnt in rows:
            items.append({
                "label": (name.upper() if name else "MANUAL"),
                "count": cnt,
                "percentage": round((cnt / total * 100), 1) if total > 0 else 0,
            })
    elif dimension == "source_type":
        rows = (
            query.with_entities(Report.ai_source_type, func.count(Report.report_id))
            .group_by(Report.ai_source_type)
            .order_by(desc(func.count(Report.report_id)))
            .all()
        )
        for name, cnt in rows:
            items.append({
                "label": name or "LAINNYA",
                "count": cnt,
                "percentage": round((cnt / total * 100), 1) if total > 0 else 0,
            })

    return {
        "dimension": dimension,
        "total": total,
        "items": items,
    }


@router.get("/top")
def get_dashboard_top(
    dimension: str = Query("topics", pattern="^(topics|actors|sources)$"),
    limit: int = Query(10, ge=1, le=50),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: DashboardUser = Depends(get_current_user),
):
    """Top canonical topics, target actors, or content sources with neutral disclaimer."""
    disclaimer = (
        "Data agregasi hasil ekstraksi dan kurasi patroli siber. "
        "Penyebutan entitas/aktor target atau sumber konten merupakan frekuensi temuan konten, "
        "bukan atribusi hukum atau penetapan kesalahan."
    )

    items = []

    if dimension == "topics":
        # Group by topic entity if linked, otherwise fallback to cluster/raw
        rows = (
            db.query(
                Entity.entity_id,
                Entity.canonical_name,
                Entity.category,
                Entity.status,
                func.count(Report.report_id).label("cnt"),
            )
            .join(Report, Report.topic_id == Entity.entity_id)
            .filter(Report.status != "REJECTED")
            .filter(Entity.entity_type == "TOPIC")
        )
        if date_from:
            rows = rows.filter(Report.created_at >= date_from)
        if date_to:
            rows = rows.filter(Report.created_at <= date_to)

        rows = (
            rows.group_by(Entity.entity_id, Entity.canonical_name, Entity.category, Entity.status)
            .order_by(desc("cnt"))
            .limit(limit)
            .all()
        )

        for ent_id, name, cat, st, cnt in rows:
            items.append({
                "id": str(ent_id),
                "name": name,
                "category": cat or "UMUM",
                "count": cnt,
                "status": st,
            })

        # Fallback 1: IssueCluster from autonomous trending engine
        if not items:
            try:
                from app.models.intelligence import IssueCluster, IssueContent
                cluster_rows = (
                    db.query(
                        IssueCluster.cluster_id,
                        IssueCluster.canonical_name,
                        IssueCluster.dominant_category,
                        func.count(IssueContent.content_id).label("cnt"),
                    )
                    .join(IssueContent, IssueContent.cluster_id == IssueCluster.cluster_id)
                    .group_by(IssueCluster.cluster_id, IssueCluster.canonical_name, IssueCluster.dominant_category)
                    .order_by(desc("cnt"))
                    .limit(limit)
                    .all()
                )
                for c_id, c_name, c_cat, cnt in cluster_rows:
                    items.append({
                        "id": str(c_id),
                        "name": c_name,
                        "category": c_cat or "ISU",
                        "count": cnt,
                        "status": "CLUSTER",
                    })
            except Exception as e:
                logger.debug(f"IssueCluster fallback skipped: {e}")

        # Fallback 2: Raw / predicted topics from active reports
        if not items:
            eff_top = func.coalesce(Report.ai_topic_raw, Report.final_label, Report.ai_predicted_label)
            raw_rows = (
                db.query(eff_top, func.count(Report.report_id).label("cnt"))
                .filter(Report.status != "REJECTED")
                .filter(eff_top.isnot(None))
                .group_by(eff_top)
                .order_by(desc("cnt"))
                .limit(limit)
                .all()
            )
            for raw_name, cnt in raw_rows:
                if raw_name:
                    items.append({
                        "id": raw_name,
                        "name": raw_name,
                        "category": "ISU",
                        "count": cnt,
                        "status": "RAW",
                    })

    elif dimension == "actors":
        rows = (
            db.query(
                Entity.entity_id,
                Entity.canonical_name,
                Entity.category,
                Entity.status,
                func.count(ReportActor.report_id).label("cnt"),
            )
            .join(ReportActor, ReportActor.entity_id == Entity.entity_id)
            .join(Report, ReportActor.report_id == Report.report_id)
            .filter(Report.status != "REJECTED")
            .filter(Entity.entity_type == "ACTOR")
        )
        if date_from:
            rows = rows.filter(Report.created_at >= date_from)
        if date_to:
            rows = rows.filter(Report.created_at <= date_to)

        rows = (
            rows.group_by(Entity.entity_id, Entity.canonical_name, Entity.category, Entity.status)
            .order_by(desc("cnt"))
            .limit(limit)
            .all()
        )

        for ent_id, name, cat, st, cnt in rows:
            items.append({
                "id": str(ent_id),
                "name": name,
                "category": cat or "FIGUR_PUBLIK",
                "count": cnt,
                "status": st,
            })

        # Fallback if no canonical actors linked via ReportActor: use Account and creators
        if not items:
            try:
                act_rows = (
                    db.query(
                        func.coalesce(Account.display_name, Account.username, "Akun Patroli").label("act_name"),
                        Content.platform,
                        func.count(Report.report_id).label("cnt"),
                    )
                    .join(Content, Report.content_id == Content.content_id)
                    .join(Account, Content.account_id == Account.account_id, isouter=True)
                    .filter(Report.status != "REJECTED")
                    .group_by("act_name", Content.platform)
                    .order_by(desc("cnt"))
                    .limit(limit)
                    .all()
                )
                for act_name, plat, cnt in act_rows:
                    if act_name:
                        items.append({
                            "id": act_name,
                            "name": act_name,
                            "category": (plat.upper() if plat else "SUMBER"),
                            "count": cnt,
                            "status": "ACCOUNT",
                        })
            except Exception as e:
                logger.debug(f"Account fallback skipped: {e}")

    elif dimension == "sources":
        rows = (
            db.query(
                Entity.entity_id,
                Entity.canonical_name,
                Entity.category,
                Entity.status,
                func.count(Report.report_id).label("cnt"),
            )
            .join(Report, Report.source_id == Entity.entity_id)
            .filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
            .filter(Entity.entity_type == "SOURCE")
        )
        if date_from:
            rows = rows.filter(Report.created_at >= date_from)
        if date_to:
            rows = rows.filter(Report.created_at <= date_to)

        rows = (
            rows.group_by(Entity.entity_id, Entity.canonical_name, Entity.category, Entity.status)
            .order_by(desc("cnt"))
            .limit(limit)
            .all()
        )

        for ent_id, name, cat, st, cnt in rows:
            items.append({
                "id": str(ent_id),
                "name": name,
                "category": cat or "MEDIA_ONLINE",
                "count": cnt,
                "status": st,
            })

        if not items:
            raw_rows = (
                db.query(Report.ai_source_raw, Report.ai_source_type, func.count(Report.report_id).label("cnt"))
                .filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
                .filter(Report.ai_source_raw.isnot(None))
                .group_by(Report.ai_source_raw, Report.ai_source_type)
                .order_by(desc("cnt"))
                .limit(limit)
                .all()
            )
            for raw_name, stype, cnt in raw_rows:
                if raw_name:
                    items.append({
                        "id": raw_name,
                        "name": raw_name,
                        "category": stype or "MEDIA_ONLINE",
                        "count": cnt,
                        "status": "RAW",
                    })

    return {
        "dimension": dimension,
        "disclaimer": disclaimer,
        "items": items,
    }


@router.get("/reports")
def list_dashboard_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: DashboardUser = Depends(get_current_user),
):
    """Paginated report listings with role-based visibility filters."""
    query = (
        db.query(Report)
        .options(
            joinedload(Report.content).joinedload(Content.account),
            joinedload(Report.topic_entity),
            joinedload(Report.source_entity),
            joinedload(Report.target_actors).joinedload(ReportActor.actor),
        )
    )

    # Role-based filtering: USER only sees VALIDATED & MODIFIED
    if current_user.role != "ADMIN":
        query = query.filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
    else:
        if status_filter:
            query = query.filter(Report.status == status_filter)

    if category:
        query = query.filter(
            or_(
                Report.final_label.ilike(f"%{category}%"),
                Report.ai_predicted_label.ilike(f"%{category}%"),
            )
        )
    if risk:
        query = query.filter(
            or_(
                Report.final_risk.ilike(f"%{risk}%"),
                Report.ai_risk_level.ilike(f"%{risk}%"),
            )
        )
    if platform:
        query = query.join(Content, Report.content_id == Content.content_id).filter(
            Content.platform.ilike(platform)
        )

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Report.ticket_number.ilike(search_pattern),
                Report.ai_summary.ilike(search_pattern),
                Report.ai_topic_raw.ilike(search_pattern),
                Report.analyst_notes.ilike(search_pattern),
            )
        )

    total = query.count()
    offset = (page - 1) * limit
    reports = query.order_by(Report.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for r in reports:
        actors = [
            ra.actor.canonical_name
            for ra in (r.target_actors or [])
            if ra.actor
        ]
        if not actors and r.ai_actors_raw:
            actors = r.ai_actors_raw if isinstance(r.ai_actors_raw, list) else [str(r.ai_actors_raw)]

        items.append({
            "report_id": str(r.report_id),
            "ticket_number": r.ticket_number,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "validated_at": r.validated_at.isoformat() if r.validated_at else None,
            "platform": r.content.platform if r.content else "UNKNOWN",
            "url": r.content.canonical_url if r.content else "",
            "account": {
                "username": r.content.account.username if r.content and r.content.account else "",
                "display_name": r.content.account.display_name if r.content and r.content.account else "",
            },
            "ai_predicted_label": r.ai_predicted_label,
            "ai_risk_level": r.ai_risk_level,
            "final_label": r.final_label or r.ai_predicted_label,
            "final_risk": r.final_risk or r.ai_risk_level,
            "topic": r.topic_entity.canonical_name if r.topic_entity else (r.ai_topic_raw or "-"),
            "source": r.source_entity.canonical_name if r.source_entity else (r.ai_source_raw or "-"),
            "actors": actors,
            "analyst_notes": r.analyst_notes or "-",
            "summary": r.ai_summary or "",
        })

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": items,
    }


def _sanitize_csv_cell(value: Any) -> str:
    """Sanitize cell value against CSV formula injection and normalize formatting."""
    if value is None:
        return ""
    val_str = str(value).strip()
    if not val_str or val_str == "-" or val_str.lower() == "none" or val_str.lower() == "null":
        return ""
    # Strip line breaks for clean multi-column spreadsheet layout
    val_str = val_str.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    # Anti-CSV formula injection protection:
    # Only escape if starts with =, +, \t, or formula function (@SUM, @cmd, etc.)
    # Social media handles like @tvOneNews or @username are NOT escaped with single quote
    if val_str.startswith(("=", "+", "\t")):
        val_str = "'" + val_str
    elif val_str.startswith("@") and any(val_str.upper().startswith(f) for f in ("@SUM", "@CMD", "@CALL", "@EXEC")):
        val_str = "'" + val_str
    elif val_str.startswith("-") and len(val_str) > 1 and not val_str[1:].replace(".", "", 1).isdigit():
        val_str = "'" + val_str
    return val_str


@router.get("/export")
def export_dashboard_reports(
    format: str = Query("pdf", pattern="^(pdf|csv|json|xlsx)$"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    category: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: DashboardUser = Depends(get_current_user),
):
    """Export complete, forensic-grade patrol reports in PDF Dossier, CSV Metadata, or JSON format."""
    query = (
        db.query(Report)
        .options(
            joinedload(Report.content).joinedload(Content.account),
            joinedload(Report.topic_entity),
            joinedload(Report.source_entity),
            joinedload(Report.target_actors).joinedload(ReportActor.actor),
            joinedload(Report.evidences),
        )
    )

    if isinstance(date_from, datetime):
        query = query.filter(Report.created_at >= date_from)
    if isinstance(date_to, datetime):
        query = query.filter(Report.created_at <= date_to)

    if isinstance(category, str) and category != "Semua":
        query = query.filter(
            or_(
                Report.final_label.ilike(f"%{category}%"),
                Report.ai_predicted_label.ilike(f"%{category}%"),
            )
        )
    if isinstance(risk_level, str) and risk_level != "Semua":
        query = query.filter(
            or_(
                Report.final_risk.ilike(f"%{risk_level}%"),
                Report.ai_risk_level.ilike(f"%{risk_level}%"),
            )
        )
    if isinstance(platform, str) and platform != "Semua":
        query = query.join(Content, Report.content_id == Content.content_id).filter(
            Content.platform.ilike(f"%{platform}%")
        )

    if isinstance(status, str) and status != "Semua":
        query = query.filter(Report.status == status)
    elif getattr(current_user, "role", "") != "ADMIN":
        query = query.filter(Report.status.in_(["VALIDATED", "MODIFIED"]))

    reports = query.order_by(Report.created_at.desc()).all()

    # Batch query 5W+1H analyses
    content_ids = [r.content_id for r in reports if r.content_id]
    ca_map: Dict[Any, ContentAnalysis] = {}
    if content_ids:
        ca_rows = db.query(ContentAnalysis).filter(ContentAnalysis.content_id.in_(content_ids)).all()
        for ca in ca_rows:
            ca_map[ca.content_id] = ca

    if format == "json":
        data = []
        for r in reports:
            acct = r.content.account if r.content else None
            ca = ca_map.get(r.content_id)
            ev = r.evidences[0] if (r.evidences and len(r.evidences) > 0) else None

            actors = [ra.actor.canonical_name for ra in (r.target_actors or []) if ra.actor]
            if not actors and r.ai_actors_raw:
                actors = r.ai_actors_raw if isinstance(r.ai_actors_raw, list) else [str(r.ai_actors_raw)]

            alasan_penilaian = ""
            indikasi_pelanggaran = ""
            rekomendasi_tindak_lanjut = ""
            if r.ai_reasoning and isinstance(r.ai_reasoning, dict):
                alasan = r.ai_reasoning.get("alasan_penilaian", "")
                alasan_penilaian = "\n".join(alasan) if isinstance(alasan, list) else str(alasan or "")
                ind = r.ai_reasoning.get("indikasi_pelanggaran", "")
                indikasi_pelanggaran = ", ".join(ind) if isinstance(ind, list) else str(ind or "")
                rekom = r.ai_reasoning.get("rekomendasi_tindak_lanjut", "")
                rekomendasi_tindak_lanjut = str(rekom or "")

            data.append({
                "ticket_number": r.ticket_number,
                "status": r.status,
                "review_decision": r.review_decision or "-",
                "source_channel": r.source_channel or "BROWSER_EXTENSION",
                "intake_type": r.intake_type or "LINK",
                "reporter_identifier": r.reporter_identifier or "-",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "validated_at": r.validated_at.isoformat() if r.validated_at else None,
                "platform": r.content.platform.upper() if r.content else "UNKNOWN",
                "canonical_url": r.content.canonical_url if r.content else "-",
                "author": {
                    "username": acct.username if acct else "-",
                    "display_name": acct.display_name if acct else "-",
                    "profile_url": acct.profile_url if acct else "-",
                    "followers_count": acct.followers_count if acct else 0,
                    "is_verified": acct.is_verified if acct else False,
                },
                "content": {
                    "title": r.content.title if r.content else "-",
                    "caption": r.content.caption_text if r.content else "-",
                    "posted_at": r.content.posted_at.isoformat() if (r.content and r.content.posted_at) else None,
                    "views_count": r.content.views_count if r.content else 0,
                    "likes_count": r.content.likes_count if r.content else 0,
                    "comments_count": r.content.comments_count if r.content else 0,
                    "shares_count": r.content.shares_count if r.content else 0,
                },
                "classification": {
                    "final_label": r.final_label or r.ai_predicted_label or "-",
                    "final_risk": r.final_risk or r.ai_risk_level or "-",
                    "ai_predicted_label": r.ai_predicted_label or "-",
                    "ai_risk_level": r.ai_risk_level or "-",
                    "ai_confidence_score": float(r.ai_confidence_score) if r.ai_confidence_score is not None else None,
                    "topic": r.topic_entity.canonical_name if r.topic_entity else (r.ai_topic_raw or "-"),
                    "source": r.source_entity.canonical_name if r.source_entity else (r.ai_source_raw or "-"),
                    "source_type": r.ai_source_type or "-",
                    "target_actors": actors,
                },
                "intelligence_5w1h": {
                    "what": ca.what if ca else "-",
                    "who": ca.who if ca else "-",
                    "where": ca.where_info if ca else "-",
                    "when": ca.when_info if ca else "-",
                    "why": ca.why if ca else "-",
                    "how": ca.how if ca else "-",
                    "summary": r.ai_summary or (ca.summary if ca else "-"),
                    "sentiment": ca.sentiment if ca else "-",
                },
                "analysis_details": {
                    "alasan_penilaian": alasan_penilaian,
                    "indikasi_pelanggaran": indikasi_pelanggaran,
                    "rekomendasi_tindak_lanjut": rekomendasi_tindak_lanjut,
                    "analyst_notes": r.analyst_notes or "-",
                    "correction_notes": r.correction_notes or "-",
                },
                "forensic_evidence": {
                    "sha256": ev.sha256 if ev else "-",
                    "storage_path": ev.storage_path if ev else "-",
                },
            })
        return data

    headers = [
        "Nomor Tiket",
        "Status Laporan",
        "Keputusan Validasi",
        "Waktu Patroli (WIB)",
        "Waktu Validasi (WIB)",
        "Kanal Asupan",
        "Tipe Asupan",
        "Petugas Pelapor",
        "Platform",
        "URL Konten Bukti",
        "Username Pembuat (@)",
        "Nama Akun / Channel",
        "URL Profil",
        "Followers Akun",
        "Status Centang Biru",
        "Waktu Unggah Konten",
        "Views (Penayangan)",
        "Likes (Suka)",
        "Komentar",
        "Shares (Dibagikan)",
        "Judul Konten",
        "Caption / Teks Konten",
        "Ringkasan Narasi (Summary)",
        "Kategori Rekomendasi AI",
        "Tingkat Risiko Rekomendasi AI",
        "Skor Keyakinan AI",
        "Alasan Penilaian AI",
        "Indikasi Pelanggaran Hukum / Etika",
        "Rekomendasi Tindak Lanjut",
        "Kategori Final Terverifikasi",
        "Tingkat Risiko Final",
        "Topik Isu Strategis",
        "Aktor / Tokoh Target",
        "Nama Media / Sumber Asal",
        "Tipe Sumber Asal",
        "Catatan Analis / Justifikasi",
        "5W1H - What (Peristiwa)",
        "5W1H - Who (Pihak Terlibat)",
        "5W1H - Where (Lokasi)",
        "5W1H - When (Waktu Kejadian)",
        "5W1H - Why (Latar Belakang / Motif)",
        "5W1H - How (Modus / Bagaimana)",
        "Sentimen Konten",
        "Integritas Bukti SHA-256",
        "Berkas Bukti Digital",
    ]

    # Audit export event
    try:
        db.add(
            AuditLog(
                action="REPORT_EXPORTED",
                actor_telegram_id=0,
                actor_username=getattr(current_user, "username", "Unknown"),
                entity_type="Report",
                entity_id=f"count={len(reports)}",
                details={
                    "format": format,
                    "exported_count": len(reports),
                    "admin": getattr(current_user, "username", "Unknown"),
                },
            )
        )
        db.commit()
    except Exception as e:
        logger.warning("Failed to record export audit log: %s", e)

    if format == "pdf":
        from app.services.pdf_report_service import PDFReportService
        pdf_svc = PDFReportService()
        filter_meta = {
            "platform": platform if platform and platform != "Semua" else "Semua Platform",
            "category": category if category and category != "Semua" else "Semua Kategori",
            "risk_level": risk_level if risk_level and risk_level != "Semua" else "Semua Risiko",
        }
        pdf_bytes = pdf_svc.generate_patrol_dossier_pdf(
            reports=reports,
            content_analysis_map=ca_map,
            filter_meta=filter_meta,
        )
        filename = f"laporan_patroli_siber_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-store, no-cache, must-revalidate, private",
                "Pragma": "no-cache",
            },
        )

    if format == "xlsx":
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Rekap Patroli Siber"
        ws.views.sheetView[0].showGridLines = True

        navy_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
        right_align = Alignment(horizontal="right", vertical="center")
        mono_font = Font(name="Consolas", size=9)
        regular_font = Font(name="Segoe UI", size=9.5)

        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        thin_border_side = Side(style='thin', color='CBD5E1')
        thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

        ws.append(headers)
        ws.row_dimensions[1].height = 32

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = navy_fill
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border

        row_idx = 2
        for r in reports:
            acct = r.content.account if r.content else None
            ca = ca_map.get(r.content_id)
            ev = r.evidences[0] if (r.evidences and len(r.evidences) > 0) else None

            actors = [ra.actor.canonical_name for ra in (r.target_actors or []) if ra.actor]
            if not actors and r.ai_actors_raw:
                actors = r.ai_actors_raw if isinstance(r.ai_actors_raw, list) else [str(r.ai_actors_raw)]
            target_actors_str = ", ".join(actors) if actors else ""

            alasan_penilaian = ""
            indikasi_pelanggaran = ""
            rekomendasi_tindak_lanjut = ""
            if r.ai_reasoning and isinstance(r.ai_reasoning, dict):
                alasan = r.ai_reasoning.get("alasan_penilaian", "")
                alasan_penilaian = " | ".join(alasan) if isinstance(alasan, list) else str(alasan or "")
                ind = r.ai_reasoning.get("indikasi_pelanggaran", "")
                indikasi_pelanggaran = ", ".join(ind) if isinstance(ind, list) else str(ind or "")
                rekom = r.ai_reasoning.get("rekomendasi_tindak_lanjut", "")
                rekomendasi_tindak_lanjut = str(rekom or "")

            confidence_val = float(r.ai_confidence_score) if r.ai_confidence_score is not None else None
            evidence_file = os.path.basename(ev.storage_path) if (ev and ev.storage_path) else ""

            row_data = [
                r.ticket_number or "",
                r.status or "",
                r.review_decision or "",
                r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                r.validated_at.strftime("%Y-%m-%d %H:%M:%S") if r.validated_at else "",
                r.source_channel or "BROWSER_EXTENSION",
                r.intake_type or "LINK",
                r.reporter_identifier or "",
                r.content.platform.upper() if r.content else "UNKNOWN",
                r.content.canonical_url if r.content else "",
                f"@{acct.username}" if (acct and acct.username) else "",
                acct.display_name if acct else "",
                acct.profile_url if acct else "",
                int(acct.followers_count or 0) if acct else 0,
                "Ya" if (acct and acct.is_verified) else "Tidak",
                r.content.posted_at.strftime("%Y-%m-%d %H:%M:%S") if (r.content and r.content.posted_at) else "",
                int(r.content.views_count or 0) if r.content else 0,
                int(r.content.likes_count or 0) if r.content else 0,
                int(r.content.comments_count or 0) if r.content else 0,
                int(r.content.shares_count or 0) if r.content else 0,
                r.content.title if (r.content and r.content.title) else "",
                r.content.caption_text if (r.content and r.content.caption_text) else "",
                r.ai_summary or (ca.summary if ca else ""),
                r.ai_predicted_label or "",
                r.ai_risk_level or "",
                confidence_val,
                alasan_penilaian,
                indikasi_pelanggaran,
                rekomendasi_tindak_lanjut,
                r.final_label or r.ai_predicted_label or "",
                r.final_risk or r.ai_risk_level or "",
                r.topic_entity.canonical_name if r.topic_entity else (r.ai_topic_raw or ""),
                target_actors_str,
                r.source_entity.canonical_name if r.source_entity else (r.ai_source_raw or ""),
                r.ai_source_type or "",
                r.analyst_notes or "",
                ca.what if ca else "",
                ca.who if ca else "",
                ca.where_info if ca else "",
                ca.when_info if ca else "",
                ca.why if ca else "",
                ca.how if ca else "",
                ca.sentiment if ca else "",
                ev.sha256 if ev else "",
                evidence_file,
            ]
            ws.append(row_data)
            ws.row_dimensions[row_idx].height = 24

            is_odd = (row_idx % 2 == 1)
            for col_idx, val in enumerate(row_data, 1):
                c = ws.cell(row=row_idx, column=col_idx)
                c.font = regular_font
                c.border = thin_border
                if is_odd:
                    c.fill = zebra_fill

                if col_idx in (1, 2, 3, 4, 5, 6, 7, 9, 15, 16, 24, 25, 30, 31, 35, 43):
                    c.alignment = center_align
                elif col_idx in (14, 17, 18, 19, 20):
                    c.alignment = right_align
                    c.number_format = '#,##0'
                elif col_idx == 26:
                    c.alignment = center_align
                    c.number_format = '0.0%'
                elif col_idx in (10, 13, 44):
                    c.alignment = left_align
                    c.font = mono_font
                else:
                    c.alignment = left_align

            row_idx += 1

        for col_idx in range(1, len(headers) + 1):
            col_letter = get_column_letter(col_idx)
            header_name = headers[col_idx - 1]
            max_len = len(header_name)
            for row_num in range(2, row_idx):
                cell_val = str(ws.cell(row=row_num, column=col_idx).value or '')
                if len(cell_val) > max_len:
                    max_len = len(cell_val)

            if col_idx in (4, 5, 16):
                # Timestamp columns: Ensure ample width so YYYY-MM-DD HH:MM:SS NEVER triggers '####'
                width = max(max_len + 5, 26)
            elif col_idx in (14, 17, 18, 19, 20):
                # Numerical metrics (Followers, Views, Likes, Comments, Shares)
                width = max(max_len + 3, 16)
            elif col_idx in (1, 2, 3, 6, 7, 8, 9, 11, 15, 24, 25, 26, 30, 31, 35, 43):
                # Categorical & ID badges
                width = min(max(max_len + 3, 16), 28)
            elif col_idx in (21, 22, 23, 27, 28, 29, 36, 37, 38, 39, 40, 41, 42):
                # Comprehensive narrative & 5W+1H fields
                width = min(max(max_len + 4, 30), 65)
            elif col_idx in (10, 13, 44):
                # URLs, Profil, and SHA256 hashes
                width = min(max(max_len + 3, 25), 50)
            else:
                width = min(max(max_len + 3, 18), 35)

            ws.column_dimensions[col_letter].width = width

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        excel_stream = io.BytesIO()
        wb.save(excel_stream)
        excel_bytes = excel_stream.getvalue()
        filename = f"rekap_patroli_siber_pro_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # Clean Essential Metadata CSV Mode (UTF-8 BOM, Sanitized against formula injection)
    csv_headers = [
        "No",
        "Nomor Tiket",
        "Status Laporan",
        "Keputusan Analis",
        "Platform",
        "Akun Pengunggah (@)",
        "Nama Akun / Channel",
        "URL Profil",
        "Followers Akun",
        "Centang Biru",
        "URL Konten Bukti",
        "Waktu Unggah Konten",
        "Waktu Temuan Patroli (WIB)",
        "Judul Konten",
        "Kategori Konten",
        "Tingkat Risiko",
        "Skor Keyakinan AI",
        "Views (Tayangan)",
        "Likes (Suka)",
        "Komentar",
        "Shares (Dibagikan)",
        "Ringkasan Narasi (AI Summary)",
        "5W1H - What (Isu yang Dibahas)",
        "5W1H - Who (Pihak Terlibat)",
        "5W1H - When (Waktu Kejadian)",
        "5W1H - Where (Kanal / Lokasi)",
        "5W1H - Why (Penyebab / Pemicu Isu)",
        "5W1H - How (Kronologi & Alur Pembahasan)",
        "Alasan Penilaian AI",
        "Indikasi Pelanggaran Hukum / Etika",
        "Rekomendasi Tindak Lanjut",
        "Catatan Analis",
        "Integritas Bukti SHA-256",
        "Nama File Bukti",
    ]

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(csv_headers)

    for idx, r in enumerate(reports, start=1):
        acct = r.content.account if r.content else None
        ca = ca_map.get(r.content_id)
        ev = r.evidences[0] if (r.evidences and len(r.evidences) > 0) else None

        alasan_penilaian = ""
        indikasi_pelanggaran = ""
        rekomendasi_tindak_lanjut = ""
        if r.ai_reasoning and isinstance(r.ai_reasoning, dict):
            alasan = r.ai_reasoning.get("alasan_penilaian", "")
            alasan_penilaian = " | ".join(alasan) if isinstance(alasan, list) else str(alasan or "")
            ind = r.ai_reasoning.get("indikasi_pelanggaran", "")
            indikasi_pelanggaran = ", ".join(ind) if isinstance(ind, list) else str(ind or "")
            rekom = r.ai_reasoning.get("rekomendasi_tindak_lanjut", "")
            rekomendasi_tindak_lanjut = str(rekom or "")

        confidence_str = f"{float(r.ai_confidence_score)*100:.1f}%" if r.ai_confidence_score is not None else ""
        evidence_file = os.path.basename(ev.storage_path) if (ev and ev.storage_path) else ""

        writer.writerow([
            idx,
            _sanitize_csv_cell(r.ticket_number),
            _sanitize_csv_cell(r.status),
            _sanitize_csv_cell(r.review_decision or "-"),
            _sanitize_csv_cell(r.content.platform.upper() if r.content else "UNKNOWN"),
            _sanitize_csv_cell(f"@{acct.username}" if (acct and acct.username) else ""),
            _sanitize_csv_cell(acct.display_name if acct else ""),
            _sanitize_csv_cell(acct.profile_url if acct else ""),
            _sanitize_csv_cell(acct.followers_count if acct else 0),
            _sanitize_csv_cell("Ya" if (acct and acct.is_verified) else "Tidak"),
            _sanitize_csv_cell(r.content.canonical_url if r.content else ""),
            _sanitize_csv_cell(r.content.posted_at.strftime("%Y-%m-%d %H:%M:%S") if (r.content and r.content.posted_at) else (ca.when_info if ca else "")),
            _sanitize_csv_cell(r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""),
            _sanitize_csv_cell(r.content.title if (r.content and r.content.title) else ""),
            _sanitize_csv_cell(r.final_label or r.ai_predicted_label or ""),
            _sanitize_csv_cell(r.final_risk or r.ai_risk_level or ""),
            _sanitize_csv_cell(confidence_str),
            _sanitize_csv_cell(r.content.views_count if r.content else 0),
            _sanitize_csv_cell(r.content.likes_count if r.content else 0),
            _sanitize_csv_cell(r.content.comments_count if r.content else 0),
            _sanitize_csv_cell(r.content.shares_count if r.content else 0),
            _sanitize_csv_cell(r.ai_summary or (ca.summary if ca else "")),
            _sanitize_csv_cell(ca.what if ca else ""),
            _sanitize_csv_cell(ca.who if ca else ""),
            _sanitize_csv_cell(ca.when_info if ca else ""),
            _sanitize_csv_cell(ca.where_info if ca else ""),
            _sanitize_csv_cell(ca.why if ca else ""),
            _sanitize_csv_cell(ca.how if ca else ""),
            _sanitize_csv_cell(alasan_penilaian),
            _sanitize_csv_cell(indikasi_pelanggaran),
            _sanitize_csv_cell(rekomendasi_tindak_lanjut),
            _sanitize_csv_cell(r.analyst_notes or ""),
            _sanitize_csv_cell(ev.sha256 if ev else ""),
            _sanitize_csv_cell(evidence_file),
        ])

    csv_data = output.getvalue()
    filename = f"rekap_patroli_siber_metadata_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
        },
    )
