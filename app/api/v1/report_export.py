"""Daily Patrol Intelligence Report Export API.

Provides executive daily reports in Markdown and PDF formats for command staff:
- Grouped by IPOLEKSOSBUDHANKAM classification
- 5W+1H structured intelligence synthesis
- NIST FIPS 198-1 Cryptographic Integrity Seals (HMAC-SHA256)
- Operator attribution and forensic audit trail
"""

import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.report import Report, Content
from app.models.evidence import Evidence
from app.models.intelligence import ContentAnalysis
from app.services.pdf_report_service import PDFReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Executive Report Export"])


@router.get("/daily-export")
def export_daily_patrol_report(
    date: Optional[str] = Query(None, description="Tanggal laporan dalam format YYYY-MM-DD. Default: hari ini."),
    format: str = Query("md", pattern="^(md|pdf)$", description="Format dokumen: 'md' (Markdown) atau 'pdf' (PDF Resmi)."),
    include_all: bool = Query(False, description="Jika true, sertakan temuan yang belum divalidasi."),
    db: Session = Depends(get_db),
):
    """Generate and download a comprehensive daily executive cyber patrol report."""
    target_date_str = date or datetime.utcnow().strftime("%Y-%m-%d")
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid. Gunakan format YYYY-MM-DD.")

    query = db.query(Report).filter(func.date(Report.created_at) == target_date)
    if not include_all:
        query = query.filter(Report.status.in_(["VALIDATED", "MODIFIED", "WAITING_VALIDATION"]))

    reports: List[Report] = query.order_by(Report.created_at.desc()).all()

    # Hitung ringkasan statistik IPOLEKSOSBUDHANKAM
    categories = ["Ideologi", "Politik", "Ekonomi", "Sosial", "Budaya", "Pertahanan", "Keamanan", "Non-Isu"]
    cat_counts = {cat: 0 for cat in categories}
    urgency_counts = {"TINGGI": 0, "SEDANG": 0, "RENDAH": 0}

    for r in reports:
        label = r.final_label or r.ai_predicted_label or "Sosial"
        matched_cat = next((c for c in categories if c.lower() == label.lower()), "Sosial")
        cat_counts[matched_cat] = cat_counts.get(matched_cat, 0) + 1

        risk = (r.final_risk or r.ai_risk_level or "RENDAH").upper()
        if risk in urgency_counts:
            urgency_counts[risk] += 1
        else:
            urgency_counts["RENDAH"] += 1

    total_findings = len(reports)

    # 1. GENERATE MARKDOWN
    if format == "md":
        md_lines = []
        md_lines.append(f"# LAPORAN EKSEKUTIF HARIAN PATROLI SIBER")
        md_lines.append(f"**Tanggal Pemantauan:** {target_date_str}  ")
        md_lines.append(f"**Klasifikasi Dokumen:** RAHASIA / DOKUMEN INTERNAL  ")
        md_lines.append(f"**Sistem Pengaman:** NIST FIPS 198-1 Cryptographic Integrity (HMAC-SHA256)  ")
        md_lines.append(f"**Waktu Pembuatan:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
        md_lines.append("\n---\n")

        md_lines.append("## 1. RINGKASAN EKSEKUTIF")
        md_lines.append(f"- **Total Temuan:** {total_findings} kasus terakuisisi.")
        md_lines.append(f"- **Distribusi Urgensi:** 🔴 Tinggi: {urgency_counts['TINGGI']} | 🟡 Sedang: {urgency_counts['SEDANG']} | 🟢 Rendah: {urgency_counts['RENDAH']}")
        md_lines.append("\n### Distribusi Klaster IPOLEKSOSBUDHANKAM:")
        md_lines.append("| Klaster Isu | Jumlah Temuan | Persentase |")
        md_lines.append("|:---|:---:|:---:|")
        for cat in categories:
            cnt = cat_counts.get(cat, 0)
            pct = f"{(cnt / total_findings * 100):.1f}%" if total_findings > 0 else "0.0%"
            md_lines.append(f"| **{cat}** | {cnt} | {pct} |")

        md_lines.append("\n---\n")
        md_lines.append("## 2. TABEL TEMUAN & BUKTI KRIPTOGRAFIS")

        if not reports:
            md_lines.append("*Tidak ada temuan patroli siber yang tercatat pada tanggal ini.*")
        else:
            md_lines.append("| No | Tiket | Platform | Operator | Kategori | Urgensi | Status Integritas | Ringkasan 5W+1H (What / Who) | URL Sumber |")
            md_lines.append("|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|:---|")
            for idx, r in enumerate(reports, 1):
                ev = r.evidences[0] if r.evidences else None
                status_integritas = ev.verification_status if ev else "UNSEALED"
                seal_badge = "🛡️ VERIFIED" if status_integritas == "VERIFIED" else "⚠️ UNVERIFIED"
                op_id = r.operator_id or r.reporter_identifier or "OP-01"
                cat_label = r.final_label or r.ai_predicted_label or "Sosial"
                risk_label = r.final_risk or r.ai_risk_level or "RENDAH"
                
                content = r.content
                title_clean = (content.title or content.caption_text or "Temuan patroli").replace("|", "/").strip()
                if len(title_clean) > 80:
                    title_clean = title_clean[:77] + "..."
                
                url_clean = (content.canonical_url or "-") if content else "-"
                md_lines.append(
                    f"| {idx} | `{r.ticket_number}` | {r.source_channel} | `{op_id}` | {cat_label} | {risk_label} | {seal_badge} | {title_clean} | [Tautan]({url_clean}) |"
                )

            md_lines.append("\n---\n")
            md_lines.append("## 3. DETAIL KASUS PRIORITAS TINGGI & RANTAI BUKTI (CHAIN OF CUSTODY)")
            high_priority = [r for r in reports if (r.final_risk or r.ai_risk_level or "").upper() == "TINGGI"]
            if not high_priority:
                high_priority = reports[:3]  # Tampilkan sampai 3 laporan pertama jika tidak ada yang tinggi

            for idx, r in enumerate(high_priority, 1):
                ev = r.evidences[0] if r.evidences else None
                content = r.content
                analysis = content.analysis if (content and hasattr(content, "analysis") and content.analysis) else None
                
                md_lines.append(f"### 3.{idx}. Kasus Tiket: `{r.ticket_number}`")
                md_lines.append(f"- **Platform:** {content.platform.upper() if content else 'WEB'} | **Operator ID:** `{r.operator_id or 'OP-01'}`")
                md_lines.append(f"- **Kategori:** `{r.final_label or r.ai_predicted_label}` | **Tingkat Risiko:** `{r.final_risk or r.ai_risk_level}`")
                md_lines.append(f"- **URL Target:** {content.canonical_url if content else '-'}")
                md_lines.append(f"- **Waktu Rekam (UTC):** `{ev.captured_at_utc if ev else '-'}`")
                md_lines.append(f"- **Hash Kanonik Bukti (SHA-256):** `{ev.canonical_hash if ev else '-'}`")
                md_lines.append(f"- **Segel Otentikasi HMAC-SHA256:** `{ev.hmac_tag if ev else '-'}`")
                md_lines.append(f"- **Status Verifikasi:** `{'VERIFIED (Valid NIST FIPS 198-1)' if (ev and ev.verification_status == 'VERIFIED') else 'TAMPERED / UNSEALED'}`")
                
                if getattr(r, "indonesian_content", None):
                    md_lines.append(f"\n**Narasi Temuan (Bahasa Indonesia):**\n> {r.indonesian_content[:500]}...")
                elif r.ai_summary:
                    md_lines.append(f"\n**Ringkasan Intelijen:**\n> {r.ai_summary}")

                if ev and ev.dom_text and getattr(r, "original_language", "id") != "id":
                    md_lines.append(f"\n**Bukti Teks Mentah Asli (Tersegel HMAC-SHA256):**\n```text\n{ev.dom_text[:300]}...\n```")

                md_lines.append("\n**Sintesis Intelijen 5W+1H:**")
                if analysis:
                    md_lines.append(f"- **What (Apa):** {analysis.what}")
                    md_lines.append(f"- **Who (Siapa):** {analysis.who}")
                    md_lines.append(f"- **When (Kapan):** {analysis.when_info}")
                    md_lines.append(f"- **Where (Di Mana):** {analysis.where_info}")
                    md_lines.append(f"- **Why (Mengapa):** {analysis.why}")
                    md_lines.append(f"- **How (Kronologi):** {analysis.how}")
                else:
                    md_lines.append(f"- **Ringkasan:** {r.ai_summary or 'Ringkasan belum diekstraksi.'}")

                md_lines.append("\n")

        md_content = "\n".join(md_lines)
        filename = f"Laporan_Harian_Patroli_{target_date_str}.md"
        return Response(
            content=md_content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # 2. GENERATE PDF RESMI
    elif format == "pdf":
        pdf_service = PDFReportService()
        title = f"LAPORAN HARIAN PATROLI SIBER — {target_date_str}"
        subtitle = f"Direktorat Operasi Siber • Sintesis Intelijen IPOLEKSOSBUDHANKAM & Segel Integritas Kriptografis"
        pdf_bytes = pdf_service.build_pdf_report(reports, title=title, subtitle=subtitle)
        filename = f"Laporan_Harian_Patroli_{target_date_str}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

