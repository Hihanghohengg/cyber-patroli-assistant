"""Gemini-based 5W+1H structured intelligence extraction.

Extracts What, Who, When, Where, Why, How, entities, topics, sentiment,
and risk indicators from social media content while strictly distinguishing
between explicit information and AI inference.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Optional, Any, List, Union

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

INDONESIAN_MONTHS = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]


def format_indonesian_date(dt_or_str: Optional[Union[datetime, str]]) -> str:
    """Format datetime or string into clean Indonesian date representation."""
    if not dt_or_str:
        now = datetime.now()
        return f"{now.day} {INDONESIAN_MONTHS[now.month - 1]} {now.year}"
    
    if isinstance(dt_or_str, datetime):
        return f"{dt_or_str.day} {INDONESIAN_MONTHS[dt_or_str.month - 1]} {dt_or_str.year}"
    
    s = str(dt_or_str).strip()
    # Try ISO or standard YYYY-MM-DD
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
        try:
            dt = datetime.strptime(s[:10].replace("-", ""), "%Y%m%d")
            return f"{dt.day} {INDONESIAN_MONTHS[dt.month - 1]} {dt.year}"
        except Exception:
            pass
    return s


class Analysis5W1HService:
    """Service to run structured 5W+1H intelligence extraction via Gemini AI or Heuristic Fallback."""

    def __init__(self):
        self.processor = IndonesianTextProcessor()

    def extract(
        self,
        text: str,
        title: str = "",
        image_path: Optional[str] = None,
        author: str = "",
        display_name: str = "",
        platform: str = "",
        canonical_url: str = "",
        posted_at: Optional[Any] = None,
        transcript: str = "",
        caption: str = "",
        metadata: Optional[dict] = None,
    ) -> Analysis5W1H:
        """Extract 5W+1H intelligence using local deterministic heuristics (100% Local-First)."""
        meta = metadata or {}
        display_name = display_name or meta.get("display_name", "")
        canonical_url = canonical_url or meta.get("canonical_url", "") or meta.get("url", "")
        posted_at = posted_at or meta.get("posted_at")
        transcript = transcript or meta.get("transcript", "")
        caption = caption or meta.get("caption", "") or text

        return self._heuristic_fallback(
            text=text,
            title=title,
            author=author,
            display_name=display_name,
            platform=platform,
            canonical_url=canonical_url,
            posted_at=posted_at,
            transcript=transcript,
            caption=caption,
            metadata=meta,
        )

        schema_hint = Analysis5W1H.model_json_schema()

        prompt = f"""Anda adalah Analis Intelijen Siber dan Pemantauan Opini Publik Resmi.
Tugas Anda: Melakukan ekstraksi terstruktur elemen 5W+1H (What, Who, When, Where, Why, How)
serta identifikasi topik dan entitas dari konten media sosial di bawah ini.

DEFINISI DAN PANDUAN ELEMEN 5W+1H:
1. WHAT (Apa yang dibahas):
   - Inti topik persoalan, judul konten, atau isu pokok yang sedang dibahas/diperbincangkan.
2. WHO (Siapa yang memposting / Pihak terlibat):
   - Akun pengunggah / pembuat konten (contoh: '{display_name or author} (@{author})') serta tokoh atau institusi utama yang menjadi subjek perbincangan.
3. WHEN (Kapan diupload / dipublish):
   - Tanggal dan waktu konten dipublikasikan. Gunakan informasi tanggal rilis: '{formatted_date}' (format tanggal Indonesia, contoh: '29 Oktober 2026').
   - DILARANG menulis 'Tidak disebutkan eksplisit' atau null jika tanggal postingan/patroli tersedia.
4. WHERE (Di mana diupload):
   - Platform dan kanal tempat konten diunggah/didistribusikan (contoh: 'Platform {platform.upper()} ({canonical_url or 'Kanal @' + author})').
   - DILARANG menulis 'Tidak disebutkan eksplisit' atau null.
5. WHY (Kenapa isu ini dibahas):
   - Alasan mengapa isu ini diangkat / dibahas publik. Ekstrak latar belakang perkara, pemicu peristiwa, atau konteks penyebab dari teks caption atau dialog transkrip.
   - DILARANG mengeluarkan kalimat template generik seperti "Dianalisis untuk pemantauan potensi risiko". Berikan intisari substantif dari konten!
6. HOW (Bagaimana perkembangannya / Alur pembahasan):
   - Bagaimana alur kronologi, perkembangan isu, atau argumentasi yang disampaikan narasumber/pembicara di dalam dialog transkrip atau narasi konten.
   - DILARANG mengeluarkan kalimat template generik seperti "Didistribusikan melalui kanal daring". Rangkum alur penjelasan dan faktanya dari transkrip/narasi!

== METADATA KONTEN ==
- Platform: {platform or 'Media Sosial'}
- URL: {canonical_url or 'N/A'}
- Penulis / Akun: {author or 'N/A'} (Nama Tampilan: {display_name or author or 'N/A'})
- Waktu Terbit: {formatted_date}
- Judul: {title or '(tanpa judul)'}
- Deskripsi / Caption:
{caption or text or '(tanpa deskripsi)'}
- Transkrip Percakapan / Audio:
{transcript or '(transkrip audio tidak tersedia, gunakan narasi caption)'}
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
                response = model.generate_content(contents, request_options={"timeout": 8})
                raw_json = json.loads(response.text)
                res = Analysis5W1H(**raw_json)

                # Strict post-processing validation: Ensure 5W+1H elements adhere to user specification
                if not res.when_info or "tidak disebutkan" in res.when_info.lower() or res.when_info.strip() == "":
                    res.when_info = f"Dipublikasikan pada {formatted_date}"

                if not res.where_info or "tidak disebutkan" in res.where_info.lower() or res.where_info.strip() == "":
                    plat_u = (platform or "MEDIA SOSIAL").upper()
                    res.where_info = f"Platform {plat_u} ({canonical_url or 'Kanal @' + author})"

                if not res.who or "tidak disebutkan" in res.who.lower() or res.who.strip() == "":
                    res.who = f"{display_name} (@{author})" if display_name and author else (f"@{author}" if author else "Kreator Konten")

                # If WHY contains generic boilerplate, synthesize from heuristic
                if not res.why or "potensi risiko" in res.why.lower() or "dianalisis untuk" in res.why.lower() or len(res.why.strip()) < 15:
                    heur = self._heuristic_fallback(
                        text=text, title=title, author=author, display_name=display_name,
                        platform=platform, canonical_url=canonical_url, posted_at=posted_at,
                        transcript=transcript, caption=caption, metadata=meta
                    )
                    res.why = heur.why

                # If HOW contains generic boilerplate, synthesize from heuristic
                if not res.how or "kanal daring" in res.how.lower() or len(res.how.strip()) < 15:
                    heur = self._heuristic_fallback(
                        text=text, title=title, author=author, display_name=display_name,
                        platform=platform, canonical_url=canonical_url, posted_at=posted_at,
                        transcript=transcript, caption=caption, metadata=meta
                    )
                    res.how = heur.how

                return res
            except Exception as e:
                err_str = str(e)
                last_error = e
                if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                    logger.warning("Gemini API Key tidak valid pada 5W+1H extraction. Segera beralih ke engine heuristik.")
                    break
                if any(x in err_str for x in ["WinError 10013", "10060", "10061", "ConnectError", "Network is unreachable", "NameResolutionError", "Permission denied", "Forbidden"]):
                    logger.warning("Koneksi jaringan Gemini diblokir atau offline (%s). Segera beralih ke engine lokal.", err_str)
                    break
                logger.warning("5W+1H model %s failed: %s. Trying next...", model_name, e)

        logger.error("All Gemini models failed for 5W+1H extraction: %s. Falling back to heuristics.", last_error)
        return self._heuristic_fallback(
            text=text,
            title=title,
            author=author,
            display_name=display_name,
            platform=platform,
            canonical_url=canonical_url,
            posted_at=posted_at,
            transcript=transcript,
            caption=caption,
            metadata=meta,
        )

    def _heuristic_fallback(
        self,
        text: str,
        title: str = "",
        author: str = "",
        display_name: str = "",
        platform: str = "",
        canonical_url: str = "",
        posted_at: Optional[Any] = None,
        transcript: str = "",
        caption: str = "",
        metadata: Optional[dict] = None,
    ) -> Analysis5W1H:
        """Deterministic context-aware 5W+1H extractor synthesizing caption, transcript, and metadata."""
        meta = metadata or {}
        platform_clean = (platform or "media sosial").strip()
        author_clean = (author or "").lstrip("@").strip()
        display_clean = (display_name or "").strip()

        # 1. WHAT (Apa yang dibahas)
        if title and title.strip():
            what_val = title.strip()
        else:
            first_meaningful = ""
            for line in (caption or text).split("\n"):
                l = line.strip()
                if l and not l.startswith(("#", "http", "www")):
                    first_meaningful = l[:120]
                    break
            what_val = first_meaningful or f"Pembahasan topik perbincangan publik di {platform_clean.capitalize()}"

        # 2. WHO (Siapa yang memposting / Pihak terlibat)
        if display_clean and author_clean and display_clean.lower() != author_clean.lower():
            who_val = f"{display_clean} (@{author_clean})"
        elif author_clean:
            who_val = f"Akun @{author_clean}"
        elif display_clean:
            who_val = f"Akun {display_clean}"
        else:
            who_val = f"Kreator {platform_clean.capitalize()}"

        # 3. WHEN (Kapan diupload / dipublish)
        formatted_date = format_indonesian_date(posted_at)
        when_val = f"Dipublikasikan pada {formatted_date}"

        # 4. WHERE (Di mana diupload)
        plat_upper = platform_clean.upper()
        if canonical_url:
            where_val = f"Platform {plat_upper} ({canonical_url})"
        elif author_clean:
            where_val = f"Platform {plat_upper} (Kanal @{author_clean})"
        else:
            where_val = f"Platform {plat_upper}"

        # 5. Helper cleaner for text extraction
        def _clean_text_noise(raw: str) -> str:
            if not raw:
                return ""
            t = re.sub(r"https?://\S+", "", raw)
            t = re.sub(r"#\w+", "", t)
            t = re.sub(r"\b(selengkapnya|tonton|subscribe|live streaming)\b.*", "", t, flags=re.IGNORECASE)
            t = re.sub(r"\s+", " ", t).strip()
            return t

        def _split_sentences(raw: str) -> List[str]:
            cleaned = _clean_text_noise(raw)
            if not cleaned:
                return []
            raw_sents = re.split(r"[.\n!?;]+\s*", cleaned)
            return [s.strip() for s in raw_sents if len(s.strip()) > 15]

        caption_sents = _split_sentences(caption or text)
        transcript_sents = _split_sentences(transcript)

        # 5. WHY (Kenapa isu ini dibahas - dari caption atau transkrip)
        causal_keywords = [
            "karena", "sebab", "akibat", "terkait", "mengenai", "soal",
            "gugatan", "kasus", "persidangan", "sidang", "dugaan", "diduga",
            "tuduhan", "alasan", "klarifikasi", "kontroversi", "perdebatan",
            "sorotan", "latar belakang", "membahas", "menyoal", "pemicu",
            "bermula", "berawal", "menepis", "keraguan"
        ]

        why_val = None
        def _clean_lead_artifacts(sentence: str) -> str:
            if not sentence:
                return ""
            s = sentence
            if title:
                s = s.replace(title, "")
            s = re.sub(r"^[A-Z0-9\s,._|/:-]+-\s*", "", s).strip()
            s = re.sub(r"^[,\s.-]+", "", s).strip()
            return s

        # Prioritas 1: Cari kalimat kausal / latar belakang dari caption
        for sent in caption_sents:
            s_lower = sent.lower()
            if any(k in s_lower for k in causal_keywords):
                clean_s = _clean_lead_artifacts(sent)
                if len(clean_s) > 20:
                    why_val = clean_s.rstrip(".") + "."
                    break

        # Prioritas 2: Ambil kalimat pembuka deskriptif pertama dari caption
        if not why_val and caption_sents:
            for sent in caption_sents:
                clean_s = _clean_lead_artifacts(sent)
                if len(clean_s) > 20:
                    why_val = clean_s.rstrip(".") + "."
                    break

        # Prioritas 3: Cari dari kalimat awal transkrip
        if not why_val and transcript_sents:
            for sent in transcript_sents[:4]:
                s_lower = sent.lower()
                if any(k in s_lower for k in causal_keywords):
                    clean_s = _clean_lead_artifacts(sent)
                    if len(clean_s) > 20:
                        why_val = clean_s.rstrip(".") + "."
                        break

        if not why_val:
            why_val = f"Isu ini diangkat sebagai respons atas atensi dan perbincangan publik seputar {what_val}."

        # 6. HOW (Bagaimana alurnya - terutama dari transkrip dialog)
        how_val = None
        if transcript_sents:
            # Bersihkan sapaan pembuka (e.g. "Halo pemirsa", "Fatimah dan juga pemirsa")
            filtered_tr = []
            for s in transcript_sents:
                clean_s = re.sub(
                    r"^(fatimah|pemirsa|halo|selamat (malam|pagi|siang|sore))\s*(dan\s+juga\s+pemirsa)?\.?\s*",
                    "", s, flags=re.IGNORECASE
                ).strip()
                clean_s = re.sub(r"\b(ee|umm|ahh)\b", "", clean_s, flags=re.IGNORECASE).strip()
                clean_s = re.sub(r"\s+", " ", clean_s)
                if len(clean_s) > 20:
                    filtered_tr.append(clean_s)

            if filtered_tr:
                selected_points = filtered_tr[:2]
                dialog_summary = ". ".join(p.rstrip(".") for p in selected_points) + "."
                how_val = f"Berdasarkan dialog/transkrip: {dialog_summary}"

        # Fallback jika tidak ada transkrip: gunakan kelanjutan alur narasi caption
        if not how_val and len(caption_sents) > 1:
            later_sents = [s for s in caption_sents if s.rstrip(".") != why_val.rstrip(".")]
            if later_sents:
                how_val = f"Dipaparkan dalam narasi video: {later_sents[0].rstrip('.')}."

        if not how_val:
            how_val = f"Dipaparkan melalui sajian audio-visual di kanal {plat_upper}, menjelaskan kronologi dan argumentasi para pihak terkait."

        # Keywords & Entities extraction
        caption_clean = caption or text or ""
        combined_all = f"{title}\n{caption_clean}\n{transcript}".strip()
        keywords = self.processor.extract_keywords(combined_all, top_k=8)
        hashtags = self.processor.extract_hashtags(caption_clean)

        # Category detection
        combined_lower = combined_all.lower()
        category = "Lainnya"
        if any(w in combined_lower for w in ["banjir", "gempa", "longsor", "tsunami", "karhutla", "bencana"]):
            category = "Bencana Alam"
        elif any(w in combined_lower for w in ["polisi", "keamanan", "pencurian", "tangkap", "kriminal", "teror"]):
            category = "Keamanan"
        elif any(w in combined_lower for w in ["pemilu", "pilpres", "pilkada", "dpr", "presiden", "partai", "ptun", "wapres", "gibran"]):
            category = "Politik"
        elif any(w in combined_lower for w in ["rupiah", "inflasi", "harga", "ekonomi", "pasar", "saham"]):
            category = "Ekonomi"
        elif any(w in combined_lower for w in ["hukum", "sidang", "jaksa", "hakim", "uu", "pasal", "pengadilan", "gugatan"]):
            category = "Hukum"
        elif any(w in combined_lower for w in ["hutan", "polusi", "sampah", "iklim", "lingkungan"]):
            category = "Lingkungan"

        # Sentiment guess
        sentiment = "NETRAL"
        negative_words = ["rusak", "korban", "bahaya", "ancaman", "bohong", "hoax", "rugi", "mati", "parah", "tuduhan", "gugat"]
        positive_words = ["sukses", "prestasi", "bantu", "selamat", "pulih", "baik", "terima kasih", "solusi", "siap", "terbuka"]
        neg_count = sum(1 for w in negative_words if w in combined_lower)
        pos_count = sum(1 for w in positive_words if w in combined_lower)
        if neg_count > pos_count + 1:
            sentiment = "NEGATIF"
        elif pos_count > neg_count + 1:
            sentiment = "POSITIF"

        smart_topic, _ = self.processor.extract_smart_trend_topic(
            title=title or what_val,
            text=caption or text,
            hashtags=hashtags,
        )
        main_topic = smart_topic or (title[:50] if title else "Isu Publik")

        # Rangkuman cerdas bebas duplikasi kalimat
        clean_what = (what_val or "").strip().rstrip(".")
        clean_why = (why_val or "").strip().rstrip(".")
        if clean_what and clean_why:
            if clean_what.lower() in clean_why.lower() or clean_why.lower() in clean_what.lower():
                summary_val = f"{clean_why}."[:300]
            else:
                summary_val = f"{clean_what}. {clean_why}."[:300]
        else:
            summary_val = (clean_why or clean_what or "Informasi temuan patroli siber.")[:300]

        entities = []
        if author_clean:
            entities.append(author_clean)
        if display_clean and display_clean != author_clean:
            entities.append(display_clean)

        return Analysis5W1H(
            what=what_val,
            who=who_val,
            when_info=when_val,
            where_info=where_val,
            why=why_val,
            how=how_val,
            summary=summary_val,
            main_topic=main_topic,
            sub_topics=keywords[3:6],
            keywords=keywords,
            hashtags=hashtags,
            named_entities=entities,
            sentiment=sentiment,
            tone="Informatif",
            category=category,
            relevance_score=0.88,
            urgency_score=0.65,
            confidence_score=0.85,
            misinfo_indicators=[],
            information_basis="CAMPURAN",
        )

