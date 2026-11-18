"""Daily Patrol Intelligence Report Export API.

Provides executive daily reports in Markdown and PDF formats for command staff:
- Grouped by IPOLEKSOSBUDHANKAM classification
- 5W+1H structured intelligence synthesis
- NIST FIPS 198-1 Cryptographic Integrity Seals (HMAC-SHA256)
- Operator attribution and forensic audit trail
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

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
    """Generate and download a comprehensive daily executive intelligence report."""
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


@router.get("/analytical-pdf")
def export_analytical_patrol_report(
    period: str = Query("daily", pattern="^(daily|weekly|custom)$", description="Periode: daily, weekly, custom"),
    date: Optional[str] = Query(None, description="Tanggal spesifik YYYY-MM-DD untuk periode daily"),
    start_date: Optional[str] = Query(None, description="Tanggal awal YYYY-MM-DD untuk periode custom"),
    end_date: Optional[str] = Query(None, description="Tanggal akhir YYYY-MM-DD untuk periode custom"),
    category: Optional[str] = Query(None, description="Filter kategori: Politik, Keamanan, dll atau Semua Kategori"),
    db: Session = Depends(get_db),
):
    """Generate and download grounded, multi-chart analytical PDF report with visual statistics and AI insights."""
    from datetime import timedelta
    from app.models.intelligence import IssueCluster

    today = datetime.utcnow().date()
    period_label = "Periode Harian"

    query = db.query(Report)

    if period == "daily":
        target_date = today
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Format tanggal tidak valid. Gunakan YYYY-MM-DD.")
        query = query.filter(func.date(Report.created_at) == target_date)
        period_label = f"Harian ({target_date.strftime('%d %B %Y')})"
    elif period == "weekly":
        start_dt = today - timedelta(days=7)
        query = query.filter(func.date(Report.created_at) >= start_dt, func.date(Report.created_at) <= today)
        period_label = f"Mingguan ({start_dt.strftime('%d %b')} – {today.strftime('%d %b %Y')})"
    elif period == "custom":
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="Parameter start_date dan end_date wajib diisi untuk periode kustom.")
        try:
            s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Format tanggal kustom tidak valid. Gunakan YYYY-MM-DD.")
        if s_date > e_date:
            s_date, e_date = e_date, s_date
        query = query.filter(func.date(Report.created_at) >= s_date, func.date(Report.created_at) <= e_date)
        period_label = f"Kustom ({s_date.strftime('%d %b %Y')} – {e_date.strftime('%d %b %Y')})"

    eff_cat = category if category and category.lower() not in ("semua", "semua kategori", "all") else None
    if eff_cat:
        query = query.filter(
            func.lower(func.coalesce(Report.final_label, Report.ai_predicted_label, "")) == eff_cat.lower()
        )

    # Order by urgency desc, then created_at desc
    reports: List[Report] = query.order_by(Report.created_at.desc()).all()

    # Map content_id -> ContentAnalysis
    content_ids = [r.content_id for r in reports if r.content_id]
    ca_map: Dict[Any, ContentAnalysis] = {}
    if content_ids:
        ca_rows = db.query(ContentAnalysis).filter(ContentAnalysis.content_id.in_(content_ids)).all()
        for ca in ca_rows:
            ca_map[ca.content_id] = ca

    # Fetch top active issues for contextual narrative
    top_issues_raw = (
        db.query(IssueCluster)
        .filter(IssueCluster.status == "ACTIVE", IssueCluster.category != "Non-Isu")
        .order_by(IssueCluster.last_seen_at.desc())
        .limit(6)
        .all()
    )
    actual_topics = [{"title": iss.title, "keywords": iss.keywords} for iss in top_issues_raw[:3]]
    thematic_topics = [{"title": iss.title, "keywords": iss.keywords} for iss in top_issues_raw[3:]]

    filter_meta = {
        "period_label": period_label,
        "category": eff_cat or "Semua Kategori",
    }

    pdf_service = PDFReportService()
    pdf_bytes = pdf_service.generate_analytical_report_pdf(
        reports=reports,
        content_analysis_map=ca_map,
        filter_meta=filter_meta,
        actual_topics=actual_topics,
        thematic_topics=thematic_topics,
    )

    clean_period_name = period
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"Laporan_Analisis_Siber_{clean_period_name}_{timestamp_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ==========================================
# ALUR DALKONTEN & EKSPOR LAPORAN MINGGUAN LHM
# ==========================================

class DalkontenStatusRequest(BaseModel):
    status: str = Field(..., description="BELUM DITERUSKAN, SIAP DITERUSKAN KE DALKONTEN, atau SUDAH DITERUSKAN")
    operator_id: Optional[str] = Field(None, description="Pengenal operator yang meneruskan")


@router.post("/{report_id}/dalkonten-status")
def update_report_dalkonten_status(
    report_id: str,
    payload: DalkontenStatusRequest,
    db: Session = Depends(get_db),
):
    """Perbarui status penerusan berkas ke Tim Dalkonten (Pengendalian Konten)."""
    valid_statuses = {"BELUM DITERUSKAN", "SIAP DITERUSKAN KE DALKONTEN", "SUDAH DITERUSKAN"}
    target_status = payload.status.strip().upper()
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status tidak valid. Pilihan yang diizinkan: {', '.join(sorted(valid_statuses))}",
        )

    report = None
    try:
        val_uuid = UUID(report_id)
        report = db.query(Report).filter(or_(Report.report_id == val_uuid, Report.content_id == val_uuid)).first()
    except Exception:
        pass
    if not report:
        report = db.query(Report).filter(Report.ticket_number == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Berkas laporan tidak ditemukan.")

    report.dalkonten_status = target_status
    if target_status in ("SIAP DITERUSKAN KE DALKONTEN", "SUDAH DITERUSKAN"):
        report.dalkonten_forwarded_at = datetime.utcnow()
        report.dalkonten_forwarded_by = payload.operator_id or report.operator_id or "op_analis_01"
    else:
        report.dalkonten_forwarded_at = None
        report.dalkonten_forwarded_by = None

    db.commit()
    db.refresh(report)

    return {
        "ok": True,
        "report_id": str(report.report_id),
        "ticket_number": report.ticket_number,
        "dalkonten_status": report.dalkonten_status,
        "dalkonten_forwarded_at": report.dalkonten_forwarded_at.isoformat() if report.dalkonten_forwarded_at else None,
        "dalkonten_forwarded_by": report.dalkonten_forwarded_by,
    }


@router.get("/weekly-lhm-export")
def export_weekly_lhm_report(
    start_date: Optional[str] = Query(None, description="Tanggal awal YYYY-MM-DD. Default: 7 hari lalu."),
    end_date: Optional[str] = Query(None, description="Tanggal akhir YYYY-MM-DD. Default: hari ini."),
    format: str = Query("md", pattern="^(md|pdf)$", description="Format laporan: 'md' atau 'pdf'"),
    include_all: bool = Query(False, description="Sertakan semua status temuan (termasuk belum divalidasi)"),
    db: Session = Depends(get_db),
):
    """Generate dan unduh rekapitulasi mingguan 6 topik operasional LHM (Lembaga Hukum & Masyarakat)."""
    today = datetime.utcnow().date()
    try:
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else today
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else (e_date - timedelta(days=7))
    except ValueError:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid. Gunakan format YYYY-MM-DD.")

    if s_date > e_date:
        s_date, e_date = e_date, s_date

    query = db.query(Report).filter(
        func.date(Report.created_at) >= s_date,
        func.date(Report.created_at) <= e_date,
    )
    if not include_all:
        query = query.filter(Report.status.in_(["VALIDATED", "MODIFIED", "WAITING_VALIDATION"]))

    reports: List[Report] = query.order_by(Report.created_at.desc()).all()

    # 6 Topik Prioritas Operasional LHM (+ 1 Kelas Fallback Umum)
    lhm_topics = [
        "Pornografi",
        "COP",
        "Violent Extremism",
        "Migrant and Human Trafficking",
        "Judi Online",
        "Narkotika",
        "Umum / Di Luar Topik",
    ]

    grouped_reports: Dict[str, List[Report]] = {topic: [] for topic in lhm_topics}
    for r in reports:
        cat_raw = r.final_label or r.ai_predicted_label or r.ai_topic_raw or "Umum / Di Luar Topik"
        # Match case-insensitively to lhm_topics
        matched = "Umum / Di Luar Topik"
        cat_lower = cat_raw.lower()
        if "porn" in cat_lower or "asusila" in cat_lower:
            matched = "Pornografi"
        elif "cop" in cat_lower or "anak" in cat_lower or "pedofil" in cat_lower or "csam" in cat_lower:
            matched = "COP"
        elif "extremism" in cat_lower or "teror" in cat_lower or "radikal" in cat_lower:
            matched = "Violent Extremism"
        elif "trafficking" in cat_lower or "tppo" in cat_lower or "migran" in cat_lower or "kamboja" in cat_lower:
            matched = "Migrant and Human Trafficking"
        elif "judi" in cat_lower or "slot" in cat_lower or "judol" in cat_lower:
            matched = "Judi Online"
        elif "narko" in cat_lower or "sabu" in cat_lower or "ganja" in cat_lower or "tramadol" in cat_lower:
            matched = "Narkotika"
        grouped_reports[matched].append(r)

    total_findings = len(reports)

    # 1. GENERATE MARKDOWN DOSSIER
    if format == "md":
        md = []
        md.append("# LAPORAN MINGGUAN OPERASIONAL LHM // PATROLI SIBER")
        md.append(f"**Rentang Periode:** {s_date.strftime('%d %B %Y')} s/d {e_date.strftime('%d %B %Y')}  ")
        md.append("**Unit Kerja:** Satuan Tugas Intelijen & Triase Pemantauan Siber (TILIK)  ")
        md.append("**Standar Integritas Bukti:** NIST FIPS 198-1 Cryptographic HMAC-SHA256  ")
        md.append(f"**Waktu Diterbitkan:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
        md.append("\n---\n")

        md.append("## 1. MATRIKS DISTRIBUSI TEMUAN 6 TOPIK LHM")
        md.append("| No | Topik Operasional LHM | Definisi Lingkup | Jumlah Temuan | Persentase |")
        md.append("|:---:|:---|:---|:---:|:---:|")
        definitions = {
            "Pornografi": "Materi asusila eksplisit & konten syur digital komersial",
            "COP": "Child Online Protection (Eksploitasi & kekerasan seksual anak daring)",
            "Violent Extremism": "Ekstremisme kekerasan, terorisme & radikalisme bersenjata",
            "Migrant and Human Trafficking": "TPPO, penipuan lowongan scamming luar negeri & perdagangan orang",
            "Judi Online": "Perjudian daring, situs slot gacor, & agen kasino online",
            "Narkotika": "Peredaran narkoba, obat keras ilegal & kurir digital",
            "Umum / Di Luar Topik": "Isu politik wajar, ekonomi, sosial & konten umum",
        }
        for i, top in enumerate(lhm_topics, 1):
            cnt = len(grouped_reports[top])
            pct = f"{(cnt / total_findings * 100):.1f}%" if total_findings > 0 else "0.0%"
            md.append(f"| {i} | **{top}** | {definitions.get(top, '-')} | {cnt} | {pct} |")

        md.append("\n---\n")
        md.append("## 2. TABEL BERKAS TEMUAN OPERASIONAL PER TOPIK")

        for top in lhm_topics:
            items = grouped_reports[top]
            md.append(f"\n### ### {top} ({len(items)} Temuan)")
            if not items:
                md.append("*Nihil temuan aktif pada periode pemantauan ini.*")
                continue

            md.append("| No | Tanggal | Platform | Akun & Tautan | Urgensi | Status Dalkonten | Status Integritas | Deskripsi Singkat Penjelasan Konten |")
            md.append("|:---:|:---:|:---:|:---|:---:|:---:|:---:|:---|")
            for idx, r in enumerate(items, 1):
                ev = r.evidences[0] if r.evidences else None
                c = r.content
                tgl = r.created_at.strftime("%d/%m/%Y") if r.created_at else "-"
                plt = (c.platform.upper() if c else "WEB")
                url = (c.canonical_url if c else "-")
                user = (c.account.username if (c and c.account) else (r.reporter_identifier or "Anonim"))
                risk = (r.final_risk or r.ai_risk_level or "RENDAH")
                dalkonten = r.dalkonten_status or "BELUM DITERUSKAN"
                seal = "🛡️ NIST OK" if (ev and ev.verification_status == "VERIFIED") else "⚠️ UNVERIFIED"
                desc = (r.ai_summary or (c.caption_text[:120] if c and c.caption_text else "Temuan patroli")).replace("|", "/").strip()
                if len(desc) > 120:
                    desc = desc[:117] + "..."
                md.append(f"| {idx} | {tgl} | {plt} | [@{user}]({url}) | {risk} | `{dalkonten}` | {seal} | {desc} |")

        md_content = "\n".join(md)
        filename = f"Laporan_Mingguan_LHM_{s_date}_{e_date}.md"
        return Response(
            content=md_content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # 2. GENERATE PDF RESMI
    elif format == "pdf":
        pdf_service = PDFReportService()
        title = f"LAPORAN MINGGUAN OPERASIONAL LHM ({s_date.strftime('%d %b')} – {e_date.strftime('%d %b %Y')})"
        subtitle = "Penyelarasan 6 Topik Prioritas Penanganan Konten Ilegal & Rantai Bukti Forensik NIST FIPS 198-1"
        pdf_bytes = pdf_service.build_pdf_report(reports, title=title, subtitle=subtitle)
        filename = f"Laporan_Mingguan_LHM_{s_date}_{e_date}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )


@router.get("/dalkonten-package-export")
def export_dalkonten_package(
    format: str = Query("md", pattern="^(md|pdf)$", description="Format dokumen: 'md' atau 'pdf'"),
    status: Optional[str] = Query(None, description="Status Dalkonten spesifik. Default: SIAP DITERUSKAN & SUDAH DITERUSKAN"),
    db: Session = Depends(get_db),
):
    """Ekspor paket dossier serah terima berkas ke Tim Pengendalian Konten (Dalkonten) untuk takedown."""
    query = db.query(Report)
    if status:
        query = query.filter(Report.dalkonten_status == status.strip().upper())
    else:
        query = query.filter(
            Report.dalkonten_status.in_(["SIAP DITERUSKAN KE DALKONTEN", "SUDAH DITERUSKAN"])
        )

    reports: List[Report] = query.order_by(Report.created_at.desc()).all()

    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. MARKDOWN DOSSIER PAKET DALKONTEN
    if format == "md":
        md = []
        md.append("# PAKET DOSSIER SERAH TERIMA BERKAS PENANGANAN KONTEN // TIM DALKONTEN")
        md.append(f"**Tanggal Pengajuan:** {datetime.utcnow().strftime('%d %B %Y, %H:%M UTC')}  ")
        md.append(f"**Total Sasaran Penanganan:** {len(reports)} Berkas Konten Terverifikasi  ")
        md.append("**Standar Forensik:** Segel Kriptografis NIST FIPS 198-1 HMAC-SHA256  ")
        md.append("\n---\n")

        if not reports:
            md.append("*Tidak ada berkas bertanda 'SIAP DITERUSKAN KE DALKONTEN' saat ini.*")
        else:
            md.append("## TABEL INVENTARIS PENGAJUAN PEMBLOKIRAN / TAKEDOWN")
            md.append("| No | Nomor Tiket | Platform | Akun Target | URL Target (Takedown) | Urgensi | Status Dalkonten | Waktu Diajukan | Hash SHA-256 Bukti |")
            md.append("|:---:|:---|:---:|:---|:---|:---:|:---:|:---:|:---|")
            for idx, r in enumerate(reports, 1):
                ev = r.evidences[0] if r.evidences else None
                c = r.content
                plt = c.platform.upper() if c else "WEB"
                url = c.canonical_url if c else "-"
                user = c.account.username if (c and c.account) else "Anonim"
                risk = r.final_risk or r.ai_risk_level or "TINGGI"
                d_stat = r.dalkonten_status or "SIAP DITERUSKAN KE DALKONTEN"
                fwd_at = r.dalkonten_forwarded_at.strftime("%Y-%m-%d %H:%M") if r.dalkonten_forwarded_at else "-"
                hsh = (ev.canonical_hash[:16] + "...") if (ev and ev.canonical_hash) else "-"
                md.append(f"| {idx} | `{r.ticket_number}` | {plt} | @{user} | [Tautan Takedown]({url}) | {risk} | `{d_stat}` | {fwd_at} | `{hsh}` |")

            md.append("\n---\n")
            md.append("## DETAIL REKOMENDASI TINDAK LANJUT OPERASIONAL")
            for idx, r in enumerate(reports, 1):
                ev = r.evidences[0] if r.evidences else None
                c = r.content
                cat = r.final_label or r.ai_predicted_label or r.ai_topic_raw or "Umum"
                md.append(f"### {idx}. Berkas: `{r.ticket_number}` ({c.platform.upper() if c else 'WEB'})")
                md.append(f"- **Kategori / Topik LHM:** `{cat}`")
                md.append(f"- **Tingkat Urgensi:** `{r.final_risk or r.ai_risk_level or 'TINGGI'}`")
                md.append(f"- **URL Sasaran:** {c.canonical_url if c else '-'}")
                md.append(f"- **Pengaju / Operator:** `{r.dalkonten_forwarded_by or r.operator_id or 'op_analis_01'}`")
                md.append(f"- **Ringkasan Konten:**\n> {r.ai_summary or (c.caption_text if c else '-')}")
                if ev:
                    md.append(f"- **Integritas Bukti:** NIST FIPS 198-1 `{ev.verification_status}` (HMAC: `{ev.hmac_tag}`)")
                md.append("\n")

        md_content = "\n".join(md)
        filename = f"Paket_Dossier_Dalkonten_{today_str}.md"
        return Response(
            content=md_content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # 2. PDF RESMI PAKET DALKONTEN
    elif format == "pdf":
        pdf_service = PDFReportService()
        title = f"PAKET SERAH TERIMA BERKAS PENANGANAN KONTEN // TIM DALKONTEN — {today_str}"
        subtitle = "Dossier Penanganan Pemblokiran Konten Ilegal & Pengamanan Rantai Bukti Forensik NIST FIPS 198-1"
        pdf_bytes = pdf_service.build_pdf_report(reports, title=title, subtitle=subtitle)
        filename = f"Paket_Dossier_Dalkonten_{today_str}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

