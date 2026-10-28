"""Gemini-based 5W+1H structured intelligence extraction.

Extracts What, Who, When, Where, Why, How, entities, topics, sentiment,
and risk indicators from social media content while strictly distinguishing
between explicit information and AI inference.
"""

import json
import logging
import os
from typing import Optional

import google.generativeai as genai
from app.config import settings
from app.schemas.intelligence import Analysis5W1H
from app.services.intelligence.text_processor import IndonesianTextProcessor

logger = logging.getLogger(__name__)

CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-pro",
]

MIN_SCREENSHOT_BYTES = 20 * 1024


class Analysis5W1HService:
    """Service to run structured 5W+1H intelligence extraction via Gemini AI."""

    def __init__(self):
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.warning("Failed to configure genai: %s", e)
        self.processor = IndonesianTextProcessor()

    def extract(
        self,
        text: str,
        title: str = "",
        image_path: Optional[str] = None,
        author: str = "",
        platform: str = "",
        metadata: Optional[dict] = None,
    ) -> Analysis5W1H:
        """Extract 5W+1H intelligence and contextual analysis.

        Args:
            text: Caption or post body text.
            title: Title of post or video.
            image_path: Path to screenshot proof image (if available).
            author: Author handle / username.
            platform: Platform name (youtube, tiktok, instagram).
            metadata: Additional engagement or interaction metrics.

        Returns:
            Validated Analysis5W1H instance.
        """
        meta = metadata or {}
        combined_text = f"{title}\n{text}".strip()

        # If no Gemini API key or in dry mode, generate deterministic rule-based analysis
        if not settings.GEMINI_API_KEY:
            logger.info("No GEMINI_API_KEY set; running heuristic fallback 5W+1H extraction.")
            return self._heuristic_fallback(combined_text, author, platform)

        schema_hint = Analysis5W1H.model_json_schema()

        prompt = f"""Anda adalah Analis Intelijen Siber dan Monitoring Opini Publik Resmi.
Tugas Anda: Melakukan ekstraksi terstruktur elemen 5W+1H (What, Who, When, Where, Why, How)
serta identifikasi topik dan entitas dari konten media sosial di bawah ini.

PRINSIP WAJIB:
1. AKURASI FAKTUAL: Jangan mengarang atau memalsukan fakta (halusinasi dilarang).
2. Jika suatu elemen (misal Kapan/Di mana/Mengapa) TIDAK disebutkan eksplisit pada konten, isi dengan null atau jelaskan singkat "Tidak disebutkan dalam konten".
3. Bedakan antara informasi EKSPLISIT (langsung tertulis), INFERENSI (kesimpulan logis analis), atau CAMPURAN.
4. Kategori WAJIB memilih salah satu dari: Politik, Bencana Alam, Lingkungan, Keamanan, Ekonomi, Sosial, Teknologi, Kesehatan, Pendidikan, Hukum, Lainnya.
5. Sentimen WAJIB memilih salah satu dari: POSITIF, NEGATIF, NETRAL, CAMPURAN.

== METADATA KONTEN ==
- Platform: {platform or 'Umum'}
- Penulis / Akun: {author or 'N/A'}
- Judul: {title or '(tanpa judul)'}
- Isi / Deskripsi:
{text or '(tanpa deskripsi)'}
- Interaksi: Views: {meta.get('views_count', 0):,} | Likes: {meta.get('likes_count', 0):,} | Comments: {meta.get('comments_count', 0):,}

== FORMAT OUTPUT ==
Keluarkan HANYA JSON valid sesuai skema berikut:
{json.dumps(schema_hint, indent=2, ensure_ascii=False)}
"""

        contents: list = [prompt]

        # Attach image if valid
        if image_path and os.path.exists(image_path):
            img_size = os.path.getsize(image_path)
            if img_size >= MIN_SCREENSHOT_BYTES:
                try:
                    with open(image_path, "rb") as img:
                        image_bytes = img.read()
                    contents.append({"mime_type": "image/png", "data": image_bytes})
                except Exception as read_err:
                    logger.warning("Could not read screenshot %s: %s", image_path, read_err)

        last_error = None
        for model_name in CANDIDATE_MODELS:
            try:
                logger.info("Running 5W+1H extraction via %s", model_name)
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={"response_mime_type": "application/json"},
                )
                response = model.generate_content(contents)
                raw_json = json.loads(response.text)
                return Analysis5W1H(**raw_json)
            except Exception as e:
                logger.warning("5W+1H model %s failed: %s. Trying next...", model_name, e)
                last_error = e

        logger.error("All Gemini models failed for 5W+1H extraction: %s. Falling back to heuristics.", last_error)
        return self._heuristic_fallback(combined_text, author, platform)

    def _heuristic_fallback(self, text: str, author: str, platform: str) -> Analysis5W1H:
        """Rule-based fallback when AI is unreachable or dry-run testing."""
        keywords = self.processor.extract_keywords(text, top_k=8)
        hashtags = self.processor.extract_hashtags(text)
        first_line = text.split("\n")[0][:100] if text else "Konten media sosial"

        # Simple category guess
        text_lower = text.lower()
        category = "Lainnya"
        if any(w in text_lower for w in ["banjir", "gempa", "longsor", "tsunami", "karhutla", "bencana"]):
            category = "Bencana Alam"
        elif any(w in text_lower for w in ["polisi", "keamanan", "pencurian", "tangkap", "kriminal", "teror"]):
            category = "Keamanan"
        elif any(w in text_lower for w in ["pemilu", "pilpres", "pilkada", "dpr", "presiden", "partai"]):
            category = "Politik"
        elif any(w in text_lower for w in ["rupiah", "inflasi", "harga", "ekonomi", "pasar", "saham"]):
            category = "Ekonomi"
        elif any(w in text_lower for w in ["hukum", "sidang", "jaksa", "hakim", "uu", "pasal"]):
            category = "Hukum"
        elif any(w in text_lower for w in ["hutan", "polusi", "sampah", "iklim", "lingkungan"]):
            category = "Lingkungan"

        # Sentiment guess
        sentiment = "NETRAL"
        negative_words = ["rusak", "korban", "bahaya", "ancaman", "bohong", "hoax", "rugi", "mati", "parah"]
        positive_words = ["sukses", "prestasi", "bantu", "selamat", "pulih", "baik", "terima kasih", "solusi"]
        neg_count = sum(1 for w in negative_words if w in text_lower)
        pos_count = sum(1 for w in positive_words if w in text_lower)
        if neg_count > pos_count:
            sentiment = "NEGATIF"
        elif pos_count > neg_count:
            sentiment = "POSITIF"

        main_topic = " ".join(keywords[:3]).title() if keywords else "Isu Media Sosial"

        return Analysis5W1H(
            what=first_line or "Konten perbincangan publik",
            who=f"Akun @{author}" if author else None,
            when_info="Tidak disebutkan eksplisit",
            where_info="Tidak disebutkan eksplisit",
            why=None,
            how=None,
            summary=first_line,
            main_topic=main_topic,
            sub_topics=keywords[3:6],
            keywords=keywords,
            hashtags=hashtags,
            named_entities=[author] if author else [],
            sentiment=sentiment,
            tone="Informatif",
            category=category,
            relevance_score=0.6,
            urgency_score=0.4,
            confidence_score=0.6,
            misinfo_indicators=[],
            information_basis="CAMPURAN",
        )
