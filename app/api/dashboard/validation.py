"""Human-in-the-Loop validation endpoints for Web Dashboard."""

from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.report import Report, Content
from app.models.audit import AuditLog
from app.models.intelligence import ContentAnalysis, IssueCluster, IssueContent
from app.auth.dependencies import get_current_user
from app.schemas.dashboard import ValidationRequest, ReclassifyRequest

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

    # If category or risk is overridden, classify as MODIFIED
    if payload.risk_level_override or payload.category_override:
        decision = "MODIFIED"

    # Constraint: If MODIFIED or REJECTED, notes are mandatory
    if decision in ["MODIFIED", "REJECTED"]:
        if not payload.notes or not payload.notes.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Catatan analis (analyst_notes) wajib diisi untuk putusan {decision}",
            )

    report.status = decision
    report.review_decision = "APPROVED" if decision == "VALIDATED" else ("MODIFIED" if decision == "MODIFIED" else "FALSE_POSITIVE")
    report.analyst_notes = payload.notes
    report.correction_notes = payload.notes

    if decision == "REJECTED":
        report.final_risk = None
        report.final_label = payload.category_override or "BUKAN_PELANGGARAN"
    else:
        report.final_risk = payload.risk_level_override or report.ai_risk_level or "RENDAH"
        report.final_label = payload.category_override or report.ai_predicted_label or "NETRAL"

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
    db.commit()

    # Ingest to RAG Knowledge Base (NFR-07 Versioning)
    try:
        from app.services.rag_service import RAGService
        rag_svc = RAGService()
        rag_svc.ingest_validated_decision(
            db=db,
            report=report,
            analyst_notes=payload.notes or "",
            decided_by=getattr(current_user, "telegram_id", None) or 0,
        )
    except Exception as rag_err:
        logger.warning("RAG ingestion failed on dashboard validation: %s", rag_err)

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
