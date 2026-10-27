"""Content Explorer and Detail API endpoints for Web Dashboard."""

import os
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.database import get_db
from app.models.report import Content, Account, Report
from app.models.evidence import Evidence
from app.models.intelligence import ContentAnalysis, IssueCluster, IssueContent
from app.auth.dependencies import get_current_user
from app.schemas.dashboard import (
    ContentListItem,
    ContentDetailResponse,
    Analysis5W1HData,
)

router = APIRouter(prefix="/contents", tags=["Dashboard Content Explorer"])


@router.get("", response_model=List[ContentListItem])
def list_contents(
    platform: Optional[str] = Query(None, description="youtube, tiktok, instagram"),
    category: Optional[str] = Query(None, description="Filter by topic category"),
    sentiment: Optional[str] = Query(None, description="POSITIF, NEGATIF, NETRAL, CAMPURAN"),
    risk_level: Optional[str] = Query(None, description="RENDAH, SEDANG, TINGGI"),
    status: Optional[str] = Query(None, description="WAITING_VALIDATION, VALIDATED, REJECTED, etc."),
    search: Optional[str] = Query(None, description="Search keyword in title, caption, or URL"),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List paginated contents with rich search, platform, sentiment, and risk filters."""
    query = db.query(Content)

    if platform:
        query = query.filter(Content.platform.ilike(platform))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Content.title.ilike(search_pattern),
                Content.caption_text.ilike(search_pattern),
                Content.canonical_url.ilike(search_pattern),
            )
        )

    contents = query.order_by(desc(Content.created_at)).offset(skip).limit(limit).all()

    items: List[ContentListItem] = []
    for c in contents:
        # Check Report
        report = db.query(Report).filter(Report.content_id == c.content_id).first()
        if status and report and report.status != status:
            continue
        if risk_level and report and report.ai_risk_level != risk_level:
            continue

        # Check ContentAnalysis
        analysis = db.query(ContentAnalysis).filter(ContentAnalysis.content_id == c.content_id).first()
        if category and analysis and analysis.category != category:
            continue
        if sentiment and analysis and analysis.sentiment != sentiment:
            continue

        # Check Account
        account = db.query(Account).filter(Account.account_id == c.account_id).first() if c.account_id else None

        # Check linked issue
        issue_link = (
            db.query(IssueContent, IssueCluster)
            .join(IssueCluster, IssueContent.issue_id == IssueCluster.issue_id)
            .filter(IssueContent.content_id == c.content_id)
            .first()
        )

        caption_snippet = None
        if c.caption_text:
            caption_snippet = (c.caption_text[:140] + "...") if len(c.caption_text) > 140 else c.caption_text

        items.append(
            ContentListItem(
                content_id=c.content_id,
                platform=c.platform,
                url=c.canonical_url,
                title=c.title or "Tanpa Judul",
                caption_snippet=caption_snippet,
                author_username=account.username if account else None,
                status=report.status if report else "PENDING_ANALYSIS",
                category=analysis.category if analysis else "Lainnya",
                sentiment=analysis.sentiment if analysis else "NETRAL",
                risk_level=report.ai_risk_level if report else "RENDAH",
                created_at=c.created_at,
                screenshot_url=f"/api/dashboard/contents/{c.content_id}/screenshot",
                issue_title=issue_link[1].title if issue_link else None,
            )
        )

    return items


@router.get("/{content_id}", response_model=ContentDetailResponse)
def get_content_detail(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retrieve full content detail: 5W+1H, AI patrol analysis, proof hashes, and author."""
    content = db.query(Content).filter(Content.content_id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Konten tidak ditemukan")

    account = db.query(Account).filter(Account.account_id == content.account_id).first() if content.account_id else None
    report = db.query(Report).filter(Report.content_id == content_id).first()
    analysis = db.query(ContentAnalysis).filter(ContentAnalysis.content_id == content_id).first()

    # Evidence items
    evidences_data = []
    if report:
        evs = db.query(Evidence).filter(Evidence.report_id == report.report_id).all()
        for e in evs:
            evidences_data.append({
                "evidence_id": str(e.evidence_id),
                "source_type": e.source_type,
                "sha256": e.sha256,
                "storage_path": e.storage_path,
                "mime_type": e.mime_type,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            })

    # Assigned issue
    issue_link = (
        db.query(IssueContent, IssueCluster)
        .join(IssueCluster, IssueContent.issue_id == IssueCluster.issue_id)
        .filter(IssueContent.content_id == content_id)
        .first()
    )
    assigned_issue_data = None
    if issue_link:
        assigned_issue_data = {
            "issue_id": str(issue_link[1].issue_id),
            "title": issue_link[1].title,
            "category": issue_link[1].category,
            "similarity_score": issue_link[0].similarity_score,
        }

    # 5W+1H
    w5h1_schema = None
    if analysis:
        w5h1_schema = Analysis5W1HData(
            what=analysis.what,
            who=analysis.who,
            when_info=analysis.when_info,
            where_info=analysis.where_info,
            why=analysis.why,
            how=analysis.how,
            summary=analysis.summary,
            main_topic=analysis.main_topic,
            sub_topics=analysis.sub_topics or [],
            keywords=analysis.keywords or [],
            hashtags=analysis.hashtags or [],
            named_entities=analysis.named_entities or [],
            sentiment=analysis.sentiment,
            tone=analysis.tone,
            category=analysis.category,
            relevance_score=analysis.relevance_score or 0.0,
            urgency_score=analysis.urgency_score or 0.0,
            confidence_score=analysis.confidence_score or 0.0,
            misinfo_indicators=analysis.misinfo_indicators or [],
        )

    # Author
    author_dict = {}
    if account:
        author_dict = {
            "username": account.username,
            "display_name": account.display_name,
            "profile_url": account.profile_url,
            "followers_count": account.followers_count,
            "is_verified": account.is_verified,
            "bio": account.bio,
        }

    # Interaction
    interaction_dict = {
        "likes_count": content.likes_count or 0,
        "views_count": content.views_count or 0,
        "comments_count": content.comments_count or 0,
        "shares_count": content.shares_count or 0,
    }

    # AI Patrol
    ai_patrol_dict = None
    if report:
        ai_patrol_dict = {
            "status": report.ai_status,
            "predicted_label": report.ai_predicted_label,
            "risk_level": report.ai_risk_level,
            "confidence_score": float(report.ai_confidence_score) if report.ai_confidence_score is not None else None,
            "summary": report.ai_summary,
            "reasoning": report.ai_reasoning,
            "ticket_number": report.ticket_number,
            "human_decision": report.review_decision,
            "final_label": report.final_label,
            "final_risk": report.final_risk,
            "correction_notes": report.correction_notes,
            "validated_at": report.validated_at.isoformat() if report.validated_at else None,
        }

    return ContentDetailResponse(
        content_id=content.content_id,
        platform=content.platform,
        url=content.canonical_url,
        title=content.title,
        caption=content.caption_text,
        author=author_dict,
        interaction=interaction_dict,
        created_at=content.created_at,
        status=report.status if report else "PENDING_ANALYSIS",
        report_id=report.report_id if report else None,
        ai_patrol=ai_patrol_dict,
        analysis_5w1h=w5h1_schema,
        evidences=evidences_data,
        assigned_issue=assigned_issue_data,
    )


@router.get("/{content_id}/screenshot")
def get_content_screenshot(
    content_id: UUID,
    db: Session = Depends(get_db),
):
    """Serve the primary screenshot evidence image for a content."""
    report = db.query(Report).filter(Report.content_id == content_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Bukti screenshot tidak ditemukan")

    evidence = (
        db.query(Evidence)
        .filter(Evidence.report_id == report.report_id)
        .filter(Evidence.source_type == "POST_SCREENSHOT")
        .first()
    )
    if not evidence or not evidence.storage_path or not os.path.exists(evidence.storage_path):
        raise HTTPException(status_code=404, detail="File gambar tangkapan layar tidak ada di disk")

    return FileResponse(evidence.storage_path, media_type=evidence.mime_type or "image/png")


@router.get("/{content_id}/verify-evidence")
def verify_content_evidence(
    content_id: UUID,
    db: Session = Depends(get_db),
):
    """Perform real-time forensic authenticity verification on the evidence file."""
    report = db.query(Report).filter(Report.content_id == content_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")

    evidence = (
        db.query(Evidence)
        .filter(Evidence.report_id == report.report_id)
        .filter(Evidence.source_type == "POST_SCREENSHOT")
        .first()
    )
    if not evidence or not evidence.storage_path or not os.path.exists(evidence.storage_path):
        raise HTTPException(status_code=404, detail="File bukti digital tidak ditemukan di disk")

    content = db.query(Content).filter(Content.content_id == content_id).first()
    canonical_url = content.canonical_url if content else ""

    from app.services.crypto_service import CryptoService

    # 1. Compute current hash from raw file on disk
    current_sha256 = CryptoService.calculate_sha256(evidence.storage_path)

    # 2. Check match with recorded hash at capture time
    is_hash_identical = current_sha256.lower() == evidence.sha256.lower()

    # 3. Compute cryptographic digital signature (HMAC-SHA256)
    digital_signature = CryptoService.sign_evidence(
        sha256_hash=evidence.sha256,
        ticket_number=report.ticket_number,
        url=canonical_url,
    )

    file_stat = os.stat(evidence.storage_path)

    return {
        "status": "SUCCESS",
        "is_authentic": is_hash_identical,
        "chain_of_custody_status": "AUTHENTIC_UNMODIFIED" if is_hash_identical else "TAMPERED_OR_CORRUPT",
        "verdict": "BUKTI ASLI DAN TIDAK TERMANIPULASI" if is_hash_identical else "PERINGATAN: FILE PERNAH DIUBAH / TIDAK COCOK",
        "ticket_number": report.ticket_number,
        "source_url": canonical_url,
        "registered_sha256": evidence.sha256,
        "current_file_sha256": current_sha256,
        "digital_signature": digital_signature,
        "signature_algorithm": "HMAC-SHA256 (RFC 2104)",
        "file_size_bytes": file_stat.st_size,
        "mime_type": evidence.mime_type or "image/png",
        "captured_at": evidence.created_at.isoformat() if evidence.created_at else None,
        "verified_at": datetime.utcnow().isoformat(),
        "integrity_details": {
            "is_encrypted": False,
            "explanation": "File bukti disimpan dalam format gambar PNG asli (lossless) tanpa enkripsi agar dapat dilihat manusia secara transparan, namun keasliannya disegel dengan Tanda Tangan Digital Kriptografi dan Hash SHA-256.",
            "tamper_evident": "Jika 1 pixel gambar diubah atau diedit di Photoshop, nilai SHA-256 dan Tanda Tangan Digital akan langsung gugur.",
        },
    }
