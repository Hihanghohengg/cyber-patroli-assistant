import logging
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.report import Report, Content
from app.models.memory import ValidatedMemory
from app.models.audit import AuditLog
from app.models.intelligence import ContentAnalysis, IssueCluster, IssueContent
from app.auth.dependencies import get_current_user
from app.schemas.dashboard import ValidationRequest, ReclassifyRequest
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contents", tags=["Dashboard Human-in-the-Loop Validation"])


@router.post("/{content_id}/validate")
def validate_content_finding(
    content_id: UUID,
    payload: ValidationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Validate, modify, or reject AI patrol triage results via dashboard interface."""
    report = db.query(Report).filter(Report.content_id == content_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Laporan patroli belum ditemukan")

    now = datetime.utcnow()
    decision = payload.status.upper()
    if decision not in ["VALIDATED", "MODIFIED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Status harus VALIDATED, MODIFIED, atau REJECTED")

    # Logika Penentuan Keputusan HITL:
    # 1. VALIDATED (Setuju / Acc): Menyetujui hasil AI. Catatan analis TIDAK WAJIB.
    # 2. MODIFIED (Ubah): Mengoreksi kategori / tingkat risiko. Catatan/alasan analis WAJIB.
    # 3. REJECTED (Tolak): Menolak temuan patroli / bukan pelanggaran. Catatan/alasan analis WAJIB.
    if decision == "VALIDATED":
        # Jangan paksa ke MODIFIED jika status eksplisit VALIDATED (Setuju)
        pass
    elif decision == "REJECTED":
        pass
    else:
        decision = "MODIFIED"

    # Constraint: Jika MODIFIED atau REJECTED, catatan/alasan analis wajib diisi
    if decision in ["MODIFIED", "REJECTED"]:
        if not payload.notes or not payload.notes.strip():
            aksi_label = "UBAH (MODIFIED)" if decision == "MODIFIED" else "TOLAK (REJECTED)"
            raise HTTPException(
                status_code=400,
                detail=f"Catatan/alasan analis wajib diisi untuk keputusan {aksi_label}.",
            )

    report.status = decision
    report.review_decision = "APPROVED" if decision == "VALIDATED" else ("MODIFIED" if decision == "MODIFIED" else "FALSE_POSITIVE")
    report.analyst_notes = payload.notes.strip() if payload.notes else None
    report.correction_notes = payload.notes.strip() if payload.notes else None

    if decision == "REJECTED":
        report.final_risk = None
        report.final_label = payload.category_override or "BUKAN_PELANGGARAN"
    elif decision == "MODIFIED":
        report.final_risk = payload.risk_level_override or report.ai_risk_level or "RENDAH"
        report.final_label = payload.category_override or report.ai_predicted_label or "NETRAL"
    else:  # VALIDATED (Acc)
        report.final_risk = report.ai_risk_level or "RENDAH"
        report.final_label = report.ai_predicted_label or "NETRAL"

    report.validated_at = now
    if current_user.telegram_id:
        report.reviewer_telegram_id = current_user.telegram_id

    # If category override, also update ContentAnalysis
    if payload.category_override:
        analysis = db.query(ContentAnalysis).filter(ContentAnalysis.content_id == content_id).first()
        if analysis:
            analysis.category = payload.category_override

    # Create immutable audit log
    client_ip = request.client.host if request.client else "unknown"
    audit = AuditLog(
        action=f"DASHBOARD_VALIDATION_{decision}",
        actor_telegram_id=current_user.telegram_id,
        actor_username=current_user.username,
        entity_type="Report",
        entity_id=str(report.report_id),
        details={
            "analyst_username": current_user.username,
            "decision": decision,
            "notes": payload.notes,
            "risk_override": payload.risk_level_override,
            "category_override": payload.category_override,
        },
        ip_address=client_ip,
        timestamp=now,
    )
    db.add(audit)

    # Gated MemPrompt Memory Entry (Anti Memory-Poisoning)
    if decision in ["VALIDATED", "MODIFIED"]:
        try:
            content = db.query(Content).filter(Content.content_id == content_id).first()
            if content:
                content_text = f"{content.title or ''} {content.caption_text or ''}".strip()
                risk_map = {"TINGGI": 5, "SEDANG": 3, "RENDAH": 1}
                urgency = risk_map.get(str(report.final_risk).upper(), 3)
                MemoryService.add_validated_case(
                    db=db,
                    content_id=content_id,
                    report_id=report.report_id,
                    content_text=content_text,
                    validated_category=report.final_label or "Sosial",
                    analyst_rationale=payload.notes or "Divalidasi analis patroli siber.",
                    validated_by=current_user.username or "analyst",
                    urgency_score=urgency
                )
                logger.info(f"MemPrompt Memory Entry added for content {content_id} [{report.final_label}]")
        except Exception as mem_err:
            logger.warning(f"Failed to add case to ValidatedMemory: {mem_err}")
    elif decision == "REJECTED":
        # Safeguard: Hapus preseden dari ValidatedMemory jika konten ini ditolak sebagai bukan pelanggaran
        try:
            db.query(ValidatedMemory).filter(ValidatedMemory.report_id == report.report_id).delete()
            logger.info(f"MemPrompt Memory Entry removed for rejected report {report.report_id}")
        except Exception as mem_del_err:
            logger.warning(f"Failed to remove rejected case from ValidatedMemory: {mem_del_err}")

    db.commit()

    # Rekam umpan balik analis ke HITL Active Learning Harness
    logger.info(
        "HITL active learning feedback terekam untuk tiket %s: putusan=%s, final_label=%s, final_risk=%s",
        report.ticket_number,
        decision,
        report.final_label,
        report.final_risk,
    )

    return {
        "status": "success",
        "message": f"Konten berhasil divalidasi dengan status {decision}",
        "report_id": str(report.report_id),
        "validated_at": now.isoformat(),
    }


@router.post("/{content_id}/reclassify")
def reclassify_content_topic(
    content_id: UUID,
    payload: ReclassifyRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Reassign content to a different issue cluster or update its category."""
    content = db.query(Content).filter(Content.content_id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Konten tidak ditemukan")

    analysis = db.query(ContentAnalysis).filter(ContentAnalysis.content_id == content_id).first()
    if payload.category and analysis:
        analysis.category = payload.category

    # Reassign issue if specified
    if payload.issue_id:
        target_issue = db.query(IssueCluster).filter(IssueCluster.issue_id == payload.issue_id).first()
        if not target_issue:
            raise HTTPException(status_code=404, detail="Topik tujuan tidak ditemukan")

        # Delete old junction
        db.query(IssueContent).filter(IssueContent.content_id == content_id).delete()

        # Add new junction
        new_link = IssueContent(
            issue_id=target_issue.issue_id,
            content_id=content_id,
            similarity_score=1.0,
            created_at=datetime.utcnow(),
        )
        db.add(new_link)

    db.commit()
    return {"status": "success", "message": "Klasifikasi konten berhasil diperbarui"}
