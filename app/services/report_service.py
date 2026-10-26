import os
import logging
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

logger = logging.getLogger(__name__)


def _set_cell_background(cell, hex_color: str):
    """Set background color for a table cell."""
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))


def _set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner padding for a table cell in dxa units."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


class ReportService:
    """Generates official daily cyber patrol recap documents in DOCX format.

    Designed for hand-off to leadership (Pimpinan), with executive summary,
    embedded high-res visual evidence snapshots, forensic SHA-256 integrity,
    risk breakdowns, and sign-off endorsement blocks.
    """

    def __init__(self, output_dir: str = "storage/reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_daily_docx(
        self,
        reports: list,
        shift_date: str,
        officer_name: str = "Regu Piket Khusus Siber",
        supervisor_name: str = "Perwira Pengawas / Pimpinan Piket",
    ) -> str:
        """Build an executive Word document summarising a day's patrol findings.

        Args:
            reports: List of Report ORM objects with eagerly loaded relationships.
            shift_date: Date string like '2026-10-22'.
            officer_name: Name of patrol analyst on duty.
            supervisor_name: Name of approving supervisor / officer.

        Returns:
            File path to the generated .docx file.
        """
        doc = Document()

        # Filter only final validated reports (VALIDATED and MODIFIED) according to Proposal FR-07 & ADR-08
        reports = [r for r in reports if getattr(r, "status", None) in ("VALIDATED", "MODIFIED")]

        # Set page orientation & margins (A4 portrait, 0.7 inch margins)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.7)
            section.bottom_margin = Inches(0.7)
            section.left_margin = Inches(0.7)
            section.right_margin = Inches(0.7)

        # ─────────────────────────────────────────────────────────
        # 1. OFFICIAL HEADER / KOP LAPORAN
        # ─────────────────────────────────────────────────────────
        header_p1 = doc.add_paragraph()
        header_p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = header_p1.add_run("KEMENTERIAN KOMUNIKASI DAN DIGITAL REPUBLIK INDONESIA\n")
        r1.font.bold = True
        r1.font.size = Pt(12)
        r1.font.name = "Arial"

        r2 = header_p1.add_run("DIREKTORAT JENDERAL PENGENDALIAN INFORMASI SIBER\n")
        r2.font.bold = True
        r2.font.size = Pt(11)
        r2.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)

        r3 = header_p1.add_run("LAPORAN OPERASIONAL HARIAN PATROLI SIBER & DETEKSI DISINFORMASI\n")
        r3.font.bold = True
        r3.font.size = Pt(13)

        # Mandatory Simulation Disclaimer (Proposal FR-07 & ADR-08)
        disclaimer_p = doc.add_paragraph()
        disclaimer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        disc_run = disclaimer_p.add_run(
            "DOKUMEN SIMULASI PROTOTIPE — Rekapitulasi berbasis keputusan analis, bukan penetapan hukum otomatis"
        )
        disc_run.font.italic = True
        disc_run.font.bold = True
        disc_run.font.size = Pt(10)
        disc_run.font.color.rgb = RGBColor(0xBA, 0x1A, 0x1A)

        div_p = doc.add_paragraph("═" * 60)
        div_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        div_p.paragraph_format.space_after = Pt(8)

        # ─────────────────────────────────────────────────────────
        # 2. METADATA PIKET & EXECUTIVE SUMMARY
        # ─────────────────────────────────────────────────────────
        meta_table = doc.add_table(rows=2, cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_table.autofit = True

        row0 = meta_table.rows[0].cells
        row0[0].paragraphs[0].add_run(f"📅 Tanggal Piket: {shift_date}").bold = True
        row0[1].paragraphs[0].add_run(f"👮 Petugas Piket: {officer_name}").bold = True

        total_findings = len(reports)
        high_risk = sum(1 for r in reports if (r.final_risk or r.ai_risk_level or "").upper() == "TINGGI")
        med_risk = sum(1 for r in reports if (r.final_risk or r.ai_risk_level or "").upper() == "SEDANG")
        low_risk = sum(1 for r in reports if (r.final_risk or r.ai_risk_level or "").upper() == "RENDAH")

        row1 = meta_table.rows[1].cells
        row1[0].paragraphs[0].add_run(f"📊 Total Temuan: {total_findings} Konten").bold = True
        stat_p = row1[1].paragraphs[0]
        stat_p.add_run("Distribusi Risiko: ").bold = True
        r_hi = stat_p.add_run(f"🔴 Tinggi: {high_risk}  ")
        r_hi.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
        r_hi.bold = True
        r_med = stat_p.add_run(f"🟡 Sedang: {med_risk}  ")
        r_med.font.color.rgb = RGBColor(0xCC, 0x88, 0x00)
        r_med.bold = True
        r_lo = stat_p.add_run(f"🟢 Rendah: {low_risk}")
        r_lo.font.color.rgb = RGBColor(0x00, 0x88, 0x00)
        r_lo.bold = True

        doc.add_paragraph("").paragraph_format.space_after = Pt(4)

        # ─────────────────────────────────────────────────────────
        # 3. TABEL KRONOLOGIS TEMUAN (6 KOLOM)
        # ─────────────────────────────────────────────────────────
        doc.add_heading("TABEL KRONOLOGIS TEMUAN & BUKTI FORENSIK DIGITAL", level=2)

        table = doc.add_table(rows=1, cols=6)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        headers = [
            "No & ID Laporan",
            "Waktu & Akun Sumber",
            "Cuplikan Bukti Visual & SHA-256",
            "Kategori & Tingkat Risiko",
            "Hasil Pengamatan & Ringkasan Narasi",
            "Status & Tindak Lanjut",
        ]

        col_widths = [Inches(1.0), Inches(1.3), Inches(2.0), Inches(1.2), Inches(2.1), Inches(1.1)]

        hdr_row = table.rows[0]
        for idx, text in enumerate(headers):
            cell = hdr_row.cells[idx]
            cell.width = col_widths[idx]
            _set_cell_background(cell, "1F497D")  # Dark blue header
            _set_cell_margins(cell, top=120, bottom=120, left=100, right=100)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(text)
            run.font.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        if not reports:
            empty_row = table.add_row().cells
            empty_row[0].merge(empty_row[5])
            p_empty = empty_row[0].paragraphs[0]
            p_empty.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_empty.add_run("Nihil temuan pelanggaran siber pada periode shift ini.").italic = True
        else:
            for i, rep in enumerate(reports, 1):
                row_cells = table.add_row().cells
                for idx, w in enumerate(col_widths):
                    row_cells[idx].width = w
                    _set_cell_margins(row_cells[idx], top=80, bottom=80, left=80, right=80)
                    row_cells[idx].vertical_alignment = WD_ALIGN_VERTICAL.TOP

                # Alternating row background
                if i % 2 == 0:
                    for cell in row_cells:
                        _set_cell_background(cell, "F2F5F9")

                # Kolom 1: No & ID Laporan
                p1 = row_cells[0].paragraphs[0]
                p1.add_run(f"#{i}\n").bold = True
                p1.add_run(rep.ticket_number).font.size = Pt(8.5)

                # Kolom 2: Waktu Penemuan & Akun Sumber (Tautan & Nama Channel)
                p2 = row_cells[1].paragraphs[0]
                time_str = rep.created_at.strftime("%H:%M:%S WIB") if rep.created_at else "-"
                p2.add_run(f"🕒 {time_str}\n").font.size = Pt(8)

                acct_name = "N/A"
                acct_handle = "N/A"
                content_url = ""
                platform = "Siber"
                if rep.content:
                    platform = rep.content.platform.upper()
                    content_url = rep.content.canonical_url
                    if rep.content.account:
                        acct_name = rep.content.account.display_name or "N/A"
                        acct_handle = rep.content.account.username or "N/A"

                p2.add_run(f"🌐 {platform}\n").bold = True
                p2.add_run(f"👤 {acct_name}\n({acct_handle})\n").font.size = Pt(8.5)
                if content_url:
                    r_link = p2.add_run(f"🔗 [Tautan Konten]\n({content_url[:35]}…)")
                    r_link.font.size = Pt(7.5)
                    r_link.font.color.rgb = RGBColor(0x00, 0x33, 0x99)

                # Kolom 3: Cuplikan Bukti Visual (Gambar tersemat) & Hash SHA-256
                p3 = row_cells[2].paragraphs[0]
                img_embedded = False
                sha_hash = "N/A"

                for ev in rep.evidences:
                    if ev.source_type == "POST_SCREENSHOT" or not img_embedded:
                        sha_hash = ev.sha256 or "N/A"
                        if ev.storage_path and os.path.exists(ev.storage_path):
                            try:
                                # Embed screenshot image with standard width
                                p3.add_run().add_picture(ev.storage_path, width=Inches(1.8))
                                img_embedded = True
                                break
                            except Exception as img_err:
                                logger.warning("Could not embed image %s: %s", ev.storage_path, img_err)

                if not img_embedded:
                    p3.add_run("[Bukti Visual Tersimpan di Arsip]").font.size = Pt(8)

                p_sha = row_cells[2].add_paragraph()
                p_sha.paragraph_format.space_before = Pt(4)
                p_sha.add_run("🔐 SHA-256:\n").bold = True
                p_sha.add_run(f"{sha_hash[:24]}…").font.size = Pt(7.5)

                # Kolom 4: Kategori & Tingkat Risiko (Hasil akhir tervalidasi analis)
                p4 = row_cells[3].paragraphs[0]
                label = rep.final_label or rep.ai_predicted_label or "NETRAL"
                risk = (rep.final_risk or rep.ai_risk_level or "RENDAH").upper()
                p4.add_run(f"🏷️ {label}\n").bold = True

                risk_run = p4.add_run(f"⚠️ Risiko: {risk}\n")
                risk_run.bold = True
                if risk == "TINGGI":
                    risk_run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
                elif risk == "SEDANG":
                    risk_run.font.color.rgb = RGBColor(0xCC, 0x88, 0x00)
                else:
                    risk_run.font.color.rgb = RGBColor(0x00, 0x88, 0x00)

                if rep.ai_confidence_score:
                    p4.add_run(f"Keyakinan: {int(rep.ai_confidence_score * 100)}%").font.size = Pt(8)

                # Kolom 5: Hasil Pengamatan & Ringkasan Narasi
                p5 = row_cells[4].paragraphs[0]
                video_title = rep.content.title if (rep.content and rep.content.title) else ""
                if video_title:
                    p5.add_run(f"📌 Judul: {video_title}\n\n").bold = True

                summary_text = rep.ai_summary or "-"
                p5.add_run(f"📝 Esensi Narasi: {summary_text}\n\n").font.size = Pt(8.5)

                # Indikasi / alasan
                if rep.ai_reasoning:
                    reasoning_str = str(rep.ai_reasoning)
                    p5.add_run(f"🔍 Indikator: {reasoning_str[:120]}…").font.size = Pt(8)

                # Kolom 6: Status & Catatan Tindak Lanjut
                p6 = row_cells[5].paragraphs[0]
                status_text = rep.status
                if status_text == "VALIDATED":
                    p6.add_run("✅ VALIDATED\n(Disetujui)\n").bold = True
                elif status_text == "MODIFIED":
                    p6.add_run("✏ MODIFIED\n(Disesuaikan)\n").bold = True
                elif status_text == "REJECTED":
                    p6.add_run("✕ BUKAN\nPELANGGARAN\n").bold = True
                else:
                    p6.add_run("⏳ PENDING\n").bold = True

                decision_notes = rep.correction_notes or "Rekomendasi tindak lanjut: klarifikasi dan pengawasan berkala."
                p6.add_run(f"📌 {decision_notes}").font.size = Pt(7.5)

                # Normalize font sizes for all paragraphs in the row
                for cell in row_cells:
                    for p in cell.paragraphs:
                        for r in p.runs:
                            if not r.font.size:
                                r.font.size = Pt(8.5)

        # ─────────────────────────────────────────────────────────
        # 4. HALAMAN PENGESAHAN / SIGN-OFF BLOCK
        # ─────────────────────────────────────────────────────────
        doc.add_paragraph("").paragraph_format.space_before = Pt(16)
        doc.add_paragraph("IV. PENGESAHAN LAPORAN OPERASIONAL").runs[0].bold = True

        sig_table = doc.add_table(rows=4, cols=2)
        sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        sig_table.autofit = True

        r_sig0 = sig_table.rows[0].cells
        r_sig0[0].paragraphs[0].add_run("Pemeriksa / Analis Piket:").bold = True
        r_sig0[1].paragraphs[0].add_run(f"Jakarta, {shift_date}\nMengetahui / Memvalidasi:").bold = True

        r_sig1 = sig_table.rows[1].cells
        r_sig1[0].paragraphs[0].add_run(f"\n\n\n___________________________\n{officer_name}\nNIP/NRP. 199203142018011002")
        r_sig1[1].paragraphs[0].add_run(f"\n\n\n___________________________\n{supervisor_name}\nNIP/NRP. 198506222009121001")

        footer_note = doc.add_paragraph()
        footer_note.paragraph_format.space_before = Pt(14)
        fn_run = footer_note.add_run(
            "Catatan: Seluruh data, cuplikan visual, dan kode hash SHA-256 dalam dokumen ini "
            "dihasilkan oleh Sistem Asisten Patroli Siber dan memiliki keabsahan forensik digital "
            "sebagai bukti penegakan hukum atau penindakan administrasi siber."
        )
        fn_run.font.size = Pt(8)
        fn_run.italic = True
        footer_note.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Save document
        filename = f"Laporan_Patroli_Siber_{shift_date.replace('-', '')}.docx"
        filepath = os.path.join(self.output_dir, filename)
        doc.save(filepath)
        logger.info("Daily patrol DOCX report generated successfully at: %s", filepath)
        return filepath
