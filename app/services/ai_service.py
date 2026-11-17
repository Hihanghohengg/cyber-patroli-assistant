import os
import json
import logging
import socket
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    import google.generativeai as genai
except Exception:
    genai = None
from app.config import settings
from app.schemas.ai_response import AIPatrolAnalysis

logger = logging.getLogger(__name__)

# Minimum valid screenshot size (10 KB)
MIN_SCREENSHOT_BYTES = 10 * 1024

CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-pro",
]


def is_gemini_reachable(timeout: float = 1.0) -> bool:
    """Pre-flight check to see if Google Gemini cloud API is network-reachable."""
    try:
        with socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=timeout):
            return True
    except Exception:
        return False


class AIService:
    """Multimodal AI analysis pipeline using Google Gemini.

    Sends screenshot visual evidence together with textual and interaction metadata
    to Gemini and enforces a strict, structured JSON schema for intelligence triage.
    Supports automatic multi-model failover if a specific tier quota is exhausted.
    """

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)

    def analyze_patrol_finding(
        self,
        caption: str,
        image_path: str | None,
        profile_info: dict,
        title: str = "",
        metadata: dict | None = None,
        hitl_context: str = "",
        rag_context: str = "",
    ) -> AIPatrolAnalysis:
        """Run multimodal AI analysis on a patrol finding with dynamic HITL learning harness.

        Args:
            caption: Caption / description text of the post.
            image_path: Path to the post screenshot image (PNG).
            profile_info: Dict with keys username, display_name, subscribers_count.
            title: Title of video or post.
            metadata: Additional metadata (views, likes, comments, duration, tags).
            hitl_context: Ground-truth human analyst decisions & corrections for continuous learning.
            rag_context: Legacy alias for hitl_context.

        Returns:
            Validated AIPatrolAnalysis Pydantic model.
        """
        meta = metadata or {}
        views = meta.get("views_count", 0)
        likes = meta.get("likes_count", 0)
        comments = meta.get("comments_count", 0)
        duration = meta.get("duration", "N/A")
        tags = meta.get("tags", [])

        schema_hint = AIPatrolAnalysis.model_json_schema()

        # Build prompt with HITL (Human-in-the-Loop) learning patterns
        active_context = hitl_context or rag_context
        hitl_section = ""
        if active_context and active_context.strip():
            hitl_section = f"""
== POLA PEMBELAJARAN AKTIF DARI ANALIS MANUSIA (HITL HARNESSING PATTERNS) ==
INSTRUKSI KHUSUS PEMBELAJARAN:
Berikut adalah putusan terverifikasi dan koreksi analis manusia resmi (Human-in-the-Loop) pada kasus sebelumnya.
Pelajari dengan seksama alasan dan pola koreksi berikut agar Anda TIDAK mengulangi kesalahan klasifikasi serupa:

{active_context.strip()}
"""

        # Parse caption and transcript if combined
        caption_body = caption or ""
        transcript_body = ""
        if "[TRANSKRIP AUDIO / DIALOG LENGKAP]:" in caption_body:
            parts = caption_body.split("[TRANSKRIP AUDIO / DIALOG LENGKAP]:", 1)
            caption_body = parts[0].strip()
            transcript_body = parts[1].strip()

        transcript_section = ""
        if transcript_body:
            # Include comprehensive dialog snippet for AI reasoning (up to 5000 chars)
            transcript_section = f"""
== TRANSKRIP PERCAKAPAN / DIALOG AUDIO LENGKAP ==
{transcript_body[:5000]}
"""

        prompt = f"""Anda adalah Analis Triase Intelijen Siber dan Patroli Media Sosial Resmi.
Tugas Anda: Melakukan analisis terukur, objektif, dan berbasis bukti terhadap postingan/video publik berikut.
{hitl_section}
== METADATA KONTEN ==
- Judul Video/Postingan: {title or '(tidak ada judul)'}
- Deskripsi/Caption: {caption_body or '(tidak tersedia)'}
- Durasi Konten: {duration}
- Statistik Interaksi: {views:,} views | {likes:,} likes | {comments:,} comments
- Tag/Kategori: {', '.join(tags) if tags else '-'}
{transcript_section}
== PROFIL PENGUNGGAH ==
- Handle / Username: {profile_info.get('username', 'N/A')}
- Nama Tampilan: {profile_info.get('display_name', 'N/A')}
- Estimasi Pengikut/Subscribers: {profile_info.get('subscribers_count', 0):,}

== INSTRUKSI ANALISIS TRIASE ==
1. Analisis Visual & OCR: Periksa gambar tangkapan layar bukti secara menyeluruh (baca teks pada thumbnail, player video, banner, dan gestur/simbol visual).
2. Analisis Transkrip Audio & Percakapan: Jika tersedia transkrip percakapan/audio, baca dan pahami seluruh alur pembicaraan narator/pembicara.
3. Rangkuman Berkualitas Tinggi (ringkasan_narasi): Buat rangkuman narasi komprehensif dan cerdas yang memadukan judul, deskripsi, dan isi transkrip pembicaraan. Jelaskan apa yang sebenarnya dibahas dan disimpulkan dalam video.
4. Pertimbangan Analis Objektif (alasan_penilaian): Uraikan secara faktual dan rinci poin-poin yang menjadi dasar penilaian Anda (mengapa aman/netral atau mengapa berisiko).
5. Kategori Utama yang Tersedia:
   - "HOAKS": Informasi palsu, rekayasa fakta, clickbait menyesatkan publik.
   - "UJARAN_KEBENCIAN": Menghina, merendahkan, menghasut kebencian terhadap individu/kelompok.
   - "PROVOKASI_SARA": Menimbulkan permusuhan berdasarkan suku, agama, ras, dan antargolongan.
   - "PENIPUAN_FINANSIAL": Skema penipuan uang, judi online, phishing, investasi bodong.
   - "DI_LUAR_KONTEKS": Menggunakan video lama atau konteks berbeda untuk memutarbalikkan fakta.
   - "NETRAL": Konten wajar, edukatif, opini biasa tanpa pelanggaran siber.
6. Tingkat Risiko:
   - "TINGGI": Berpotensi memicu kegaduhan massal, kerusuhan, kerugian finansial luas, atau pencatutan instansi negara.
   - "SEDANG": Narasi bias berpotensi membingungkan publik, memerlukan klarifikasi.
   - "RENDAH": Risiko minimal atau konten netral/aman.
7. Ekstraksi Entitas & Topik (PRD v3):
   - "topik": Topik utama konten secara singkat (contoh: "Review Sepatu Lokal", "Program MBG", "Ijazah PTUN").
   - "aktor_target": Daftar tokoh, pejabat, institusi, atau kelompok sasaran (contoh: ["KPU", "Presiden"]). Boleh kosong [].
   - "sumber_konten": Nama media atau kanal asal (contoh: "Tribunnews", "Kompas", atau username jika akun pribadi).
   - "tipe_sumber": Pilih salah satu: "MEDIA_ONLINE", "MEDIA_TV", "AKUN_INDIVIDU", "KOMUNITAS", "LAINNYA".
8. Output WAJIB dalam format JSON valid sesuai skema berikut:
{json.dumps(schema_hint, indent=2, ensure_ascii=False)}
"""

        contents: list = [prompt]

        # Attach image ONLY if it exists and passes anti-blank validation
        has_valid_image = False
        if image_path and os.path.exists(image_path):
            img_size = os.path.getsize(image_path)
            if img_size >= MIN_SCREENSHOT_BYTES:
                try:
                    with open(image_path, "rb") as img:
                        image_bytes = img.read()
                    contents.append(
                        {"mime_type": "image/png", "data": image_bytes}
                    )
                    has_valid_image = True
                    logger.info("Attached valid screenshot (%d bytes) to AI analysis", img_size)
                except Exception as read_err:
                    logger.warning("Failed to read screenshot %s: %s", image_path, read_err)
            else:
                logger.warning(
                    "Screenshot %s size (%d bytes) < 20KB threshold; skipping visual attachment to avoid blank analysis.",
                    image_path,
                    img_size,
                )

        if not has_valid_image:
            logger.info("Running AI analysis with text and metadata only.")

        # Try candidate models with automatic failover
        last_error = None
        for model_name in CANDIDATE_MODELS:
            try:
                logger.info("Attempting AI analysis using model: %s", model_name)
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={"response_mime_type": "application/json"},
                )
                response = model.generate_content(contents, request_options={"timeout": 8})
                raw_json = json.loads(response.text)
                result = AIPatrolAnalysis(**raw_json)
                logger.info(
                    "AI analysis complete via %s — status=%s, kategori=%s, risiko=%s, confidence=%.2f",
                    model_name,
                    result.status_keamanan,
                    result.kategori_utama,
                    result.tingkat_risiko,
                    result.skor_keyakinan,
                )
                return result
            except Exception as e:
                err_str = str(e)
                last_error = e
                if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                    logger.warning("Gemini API Key tidak valid. Segera beralih ke engine heuristik.")
                    break
                if any(x in err_str for x in ["WinError 10013", "10060", "10061", "ConnectError", "Network is unreachable", "NameResolutionError", "Permission denied", "Forbidden"]):
                    logger.warning("Koneksi jaringan Gemini diblokir atau offline (%s). Segera beralih ke engine lokal.", err_str)
                    break
                logger.warning("Model %s failed: %s. Trying next candidate...", model_name, e)

        # If all API calls fail, raise the last exception
        raise RuntimeError(f"All Gemini models failed: {last_error}")
