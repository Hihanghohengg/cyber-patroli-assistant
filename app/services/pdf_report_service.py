"""Layanan Ekspor Laporan PDF Resmi Intelijen & Temuan Patroli Siber.

Menghasilkan dokumen PDF siap pakai untuk pimpinan/penyidik yang memuat:
- Penomoran dan daftar terstruktur kasus temuan
- Foto snapshot bukti visual (screenshot) dengan auto-scaling proporsional
- Tautan / URL konten yang dapat diklik
- Ringkasan narasi konten (AI Multimodal + transkrip)
- Kategori, tingkat risiko, dan metrik interaksi
- Timeline / kronologi pembahasan lengkap (Struktur Intelijen 5W+1H)
- Integritas rantai bukti digital (SHA-256 hash)
"""

import io
import os
import logging
from datetime import datetime
from typing import List, Optional, Any, Dict

from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# Warna Standar Dinas & Intelijen Siber
COLOR_PRIMARY_DARK = colors.HexColor("#0F172A")    # Slate 900
COLOR_PRIMARY_BLUE = colors.HexColor("#1D4ED8")    # Blue 700
COLOR_TEXT_MAIN    = colors.HexColor("#1E293B")    # Slate 800
COLOR_TEXT_MUTED   = colors.HexColor("#64748B")    # Slate 500
COLOR_BG_LIGHT     = colors.HexColor("#F8FAFC")    # Slate 50
COLOR_BG_CARD      = colors.HexColor("#FFFFFF")    # White
COLOR_BORDER       = colors.HexColor("#CBD5E1")    # Slate 300
COLOR_BORDER_LIGHT = colors.HexColor("#E2E8F0")    # Slate 200

# Palet Status & Risiko
COLOR_RISK_HIGH    = colors.HexColor("#DC2626")    # Red 600
COLOR_RISK_MED     = colors.HexColor("#D97706")    # Amber 600
COLOR_RISK_LOW     = colors.HexColor("#059669")    # Emerald 600
COLOR_RISK_NEUTRAL = colors.HexColor("#475569")    # Slate 600


class NumberedCanvas(canvas.Canvas):
    """Canvas yang menghitung total halaman secara dinamis dan menggambar running header/footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header Running Banner
        self.drawString(36, 810, "DIREKTORAT OPERASI SIBER • SISTEM ASISTEN PATROLI SIBER")
        self.drawRightString(559, 810, "KLASIFIKASI: DOKUMEN INTERNAL / RESMI")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(36, 804, 559, 804)

        # Footer Running Banner
        self.line(36, 36, 559, 36)
        self.setFont("Helvetica", 7.5)
        self.drawString(36, 25, "Bukti digital terenkripsi dengan algoritma kriptografis SHA-256 sesuai standar forensik UU ITE.")
        page_str = f"Halaman {self._pageNumber} dari {page_count}"
        self.drawRightString(559, 25, page_str)
        self.restoreState()


class PDFReportService:
    """Service pembuat dokumen PDF resmi untuk resume patroli siber."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        """Siapkan gaya tipografi agar rapi, proporsional, dan nyaman dibaca."""
        self.style_title = ParagraphStyle(
            "DocTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=COLOR_PRIMARY_DARK,
            alignment=0,
        )
        self.style_subtitle = ParagraphStyle(
            "DocSubtitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=COLOR_TEXT_MUTED,
            alignment=0,
        )
        self.style_case_number = ParagraphStyle(
            "CaseNumber",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=COLOR_PRIMARY_DARK,
        )
        self.style_url = ParagraphStyle(
            "CaseURL",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=COLOR_PRIMARY_BLUE,
        )
        self.style_meta_label = ParagraphStyle(
            "MetaLabel",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_MUTED,
        )
        self.style_meta_val = ParagraphStyle(
            "MetaValue",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=COLOR_TEXT_MAIN,
        )
        self.style_summary_box = ParagraphStyle(
            "SummaryBox",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12.5,
            textColor=COLOR_TEXT_MAIN,
        )
        self.style_timeline_item = ParagraphStyle(
            "TimelineItem",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11.5,
            textColor=COLOR_TEXT_MAIN,
        )
        self.style_caption = ParagraphStyle(
            "ImageCaption",
            parent=self.styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7,
            leading=9,
            textColor=COLOR_TEXT_MUTED,
            alignment=1,
        )

    def _prepare_image(self, image_path: Optional[str], max_width: float = 460.0, max_height: float = 210.0) -> Optional[Image]:
        """Validasi, kompresi, dan sesuaikan skala foto snapshot agar pas dengan margin halaman dan hemat memori."""
        if not image_path or not os.path.exists(image_path):
            return None

        # Jangan muat gambar kosong / corrupt (< 200 bytes)
        try:
            if os.path.getsize(image_path) < 200:
                return None
            with PILImage.open(image_path) as pil_img:
                orig_w, orig_h = pil_img.size
                if orig_w <= 0 or orig_h <= 0:
                    return None
                scale = min(max_width / float(orig_w), max_height / float(orig_h), 1.0)
                final_w = orig_w * scale
                final_h = orig_h * scale

                # Optimasi ukuran biner agar PDF ringan dan cepat dibuka
                if pil_img.mode in ("RGBA", "P"):
                    pil_img = pil_img.convert("RGB")
                pil_img.thumbnail((int(max_width * 2), int(max_height * 2)), PILImage.Resampling.LANCZOS)
                img_buf = io.BytesIO()
                pil_img.save(img_buf, format="JPEG", quality=85, optimize=True)
                img_buf.seek(0)

            return Image(img_buf, width=final_w, height=final_h)
        except Exception as ex:
            logger.warning("Gagal memuat visual evidence %s untuk PDF: %s", image_path, ex)
            return None

    def generate_patrol_dossier_pdf(
        self,
        reports: List[Any],
        content_analysis_map: Dict[Any, Any],
        filter_meta: Optional[Dict[str, str]] = None,
    ) -> bytes:
        """Membuat file biner PDF lengkap untuk daftar laporan temuan patroli siber."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=46,
        )

        flowables = []

        # ── KOP / HEADER LAPORAN RESMI ──
        print_date = datetime.now().strftime("%d %B %Y, %H:%M WIB")
        filter_info = filter_meta or {}
        kategori_filter = filter_info.get("category", "Semua Kategori")
        platform_filter = filter_info.get("platform", "Semua Platform")

        kop_data = [
            [
                Paragraph("<b>RESUME EKSEKUTIF TEMUAN PATROLI SIBER</b>", self.style_title),
                Paragraph(f"<b>TANGGAL DITERBITKAN</b><br/>{print_date}", self.style_meta_val),
            ],
            [
                Paragraph(
                    "<b>Sistem Intelijen Siber & Pemantauan Opini Publik Terpadu</b><br/>"
                    f"Cakupan Filter: {platform_filter} • Kategori: {kategori_filter} • Total Kasus: {len(reports)} Temuan Terverifikasi",
                    self.style_subtitle,
                ),
                Paragraph("<b>STATUS RESMI</b><br/><font color='#059669'><b>DIVERIFIKASI RESMI</b></font>", self.style_meta_val),
            ],
        ]
        kop_table = Table(kop_data, colWidths=[380, 143])
        kop_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ])
        )
        flowables.append(kop_table)
        flowables.append(Spacer(1, 8))
        flowables.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY_DARK, spaceAfter=14))

        # ── DAFTAR TEMUAN BERNOMOR ──
        for idx, r in enumerate(reports, start=1):
            ca = content_analysis_map.get(r.content_id)
            content = r.content
            acct = content.account if content else None
            ev = r.evidences[0] if (r.evidences and len(r.evidences) > 0) else None

            # Warna & Teks Risiko
            final_risk = (r.final_risk or r.ai_risk_level or "RENDAH").upper()
            if "TINGGI" in final_risk:
                risk_color = "#DC2626"
            elif "SEDANG" in final_risk:
                risk_color = "#D97706"
            else:
                risk_color = "#059669"

            final_label = (r.final_label or r.ai_predicted_label or "LAINNYA").upper()
            platform_str = (content.platform.upper() if content and content.platform else "MEDIA SOSIAL")
            ticket_str = r.ticket_number or f"TIKET-{idx}"
            title_str = (content.title if (content and content.title) else f"Temuan {platform_str} #{ticket_str}").strip()

            item_flowables = []

            # 1. Baris Judul & Nomor Urut
            header_text = f"<b>{idx}. [{ticket_str}] {title_str}</b>"
            badge_html = (
                f"<font color='{risk_color}'><b>[RISIKO {final_risk}]</b></font>  "
                f"<font color='#1D4ED8'><b>[{final_label}]</b></font>  "
                f"<font color='#475569'><b>[{r.status}]</b></font>"
            )

            case_header_data = [
                [
                    Paragraph(header_text, self.style_case_number),
                    Paragraph(badge_html, ParagraphStyle("Badge", parent=self.style_meta_val, alignment=2)),
                ]
            ]
            case_header_table = Table(case_header_data, colWidths=[360, 163])
            case_header_table.setStyle(
                TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ])
            )
            item_flowables.append(case_header_table)

            # 2. Foto Snapshot Bukti Visual
            evidence_img = None
            if ev and ev.storage_path:
                evidence_img = self._prepare_image(ev.storage_path, max_width=515, max_height=210)

            if evidence_img:
                img_data = [
                    [evidence_img],
                    [Paragraph(f"Tangkapan Layar Bukti Digital Asli • SHA-256: <code>{ev.sha256}</code>", self.style_caption)],
                ]
                img_table = Table(img_data, colWidths=[523])
                img_table.setStyle(
                    TableStyle([
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
                        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                        ("TOPPADDING", (0, 0), (-1, 0), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
                        ("TOPPADDING", (0, 1), (-1, 1), 2),
                        ("BOTTOMPADDING", (0, 1), (-1, 1), 4),
                    ])
                )
                item_flowables.append(img_table)
                item_flowables.append(Spacer(1, 4))

            # 3. Kotak Tautan / URL Konten Target
            canonical_url = content.canonical_url if (content and content.canonical_url) else "-"
            url_p = Paragraph(f"<b>Tautan Konten:</b> <u>{canonical_url}</u>", self.style_url)
            url_table = Table([[url_p]], colWidths=[523])
            url_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ])
            )
            item_flowables.append(url_table)
            item_flowables.append(Spacer(1, 4))

            # 4. Ringkasan Narasi Konten (Summarize & Indonesian Translation)
            summary_content = (
                r.ai_summary
                or (ca.summary if ca else None)
                or (r.indonesian_content[:300] if getattr(r, "indonesian_content", None) else None)
                or (content.caption_text[:300] if content else "Ringkasan konten belum tersedia.")
            )
            lang_badge = ""
            if getattr(r, "original_language", None) and r.original_language.lower() != "id":
                lang_badge = f" <font color='#1D4ED8'><b>[SUMBER: {r.original_language.upper()} • TERJEMAHAN ID BAKU]</b></font>"

            summary_box_data = [
                [
                    Paragraph(
                        f"<b>RINGKASAN NARASI / ISU KONTEN:</b>{lang_badge}<br/>" + summary_content,
                        self.style_summary_box,
                    )
                ]
            ]
            summary_table = Table(summary_box_data, colWidths=[523])
            summary_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),  # Light blue
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#93C5FD")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ])
            )
            item_flowables.append(summary_table)
            item_flowables.append(Spacer(1, 4))

            # 5. Metadata Akun & Waktu (Postingannya itu apa, siapa)
            author_str = f"@{acct.username}" if (acct and acct.username) else "@patrol_finder"
            display_str = acct.display_name if (acct and acct.display_name) else author_str
            verified_str = " (Terverifikasi)" if (acct and acct.is_verified) else ""
            followers_cnt = f"{acct.followers_count:,}" if (acct and acct.followers_count) else "-"
            views_cnt = f"{content.views_count:,}" if (content and content.views_count) else "-"
            likes_cnt = f"{content.likes_count:,}" if (content and content.likes_count) else "-"
            comments_cnt = f"{content.comments_count:,}" if (content and content.comments_count) else "-"

            patrol_time_str = r.created_at.strftime("%d/%m/%Y %H:%M WIB") if r.created_at else "-"
            post_time_str = (
                content.posted_at.strftime("%d/%m/%Y %H:%M WIB")
                if (content and content.posted_at)
                else (ca.when_info if ca else "-")
            )

            meta_grid = [
                [
                    Paragraph("<b>PENGUNGGAH / SUMBER</b>", self.style_meta_label),
                    Paragraph(f"{display_str} ({author_str}){verified_str} • {followers_cnt} Pengikut", self.style_meta_val),
                    Paragraph("<b>PLATFORM & WAKTU</b>", self.style_meta_label),
                    Paragraph(f"Kanal {platform_str} • Rilis: {post_time_str}", self.style_meta_val),
                ],
                [
                    Paragraph("<b>STATISTIK ENGAGEMENT</b>", self.style_meta_label),
                    Paragraph(f"{views_cnt} Tayangan • {likes_cnt} Suka • {comments_cnt} Komentar", self.style_meta_val),
                    Paragraph("<b>WAKTU PATROLI</b>", self.style_meta_label),
                    Paragraph(f"{patrol_time_str} • Petugas: {r.reporter_identifier or 'Analis Ekstensi'}", self.style_meta_val),
                ],
            ]
            meta_table = Table(meta_grid, colWidths=[105, 156, 95, 167])
            meta_table.setStyle(
                TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
                    ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER_LIGHT),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            item_flowables.append(meta_table)
            item_flowables.append(Spacer(1, 4))

            # 6. Struktur Intelijen & Kronologi 5W+1H (Timeline / Pembahasan)
            what_val = ca.what if (ca and ca.what) else title_str
            who_val = ca.who if (ca and ca.who) else f"{display_str} ({author_str})"
            when_val = ca.when_info if (ca and ca.when_info) else post_time_str
            where_val = ca.where_info if (ca and ca.where_info) else f"Platform {platform_str}"
            why_val = ca.why if (ca and ca.why) else "Isu diangkat berdasarkan perkembangan percakapan publik di media sosial."
            how_val = ca.how if (ca and ca.how) else "Dipaparkan melalui konten visual dan audio pada platform terkait."

            timeline_grid = [
                [
                    Paragraph("<b>WHAT (APA)</b>", self.style_meta_label),
                    Paragraph(what_val, self.style_timeline_item),
                ],
                [
                    Paragraph("<b>WHO (SIAPA)</b>", self.style_meta_label),
                    Paragraph(who_val, self.style_timeline_item),
                ],
                [
                    Paragraph("<b>WHEN (KAPAN)</b>", self.style_meta_label),
                    Paragraph(when_val, self.style_timeline_item),
                ],
                [
                    Paragraph("<b>WHERE (DI MANA)</b>", self.style_meta_label),
                    Paragraph(where_val, self.style_timeline_item),
                ],
                [
                    Paragraph("<b>WHY (KENAPA)</b>", self.style_meta_label),
                    Paragraph(why_val, self.style_timeline_item),
                ],
                [
                    Paragraph("<b>HOW (KRONOLOGI)</b>", self.style_meta_label),
                    Paragraph(how_val, self.style_timeline_item),
                ],
            ]
            timeline_table = Table(timeline_grid, colWidths=[95, 428])
            timeline_table.setStyle(
                TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
                    ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER_LIGHT),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            item_flowables.append(timeline_table)

            # Pembatas elegan antar temuan
            item_flowables.append(Spacer(1, 10))
            if idx < len(reports):
                item_flowables.append(HRFlowable(width="100%", thickness=0.8, color=COLOR_BORDER, spaceAfter=12))

            # Susun ke flowable dokumen utama
            flowables.append(KeepTogether(item_flowables[:4]))  # Header, image, URL bersamaan
            for rem in item_flowables[4:]:
                flowables.append(rem)

        # Bangun dokumen
        doc.build(flowables, canvasmaker=NumberedCanvas)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
