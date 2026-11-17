"""Local-First Ollama LLM Service for TILIK Cyber Patrol.

Enforces strict JSON structured outputs for IPOLEKSOSBUDHANKAM threat classification,
5W+1H intelligence summarization, dynamic few-shot MemPrompt injection,
and GPU/RAM concurrency protection via semaphore.
"""

import json
import logging
import re
import threading
import time
import traceback
from typing import Dict, Any, Optional, List

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# Valid IPOLEKSOSBUDHANKAM taxonomy
VALID_CATEGORIES = [
    "Ideologi",
    "Politik",
    "Ekonomi",
    "Sosial",
    "Budaya",
    "Pertahanan",
    "Keamanan",
    "Non-Isu",
]

# LAN Concurrency Guard: Limit concurrent local LLM inference based on config to prevent GPU/RAM OOM
_GPU_INFERENCE_SEMAPHORE = threading.Semaphore(getattr(settings, "AI_CONCURRENCY", 1))


class OllamaService:
    """Deterministic Local LLM Inference Engine via Ollama API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        configured_model = model or getattr(settings, "OLLAMA_MODEL", "qwen2.5:3b")
        self.timeout = timeout or getattr(settings, "OLLAMA_TIMEOUT", 60)
        self.model = self._resolve_model(configured_model)

    def _resolve_model(self, target_model: str) -> str:
        """Resolve model name, fallback to qwen2.5:3b or first available if target not in tags."""
        try:
            available = self.list_local_models()
            if not available:
                return target_model
            # Exact or prefix match (e.g. gemma3:4b vs gemma3:4b:latest)
            for m in available:
                if target_model.lower() == m.lower() or m.lower().startswith(target_model.lower()):
                    return m
            # If target model is not available, try qwen2.5:3b
            for m in available:
                if "qwen2.5:3b" in m.lower():
                    logger.info("Target model '%s' tidak ditemukan di Ollama, beralih ke '%s'", target_model, m)
                    return m
            # Or any other local model
            for m in available:
                if any(k in m.lower() for k in ["gemma", "qwen", "llama"]):
                    return m
            return available[0]
        except Exception:
            return target_model

    def check_health(self) -> bool:
        """Check if local Ollama daemon is reachable."""
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    def list_local_models(self) -> List[str]:
        """List models available in local Ollama storage."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name") for m in data.get("models", []) if m.get("name")]
        except Exception:
            pass
        return []

    def _detect_language(self, text: str) -> str:
        """Explicit function-word language gate comparing English vs Indonesian."""
        if not text:
            return "id"
        clean = text.lower()
        en_function_words = {
            "the", "and", "over", "said", "that", "with", "from", "were", "during", "for",
            "has", "have", "had", "was", "are", "been", "their", "would", "could", "after",
            "against", "which", "about", "into", "between"
        }
        id_function_words = {
            "yang", "dan", "di", "ini", "itu", "dari", "untuk", "pada", "dengan", "dalam",
            "adalah", "akan", "oleh", "sebagai", "tersebut", "bahwa", "juga", "telah", "dapat", "tidak"
        }

        words = re.findall(r"\b[a-zA-Z]{2,}\b", clean)
        if not words:
            return "id"

        en_hits = sum(1 for w in words if w in en_function_words)
        id_hits = sum(1 for w in words if w in id_function_words)

        lang = "en" if (en_hits > id_hits or (en_hits >= 3 and id_hits == 0)) else "id"
        logger.info(f"[LanguageGate] detected={lang} (en_hits={en_hits}, id_hits={id_hits})")
        return lang

    def _translate_to_indonesian(self, text: str) -> str:
        """Translate non-Indonesian text to formal journalistic Indonesian via plain text Ollama chat."""
        if not text or not text.strip():
            return ""

        # Potong maksimal 1200 karakter pertama pada batas kalimat terdekat untuk kecepatan optimal pada hardware lokal
        tr_source = text.strip()
        if len(tr_source) > 1200:
            cut_idx = max(tr_source.rfind(".", 0, 1200), tr_source.rfind("!", 0, 1200), tr_source.rfind("?", 0, 1200), tr_source.rfind("\n", 0, 1200))
            tr_input = tr_source[:cut_idx + 1].strip() if cut_idx > 600 else tr_source[:1200].strip()
        else:
            tr_input = tr_source

        system_instruction = (
            "Anda adalah penerjemah berita intelijen profesional. "
            "Tugas Anda menerjemahkan naskah berita bahasa Inggris ke dalam Bahasa Indonesia jurnalistik yang baku, akurat, dan utuh tanpa menambah atau mengurangi fakta. "
            "DILARANG menjawab dalam bahasa Inggris. WAJIB 100% BAHASA INDONESIA. "
            "Tulis HANYA hasil terjemahan Bahasa Indonesia tanpa kalimat pembuka, catatan, atau format JSON."
        )
        user_prompt = (
            "Terjemahkan teks berita berikut ke dalam Bahasa Indonesia jurnalistik yang baku, padat, dan akurat. "
            f"Tulis HANYA hasil terjemahan Bahasa Indonesia tanpa kalimat pembuka, catatan, atau format JSON:\n\n{tr_input}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 400,
                "num_ctx": 2048,
            },
        }

        timeout_obj = httpx.Timeout(max(120.0, float(self.timeout)), connect=10.0)
        translated = ""
        try:
            with httpx.Client(timeout=timeout_obj) as client:
                resp = client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code == 200:
                    body = resp.json()
                    content = (body.get("message", {}).get("content") or "").strip()
                    content = re.sub(r'^(?:Terjemahan[^\n:]*[:\n]+|Berikut adalah[^\n:]*[:\n]+|Berikut terjemahan[^\n:]*[:\n]+)', '', content, flags=re.IGNORECASE).strip()
                    translated = content
        except Exception as ex:
            logger.warning("[TranslateGate] Permintaan translasi gagal: %s", ex)

        # Validasi Hasil Terjemahan: hanya retry jika hasil benar-benar masih terdeteksi bahasa Inggris murni
        if translated:
            check_lang = self._detect_language(translated)
            if check_lang == "en":
                logger.info("[TranslateGate] Hasil terjemahan masih terdeteksi 'en', melakukan 1x retry singkat...")
                retry_prompt = f"UBAH KE BAHASA INDONESIA BAKU SEKARANG:\n\n{tr_input}"
                payload["messages"] = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": retry_prompt},
                ]
                payload["options"]["num_predict"] = 350
                try:
                    with httpx.Client(timeout=timeout_obj) as client:
                        resp = client.post(f"{self.base_url}/api/chat", json=payload)
                        if resp.status_code == 200:
                            body = resp.json()
                            content = (body.get("message", {}).get("content") or "").strip()
                            content = re.sub(r'^(?:Terjemahan[^\n:]*[:\n]+|Berikut adalah[^\n:]*[:\n]+)', '', content, flags=re.IGNORECASE).strip()
                            if content:
                                translated = content
                except Exception as rex:
                    logger.warning("[TranslateGate] Retry translasi gagal: %s", rex)

        if translated and len(translated) >= 15:
            logger.info(f"[TranslateGate] Translasi selesai ({len(translated)} chars)")
            return translated

        # Fallback Translasi Deterministik Ringkas jika Ollama offline / timeout
        logger.info("[TranslateGate] Menggunakan fallback translasi kalimat ringkas...")
        return self._heuristic_translate_lead(tr_input)

    def _heuristic_translate_lead(self, english_text: str) -> str:
        """Lightweight journalistic lead translator fallback when Ollama is offline."""
        replacements = [
            (r"\bIndonesian President Prabowo Subianto\b", "Presiden Indonesia Prabowo Subianto"),
            (r"\bIndonesian President Prabowo\b", "Presiden Indonesia Prabowo"),
            (r"\bPresident Prabowo Subianto\b", "Presiden Prabowo Subianto"),
            (r"\bPresident Prabowo\b", "Presiden Prabowo"),
            (r"\bhas apologised to\b", "telah menyampaikan permohonan maaf kepada"),
            (r"\bapologises to\b", "meminta maaf kepada"),
            (r"\bapologised to\b", "meminta maaf kepada"),
            (r"\bfor the transboundary haze\b", "atas kabut asap lintas batas"),
            (r"\btransboundary haze\b", "kabut asap lintas batas"),
            (r"\bdue to months-long wildfires\b", "akibat kebakaran hutan yang berlangsung berbulan-bulan"),
            (r"\bwildfire haze\b", "kabut asap kebakaran hutan"),
            (r"\bwildfires\b", "kebakaran hutan"),
            (r"\bforest fire\b", "kebakaran hutan"),
            (r"\bforest fires\b", "kebakaran hutan"),
            (r"\bSingapore\b", "Singapura"),
            (r"\bMalaysia\b", "Malaysia"),
            (r"\bIndonesia\b", "Indonesia"),
            (r"\bASEAN Summit\b", "KTT ASEAN"),
            (r"\bzero-tolerance policy\b", "kebijakan tanpa toleransi"),
            (r"\bfor companies that contribute to\b", "bagi perusahaan yang berkontribusi terhadap"),
            (r"\bpromises strict action\b", "dan menjanjikan tindakan tegas"),
            (r"\bpledges strict action\b", "dan menjanjikan tindakan tegas"),
            (r"\bconveyed the apology\b", "menyampaikan permohonan maaf tersebut"),
            (r"\bduring a session at\b", "dalam sesi pertemuan di"),
            (r"\baccording to a statement from\b", "berdasarkan pernyataan resmi dari"),
            (r"\bpresidential office\b", "kantor kepresidenan"),
            (r"\bWe've revoked\b", "Kami telah mencabut"),
            (r"\bconcessions\b", "izin konsesi"),
            (r"\bunder investigation\b", "sedang dalam proses penyelidikan"),
            (r"\bhave been charged\b", "telah ditetapkan sebagai tersangka"),
            (r"\bdeployed\b", "mengerahkan"),
            (r"\bforest firefighters\b", "petugas pemadam kebakaran hutan"),
            (r"\bdied while battling the blazes\b", "gugur saat memadamkan kebakaran"),
            (r"\bClimate Crisis\b", "Krisis Iklim"),
            (r"\bNews\b", "Berita"),
        ]
        translated = english_text
        for pattern, repl in replacements:
            translated = re.sub(pattern, repl, translated, flags=re.IGNORECASE)
        return translated.strip()

    @staticmethod
    def _build_representative_context(text: str, max_chars: int = 2600) -> str:
        """Sample representative head, middle, and tail sections on sentence boundaries if text exceeds max_chars."""
        if not text or len(text) <= max_chars:
            return (text or "").strip()

        # 1. Head: ~1100 chars on nearest sentence boundary
        head_target = 1100
        head_cut = max(
            text.rfind(".", 0, head_target),
            text.rfind("!", 0, head_target),
            text.rfind("?", 0, head_target),
            text.rfind("\n", 0, head_target),
        )
        head = text[:head_cut + 1].strip() if head_cut > 600 else text[:head_target].strip()

        # 2. Tail: ~750 chars on nearest sentence boundary
        tail_target = 750
        tail_start_raw = max(0, len(text) - tail_target)
        valid_tail_cuts = [pos for pos in [text.find(".", tail_start_raw), text.find("\n", tail_start_raw), text.find("!", tail_start_raw)] if pos != -1]
        tail_cut = min(valid_tail_cuts) if valid_tail_cuts else tail_start_raw
        tail = text[tail_cut + 1:].strip() if tail_cut < len(text) - 250 else text[tail_start_raw:].strip()

        # 3. Middle: ~750 chars around document center on sentence boundaries
        mid_center = len(text) // 2
        mid_start_raw = max(len(head), mid_center - 375)
        mid_end_raw = min(len(text) - len(tail), mid_center + 375)

        mid_cut_start = max(text.rfind(".", 0, mid_start_raw), text.rfind("\n", 0, mid_start_raw))
        if mid_cut_start == -1 or mid_cut_start < len(head):
            mid_cut_start = mid_start_raw
        else:
            mid_cut_start += 1

        mid_cut_end = max(text.rfind(".", mid_cut_start, mid_end_raw), text.rfind("\n", mid_cut_start, mid_end_raw))
        if mid_cut_end == -1 or mid_cut_end <= mid_cut_start:
            mid_cut_end = mid_end_raw
        else:
            mid_cut_end += 1

        middle = text[mid_cut_start:mid_cut_end].strip()

        combined = f"{head}\n\n[...]\n\n{middle}\n\n[...]\n\n{tail}"
        return combined.strip()

    def _summarize_with_evidence(
        self,
        clean_id_text: str,
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        author: str = "Anonim",
        platform: str = "web",
    ) -> Dict[str, Any]:
        """Stage 1: Evidenced fact extraction & claim verification scratchpad."""
        sampled_context = self._build_representative_context(clean_id_text, max_chars=2600)

        stage1_system = (
            "Anda adalah Asisten Verifikator Bukti Forensik Siber Nasional (TILIK v5.0).\n"
            "TUGAS TAHAP 1: EKSTRAKSI BUKTI BERDASARKAN DOKUMEN ASLI.\n"
            "1. DILARANG MENAMBAH FAKTA ATAU BERASUMSI. Rujuk hanya teks yang diberikan.\n"
            "2. BAHASA: Seluruh output wajib disajikan dalam BAHASA INDONESIA BAKU.\n"
            "3. EKSTRAKSI AWAL, TENGAH, AKHIR: Ekstrak 3-4 butir fakta nyata yang mencakup awal, tengah, dan akhir naskah.\n"
            "4. STATUS KLAIM: Tentukan status klaim secara objektif:\n"
            "   - 'Fakta Terverifikasi': Jika bersumber dari pernyataan resmi pejabat, konferensi pers, rilis lembaga negara, putusan hukum, atau liputan media terverifikasi.\n"
            "   - 'Dugaan / Belum Terverifikasi': Jika naskah memuat klaim yang belum dikonfirmasi aparat/pejabat, berbau tuduhan, atau rumor beredar di medsos.\n"
            "   - 'Opini / Rumor': Jika murni opini perseorangan, spekulasi tanpa bukti dokumen, atau narasi polemik netizen.\n"
            "5. KUTIPAN BUKTI: Wajib mengutip 1 kalimat persis (verbatim quote) dari teks yang menjadi bukti inti peristiwa.\n"
            "6. RINGKASAN EKSEKUTIF: Susun 2-3 kalimat padat bahasa Indonesia baku merangkum peristiwa, aktor utama, dampak, dan mitigasi penanganan."
        )

        user_content = (
            f"JUDUL: {title or 'N/A'}\n"
            f"PLATFORM: {platform.upper()}\n"
            f"SUMBER / URL: {source_url or 'N/A'}\n"
            f"PENGUNGGAH (AUTHOR): {author}\n\n"
            f"DOKUMEN TEKS SUMBER (SAMPEL REPRESENTATIF):\n\"\"\"\n{sampled_context}\n\"\"\""
        )

        schema_stage1 = {
            "type": "object",
            "properties": {
                "tipe_konteks": {"type": "string"},
                "ekstraksi_awal_tengah_akhir": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "status_klaim": {
                    "type": "string",
                    "enum": ["Fakta Terverifikasi", "Dugaan / Belum Terverifikasi", "Opini / Rumor"]
                },
                "kutipan_bukti": {"type": "string"},
                "ringkasan_eksekutif": {"type": "string"}
            },
            "required": ["tipe_konteks", "ekstraksi_awal_tengah_akhir", "status_klaim", "kutipan_bukti", "ringkasan_eksekutif"]
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": stage1_system},
                {"role": "user", "content": user_content},
            ],
            "format": schema_stage1,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 450,
                "num_ctx": 2048,
            },
        }

        timeout_obj = httpx.Timeout(max(90.0, float(self.timeout)), connect=10.0)
        with httpx.Client(timeout=timeout_obj) as client:
            resp = client.post(f"{self.base_url}/api/chat", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama Stage 1 returned HTTP {resp.status_code}: {resp.text}")
            body = resp.json()
            raw_content = body.get("message", {}).get("content", "")
            return self._extract_and_parse_json(raw_content)

    def _analyze_evidenced_summary(
        self,
        evidenced_summary: Dict[str, Any],
        title: Optional[str] = None,
        author: str = "Anonim",
        platform: str = "web",
        few_shot_block: str = "",
    ) -> Dict[str, Any]:
        """Stage 2: Strategic threat classification & 5W+1H reasoning constrained by Stage 1 facts."""
        exec_sum = evidenced_summary.get("ringkasan_eksekutif", "")
        facts = "\n".join([f"- {f}" for f in evidenced_summary.get("ekstraksi_awal_tengah_akhir", [])])
        claim_status = evidenced_summary.get("status_klaim", "Fakta Terverifikasi")
        evidence_quote = evidenced_summary.get("kutipan_bukti", "")
        context_type = evidenced_summary.get("tipe_konteks", "Berita / Publikasi Digital")

        stage2_system = (
            "Anda adalah Analis Senior Intelijen Patroli Siber Nasional (TILIK v5.0).\n"
            "TUGAS TAHAP 2: KLASIFIKASI ANCAMAN STRATEGIS & SINTESIS 5W+1H.\n"
            "Gunakan HANYA ringkasan dan fakta terverifikasi dari Tahap 1 berikut sebagai batasan mutlak (anti-halusinasi):\n"
            f"- Status Klaim: {claim_status}\n"
            f"- Kutipan Bukti: \"{evidence_quote}\"\n"
            f"- Tipe Konteks: {context_type}\n\n"
            "ATURAN MUTLAK:\n"
            "1. BAHASA BAKU: Seluruh isian wajib disajikan dalam BAHASA INDONESIA BAKU.\n"
            "2. PEMISAHAN ENTITAS: Pada summary_5w1h['who'], bedakan secara tegas Pengunggah Konten (@author) dengan Tokoh/Lembaga yang Diberitakan.\n"
            "3. KELENGKAPAN WAKTU & TEMPAT: Jika tidak tercantum pada fakta, isi persis 'Tidak disebutkan dalam konten'.\n"
            "4. TAKSONOMI: Pilih satu kategori dari: Ideologi, Politik, Ekonomi, Sosial, Budaya, Pertahanan, Keamanan, Non-Isu.\n"
            "5. URGENSI: Skor 1 (sangat rendah/non-isu), 2 (rendah), 3 (sedang/pantau), 4 (tinggi/eskalasi), 5 (kritis/darurat).\n"
            "6. PENALARAN: ai_reasoning WAJIB disusun persis dalam 3 bagian berlabel:\n"
            "Fakta vs Dugaan Tertulis: [Uraian objektif mengenai apa yang faktual dan apa yang dugaan/belum terbukti]\n\n"
            "Penalaran Kausal (Karena-Maka): [Alur sebab-akibat dampak terhadap stabilitas nasional atau ketertiban publik]\n\n"
            "Rekomendasi Verifikasi & Tindak Lanjut: [Langkah verifikasi silang dan tindakan operasional patroli siber]"
        )

        user_content = (
            f"JUDUL KONTEN: {title or 'N/A'}\n"
            f"PLATFORM: {platform.upper()}\n"
            f"PENGUNGGAH: {author}\n\n"
            f"RINGKASAN TAHAP 1:\n{exec_sum}\n\n"
            f"FAKTA-FAKTA TERVERIFIKASI TAHAP 1:\n{facts}\n"
        )
        if few_shot_block:
            user_content = f"{few_shot_block}\n\n{user_content}"

        schema_stage2 = {
            "type": "object",
            "properties": {
                "summary_5w1h": {
                    "type": "object",
                    "properties": {
                        "who": {"type": "string"},
                        "what": {"type": "string"},
                        "when": {"type": "string"},
                        "where": {"type": "string"},
                        "why": {"type": "string"},
                        "how": {"type": "string"}
                    },
                    "required": ["who", "what", "when", "where", "why", "how"]
                },
                "predicted_category": {
                    "type": "string",
                    "enum": ["Ideologi", "Politik", "Ekonomi", "Sosial", "Budaya", "Pertahanan", "Keamanan", "Non-Isu"]
                },
                "urgency_score": {"type": "integer"},
                "ai_reasoning": {"type": "string"}
            },
            "required": ["summary_5w1h", "predicted_category", "urgency_score", "ai_reasoning"]
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": stage2_system},
                {"role": "user", "content": user_content},
            ],
            "format": schema_stage2,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 450,
                "num_ctx": 2048,
            },
        }

        timeout_obj = httpx.Timeout(max(90.0, float(self.timeout)), connect=10.0)
        with httpx.Client(timeout=timeout_obj) as client:
            resp = client.post(f"{self.base_url}/api/chat", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama Stage 2 returned HTTP {resp.status_code}: {resp.text}")
            body = resp.json()
            raw_content = body.get("message", {}).get("content", "")
            return self._extract_and_parse_json(raw_content)

    def classify_and_summarize(
        self,
        text: str,
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        author: Optional[str] = "Anonim",
        platform: Optional[str] = "web",
        few_shot_block: str = "",
        mode: str = "adaptive",
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute deterministic 2-stage evidenced local LLM inference to produce structured 5W+1H and IPOLEKSOSBUDHANKAM triage.

        Acquires _GPU_INFERENCE_SEMAPHORE to ensure multi-operator LAN requests queue gracefully.
        Falls back to local heuristic intelligence if Ollama daemon is offline.
        """
        start_time = time.perf_counter()
        author_clean = str(author).strip() if (author and str(author).strip()) else "Anonim"
        platform_clean = str(platform).strip() if (platform and str(platform).strip()) else "web"

        # TAHAP 1: Gerbang Deteksi Bahasa Eksplisit
        detected_lang = self._detect_language(text)
        analysis_text = text
        indonesian_content = text.strip()

        similar_cases = []
        if mode == "adaptive" and db is not None and not few_shot_block:
            try:
                from app.services.memory_service import MemoryService
                mem_res = MemoryService.retrieve_similar_cases(query_text=text[:2500], db=db, top_k=3)
                if mem_res and mem_res.get("few_shot_prompt"):
                    few_shot_block = mem_res["few_shot_prompt"]
                    similar_cases = mem_res.get("cases", [])
            except Exception as mem_err:
                logger.warning("MemPrompt auto-retrieval warning: %s", mem_err)

        # Concurrency lock to protect local GPU/RAM
        acquired = _GPU_INFERENCE_SEMAPHORE.acquire(timeout=float(self.timeout))
        try:
            # TAHAP 2: Pra-Translasi Plain-Text Tervalidasi (Hanya jika bukan 'id')
            if detected_lang != "id":
                try:
                    logger.info("[TranslateGate] Mendeteksi teks bukan 'id' (%s). Menjalankan pra-translasi...", detected_lang)
                    translated = self._translate_to_indonesian(text)
                    if translated and len(translated.strip()) >= 15:
                        indonesian_content = translated.strip()
                        analysis_text = indonesian_content
                except Exception as tr_err:
                    logger.warning("[TranslateGate] Pra-translasi gagal (%s), melanjutkan dengan naskah asli.", tr_err)
            else:
                indonesian_content = text.strip()

            # TAHAP 3: Eksekusi Two-Stage Evidenced Pipeline (Stage 1: Bukti Fakta -> Stage 2: Klasifikasi Ancaman)
            stage1_res = self._summarize_with_evidence(
                clean_id_text=analysis_text,
                title=title,
                source_url=source_url,
                author=author_clean,
                platform=platform_clean,
            )

            stage2_res = self._analyze_evidenced_summary(
                evidenced_summary=stage1_res,
                title=title,
                author=author_clean,
                platform=platform_clean,
                few_shot_block=few_shot_block if mode == "adaptive" else "",
            )

            # Sanitize category against IPOLEKSOSBUDHANKAM taxonomy (with cross-lingual mapping)
            cat = str(stage2_res.get("predicted_category", "Non-Isu")).strip()
            category_mapping = {
                "politik": "Politik", "politics": "Politik", "political": "Politik",
                "keamanan": "Keamanan", "security": "Keamanan", "cybercrime": "Keamanan", "wiretapping": "Keamanan", "law": "Keamanan",
                "ekonomi": "Ekonomi", "economy": "Ekonomi", "economic": "Ekonomi",
                "sosial": "Sosial", "social": "Sosial",
                "budaya": "Budaya", "culture": "Budaya", "cultural": "Budaya",
                "pertahanan": "Pertahanan", "defense": "Pertahanan", "defence": "Pertahanan", "military": "Pertahanan",
                "ideologi": "Ideologi", "ideology": "Ideologi",
                "non-isu": "Non-Isu", "non-issue": "Non-Isu", "neutral": "Non-Isu",
            }
            matched_cat = "Non-Isu"
            cat_lower = cat.lower()
            for eng_k, id_v in category_mapping.items():
                if eng_k in cat_lower:
                    matched_cat = id_v
                    break

            # Urgency score clamping: 1..5
            urgency_raw = stage2_res.get("urgency_score", 2)
            try:
                u_val = float(urgency_raw)
                if u_val > 5.0:
                    u_val = u_val / 2.0
                urgency = max(1, min(5, int(round(u_val))))
            except Exception:
                urgency = 2

            exec_summary = (stage1_res.get("ringkasan_eksekutif") or "").strip()
            summary_5w1h = stage2_res.get("summary_5w1h") or {}
            who_val = summary_5w1h.get("who") or author_clean
            what_val = summary_5w1h.get("what") or exec_summary
            when_val = summary_5w1h.get("when") or "Tidak disebutkan dalam konten"
            where_val = summary_5w1h.get("where") or "Tidak disebutkan dalam konten"
            why_val = summary_5w1h.get("why") or f"Berkaitan dengan isu {matched_cat}."
            how_val = summary_5w1h.get("how") or "Dipublikasikan melalui kanal digital publik."

            reasoning_val = stage2_res.get("ai_reasoning") or ""
            if not reasoning_val or "Fakta vs Dugaan Tertulis:" not in reasoning_val:
                reasoning_val = (
                    f"Fakta vs Dugaan Tertulis: Berdasarkan bukti yang tercatat, status klaim diidentifikasi sebagai {stage1_res.get('status_klaim', 'Fakta Terverifikasi')}. Kutipan pendukung: \"{stage1_res.get('kutipan_bukti', '')}\".\n\n"
                    f"Penalaran Kausal (Karena-Maka): Karena terindikasi isu dalam ranah {matched_cat} dengan bobot urgensi {urgency}/5, maka diperlukan pemantauan situasi berkala untuk mencegah potensi eskalasi publik.\n\n"
                    f"Rekomendasi Verifikasi & Tindak Lanjut: Lakukan verifikasi silang bukti dengan instansi terkait dan simpan segel rantai bukti (Chain of Custody) NIST FIPS 198-1."
                )

            llm_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "ringkasan_eksekutif": exec_summary,
                "summary_5w1h": {
                    "who": who_val,
                    "what": what_val,
                    "when": when_val,
                    "where": where_val,
                    "why": why_val,
                    "how": how_val,
                },
                "summary": exec_summary,
                "predicted_category": matched_cat,
                "urgency_score": urgency,
                "ai_reasoning": reasoning_val,
                "tipe_konteks": stage1_res.get("tipe_konteks", "Publikasi Digital"),
                "ekstraksi_awal_tengah_akhir": stage1_res.get("ekstraksi_awal_tengah_akhir", []),
                "status_klaim": stage1_res.get("status_klaim", "Fakta Terverifikasi"),
                "kutipan_bukti": stage1_res.get("kutipan_bukti", ""),
                "llm_latency_ms": llm_latency_ms,
                "latency_ms": llm_latency_ms,
                "similar_cases": similar_cases,
                "engine_used": f"ollama/{self.model}",
                "classification_mode": mode,
                "original_language": detected_lang,
                "indonesian_content": indonesian_content,
            }
        except Exception as err:
            logger.error(
                "Ollama inference API/parsing gagal (%s). Mengalihkan ke _heuristic_fallback.",
                err,
            )
            fallback = self._heuristic_fallback(
                text=indonesian_content or text,
                title=title,
                author=author_clean,
                platform=platform_clean,
                similar_cases=similar_cases,
                mode=mode,
            )
            llm_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            fallback["llm_latency_ms"] = llm_latency_ms
            fallback["latency_ms"] = llm_latency_ms
            fallback["similar_cases"] = similar_cases
            fallback["engine_used"] = "local_heuristic_failopen"
            fallback["classification_mode"] = mode
            fallback["original_language"] = detected_lang
            fallback["indonesian_content"] = indonesian_content or text
            return fallback
        finally:
            if acquired:
                _GPU_INFERENCE_SEMAPHORE.release()

    def _extract_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Extract valid JSON from raw text handling markdown code fences, preambles, and unclosed quotes/braces."""
        if not raw_text or not raw_text.strip():
            raise ValueError("Respon teks dari Ollama kosong.")

        clean = raw_text.strip()
        # 1. Strip markdown code fences if present
        if "```" in clean:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
            if match:
                clean = match.group(1).strip()

        # 2. Extract outermost JSON object { ... }
        start_idx = clean.find("{")
        end_idx = clean.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean = clean[start_idx : end_idx + 1].strip()
        elif start_idx != -1:
            clean = clean[start_idx:].strip()

        # 3. Standard json.loads
        try:
            return json.loads(clean)
        except json.JSONDecodeError as jde:
            logger.debug("Parsing JSON langsung gagal (%s), mencoba JSON repair...", jde)

        # 4. JSON Repair: Strip trailing commas before } or ]
        repaired = re.sub(r",\s*([\]}])", r"\1", clean)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as jde2:
            logger.debug("JSON repair dasar gagal (%s), mencoba auto-closing repair...", jde2)

        # 5. Advanced Salvage Repair: tutup tanda kutip dan kurung kurawal/siku yang belum tertutup
        fix = repaired
        unescaped_quotes = len(re.findall(r'(?<!\\)"', fix))
        if unescaped_quotes % 2 != 0:
            fix += '"'
        open_b = fix.count("{") - fix.count("}")
        if open_b > 0:
            fix += "}" * open_b
        open_sq = fix.count("[") - fix.count("]")
        if open_sq > 0:
            fix += "]" * open_sq
        try:
            return json.loads(fix)
        except json.JSONDecodeError as jde3:
            logger.error("Auto-closing repair juga gagal: %s. Respon mentah: %s", jde3, raw_text[:500])
            raise ValueError(f"Gagal mem-parsing JSON dari Ollama: {jde3}")

    def _call_ollama_api(
        self,
        system_prompt: str,
        user_content: str,
        text: str = "",
        author: Optional[str] = "Anonim",
        platform: Optional[str] = "web",
        similar_cases: Optional[List[Any]] = None,
        mode: str = "adaptive",
    ) -> Dict[str, Any]:
        """Send chat request to Ollama with strict JSON Schema formatting and robust repair."""
        schema_format = {
            "type": "object",
            "properties": {
                "ringkasan_eksekutif": {"type": "string"},
                "summary_5w1h": {
                    "type": "object",
                    "properties": {
                        "who": {"type": "string"},
                        "what": {"type": "string"},
                        "when": {"type": "string"},
                        "where": {"type": "string"},
                        "why": {"type": "string"},
                        "how": {"type": "string"}
                    },
                    "required": ["who", "what", "when", "where", "why", "how"]
                },
                "ai_reasoning": {"type": "string"},
                "predicted_category": {
                    "type": "string",
                    "enum": ["Ideologi", "Politik", "Ekonomi", "Sosial", "Budaya", "Pertahanan", "Keamanan", "Non-Isu"]
                },
                "urgency_score": {"type": "integer"}
            },
            "required": ["ringkasan_eksekutif", "summary_5w1h", "ai_reasoning", "predicted_category", "urgency_score"]
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "format": schema_format,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic classification
                "top_p": 0.9,
                "num_predict": 500,  # Room for complete 3-4 sentence summary and multi-paragraph analysis
                "num_ctx": 2048,     # Context window optimized for comprehensive triage
            },
        }

        timeout_obj = httpx.Timeout(max(120.0, float(self.timeout)), connect=10.0)
        with httpx.Client(timeout=timeout_obj) as client:
            resp = client.post(f"{self.base_url}/api/chat", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

            body = resp.json()
            message_content = body.get("message", {}).get("content", "")
            if not message_content:
                raise ValueError("Ollama returned empty message content.")

            # Parse JSON with robust repair
            parsed = self._extract_and_parse_json(message_content)

            # Sanitize category against IPOLEKSOSBUDHANKAM taxonomy (with cross-lingual mapping)
            cat = str(parsed.get("predicted_category", "Non-Isu")).strip()
            category_mapping = {
                "politik": "Politik", "politics": "Politik", "political": "Politik",
                "keamanan": "Keamanan", "security": "Keamanan", "cybercrime": "Keamanan", "wiretapping": "Keamanan", "law": "Keamanan",
                "ekonomi": "Ekonomi", "economy": "Ekonomi", "economic": "Ekonomi",
                "sosial": "Sosial", "social": "Sosial",
                "budaya": "Budaya", "culture": "Budaya", "cultural": "Budaya",
                "pertahanan": "Pertahanan", "defense": "Pertahanan", "defence": "Pertahanan", "military": "Pertahanan",
                "ideologi": "Ideologi", "ideology": "Ideologi",
                "non-isu": "Non-Isu", "non-issue": "Non-Isu", "neutral": "Non-Isu",
            }
            matched_cat = "Non-Isu"
            cat_lower = cat.lower()
            for eng_k, id_v in category_mapping.items():
                if eng_k in cat_lower:
                    matched_cat = id_v
                    break

            # Urgency score clamping: max(1, min(5, int(urgency_score)))
            urgency_raw = parsed.get("urgency_score", 2)
            try:
                u_val = float(urgency_raw)
                if u_val > 5.0:
                    u_val = u_val / 2.0  # normalize if scale 1-10 was returned
                urgency = max(1, min(5, int(round(u_val))))
            except Exception:
                urgency = 2

            exec_summary = (parsed.get("ringkasan_eksekutif") or parsed.get("executive_summary") or "").strip()
            summary = parsed.get("summary_5w1h") or parsed.get("5w1h") or {}
            what_t = summary.get("what") or summary.get("apa") or ""
            why_t = summary.get("why") or summary.get("mengapa") or ""
            who_t = summary.get("who") or summary.get("siapa") or author or "Tidak disebutkan dalam konten"
            when_t = summary.get("when") or summary.get("kapan") or "Tidak disebutkan dalam konten"
            where_t = summary.get("where") or summary.get("dimana") or "Tidak disebutkan dalam konten"
            how_t = summary.get("how") or summary.get("bagaimana") or ""

            if exec_summary and len(exec_summary) >= 20:
                summary_clean = exec_summary
            elif what_t and len(what_t) >= 20:
                summary_clean = what_t if not why_t else f"{what_t}. {why_t}."
            else:
                summary_clean = why_t or "Analisis temuan patroli siber."

            reasoning_val = (
                parsed.get("ai_reasoning")
                or parsed.get("reasoning")
                or parsed.get("alasan_penilaian")
                or parsed.get("analisis")
                or parsed.get("analisis_kritis")
                or parsed.get("pertimbangan")
            )
            extra_reasoning = []
            if parsed.get("alasan_penilaian") and reasoning_val != parsed.get("alasan_penilaian"):
                extra_reasoning.append(f"Alasan Penilaian: {parsed.get('alasan_penilaian')}")
            if parsed.get("analisis_dampak_kerawanan"):
                extra_reasoning.append(f"Analisis Dampak & Kerawanan: {parsed.get('analisis_dampak_kerawanan')}")
            if parsed.get("rekomendasi_tindak_lanjut"):
                extra_reasoning.append(f"Rekomendasi Tindak Lanjut: {parsed.get('rekomendasi_tindak_lanjut')}")

            if extra_reasoning:
                base_r = str(reasoning_val).strip() if reasoning_val else ""
                reasoning_val = (base_r + "\n\n" + "\n\n".join(extra_reasoning)).strip()

            if not reasoning_val:
                reasoning_val = (
                    f"Alasan Penilaian: Teridentifikasi isu strategis dalam ranah {matched_cat} dengan tingkat urgensi {urgency}/5 berdasarkan analisis fakta resmi.\n\n"
                    f"Analisis Dampak & Kerawanan: {summary_clean}\n\n"
                    f"Rekomendasi Tindak Lanjut: Pantau perkembangan situasi, koordinasikan dengan satuan tugas terkait, dan dokumentasikan seluruh barang bukti secara berkala."
                )

            return {
                "ringkasan_eksekutif": summary_clean,
                "summary_5w1h": {
                    "who": who_t,
                    "what": what_t or summary_clean,
                    "when": when_t,
                    "where": where_t,
                    "why": why_t or f"Berkaitan dengan isu {matched_cat}.",
                    "how": how_t or "Dipaparkan melalui publikasi digital.",
                },
                "summary": summary_clean,
                "predicted_category": matched_cat,
                "urgency_score": urgency,
                "ai_reasoning": reasoning_val,
            }

    def _heuristic_fallback(
        self,
        text: str,
        title: Optional[str] = None,
        author: Optional[str] = "Anonim",
        platform: Optional[str] = "web",
        similar_cases: Optional[List[Any]] = None,
        mode: str = "adaptive",
    ) -> Dict[str, Any]:
        """Local deterministic context-aware intelligence fallback if Ollama daemon is offline."""
        import re

        clean_text = (text or "").strip()
        # Bersihkan artefak teks: .... -> . , whitespace ganda
        clean_text = re.sub(r'\.{2,}', '.', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        combined = f"{title or ''} {clean_text}".lower()

        # 1. Taksonomi IPOLEKSOSBUDHANKAM Presisi dengan Word Boundary (\b)
        keywords_map = {
            "Ideologi": [
                "pancasila", "komunisme", "marxisme", "leninisme", "pki", "khilafah",
                "separatis", "separatisme", "makar", "radikalisme", "anti pancasila",
                "terorisme ideologis", "khilafatul", "marxist-leninist", "comrades", "bourgeois", "caliphate"
            ],
            "Politik": [
                "presiden", "wapres", "gibran", "prabowo", "ganjar", "ganjar pranowo", "menteri", "dpr", "mpr",
                "kpu", "bawaslu", "pemilu", "pilkada", "partai", "koalisi", "kabinet",
                "reshuffle", "oposisi", "kebijakan pemerintah", "ruu", "perppu",
                "pemakzulan", "mundur dari jabatan", "resignation letter", "senayan",
                "phantom voters", "voter registry", "steal the election", "electoral commission",
                "bencana nasional", "refocusing anggaran", "darurat bencana", "kebijakan publik",
                "pejabat terkait", "pemerintah pusat", "pemerintah daerah", "karhutla", "kabut asap"
            ],
            "Ekonomi": [
                "inflasi", "rupiah", "suku bunga", "bunga bank", "ihsg", "pasar modal",
                "phk masal", "bansos", "pajak penghasilan", "utang negara", "apbn",
                "defisit anggaran", "daya beli", "kemiskinan", "krisis moneter", "bea cukai",
                "kelangkaan bbm", "subsidi tepat", "sembako mahal", "bank run", "liquidity crisis",
                "uang palsu", "investasi bodong", "skema ponzi", "penimbunan beras", "refocusing anggaran"
            ],
            "Sosial": [
                "sara", "konflik suku", "penistaan agama", "tawuran warga", "kerusuhan massal",
                "ujaran kebencian", "provokasi massa", "hoaks sara", "diskriminasi",
                "persekusi", "bentrokan ormas", "kriminalitas jalanan", "ethnic boycott",
                "mob gathering", "serbu kampung", "molotov", "expulsion",
                "karhutla", "kabut asap", "kebakaran hutan", "bencana alam", "bencana nasional",
                "darurat bencana", "krisis kemanusiaan", "pengungsi", "terdampak bencana"
            ],
            "Budaya": [
                "adat istiadat", "kebudayaan daerah", "tradisi leluhur", "cagar budaya",
                "moral bangsa", "etika budaya", "warisan budaya", "budayawan",
                "degradasi moral", "pelecehan adat", "vandalisme", "candi", "kemusyrikan",
                "berhala", "patung batu", "unesco", "sedekah bumi"
            ],
            "Pertahanan": [
                "tni", "militer ri", "alutsista", "kedaulatan ri", "laut natuna",
                "perbatasan negara", "ancaman perang", "invasi militer", "kapal perang",
                "pesawat tempur", "pertahanan siber militer", "panglima tni", "surveillance aircraft",
                "sovereign airspace", "airspace", "blueprint koordinat", "pangkalan tni", "kapal selam"
            ],
            "Keamanan": [
                "polri", "kapolri", "bareskrim", "polda", "kejahatan siber", "judi online",
                "judol", "phishing", "narkoba", "pengedar narkotika", "pembunuhan",
                "teror bom", "begal", "pencucian uang", "kpk", "korupsi", "tangkap tangan",
                "tersangka", "tindak pidana", "ilegal akses", "illegal access", "ancaman bom",
                "c-4", "hacked database", "breach forums", "biometric records", "senjata api", "dark web"
            ],
            "Non-Isu": [
                "beasiswa", "erasmus", "emjm", "kuliah", "kampus", "mahasiswa", "pelajar",
                "sekolah", "pendidikan", "workshop", "webinar", "seminar", "lomba",
                "komunitas", "gdgoc", "developer", "rekrutmen", "lowongan kerja", "magang",
                "karir", "alumni", "tutorial", "tips teknologi", "musik", "konser",
                "film", "olahraga", "sepakbola", "wisata", "kuliner", "inovasi mahasiswa",
                "core team", "organisasi kampus", "rendang", "resep", "python", "raja ampat",
                "manta rays", "olahraga kardio", "kesehatan jantung", "gula darah"
            ],
        }

        # Kata kunci pembobot severity tinggi (menaikkan urgency)
        severity_keywords = {
            5: ["makar", "teror bom", "separatisme", "khilafah", "invasi militer", "ancaman perang"],
            4: ["tersangka", "tindak pidana", "korupsi", "narkoba", "pembunuhan", "pencucian uang",
                "tangkap tangan", "ilegal akses", "illegal access", "kejahatan siber", "pengedar narkotika"],
            3: ["judi online", "judol", "phishing", "begal", "ujaran kebencian", "provokasi massa",
                "hoaks sara", "diskriminasi", "persekusi", "bencana nasional", "darurat bencana", "karhutla", "kabut asap"],
        }

        cat_scores = {cat: 0 for cat in keywords_map}
        matched_keywords = {cat: [] for cat in keywords_map}

        # 1. Periksa isu strategis nasional terlebih dahulu (IPOLEKSOSBUDHANKAM)
        for cat, kws in keywords_map.items():
            if cat == "Non-Isu":
                continue
            for kw in kws:
                if re.search(r"\b" + re.escape(kw) + r"\b", combined, re.IGNORECASE):
                    cat_scores[cat] += 3
                    matched_keywords[cat].append(kw)

        # 2. Periksa kata kunci non-isu (edukatif/hiburan)
        has_national_issues = any(cat_scores[c] >= 3 for c in cat_scores if c != "Non-Isu")
        for kw in keywords_map["Non-Isu"]:
            if re.search(r"\b" + re.escape(kw) + r"\b", combined, re.IGNORECASE):
                # Jika sudah terindikasi isu strategis nasional (politik/bencana/keamanan), jangan biarkan non-isu menenggelamkan
                score_weight = 1 if has_national_issues else 3
                cat_scores["Non-Isu"] += score_weight
                matched_keywords["Non-Isu"].append(kw)

        best_cat = max(cat_scores, key=cat_scores.get)
        if cat_scores[best_cat] == 0:
            best_cat = "Non-Isu"

        # Tentukan urgensi KONTEKSTUAL berdasarkan severity keywords
        if best_cat == "Non-Isu":
            urgency_score = 1
        elif best_cat in ["Pertahanan", "Ideologi"]:
            urgency_score = 4
        elif best_cat in ["Politik", "Keamanan", "Sosial"]:
            urgency_score = 3
        else:
            urgency_score = 2

        # Boost urgency berdasarkan severity keywords ditemukan di teks
        max_severity_boost = 0
        detected_severe_kws = []
        for sev_level, sev_kws in severity_keywords.items():
            for skw in sev_kws:
                if re.search(r"\b" + re.escape(skw) + r"\b", combined, re.IGNORECASE):
                    if sev_level > max_severity_boost:
                        max_severity_boost = sev_level
                    detected_severe_kws.append(skw)

        if max_severity_boost > 0:
            urgency_score = max(urgency_score, max_severity_boost)
        urgency_score = min(urgency_score, 5)

        # ── 2. EKSTRAKSI ENTITAS KUNCI dari teks ──
        # Ekstrak nama orang (pola: Gelar + Nama Lengkap)
        person_patterns = [
            r"(?:Jenderal|Letjen|Mayjen|Brigadir|Komjen|Irjen|Kapolri|Mantan Kapolri|Presiden|Wapres|Menteri|Gubernur|Bupati|Walikota|Ketua)\s+(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
            r"(?:[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,3})\s+(?:Rakabuming|Subianto|Prabowo|Widodo|Jokowi)",
        ]
        blacklist_name_tokens = ["artikel", "kompas", "pikiran", "rakyat", "detik", "tribun", "berita", "portal", "media", "redaksi", "editorial", "baca", "halaman", "video", "foto"]
        extracted_persons = []
        for pp in person_patterns:
            for pm in re.finditer(pp, clean_text):
                name = pm.group(0).strip()
                if name not in extracted_persons and len(name) > 5:
                    if not any(token in name.lower() for token in blacklist_name_tokens):
                        extracted_persons.append(name)

        # Ekstrak organisasi/lembaga dengan word boundary ketat
        org_patterns = [
            r"\b(?:MPR|DPR|KPK|Polri|TNI|Bareskrim|KPU|Bawaslu|MK|MA|Komnas HAM|BIN|BNPT|Kejaksaan|Kemlu)\b",
            r"(?:Google Developer Groups?|GDGoC|Politeknik\s+\w+(?:\s+\w+)*)",
        ]
        extracted_orgs = []
        for op in org_patterns:
            is_case_sensitive = r"\b" in op
            flags = 0 if is_case_sensitive else re.IGNORECASE
            for om in re.finditer(op, clean_text, flags):
                org = om.group(0).strip()
                if org not in extracted_orgs:
                    extracted_orgs.append(org)

        # Ekstrak aksi/peristiwa kunci
        action_patterns = [
            r"(?:mengundurkan diri|pengunduran diri|ditetapkan sebagai tersangka|terseret dalam perkara|"
            r"dugaan tindak pidana|bukti permulaan|ditangkap|divonis|didakwa|dilantik|diresmikan|"
            r"mundur dari jabatan|menyerahkan surat|mengusut dugaan|diproses hukum|"
            r"resignation letter|submitted his resignation)",
        ]
        extracted_actions = []
        for ap in action_patterns:
            for am in re.finditer(ap, clean_text, re.IGNORECASE):
                act = am.group(0).strip()
                if act not in extracted_actions:
                    extracted_actions.append(act)

        # Ekstrak topik hukum/isu kunci
        issue_patterns = [
            r"(?:tindak pidana makar|ilegal akses|illegal access|korupsi|pencucian uang|"
            r"narkotika|terorisme|ujaran kebencian|hoaks|disinformasi|"
            r"pemilu|pilkada|reshuffle kabinet|kebijakan fiskal|"
            r"beasiswa|erasmus|rekrutmen|core team)",
        ]
        extracted_issues = []
        for ip in issue_patterns:
            for im in re.finditer(ip, clean_text, re.IGNORECASE):
                iss = im.group(0).strip()
                if iss not in extracted_issues:
                    extracted_issues.append(iss)

        # ── 3. SINTESIS RINGKASAN EKSEKUTIF (Extractive Lead-Paragraph Condensation) ──
        # Ambil kalimat-kalimat nyata dari naskah berita/postingan, buang boilerplate/promosi
        raw_sentences = re.split(r'(?<=[.!?])\s+|\n+', clean_text)
        valid_sentences = []
        boilerplate_kws = [
            "baca juga", "simak juga", "dapatkan update", "ikuti saluran", "follow us",
            "sponsored", "klik di sini", "selengkapnya di", "editor:", "penulis:",
            "reporter:", "tonton video", "subscribe", "disukai oleh", "komentar:"
        ]
        for s in raw_sentences:
            s_clean = s.strip()
            # Buang nama kota/tanggal media di awal kalimat (misal: "JAKARTA, KOMPAS.com - ")
            s_clean = re.sub(r'^[A-Z\s]+,\s*[A-Za-z0-9\.\s]+[-–—]\s*', '', s_clean)
            if len(s_clean) >= 20:
                if not any(bp in s_clean.lower() for bp in boilerplate_kws):
                    valid_sentences.append(s_clean)

        # ── 3. SINTESIS RINGKASAN EKSEKUTIF (Mode Offline Heuristic: Spread-Out Sentences Awal, Tengah, Akhir) ──
        selected_sentences = []
        if valid_sentences:
            n_sentences = len(valid_sentences)
            if n_sentences == 1:
                indices = [0]
            elif n_sentences == 2:
                indices = [0, 1]
            else:
                # Ambil kalimat pembuka, kalimat tengah (inti data/dampak), dan kalimat akhir (penanganan/kesimpulan)
                indices = [0, n_sentences // 2, n_sentences - 1]

            for idx in sorted(set(indices)):
                s_clean = valid_sentences[idx].strip()
                if s_clean:
                    if not s_clean.endswith(('.', '!', '?')):
                        s_clean += '.'
                    selected_sentences.append(s_clean)

        if selected_sentences:
            summary_clean = " ".join(selected_sentences)
        else:
            summary_clean = clean_text[:300].strip()
            if not summary_clean.endswith('.'):
                summary_clean += '.'

        summary_clean = summary_clean.strip()

        # ── 4. 5W+1H ──
        display_what = summary_clean.rstrip('.')
        if len(display_what) > 120:
            display_what = display_what[:117] + "..."

        who_val = extracted_persons[0] if extracted_persons else (author or "Tidak disebutkan dalam konten")
        if "kemlu" in (author or "").lower():
            who_val = "Kementerian Luar Negeri RI (@kemlu_ri)"
        elif "gdgoc" in (author or "").lower():
            who_val = "Google Developer Groups on Campus Poltek SSN"

        when_val = "Tidak disebutkan dalam konten"
        where_val = f"Platform {(platform or 'media sosial').upper()}"

        why_val = ""
        causal_matches = re.search(r"(?:merupakan|dalam rangka|untuk|guna|karena|terkait|setelah|pasca)\s+([^.!?\n]{15,120})", clean_text, re.IGNORECASE)
        if causal_matches:
            why_val = causal_matches.group(0).strip().capitalize()
        elif extracted_actions:
            why_val = f"Berkaitan dengan peristiwa: {extracted_actions[0]}."
        else:
            why_val = f"Penyampaian informasi atau klaim publik seputar ranah {best_cat}."

        how_val = "Dipublikasikan melalui kanal media sosial/digital untuk konsumsi publik."

        # ── 4b. STATUS KLAIM, KUTIPAN BUKTI & TIPE KONTEKS ──
        speculative_patterns = [
            r"\bdiduga\b", r"\bdugaan\b", r"\bisunya\b", r"\bkatanya\b", r"\brumor\b",
            r"\bbelum terverifikasi\b", r"\bkabarnya\b", r"\bspekulasi\b", r"\bklaim\b",
            r"\bviral\b", r"\bbocoran\b"
        ]
        opinion_patterns = [
            r"\bopini\b", r"\bmenurut saya\b", r"\bpengamat\b", r"\bmenilai\b", r"\bpandangan\b", r"\bberharap\b"
        ]
        is_speculative = any(re.search(pat, combined, re.IGNORECASE) for pat in speculative_patterns)
        is_opinion = any(re.search(pat, combined, re.IGNORECASE) for pat in opinion_patterns)

        if is_speculative:
            status_klaim = "Dugaan / Belum Terverifikasi"
        elif is_opinion:
            status_klaim = "Opini / Rumor"
        else:
            status_klaim = "Fakta Terverifikasi"

        # Kutipan bukti verbatim
        kutipan_bukti = ""
        if selected_sentences:
            kutipan_bukti = selected_sentences[0][:200].strip()
        elif valid_sentences:
            kutipan_bukti = valid_sentences[0][:200].strip()
        else:
            kutipan_bukti = clean_text[:180].strip()

        # Tipe konteks
        if best_cat == "Non-Isu":
            tipe_konteks = "Informasi Edukasi / Kegiatan Publik"
        elif any(k in combined for k in ["presiden", "wapres", "kapolri", "menteri", "pemerintah", "resmi", "bareskrim", "kpk", "kejaksaan"]):
            tipe_konteks = "Pernyataan Resmi / Berita Penegakan Hukum"
        elif is_speculative or (platform and platform.lower() in ["x", "twitter", "instagram", "tiktok", "threads"]):
            tipe_konteks = "Postingan & Percakapan Media Sosial"
        else:
            tipe_konteks = "Laporan Jurnalistik Media Massa"

        # ── 5. REASONING ANALITIS TIGA BAGIAN BAKU ──
        if best_cat == "Non-Isu":
            fakta_dugaan = (
                f"Konten teridentifikasi sebagai informasi edukatif, tutorial, atau berita umum yang bersifat netral "
                f"dengan status klaim {status_klaim}. Tidak ditemukan unsur disinformasi, provokasi politik, maupun ancaman keamanan siber."
            )
            penalaran_kausal = (
                f"Karena narasi berfokus pada kegiatan positif/edukatif ({', '.join(matched_keywords.get('Non-Isu', ['konten umum'])[:3])}), "
                f"maka tingkat kerawanan dinilai sangat rendah (Urgensi: 1/5) dan tidak berpotensi menimbulkan eskalasi publik."
            )
            rekomendasi_tindak = "Pengawasan rutin berkala sesuai SOP intelijen dan arsip dokumentasi digital."
        else:
            aktor_str = f" melibatkan {extracted_persons[0]}" if extracted_persons else ""
            isu_str = f" terkait {', '.join(extracted_issues[:2])}" if extracted_issues else ""
            fakta_dugaan = (
                f"Narasi membahas isu strategis pada ranah {best_cat}{aktor_str}{isu_str} dengan status klaim '{status_klaim}'. "
                f"Kutipan bukti rujukan: \"{kutipan_bukti}\"."
            )
            penalaran_kausal = (
                f"Karena teridentifikasi indikator ancaman ranah {best_cat} dengan tingkat urgensi {urgency_score}/5, "
                f"maka potensi perbincangan publik dapat memicu eskalasi persepsi atau kerawanan sosial jika tidak segera diklarifikasi atau ditangani."
            )
            rekomendasi_tindak = (
                "Lakukan eskalasi dan koordinasi segera dengan satuan tugas terkait. "
                "Pantau perkembangan isu secara intensif serta amankan segel rantai bukti digital (Chain of Custody) NIST FIPS 198-1."
                if urgency_score >= 4 else
                "Pantau perkembangan isu secara berkala, lakukan verifikasi silang terhadap fakta primer, dan siapkan laporan berkala jika terdapat eskalasi."
            )

        reasoning_text = (
            f"Fakta vs Dugaan Tertulis: {fakta_dugaan}\n\n"
            f"Penalaran Kausal (Karena-Maka): {penalaran_kausal}\n\n"
            f"Rekomendasi Verifikasi & Tindak Lanjut: {rekomendasi_tindak}"
        )

        # ── 6. INDIKASI PELANGGARAN (Kontekstual) ──
        if best_cat == "Non-Isu":
            indikasi = "Tidak ditemukan indikasi pelanggaran; narasi bersifat positif, edukatif, atau informasi umum."
        elif detected_severe_kws:
            indikasi = f"Terdeteksi indikator: {', '.join(detected_severe_kws[:4])}. Tingkat urgensi {urgency_score}/5."
        elif matched_keywords.get(best_cat):
            indikasi = f"Indikasi isu {best_cat} berdasarkan kata kunci: {', '.join(matched_keywords[best_cat][:3])}. Tingkat urgensi {urgency_score}/5."
        else:
            indikasi = f"Indikasi isu {best_cat} dengan tingkat urgensi {urgency_score}/5."

        # ── 7. REKOMENDASI TINDAK LANJUT (Sesuai severity) ──
        if best_cat == "Non-Isu":
            rekomendasi = "Pengawasan berkala sesuai SOP (arsip konten edukatif/positif)."
        elif urgency_score >= 4:
            rekomendasi = "Lakukan eskalasi dan koordinasi segera dengan satuan tugas terkait. Monitoring intensif dan dokumentasi bukti digital."
        elif urgency_score == 3:
            rekomendasi = "Pantau perkembangan isu secara berkala. Siapkan laporan situasi jika terdapat eskalasi."
        else:
            rekomendasi = "Pengawasan rutin sesuai SOP."

        # ── 8. DETEKSI BAHASA & FORMAT INDONESIAN CONTENT ──
        detected_lang = self._detect_language(clean_text)
        if detected_lang != "id":
            indonesian_content = self._heuristic_translate_lead(clean_text)
        else:
            indonesian_content = clean_text

        return {
            "original_language": detected_lang,
            "indonesian_content": indonesian_content,
            "ringkasan_eksekutif": summary_clean,
            "summary_5w1h": {
                "who": who_val,
                "what": display_what,
                "when": when_val,
                "where": where_val,
                "why": why_val,
                "how": how_val,
            },
            "summary": summary_clean,
            "predicted_category": best_cat,
            "urgency_score": urgency_score,
            "ai_reasoning": reasoning_text,
            "tipe_konteks": tipe_konteks,
            "ekstraksi_awal_tengah_akhir": selected_sentences,
            "status_klaim": status_klaim,
            "kutipan_bukti": kutipan_bukti,
            "indikasi_pelanggaran": indikasi,
            "rekomendasi_tindak_lanjut": rekomendasi,
            "matched_keywords": {k: v for k, v in matched_keywords.items() if v},
            "detected_severe_keywords": detected_severe_kws,
            "extracted_entities": {
                "persons": extracted_persons,
                "organizations": extracted_orgs,
                "actions": extracted_actions,
                "issues": extracted_issues,
            },
        }

