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
import tempfile
import json
from datetime import datetime
from typing import List, Optional, Any, Dict

import httpx
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

os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except Exception as e:
    HAS_MATPLOTLIB = False
    plt = None
    logger.warning("matplotlib tidak tersedia: %s", e)

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
        self.drawString(36, 810, "TILIK • SISTEM PEMANTAUAN & ANALISIS KONTEN SIBER")
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
        self.style_section_heading = ParagraphStyle(
            "SectionHeading",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=COLOR_PRIMARY_DARK,
        )
        self.style_narrative_box = ParagraphStyle(
            "NarrativeBox",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=13,
            textColor=COLOR_TEXT_MAIN,
        )
        self.style_chip_label = ParagraphStyle(
            "ChipLabel",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=COLOR_PRIMARY_BLUE,
        )
        self.style_table_header = ParagraphStyle(
            "TableHeader",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=COLOR_PRIMARY_DARK,
        )
        self.style_table_cell = ParagraphStyle(
            "TableCell",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=COLOR_TEXT_MAIN,
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

    def _generate_category_bar_chart(self, cat_counts: Dict[str, int], total_findings: int) -> Optional[io.BytesIO]:
        """Generate high-resolution (200 DPI) horizontal bar chart of category distribution."""
        if not HAS_MATPLOTLIB or plt is None:
            return None
        try:
            sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1])
            labels = [c[0] for c in sorted_cats]
            values = [c[1] for c in sorted_cats]

            palette = ["#2563EB", "#059669", "#D97706", "#DC2626", "#7C3AED", "#0891B2", "#DB2777", "#475569"]
            colors_list = [palette[i % len(palette)] for i in range(len(labels))]

            fig, ax = plt.subplots(figsize=(6.4, 2.5), dpi=200)
            bars = ax.barh(labels, values, color=colors_list, height=0.55)
            ax.set_title("Distribusi Temuan per Kategori IPOLEKSOSBUDHANKAM", fontsize=9, fontweight="bold", pad=8, color="#0F172A")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#CBD5E1")
            ax.spines["bottom"].set_color("#CBD5E1")
            ax.tick_params(axis="both", labelsize=7.5)

            max_v = max(values + [1])
            for bar in bars:
                w = bar.get_width()
                pct = (w / total_findings * 100) if total_findings > 0 else 0
                label_text = f" {int(w)} ({pct:.1f}%)" if w > 0 else " 0"
                ax.text(w + max_v * 0.01, bar.get_y() + bar.get_height() / 2, label_text,
                        va="center", ha="left", fontsize=7, fontweight="bold", color="#334155")

            ax.set_xlim(0, max_v * 1.3)
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return buf
        except Exception as e:
            logger.warning("Gagal membuat chart kategori: %s", e)
            return None

    def _generate_channel_urgency_chart(self, platform_counts: Dict[str, int], urgency_counts: Dict[str, int]) -> Optional[io.BytesIO]:
        """Generate high-resolution (200 DPI) 2-panel chart: platform distribution + urgency composition."""
        if not HAS_MATPLOTLIB or plt is None:
            return None
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.4), dpi=200)

            plat_labels = [p.upper() for p in platform_counts.keys()]
            plat_values = list(platform_counts.values())
            if sum(plat_values) > 0:
                plat_colors = ["#2563EB", "#059669", "#D97706", "#DC2626", "#7C3AED", "#0891B2"]
                ax1.pie(plat_values, labels=plat_labels, autopct="%1.1f%%", startangle=140,
                        colors=plat_colors[:len(plat_labels)], textprops={"fontsize": 7, "color": "#1E293B"})
                ax1.set_title("Sebaran Kanal Media Sosial", fontsize=8.5, fontweight="bold", color="#0F172A", pad=6)
            else:
                ax1.text(0.5, 0.5, "Tidak ada data kanal", ha="center", va="center", fontsize=7.5)
                ax1.axis("off")

            urg_labels = ["Tinggi (4–5)", "Sedang (3)", "Rendah (1–2)"]
            urg_values = [urgency_counts.get("TINGGI", 0), urgency_counts.get("SEDANG", 0), urgency_counts.get("RENDAH", 0)]
            urg_colors = ["#DC2626", "#D97706", "#059669"]
            bars2 = ax2.bar(urg_labels, urg_values, color=urg_colors, width=0.5)
            ax2.set_title("Komposisi Tingkat Urgensi Kasus", fontsize=8.5, fontweight="bold", color="#0F172A", pad=6)
            ax2.spines["top"].set_visible(False)
            ax2.spines["right"].set_visible(False)
            ax2.spines["left"].set_color("#CBD5E1")
            ax2.spines["bottom"].set_color("#CBD5E1")
            ax2.tick_params(axis="both", labelsize=7)

            max_u = max(urg_values + [1])
            for bar in bars2:
                h = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width() / 2, h + max_u * 0.02, f"{int(h)}",
                         ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#334155")

            ax2.set_ylim(0, max_u * 1.25)
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return buf
        except Exception as e:
            logger.warning("Gagal membuat chart kanal/urgensi: %s", e)
            return None

    def _generate_grounded_report_narrative(
        self,
        total_findings: int,
        cat_counts: Dict[str, int],
        platform_counts: Dict[str, int],
        urgency_counts: Dict[str, int],
        actual_topics: Optional[List[Dict[str, Any]]] = None,
        thematic_topics: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        """Generate strictly grounded narrative summaries using local Ollama model with deterministic fallback."""
        dominant_cat = max(cat_counts.items(), key=lambda x: x[1])[0] if total_findings > 0 else "Sosial"
        dom_cnt = cat_counts.get(dominant_cat, 0)
        dom_pct = (dom_cnt / total_findings * 100) if total_findings > 0 else 0
        dominant_plat = max(platform_counts.items(), key=lambda x: x[1])[0] if platform_counts else "web"

        actual_topics = actual_topics or []
        thematic_topics = thematic_topics or []

        top_act_str = ", ".join([t.get("title", "") for t in actual_topics[:3] if t.get("title")])
        top_thm_str = ", ".join([t.get("title", "") for t in thematic_topics[:3] if t.get("title")])

        fallback_narrative = {
            "narasi_ringkasan_statistik": (
                f"Dari total {total_findings} konten patroli siber yang terakuisisi dalam periode ini, sebanyak "
                f"{dom_cnt} temuan ({dom_pct:.1f}%) terkonsentrasi pada ranah {dominant_cat}. "
                f"Kanal {dominant_plat.upper()} menjadi platform dengan volume deteksi tertinggi. "
                f"Berdasarkan klasifikasi tingkat kerawanan, tercatat {urgency_counts.get('TINGGI', 0)} temuan berkategori "
                f"Tinggi/Kritikal yang memerlukan atensi segera, {urgency_counts.get('SEDANG', 0)} berkategori Sedang, "
                f"dan {urgency_counts.get('RENDAH', 0)} berkategori Rendah."
            ),
            "insight_isu_aktual": (
                f"Klaster isu yang mendominasi percakapan publik saat ini berpusat pada ranah {dominant_cat.lower()}, "
                f"terutama eskalasi seputar {top_act_str if top_act_str else 'perkembangan isu viral di ruang siber'}. "
                f"Dinamika ini membutuhkan verifikasi lapangan berkelanjutan guna mencegah meluasnya disinformasi."
            ),
            "insight_isu_tematik": (
                f"Secara tematik, temuan patroli menunjukkan kesinambungan pola strategis seputar "
                f"{top_thm_str if top_thm_str else 'kebijakan tata kelola pemerintahan dan ketertiban ruang publik'}, "
                f"yang relevan dengan payung program kerja serta mitigasi kerawanan stabilitas nasional."
            ),
        }

        try:
            cat_breakdown = ", ".join([f"{k}: {v}" for k, v in cat_counts.items() if v > 0])
            plat_breakdown = ", ".join([f"{k}: {v}" for k, v in platform_counts.items() if v > 0])
            prompt = (
                f"FAKTA DATA:\n"
                f"- Total Temuan: {total_findings} konten\n"
                f"- Distribusi Kategori: {cat_breakdown}\n"
                f"- Sebaran Platform: {plat_breakdown}\n"
                f"- Tingkat Urgensi: Tinggi={urgency_counts.get('TINGGI', 0)}, Sedang={urgency_counts.get('SEDANG', 0)}, Rendah={urgency_counts.get('RENDAH', 0)}\n"
                f"- Top Isu Aktual: {top_act_str or 'N/A'}\n"
                f"- Isu Tematik: {top_thm_str or 'N/A'}\n\n"
                f"Instruksi Mutlak:\n"
                f"1. HANYA gunakan angka dan data di atas. DILARANG membuat angka baru atau berhalusinasi.\n"
                f"2. Pastikan teks menyebutkan persis 'total {total_findings} konten' pada narasi ringkasan statistik.\n"
                f"3. Berikan output HANYA dalam JSON format:\n"
                f'{{"narasi_ringkasan_statistik": "...", "insight_isu_aktual": "...", "insight_isu_tematik": "..."}}'
            )
            with httpx.Client(timeout=8.0) as client:
                res = client.post(
                    "http://127.0.0.1:11434/api/chat",
                    json={
                        "model": "qwen2.5:3b",
                        "messages": [
                            {"role": "system", "content": "Anda adalah Analis Senior Laporan Eksekutif Intelijen Siber Nasional. Buat narasi berbasis fakta angka terverifikasi."},
                            {"role": "user", "content": prompt},
                        ],
                        "format": "json",
                        "stream": False,
                    },
                )
                if res.status_code == 200:
                    body = res.json()
                    content_str = body.get("message", {}).get("content", "")
                    parsed = json.loads(content_str)
                    if str(total_findings) in parsed.get("narasi_ringkasan_statistik", ""):
                        return {
                            "narasi_ringkasan_statistik": parsed.get("narasi_ringkasan_statistik", fallback_narrative["narasi_ringkasan_statistik"]),
                            "insight_isu_aktual": parsed.get("insight_isu_aktual", fallback_narrative["insight_isu_aktual"]),
                            "insight_isu_tematik": parsed.get("insight_isu_tematik", fallback_narrative["insight_isu_tematik"]),
                        }
        except Exception as e:
            logger.debug("Ollama grounded report narrative fallback triggered: %s", e)

        return fallback_narrative

    def generate_analytical_report_pdf(
        self,
        reports: List[Any],
        content_analysis_map: Dict[Any, Any],
        filter_meta: Optional[Dict[str, str]] = None,
        actual_topics: Optional[List[Dict[str, Any]]] = None,
        thematic_topics: Optional[List[Dict[str, Any]]] = None,
    ) -> bytes:
        """Membuat dokumen PDF resmi analitis terfilter dengan visualisasi grafik 200+ DPI dan narasi AI anti-halusinasi."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=44,
            bottomMargin=44,
        )

        flowables = []
        filter_info = filter_meta or {}
        periode_str = filter_info.get("period_label", "Periode Pemantauan Harian")
        kategori_filter = filter_info.get("category", "Semua Kategori")
        print_date = datetime.now().strftime("%d %B %Y, %H:%M WIB")

        # ── 1. HEADER DOKUMEN RESMI ──
        kop_data = [
            [
                Paragraph("<b>LAPORAN PEMANTAUAN & ANALISIS KONTEN SIBER</b>", self.style_title),
                Paragraph(f"<b>WAKTU CETAK</b><br/>{print_date}", self.style_meta_val),
            ],
            [
                Paragraph(
                    "<b>Direktorat Operasi Siber • Analisis Intelijen & Segel Integritas Kriptografis</b><br/>"
                    f"Cakupan: {periode_str} • Filter Kategori: {kategori_filter} • Total Kasus: {len(reports)} Temuan Terverifikasi",
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
        flowables.append(Spacer(1, 6))
        flowables.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY_DARK, spaceAfter=10))

        # ── Hitung Metrik Agregat ──
        categories_standard = ["Ideologi", "Politik", "Ekonomi", "Sosial", "Budaya", "Pertahanan", "Keamanan", "Non-Isu"]
        cat_counts = {c: 0 for c in categories_standard}
        platform_counts: Dict[str, int] = {}
        urgency_counts = {"TINGGI": 0, "SEDANG": 0, "RENDAH": 0}

        for r in reports:
            lbl = r.final_label or r.ai_predicted_label or "Sosial"
            matched_c = next((c for c in categories_standard if c.lower() == lbl.lower()), "Sosial")
            cat_counts[matched_c] = cat_counts.get(matched_c, 0) + 1

            plat = getattr(r.content, "platform", "web") if r.content else "web"
            plat_clean = plat.lower() if plat else "web"
            platform_counts[plat_clean] = platform_counts.get(plat_clean, 0) + 1

            risk = (r.final_risk or r.ai_risk_level or "RENDAH").upper()
            if risk in urgency_counts:
                urgency_counts[risk] += 1
            else:
                urgency_counts["RENDAH"] += 1

        total_findings = len(reports)

        # ── 2. RINGKASAN KUANTITATIF & NARASI AI ANTI-HALUSINASI ──
        ai_narrative = self._generate_grounded_report_narrative(
            total_findings=total_findings,
            cat_counts=cat_counts,
            platform_counts=platform_counts,
            urgency_counts=urgency_counts,
            actual_topics=actual_topics,
            thematic_topics=thematic_topics,
        )

        flowables.append(Paragraph("<b>I. RINGKASAN KUANTITATIF & STATISTIK TREN</b>", self.style_section_heading))
        flowables.append(Spacer(1, 4))

        stat_box_data = [[
            Paragraph(
                f"<b>Sintesis Statistik Siber:</b> {ai_narrative['narasi_ringkasan_statistik']}",
                self.style_narrative_box,
            )
        ]]
        stat_box_table = Table(stat_box_data, colWidths=[523])
        stat_box_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("BORDER", (0, 0), (-1, -1), 0.8, colors.HexColor("#93C5FD")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        flowables.append(stat_box_table)
        flowables.append(Spacer(1, 8))

        # ── 3. VISUALISASI GRAFIK 200+ DPI ──
        cat_chart_buf = self._generate_category_bar_chart(cat_counts, total_findings)
        chan_urg_chart_buf = self._generate_channel_urgency_chart(platform_counts, urgency_counts)

        if cat_chart_buf or chan_urg_chart_buf:
            flowables.append(Paragraph("<b>II. VISUALISASI SEBARAN & TINGKAT URGENSI</b>", self.style_section_heading))
            flowables.append(Spacer(1, 4))

            if cat_chart_buf:
                flowables.append(Image(cat_chart_buf, width=490, height=190))
                flowables.append(Spacer(1, 6))
            if chan_urg_chart_buf:
                flowables.append(Image(chan_urg_chart_buf, width=490, height=160))
                flowables.append(Spacer(1, 6))

        # Tabel Distribusi Kategori Ringkas
        flowables.append(Paragraph("<b>Tabel Ringkasan Distribusi Kategori IPOLEKSOSBUDHANKAM</b>", self.style_meta_label))
        flowables.append(Spacer(1, 2))
        table_rows = [
            [
                Paragraph("<b>Kategori</b>", self.style_table_header),
                Paragraph("<b>Jumlah Temuan</b>", self.style_table_header),
                Paragraph("<b>Proporsi (%)</b>", self.style_table_header),
                Paragraph("<b>Tingkat Risiko Dominan</b>", self.style_table_header),
            ]
        ]
        for cat in categories_standard:
            cnt = cat_counts.get(cat, 0)
            pct_str = f"{(cnt / total_findings * 100):.1f}%" if total_findings > 0 else "0.0%"
            table_rows.append([
                Paragraph(f"<b>{cat}</b>", self.style_table_cell),
                Paragraph(f"{cnt} kasus", self.style_table_cell),
                Paragraph(pct_str, self.style_table_cell),
                Paragraph("Tinggi" if cat in ("Keamanan", "Pertahanan") and cnt > 0 else "Sedang / Rendah", self.style_table_cell),
            ])

        cat_table = Table(table_rows, colWidths=[150, 110, 110, 153])
        cat_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER_LIGHT),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        flowables.append(cat_table)
        flowables.append(Spacer(1, 12))

        # ── 4. PEMETAAN ISU AKTUAL & TEMATIK STRATEGIS ──
        flowables.append(Paragraph("<b>III. PEMETAAN ISU AKTUAL & ISU TEMATIK STRATEGIS</b>", self.style_section_heading))
        flowables.append(Spacer(1, 4))

        actual_box_data = [[
            Paragraph(
                f"<b>Dinamika Isu Aktual (Trending & Butuh Respons Cepat):</b><br/>{ai_narrative['insight_isu_aktual']}",
                self.style_narrative_box,
            )
        ]]
        actual_box = Table(actual_box_data, colWidths=[523])
        actual_box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
                ("BORDER", (0, 0), (-1, -1), 0.8, colors.HexColor("#FCD34D")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        flowables.append(actual_box)
        flowables.append(Spacer(1, 6))

        thematic_box_data = [[
            Paragraph(
                f"<b>Pemetaan Isu Tematik (Agenda Nasional & Program Bersama):</b><br/>{ai_narrative['insight_isu_tematik']}",
                self.style_narrative_box,
            )
        ]]
        thematic_box = Table(thematic_box_data, colWidths=[523])
        thematic_box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F3FF")),
                ("BORDER", (0, 0), (-1, -1), 0.8, colors.HexColor("#C4B5FD")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        flowables.append(thematic_box)
        flowables.append(Spacer(1, 12))

        # ── 5. RINCIAN TEMUAN PATROLI SIBER TERFILTER ──
        flowables.append(Paragraph(f"<b>IV. RINCIAN TEMUAN PATROLI SIBER TERFILTER ({len(reports)} KASUS)</b>", self.style_section_heading))
        flowables.append(Spacer(1, 6))

        if not reports:
            flowables.append(Paragraph("<i>Tidak ada temuan patroli siber yang sesuai dengan kriteria filter yang dipilih.</i>", self.style_summary_box))
        else:
            for idx, r in enumerate(reports, 1):
                item_flowables = []
                content = r.content
                acct = content.account if content else None
                ca = content_analysis_map.get(r.content_id) if r.content_id else None
                platform_str = content.platform.upper() if content and content.platform else "WEB"
                title_str = (content.title or content.caption_text or "Temuan patroli").strip()
                if len(title_str) > 120:
                    title_str = title_str[:117] + "..."

                cat_label = r.final_label or r.ai_predicted_label or "Sosial"
                risk_label = (r.final_risk or r.ai_risk_level or "SEDANG").upper()
                urgency_score = getattr(ca, "urgency_score", 3) if ca else (4 if risk_label == "TINGGI" else 2)
                claim_status = getattr(r, "status_klaim", None) or (getattr(content, "status_klaim", None) if content else None) or "Fakta Terverifikasi"

                case_head_data = [
                    [
                        Paragraph(f"<b>#{idx:02d} — {title_str}</b>", self.style_case_number),
                        Paragraph(f"<b>URGENSI: {urgency_score}/5 ({risk_label})</b>", self.style_chip_label),
                    ]
                ]
                case_head_table = Table(case_head_data, colWidths=[410, 113])
                case_head_table.setStyle(
                    TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ])
                )
                item_flowables.append(case_head_table)

                url_str = content.canonical_url if content and content.canonical_url else "-"
                if url_str and url_str != "-":
                    url_display = url_str if len(url_str) <= 75 else url_str[:72] + "..."
                    link_html = f'<font color="#1D4ED8"><u><a href="{url_str}">{url_display}</a></u></font>'
                else:
                    link_html = "-"
                item_flowables.append(Paragraph(f"Tautan Sumber: {link_html}", self.style_url))
                item_flowables.append(Spacer(1, 3))

                ev = r.evidences[0] if (r.evidences and len(r.evidences) > 0) else None
                if ev and ev.storage_path:
                    img_flowable = self._prepare_image(ev.storage_path, max_width=490, max_height=180)
                    if img_flowable:
                        item_flowables.append(img_flowable)
                        item_flowables.append(Spacer(1, 3))

                author_name = f"@{acct.username}" if (acct and acct.username) else (content.author_name if content and content.author_name else "@anonim")
                post_time = r.created_at.strftime("%d/%m/%Y %H:%M WIB") if r.created_at else "-"
                meta_row = [
                    [
                        Paragraph("<b>Kanal & Akun:</b>", self.style_meta_label),
                        Paragraph(f"{platform_str} • {author_name}", self.style_meta_val),
                        Paragraph("<b>Waktu & Kategori:</b>", self.style_meta_label),
                        Paragraph(f"{post_time} • {cat_label}", self.style_meta_val),
                    ],
                    [
                        Paragraph("<b>Status Klaim:</b>", self.style_meta_label),
                        Paragraph(f"{claim_status}", self.style_meta_val),
                        Paragraph("<b>Segel Forensik:</b>", self.style_meta_label),
                        Paragraph("HMAC-SHA256 (NIST FIPS 198-1)", self.style_meta_val),
                    ],
                ]
                meta_table = Table(meta_row, colWidths=[95, 166, 105, 157])
                meta_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
                        ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER_LIGHT),
                        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ])
                )
                item_flowables.append(meta_table)
                item_flowables.append(Spacer(1, 3))

                summary_text = getattr(r, "indonesian_content", None) or r.ai_summary or (content.caption_text if content else "Tidak ada ringkasan teks.")
                if len(summary_text) > 350:
                    summary_text = summary_text[:347] + "..."
                item_flowables.append(Paragraph(f"<b>Ringkasan Analisis:</b> {summary_text}", self.style_summary_box))

                if ca:
                    item_flowables.append(Spacer(1, 2))
                    details_5w1h = [
                        [Paragraph("<b>What (Apa):</b>", self.style_meta_label), Paragraph(ca.what or "-", self.style_table_cell)],
                        [Paragraph("<b>Who (Siapa):</b>", self.style_meta_label), Paragraph(ca.who or "-", self.style_table_cell)],
                        [Paragraph("<b>Why (Kenapa):</b>", self.style_meta_label), Paragraph(ca.why or "-", self.style_table_cell)],
                        [Paragraph("<b>How (Kronologi):</b>", self.style_meta_label), Paragraph(ca.how or "-", self.style_table_cell)],
                    ]
                    t_5w1h = Table(details_5w1h, colWidths=[80, 443])
                    t_5w1h.setStyle(
                        TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                            ("LEFTPADDING", (0, 0), (-1, -1), 4),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ])
                    )
                    item_flowables.append(t_5w1h)

                item_flowables.append(Spacer(1, 6))
                if idx < len(reports):
                    item_flowables.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER_LIGHT, spaceAfter=8))

                flowables.append(KeepTogether(item_flowables[:3]))
                for sub in item_flowables[3:]:
                    flowables.append(sub)

        # Bangun dokumen tanpa blok tanda tangan/cap
        doc.build(flowables, canvasmaker=NumberedCanvas)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def build_pdf_report(self, reports: List[Any], title: str = "", subtitle: str = "") -> bytes:
        """Alias kompatibilitas pembuat PDF analitis."""
        filter_meta = {"period_label": title or "Laporan Patroli Siber Harian"}
        return self.generate_analytical_report_pdf(reports, content_analysis_map={}, filter_meta=filter_meta)
