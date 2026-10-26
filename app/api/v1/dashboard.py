"""Web Dashboard Public API Endpoints (v1).

Role: USER and ADMIN.
Implements summary, timeseries, breakdown, top entities, reports explorer, and export.
Strictly surfaces VALIDATED and MODIFIED reports with final labels and neutral disclaimers.
"""

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_

from app.database import get_db
from app.models.report import Report, Content
from app.models.entities import Entity, ReportActor
from app.models.intelligence import DashboardUser
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

    # Query temuan tervalidasi dengan filter kategori & risiko tambahan
    val_q = base_all_q.filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
    if category:
        val_q = val_q.filter(Report.final_label.ilike(category))
    if risk_level:
        val_q = val_q.filter(Report.final_risk.ilike(risk_level))

    # Kategori
    kategori_rows = (
        val_q.with_entities(Report.final_label, func.count(Report.report_id))
        .group_by(Report.final_label)
        .all()
    )
    distribusi_kategori = {cat or "LAINNYA": count for cat, count in kategori_rows}

    # Risiko
    risiko_rows = (
        val_q.with_entities(Report.final_risk, func.count(Report.report_id))
        .group_by(Report.final_risk)
        .all()
    )
    distribusi_risiko = {rsk or "BELUM_DITENTUKAN": count for rsk, count in risiko_rows}

    # Platform
    platform_rows = (
        val_q.with_entities(Content.platform, func.count(Report.report_id))
        .group_by(Content.platform)
        .all()
    )
    distribusi_platform = {
        (plt.upper() if plt else "MANUAL"): count for plt, count in platform_rows
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
    interval: str = Query("day", regex="^(hour|day|week)$"),
    metric: str = Query("total", regex="^(total|by_category|by_risk)$"),
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
    dimension: str = Query("category", regex="^(category|risk|platform|source_type)$"),
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
    dimension: str = Query("topics", regex="^(topics|actors|sources)$"),
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
        # Group by topic entity if linked, otherwise raw topic
        rows = (
            db.query(
                Entity.entity_id,
                Entity.canonical_name,
                Entity.category,
                Entity.status,
                func.count(Report.report_id).label("cnt"),
            )
            .join(Report, Report.topic_id == Entity.entity_id)
            .filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
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

        # Fallback if no canonical topics linked yet
        if not items:
            raw_rows = (
                db.query(Report.ai_topic_raw, func.count(Report.report_id).label("cnt"))
                .filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
                .filter(Report.ai_topic_raw.isnot(None))
                .group_by(Report.ai_topic_raw)
                .order_by(desc("cnt"))
                .limit(limit)
                .all()
            )
            for raw_name, cnt in raw_rows:
                if raw_name:
                    items.append({
                        "id": raw_name,
                        "name": raw_name,
                        "category": "UMUM",
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
            .filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
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


@router.get("/export")
def export_dashboard_reports(
    format: str = Query("csv", regex="^(csv|json)$"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    category: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: DashboardUser = Depends(get_current_user),
):
    """Export validated patrol reports in CSV or JSON format."""
    query = (
        db.query(Report)
        .options(
            joinedload(Report.content),
            joinedload(Report.topic_entity),
            joinedload(Report.source_entity),
        )
        .filter(Report.status.in_(["VALIDATED", "MODIFIED"]))
    )

    if date_from:
        query = query.filter(Report.created_at >= date_from)
    if date_to:
        query = query.filter(Report.created_at <= date_to)
    if category:
        query = query.filter(Report.final_label.ilike(category))
    if risk_level:
        query = query.filter(Report.final_risk.ilike(risk_level))

    reports = query.order_by(Report.created_at.desc()).all()

    if format == "json":
        data = [
            {
                "ticket": r.ticket_number,
                "platform": r.content.platform if r.content else "",
                "url": r.content.canonical_url if r.content else "",
                "final_label": r.final_label,
                "final_risk": r.final_risk,
                "topic": r.topic_entity.canonical_name if r.topic_entity else r.ai_topic_raw,
                "source": r.source_entity.canonical_name if r.source_entity else r.ai_source_raw,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "validated_at": r.validated_at.isoformat() if r.validated_at else None,
                "analyst_notes": r.analyst_notes or "",
            }
            for r in reports
        ]
        return data

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Ticket Number",
        "Platform",
        "Kategori",
        "Tingkat Risiko",
        "Topik",
        "Sumber Konten",
        "Status",
        "Waktu Patroli",
        "Waktu Validasi",
        "Catatan Analis",
        "URL Bukti",
    ])

    for r in reports:
        writer.writerow([
            r.ticket_number,
            r.content.platform.upper() if r.content else "MANUAL",
            r.final_label or r.ai_predicted_label,
            r.final_risk or r.ai_risk_level,
            r.topic_entity.canonical_name if r.topic_entity else (r.ai_topic_raw or "-"),
            r.source_entity.canonical_name if r.source_entity else (r.ai_source_raw or "-"),
            r.status,
            r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "-",
            r.validated_at.strftime("%Y-%m-%d %H:%M:%S") if r.validated_at else "-",
            r.analyst_notes or "-",
            r.content.canonical_url if r.content else "-",
        ])

    csv_data = output.getvalue()
    filename = f"rekap_patroli_siber_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    # Audit export event
    try:
        db.add(
            AuditLog(
                action="REPORT_EXPORTED",
                actor_telegram_id=getattr(current_user, "telegram_id", None),
                actor_username=getattr(current_user, "username", "Unknown"),
                entity_type="Report",
                entity_id=f"count={len(reports)}",
                details={
                    "format": format,
                    "exported_count": len(reports),
                    "admin": current_user.username,
                },
            )
        )
        db.commit()
    except Exception as e:
        logger.warning("Failed to record export audit log: %s", e)

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
