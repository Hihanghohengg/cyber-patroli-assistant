import os
import json
import logging
import google.generativeai as genai
from app.config import settings
from app.schemas.ai_response import AIPatrolAnalysis

logger = logging.getLogger(__name__)

# Minimum valid screenshot size (20 KB)
MIN_SCREENSHOT_BYTES = 20 * 1024

CANDIDATE_MODELS = [
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
]


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
        rag_context: str = "",
    ) -> AIPatrolAnalysis:
        """Run multimodal AI analysis on a patrol finding with optional RAG context.

        Args:
            caption: Caption / description text of the post.
            image_path: Path to the post screenshot image (PNG).
            profile_info: Dict with keys username, display_name, subscribers_count.
            title: Title of video or post.
            metadata: Additional metadata (views, likes, comments, duration, tags).
            rag_context: Retrieved similar past verified cases for in-context learning.

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

        # Build prompt with RAG reference context if available
        rag_section = ""
        if rag_context and rag_context.strip():
            rag_section = f"""
== KASUS REFERENSI DARI KEPUTUSAN ANALIS SEBELUMNYA (RAG KNOWLEDGE BASE) ==
PENTING: Contoh-contoh di bawah ini adalah keputusan resmi analis piket pada kasus serupa sebelumnya.
Gunakan HANYA sebagai acuan pemahaman konteks lokal dan pola putusan. Kasus referensi ini BUKAN kebenaran mutlak;
konten yang sedang diperiksa saat ini WAJIB tetap dinilai secara independen berdasarkan bukti isinya sendiri:

{rag_context.strip()}
"""

        prompt = f"""Anda adalah Analis Triase Intelijen Siber dan Patroli Media Sosial Resmi.
Tugas Anda: Melakukan analisis terukur, objektif, dan berbasis bukti terhadap postingan/video publik berikut.
{rag_section}
== METADATA KONTEN ==
- Judul Video/Postingan: {title or '(tidak ada judul)'}
- Deskripsi/Caption: {caption or '(tidak tersedia)'}
- Durasi Konten: {duration}
- Statistik Interaksi: {views:,} views | {likes:,} likes | {comments:,} comments
- Tag/Kategori: {', '.join(tags) if tags else '-'}

== PROFIL PENGUNGGAH ==
- Handle / Username: {profile_info.get('username', 'N/A')}
- Nama Tampilan: {profile_info.get('display_name', 'N/A')}
- Estimasi Pengikut/Subscribers: {profile_info.get('subscribers_count', 0):,}

== INSTRUKSI ANALISIS TRIASE ==
1. Analisis Visual & OCR: Periksa gambar tangkapan layar bukti secara menyeluruh (baca teks pada thumbnail, player video, banner, dan gestur/simbol visual).
2. Kategori Utama yang Tersedia:
   - "HOAKS": Informasi palsu, rekayasa fakta, clickbait menyesatkan publik.
   - "UJARAN_KEBENCIAN": Menghina, merendahkan, menghasut kebencian terhadap individu/kelompok.
   - "PROVOKASI_SARA": Menimbulkan permusuhan berdasarkan suku, agama, ras, dan antargolongan.
   - "PENIPUAN_FINANSIAL": Skema penipuan uang, judi online, phishing, investasi bodong.
   - "DI_LUAR_KONTEKS": Menggunakan video lama atau konteks berbeda untuk memutarbalikkan fakta.
   - "NETRAL": Konten wajar, edukatif, opini biasa tanpa pelanggaran siber.
3. Tingkat Risiko:
   - "TINGGI": Berpotensi memicu kegaduhan massal, kerusuhan, kerugian finansial luas, atau pencatutan instansi negara.
   - "SEDANG": Narasi bias berpotensi membingungkan publik, memerlukan klarifikasi.
   - "RENDAH": Risiko minimal atau konten netral/aman.
4. Ekstraksi Entitas & Topik (PRD v2):
   - "topik": Topik utama konten secara singkat (contoh: "Pemilu 2024", "Kenaikan Harga BBM", "Bansos").
   - "aktor_target": Daftar tokoh, pejabat, institusi, atau kelompok sasaran (contoh: ["KPU", "Presiden"]). Boleh kosong [].
   - "sumber_konten": Nama media atau kanal asal (contoh: "Tribunnews", "Kompas", atau username jika akun pribadi).
   - "tipe_sumber": Pilih salah satu: "MEDIA_ONLINE", "MEDIA_TV", "AKUN_INDIVIDU", "KOMUNITAS", "LAINNYA".
5. Output WAJIB dalam format JSON valid sesuai skema berikut:
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
                response = model.generate_content(contents)
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
                logger.warning("Model %s failed: %s. Trying next candidate...", model_name, e)
                last_error = e

        # If all API calls fail, raise the last exception
        raise RuntimeError(f"All Gemini models failed: {last_error}")
