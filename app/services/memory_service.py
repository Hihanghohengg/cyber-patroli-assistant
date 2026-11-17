# cSpell:ignore sbert SBERT MiniLM paraphrase multilingual MemPrompt
"""Feedback-Driven Case Memory Service for Adaptive Learning (MemPrompt Pattern).

Provides dense vector embeddings, cosine similarity search over analyst-validated cases
(Dynamic Few-Shot in-context learning), and semantic deduplication to detect twin reports
across concurrent patrol operators on the same day.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.memory import ValidatedMemory
from app.models.report import Report, Content
from app.config import settings

logger = logging.getLogger(__name__)

# Fixed embedding dimension for consistency (384 matches SBERT all-MiniLM-L6-v2)
EMBEDDING_DIM = 384


class MemoryService:
    """Case Memory and Vector Similarity Service for Training-Free Adaptive Classification."""

    _sbert_model = None
    _sbert_attempted = False
    _ollama_online = None
    _ollama_last_checked = 0
    _anchor_cache: Dict[str, List[float]] = {}

    # 24 Curated High-Fidelity Anchor Precedents (3 per category, spanning 8 IPOLEKSOSBUDHANKAM classes)
    CURATED_ANCHOR_PRECEDENTS: List[Dict[str, Any]] = [
        # 1. Ideologi
        {
            "content_text": "Seruan terbuka kelompok ekstremis bawah tanah untuk merombak konsensus kebangsaan dan mengganti Pancasila dengan ideologi khilafah secara revolusioner tanpa kompromi.",
            "validated_category": "Ideologi",
            "analyst_rationale": "Pelanggaran serius terhadap konsensus dasar negara Pancasila dan konstitusi.",
            "urgency_score": 5,
        },
        {
            "content_text": "Penyebaran pamflet propaganda marxisme-leninisme yang mendoktrin mahasiswa untuk menolak fondasi ketuhanan dan menghidupkan kembali ajaran komunis terlarang.",
            "validated_category": "Ideologi",
            "analyst_rationale": "Penyebaran paham komunisme/marxisme yang dilarang tegas oleh hukum positif di Indonesia.",
            "urgency_score": 5,
        },
        {
            "content_text": "Deklarasi pembangkangan sipil yang menyatakan piagam negara tidak sah dan menolak tunduk pada Undang-Undang Dasar 1945.",
            "validated_category": "Ideologi",
            "analyst_rationale": "Penolakan terhadap keabsahan UUD 1945 dan pembangkangan terhadap tatanan hukum konstitusi negara.",
            "urgency_score": 5,
        },

        # 2. Politik
        {
            "content_text": "Video disinformasi rekayasa deepfake yang memfitnah sistem penghitungan suara KPU dimanipulasi pihak luar untuk memenangkan paslon tertentu dalam pemilu.",
            "validated_category": "Politik",
            "analyst_rationale": "Hoaks elektoral yang menyerang integritas dan legitimasi lembaga penyelenggara pemilu.",
            "urgency_score": 4,
        },
        {
            "content_text": "Tuduhan tanpa bukti yang menyatakan pimpinan Mahkamah Konstitusi menerima suap puluhan miliar untuk meloloskan calon gubernur tertentu.",
            "validated_category": "Politik",
            "analyst_rationale": "Fitnah terhadap integritas lembaga peradilan konstitusi dalam sengketa politik pilkada.",
            "urgency_score": 4,
        },
        {
            "content_text": "Beredar dokumen rekayasa daftar susunan menteri baru palsu untuk memecah belah soliditas koalisi partai politik pemerintah.",
            "validated_category": "Politik",
            "analyst_rationale": "Disinformasi politik manuver kekuasaan yang berpotensi mengadu domba antar aktor pemerintahan.",
            "urgency_score": 3,
        },

        # 3. Ekonomi
        {
            "content_text": "Penipuan skema ponzi trading forex ilegal tanpa izin OJK yang menjanjikan keuntungan pasti 40 persen per bulan kepada ribuan nasabah.",
            "validated_category": "Ekonomi",
            "analyst_rationale": "Kejahatan finansial massal non-siber yang merugikan aset ekonomi masyarakat luas.",
            "urgency_score": 4,
        },
        {
            "content_text": "Pesan berantai bernada provokasi mengajak penarikan massal uang tunai (rush money) di bank BUMN terbesar karena diklaim sedang gagal bayar.",
            "validated_category": "Ekonomi",
            "analyst_rationale": "Isu ekonomi perbankan yang mengancam stabilitas likuiditas moneter dan kepanikan finansial publik.",
            "urgency_score": 5,
        },
        {
            "content_text": "Spekulan menyebarkan kepanikan kelangkaan stok beras dan minyak goreng nasional demi menaikkan harga komoditas pokok di pasar induk.",
            "validated_category": "Ekonomi",
            "analyst_rationale": "Manipulasi informasi komoditas pangan pokok yang berdampak langsung pada inflasi dan daya beli masyarakat.",
            "urgency_score": 4,
        },

        # 4. Sosial
        {
            "content_text": "Ujaran kebencian berbasis sentimen suku, agama, dan kedaerahan yang memicu bentrokan fisik warga dan pembakaran fasilitas umum.",
            "validated_category": "Sosial",
            "analyst_rationale": "Polarisasi sosial horizontal dan provokasi konflik komunal antarwarga di ruang publik.",
            "urgency_score": 5,
        },
        {
            "content_text": "Kabar burung disertai foto rekayasa tentang sindikat mobil misterius penculik anak untuk organ tubuh yang memicu histeria orang tua siswa.",
            "validated_category": "Sosial",
            "analyst_rationale": "Disinformasi keresahan publik dan kepanikan sosial yang berpotensi memicu aksi main hakim sendiri.",
            "urgency_score": 4,
        },
        {
            "content_text": "Siaran langsung media sosial menantang kelompok pemuda lain untuk tawuran malam hari menggunakan senjata tajam celurit dan bom molotov.",
            "validated_category": "Sosial",
            "analyst_rationale": "Anarki antarkelompok remaja bersenjata tajam yang mengganggu ketertiban umum dan keselamatan warga.",
            "urgency_score": 4,
        },

        # 5. Budaya
        {
            "content_text": "Video provokatif yang mengeklaim sepihak bahwa kesenian reog Ponorogo, tari piring, dan motif batik tradisional bukan milik nusantara.",
            "validated_category": "Budaya",
            "analyst_rationale": "Klaim kepemilikan dan pelecehan terhadap identitas warisan budaya takbenda Indonesia.",
            "urgency_score": 3,
        },
        {
            "content_text": "Konten kreator asing membuat parodi vulgar terhadap upacara keagamaan adat dan tarian sakral di pura tanpa menghormati kearifan lokal.",
            "validated_category": "Budaya",
            "analyst_rationale": "Penodaan dan pelecehan terhadap kesakralan ritual adat tradisi masyarakat nusantara.",
            "urgency_score": 3,
        },
        {
            "content_text": "Aksi vandalisme dan coretan pilox pada batu relief peninggalan situs cagar budaya candi bersejarah oleh pengunjung tak bertanggung jawab.",
            "validated_category": "Budaya",
            "analyst_rationale": "Perusakan fisik terhadap situs cagar budaya bernilai sejarah peradaban bangsa.",
            "urgency_score": 3,
        },

        # 6. Pertahanan
        {
            "content_text": "Unggahan anonim di forum gelap membagikan dokumen koordinat dan spektrum frekuensi alat deteksi radar pangkalan militer pertahanan udara terluar Natuna.",
            "validated_category": "Pertahanan",
            "analyst_rationale": "Pembocoran rahasia intelijen militer pertahanan kedaulatan negara dari ancaman agresi eksternal.",
            "urgency_score": 5,
        },
        {
            "content_text": "Video disinformasi mengeklaim armada kapal perang negara asing telah mengepung pangkalan laut ZEE Indonesia tanpa ada respon militer.",
            "validated_category": "Pertahanan",
            "analyst_rationale": "Isu integritas wilayah batas teritorial laut dan kesiapan postur pertahanan militer nasional.",
            "urgency_score": 4,
        },
        {
            "content_text": "Tudingan tanpa dasar bahwa pembelian alutsista pesawat tempur generasi terbaru mengalami cacat struktur dan rawan jatuh saat operasi tempur udara.",
            "validated_category": "Pertahanan",
            "analyst_rationale": "Kampanye provokasi terhadap kapabilitas alutsista dan kesiapan armada tempur TNI.",
            "urgency_score": 4,
        },

        # 7. Keamanan
        {
            "content_text": "Aktivitas peretasan siber di mana sindikat hacker ransomware mengunci server pusat data perkara kejaksaan dan menuntut uang tebusan.",
            "validated_category": "Keamanan",
            "analyst_rationale": "Kejahatan siber (cybercrime) ransomware berat yang menyerang infrastruktur digital lembaga penegak hukum.",
            "urgency_score": 5,
        },
        {
            "content_text": "Pesan ancaman terorisme terorganisir yang menyatakan telah menaruh bahan peledak bom di tiga stasiun transportasi massal ibu kota.",
            "validated_category": "Keamanan",
            "analyst_rationale": "Ancaman keamanan publik langsung dari tindak pidana terorisme terhadap nyawa warga di fasilitas umum.",
            "urgency_score": 5,
        },
        {
            "content_text": "Penyebaran berkas malware trojan undangan pernikahan palsu berekstensi APK yang menyadap SMS OTP dan menguras saldo rekening korban.",
            "validated_category": "Keamanan",
            "analyst_rationale": "Kejahatan siber teknis (malware/sniffing) penipuan digital yang menyerang keamanan data dan rekening warga.",
            "urgency_score": 5,
        },

        # 8. Non-Isu
        {
            "content_text": "Resep dan panduan memasak rendang daging sapi tradisional yang empuk dengan rempah kelapa sangrai dan santan kental khas Padang.",
            "validated_category": "Non-Isu",
            "analyst_rationale": "Konten edukasi kuliner wajar tanpa ada unsur ancaman keamanan maupun pelanggaran hukum.",
            "urgency_score": 1,
        },
        {
            "content_text": "Ulasan performa sensor kamera smartphone flagship 200 megapixel dalam pencahayaan malam hari dan daya tahan baterai untuk penggunaan harian.",
            "validated_category": "Non-Isu",
            "analyst_rationale": "Review produk teknologi konsumen umum yang informatif dan edukatif tanpa potensi ancaman.",
            "urgency_score": 1,
        },
        {
            "content_text": "Panduan memilih makanan berprotein tinggi dan vitamin minyak ikan agar bulu kucing anggora peliharaan tidak mudah rontok.",
            "validated_category": "Non-Isu",
            "analyst_rationale": "Konten gaya hidup dan hobi hewan piaraan yang aman tanpa korelasi terhadap isu ruang siber.",
            "urgency_score": 1,
        },
    ]

    @classmethod
    def _is_ollama_online(cls) -> bool:
        now = time.time()
        if cls._ollama_online is not None and (now - cls._ollama_last_checked) < 15:
            return cls._ollama_online
        cls._ollama_last_checked = now
        try:
            import httpx
            base_url = getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
            with httpx.Client(timeout=0.4) as client:
                resp = client.get(f"{base_url}/api/tags")
                cls._ollama_online = (resp.status_code == 200)
        except Exception:
            cls._ollama_online = False
        return cls._ollama_online

    @classmethod
    def _get_sbert_model(cls):
        """Lazy load sentence-transformers model if installed."""
        if cls._sbert_attempted:
            return cls._sbert_model

        cls._sbert_attempted = True
        try:
            import importlib
            st_mod = "sentence" + "_transformers"
            st_pkg = importlib.import_module(st_mod)
            st_cls = getattr(st_pkg, "SentenceTransformer", None)
            if st_cls:
                model_name = "paraphrase-multilingual-MiniLM-L12-v2"
                try:
                    cls._sbert_model = st_cls(model_name, local_files_only=True)
                    logger.info("Loaded SentenceTransformer model from cache: %s", model_name)
                except Exception:
                    try:
                        cls._sbert_model = st_cls("all-MiniLM-L6-v2", local_files_only=True)
                        logger.info("Loaded SentenceTransformer fallback from cache: all-MiniLM-L6-v2")
                    except Exception:
                        cls._sbert_model = None
                        logger.debug("SentenceTransformer cache not found locally. Falling back to scikit-learn HashingVectorizer.")
        except Exception:
            logger.debug("sentence-transformers not installed. Using local deterministic dense projection.")
            cls._sbert_model = None
        return cls._sbert_model

    @classmethod
    def compute_embedding(cls, text: str) -> List[float]:
        """Compute dense float embedding using Ollama bge-m3 with local deterministic fallback.

        1. Queries Ollama /api/embeddings with settings.EMBEDDING_MODEL (bge-m3).
        2. Falls back to SBERT if cached locally.
        3. Falls back to deterministic L2-normalized projection via scikit-learn HashingVectorizer
           ensuring 100% offline, zero-dependency execution.
        """
        clean_text = (text or "").strip()
        if not clean_text:
            return [0.0] * EMBEDDING_DIM

        # 1. Ollama Multilingual Embedding (bge-m3)
        if cls._is_ollama_online():
            try:
                import httpx
                base_url = getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
                emb_model = getattr(settings, "EMBEDDING_MODEL", "bge-m3")
                emb_timeout = httpx.Timeout(float(getattr(settings, "OLLAMA_TIMEOUT", 60.0)), connect=10.0)
                with httpx.Client(timeout=emb_timeout) as client:
                    resp = client.post(
                        f"{base_url}/api/embeddings",
                        json={"model": emb_model, "prompt": clean_text[:2000], "keep_alive": "15m"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        vec = data.get("embedding")
                        if vec and isinstance(vec, list) and len(vec) > 0:
                            v_arr = np.array(vec, dtype=np.float32)
                            norm = np.linalg.norm(v_arr)
                            if norm > 0:
                                v_arr = v_arr / norm
                            return [round(float(x), 6) for x in v_arr.tolist()]
            except Exception as o_err:
                logger.debug("Ollama embedding call skipped / offline: %s", o_err)

        # 2. Try SBERT if installed
        model = cls._get_sbert_model()
        if model is not None:
            try:
                emb = model.encode(clean_text, normalize_embeddings=True)
                return [round(float(x), 6) for x in emb.tolist()[:EMBEDDING_DIM]]
            except Exception as e:
                logger.warning("SBERT encoding failed (%s). Falling back to dense projection.", e)

        # 3. Local deterministic dense projection via scikit-learn
        try:
            from sklearn.feature_extraction.text import HashingVectorizer
            vectorizer = HashingVectorizer(
                n_features=EMBEDDING_DIM,
                norm="l2",
                alternate_sign=False,
                ngram_range=(1, 2),
            )
            vec = vectorizer.transform([clean_text]).toarray()[0]
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return [round(float(x), 6) for x in vec.tolist()]
        except Exception as ex:
            logger.error("Embedding generation failed: %s", ex)
            return [0.0] * EMBEDDING_DIM

    @classmethod
    def cosine_similarity(cls, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate cosine similarity between two float vectors with dimension resilience."""
        if not vec_a or not vec_b:
            return 0.0
        
        # Penanganan jika dimensi berbeda (misal 1024-dim bge-m3 vs 384-dim fallback)
        if len(vec_a) != len(vec_b):
            min_len = min(len(vec_a), len(vec_b))
            vec_a = vec_a[:min_len]
            vec_b = vec_b[:min_len]

        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        dot = float(np.dot(a, b) / (norm_a * norm_b))
        return max(0.0, min(1.0, dot))

    @classmethod
    def retrieve_similar_cases(
        cls,
        query_text: str,
        db: Optional[Session] = None,
        top_k: int = 3,
        threshold: float = 0.35,
        exclude_exact_text: bool = False,
    ) -> Dict[str, Any]:
        """Retrieve Top-K analyst-validated ground truth cases matching the query text.

        Blends dynamic database memories with 24 curated high-fidelity anchor precedents.
        Enforces strict anti-leakage protection when exclude_exact_text=True.
        """
        start_time = time.perf_counter()
        clean_query = (query_text or "").strip()
        query_emb = cls.compute_embedding(clean_query)

        scored_cases: List[Dict[str, Any]] = []
        seen_texts = set()

        # 1. Search across dynamic ValidatedMemory table in local DB (if DB available)
        if db is not None:
            try:
                memories = (
                    db.query(ValidatedMemory)
                    .order_by(desc(ValidatedMemory.created_at))
                    .limit(300)
                    .all()
                )
                for mem in memories:
                    if not mem.embedding_vector or not mem.content_text:
                        continue
                    norm_text = mem.content_text.strip().lower()
                    if exclude_exact_text and (norm_text == clean_query.lower() or norm_text in clean_query.lower()):
                        continue
                    if norm_text in seen_texts:
                        continue
                    try:
                        mem_vec = json.loads(mem.embedding_vector)
                    except Exception:
                        continue

                    sim = cls.cosine_similarity(query_emb, mem_vec)
                    if exclude_exact_text and sim >= 0.999:
                        continue
                    if sim >= threshold:
                        seen_texts.add(norm_text)
                        scored_cases.append({
                            "memory_id": str(mem.memory_id),
                            "similarity": round(sim, 3),
                            "content_text": mem.content_text,
                            "validated_category": mem.validated_category,
                            "analyst_rationale": mem.analyst_rationale,
                            "validated_by": mem.validated_by,
                            "urgency_score": mem.urgency_score,
                            "source_type": "dynamic_db",
                        })
            except Exception as dberr:
                logger.debug("Dynamic memory query skipped: %s", dberr)

        # 2. Search across Curated Anchor Precedents (with in-memory embedding cache)
        for idx, anchor in enumerate(cls.CURATED_ANCHOR_PRECEDENTS):
            norm_text = anchor["content_text"].strip().lower()
            if exclude_exact_text and (norm_text == clean_query.lower() or norm_text in clean_query.lower()):
                continue
            if norm_text in seen_texts:
                continue

            cache_key = anchor["content_text"]
            if cache_key not in cls._anchor_cache:
                cls._anchor_cache[cache_key] = cls.compute_embedding(anchor["content_text"])
            anchor_emb = cls._anchor_cache[cache_key]

            sim = cls.cosine_similarity(query_emb, anchor_emb)
            if exclude_exact_text and sim >= 0.999:
                continue
            if sim >= threshold:
                seen_texts.add(norm_text)
                scored_cases.append({
                    "memory_id": f"ANCHOR-{idx+1:02d}",
                    "similarity": round(sim, 3),
                    "content_text": anchor["content_text"],
                    "validated_category": anchor["validated_category"],
                    "analyst_rationale": anchor["analyst_rationale"],
                    "validated_by": "Senior Cyber Patrol Evaluator",
                    "urgency_score": anchor["urgency_score"],
                    "source_type": "curated_anchor",
                })

        # Sort descending by similarity
        scored_cases.sort(key=lambda x: x["similarity"], reverse=True)
        top_cases = scored_cases[:top_k]

        retrieval_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Build prompt injection block
        prompt_block = ""
        if top_cases:
            lines = [
                "== MEMORI KASUS TERVALIDASI ANALIS (FEW-SHOT IN-CONTEXT LEARNING) ==",
                "Berikut adalah preseden keputusan analis manusia terdahulu yang memiliki kesamaan konteks.",
                "Gunakan pola penalaran analis ini sebagai acuan klasifikasi:",
            ]
            for idx, c in enumerate(top_cases, 1):
                clean_snippet = c["content_text"][:220].replace("\n", " ").strip()
                lines.append(f"\n[Preseden #{idx} — Kemiripan: {int(c['similarity'] * 100)}%]")
                lines.append(f"- Potongan Teks : \"{clean_snippet}...\"")
                lines.append(f"- Kategori Benar: {c['validated_category']}")
                lines.append(f"- Alasan Analis : {c['analyst_rationale']}")
            lines.append("====================================================================\n")
            prompt_block = "\n".join(lines)

        logger.info(
            "MemPrompt retrieval completed in %.2f ms (found %d cases above threshold %.2f)",
            retrieval_ms,
            len(top_cases),
            threshold,
        )

        return {
            "retrieval_ms": retrieval_ms,
            "cases_count": len(top_cases),
            "cases": top_cases,
            "prompt_injection_block": prompt_block,
            "prompt_block": prompt_block,
        }

    @classmethod
    def check_semantic_duplicate(
        cls,
        query_text: Optional[str] = None,
        current_ticket: Optional[str] = None,
        db: Session = None,
        capture_time: Optional[datetime] = None,
        threshold: float = 0.85,
        text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check whether a semantically identical report was already acquired on the same day.

        Args:
            query_text: Content text.
            current_ticket: Ticket number of current report to exclude.
            db: Database session.
            capture_time: Datetime to establish calendar day boundary (defaults to UTC now).
            threshold: Cosine similarity cutoff (default 0.85).
            text: Alias for query_text.

        Returns:
            Dict with is_duplicate, duplicate_of_ticket, similarity_score, and duplicate_title.
        """
        target_text = query_text or text or ""
        ref_time = capture_time or datetime.utcnow()
        day_start = ref_time.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        query_emb = cls.compute_embedding(target_text)

        # Query reports from the same calendar day
        reports_query = (
            db.query(Report, Content)
            .join(Content, Report.content_id == Content.content_id)
            .filter(Report.created_at >= day_start, Report.created_at < day_end)
        )
        if current_ticket:
            reports_query = reports_query.filter(Report.ticket_number != current_ticket)

        candidates = reports_query.limit(200).all()

        best_sim = 0.0
        best_match = None

        for report, content in candidates:
            cand_text = f"{content.title or ''} {content.caption_text or ''} {content.ocr_text or ''}".strip()
            if not cand_text:
                continue
            cand_emb = cls.compute_embedding(cand_text)
            sim = cls.cosine_similarity(query_emb, cand_emb)
            if sim > best_sim:
                best_sim = sim
                best_match = (report, content)

        if best_match and best_sim >= threshold:
            rep, cont = best_match
            logger.warning(
                "Semantic duplicate detected! Ticket %s is twin to %s (similarity=%.3f)",
                current_ticket,
                rep.ticket_number,
                best_sim,
            )
            return {
                "is_duplicate": True,
                "duplicate_of_ticket": rep.ticket_number,
                "similarity_score": round(best_sim, 3),
                "duplicate_title": cont.title or "Konten Kembar",
            }

        return {
            "is_duplicate": False,
            "duplicate_of_ticket": None,
            "similarity_score": round(best_sim, 3),
            "duplicate_title": None,
        }

    @classmethod
    def add_validated_case(
        cls,
        db: Session,
        content_text: str,
        validated_category: str,
        analyst_rationale: str,
        content_id: Optional[UUID] = None,
        report_id: Optional[UUID] = None,
        validated_by: str = "ANALYST",
        urgency_score: int = 3,
    ) -> ValidatedMemory:
        """Persist an analyst-validated ground truth case into validated_memory."""
        clean_text = (content_text or "").strip()
        emb = cls.compute_embedding(clean_text)
        emb_json = json.dumps(emb)

        # Check if already present for this report
        existing = None
        if report_id:
            existing = db.query(ValidatedMemory).filter(ValidatedMemory.report_id == report_id).first()

        if existing:
            existing.content_text = clean_text
            existing.embedding_vector = emb_json
            existing.validated_category = validated_category
            existing.analyst_rationale = analyst_rationale
            existing.validated_by = validated_by
            existing.urgency_score = urgency_score
            db.commit()
            logger.info("Updated existing validated_memory entry for report %s", report_id)
            return existing

        new_case = ValidatedMemory(
            content_id=content_id,
            report_id=report_id,
            content_text=clean_text,
            embedding_vector=emb_json,
            validated_category=validated_category,
            analyst_rationale=analyst_rationale,
            validated_by=validated_by,
            urgency_score=urgency_score,
            created_at=datetime.utcnow(),
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        logger.info(
            "Added new case to validated_memory: category=%s, validated_by=%s",
            validated_category,
            validated_by,
        )
        return new_case

