"""RAG (Retrieval-Augmented Generation) Service for Cyber Patrol Assistant (PRD v2).

Provides vector embedding generation via Gemini Embedding API, cosine similarity
retrieval of past verified cases, prompt block formatting, and quality-controlled
knowledge base ingestion.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

import numpy as np
import google.generativeai as genai
from sqlalchemy.orm import Session

from app.config import settings
from app.models.knowledge import KnowledgeEntry
from app.models.report import Report
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "models/text-embedding-004"
DEFAULT_SIMILARITY_THRESHOLD = 0.75  # Calibrated default per Proposal ADR-04
DEFAULT_TOP_K = 5


class RAGService:
    """Core RAG retrieval and knowledge base service (DFD 4.0 & NFR-04)."""

    def __init__(self):
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.warning("Failed to configure genai for embeddings: %s", e)

    def _log_rag_fallback(self, db: Optional[Session], reason_code: str, details: str):
        """Record RAG fail-open empty event to audit_logs (DFD 4.5)."""
        if not db:
            return
        try:
            audit = AuditLog(
                action="RAG_FALLBACK_EMPTY",
                actor_telegram_id=0,
                actor_username="RAG_SYSTEM",
                entity_type="KnowledgeEntry",
                entity_id="N/A",
                details={"reason_code": reason_code, "details": details},
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning("Could not record RAG_FALLBACK_EMPTY audit log: %s", e)

    def generate_embedding(self, text: str, db: Optional[Session] = None) -> Optional[List[float]]:
        """Generate a 768-dimensional vector embedding for a given text via Gemini API (DFD 4.2).

        Pure Fail-Open: Pseudo-deterministic / random vector generation has been removed
        to protect forensic and semantic validity. Returns None if API is unavailable.
        """
        if not text or not text.strip():
            return None

        truncated = text.strip()[:3000]

        if not settings.GEMINI_API_KEY:
            logger.info("No GEMINI_API_KEY configured; RAG embedding skipped (fail-open)")
            self._log_rag_fallback(db, "NO_API_KEY", "GEMINI_API_KEY not configured")
            return None

        try:
            response = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=truncated,
                task_type="retrieval_query",
            )
            embedding = response.get("embedding")
            if embedding:
                return embedding
        except Exception as e:
            logger.warning("Gemini embedding generation failed (%s); pure fail-open mode engaged", e)
            self._log_rag_fallback(db, "EMBED_API_FAILED", str(e))

        return None

    def retrieve_similar_cases(
        self,
        db: Session,
        query_text: str = "",
        text: Optional[str] = None,
        title: str = "",
        caption: str = "",
        ocr_text: str = "",
        k: int = DEFAULT_TOP_K,
        top_k: Optional[int] = None,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        format_as_text: bool = True,
    ) -> Any:
        """DFD Level 2 Proses 4.0: Pure fail-open retrieval of similar verified cases.

        4.1: Susun kueri dari judul + caption + teks OCR awal.
        4.2: Panggil Gemini Embedding API (768 dimensi).
        4.3: Cari di knowledge_entries (is_active == True) dengan threshold >= 0.75 (ADR-04).
        4.4: Susun blok referensi kasus non-otoritatif untuk diinjeksikan ke prompt.
        4.5: Fail-open: jika gagal/cold start/di bawah threshold, kembalikan empty context dan catat ke audit_logs.
        """
        # 4.1 Compile query text
        effective_query = text if text is not None else query_text
        if not effective_query:
            parts = [title.strip(), caption.strip(), ocr_text.strip()]
            effective_query = " ".join([p for p in parts if p]).strip()

        effective_k = top_k if top_k is not None else k
        if not effective_query:
            return "" if format_as_text else []

        # 4.2 Generate embedding vector
        query_vec = self.generate_embedding(effective_query, db=db)
        if not query_vec:
            # 4.5 Fail-open: empty context
            logger.info("RAG fail-open: No query embedding generated. Proceeding with empty context.")
            return "" if format_as_text else []

        # 4.3 Query active entries
        entries = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.is_active.is_(True))
            .filter(KnowledgeEntry.embedding.isnot(None))
            .all()
        )

        if not entries:
            # 4.5 Cold start
            logger.info("RAG fail-open: Knowledge base empty. Proceeding with empty context.")
            self._log_rag_fallback(db, "COLD_START", "Knowledge base has 0 active entries")
            return "" if format_as_text else []

        query_arr = np.array(query_vec, dtype=float)
        query_norm = np.linalg.norm(query_arr)
        if query_norm == 0:
            return "" if format_as_text else []

        scored_cases = []
        for entry in entries:
            try:
                raw_emb = entry.embedding
                if isinstance(raw_emb, str):
                    cand_arr = np.array(json.loads(raw_emb), dtype=float)
                elif hasattr(raw_emb, "tolist"):
                    cand_arr = np.array(raw_emb.tolist(), dtype=float)
                else:
                    cand_arr = np.array(raw_emb, dtype=float)

                cand_norm = np.linalg.norm(cand_arr)
                if cand_norm == 0:
                    continue

                cosine_sim = float(np.dot(query_arr, cand_arr) / (query_norm * cand_norm))
                if cosine_sim >= threshold:
                    scored_cases.append({
                        "entry_id": str(entry.entry_id),
                        "decision": entry.decision,
                        "final_label": entry.final_label,
                        "final_risk": entry.final_risk or "-",
                        "reasoning": entry.reasoning or "",
                        "analyst_notes": entry.analyst_notes or "",
                        "summary": entry.summary_text or "",
                        "similarity": round(cosine_sim, 4),
                        "topic": entry.topic.canonical_name if entry.topic else "-",
                        "source": entry.source.canonical_name if entry.source else "-",
                    })
            except Exception:
                continue

        scored_cases.sort(key=lambda x: x["similarity"], reverse=True)
        top_cases = scored_cases[:effective_k]

        if not top_cases:
            logger.info("RAG fail-open: No verified cases exceeded similarity threshold %s.", threshold)
            self._log_rag_fallback(db, "BELOW_THRESHOLD", f"0 cases exceeded threshold {threshold}")
            return "" if format_as_text else []

        # 4.4 Format reference block
        if format_as_text:
            return self.format_rag_prompt_block(top_cases)
        return top_cases

    @staticmethod
    def format_rag_prompt_block(cases: List[Dict]) -> str:
        """Format retrieved cases into clean, structured prompt text."""
        if not cases:
            return ""

        blocks = []
        for i, c in enumerate(cases, 1):
            decision_label = c.get("final_label") or c.get("verified_label") or c.get("verified_category") or "NETRAL"
            risk_label = c.get("final_risk") or c.get("verified_risk") or "SEDANG"
            summary = c.get("summary_text") or c.get("content_snippet") or c.get("content_text") or "(tanpa ringkasan)"
            reasoning = c.get("reasoning") or "-"
            notes = c.get("analyst_notes") or "-"
            ticket = c.get("ticket") or c.get("ticket_number") or ""
            ticket_str = f" | Tiket: {ticket}" if ticket else ""

            blocks.append(
                f"[Kasus Referensi #{i} | Kemiripan: {int(c.get('similarity', 0.8) * 100)}%{ticket_str}]\n"
                f"- Narasi Konten: {summary}\n"
                f"- Keputusan Final Analis: {decision_label} (Tingkat Risiko: {risk_label})\n"
                f"- Alasan Penilaian: {reasoning}\n"
                f"- Catatan Resmi Analis: {notes}"
            )

        prompt_text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📚 KASUS PRESEDEN HISTORIS DARI ANALIS SIBER (RAG KNOWLEDGE BASE):\n"
            "Berikut adalah kasus serupa yang telah diverifikasi oleh analis manusia sebelumnya.\n"
            "Jadikan pedoman konsistensi label dan mitigasi false-positive.\n"
            "PENTING: Gunakan hanya sebagai konteks preseden pertimbangan; putuskan berdasarkan bukti konten baru.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(blocks)
        )
        return prompt_text

    def create_knowledge_entry(
        self,
        db: Session,
        report_id: Any,
        decision: Optional[str] = None,
        analyst_id: Optional[int] = None,
        analyst_notes: Optional[str] = None,
    ) -> Optional[KnowledgeEntry]:
        """Record verified decision into Knowledge Base (FR-09.1, FR-09.2, FR-09.7).

        Idempotency: Any existing active entry for this report_id is deactivated first.
        """
        if isinstance(report_id, Report):
            report = report_id
            rep_id = report.report_id
            decision = decision or report.review_decision or report.status
            analyst_id = analyst_id or report.reviewer_telegram_id
            analyst_notes = analyst_notes or report.analyst_notes
        else:
            rep_id = report_id
            report = db.query(Report).filter(Report.report_id == rep_id).first()

        if not report:
            logger.error("Cannot create KB entry: Report %s not found", rep_id)
            return None

        now = datetime.utcnow()

        # FR-09.7: Deactivate any existing active entry for this report
        existing_entries = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.report_id == rep_id, KnowledgeEntry.is_active.is_(True))
            .all()
        )
        for old in existing_entries:
            old.is_active = False
            old.deactivated_by = analyst_id
            old.deactivated_at = now

        # Compile embed text
        content = report.content
        title = content.title or "" if content else ""
        caption = content.caption_text or "" if content else ""
        summary = report.ai_summary or ""
        embed_text = f"{title}\n{caption}\n{summary}".strip()

        # Generate embedding vector
        embedding_vec = self.generate_embedding(embed_text)

        # Label resolution
        if decision == "REJECTED" or decision == "FALSE_POSITIVE":
            final_label = "BUKAN_PELANGGARAN"
            final_risk = "RENDAH"
        else:
            final_label = report.final_label or report.ai_predicted_label or "NETRAL"
            final_risk = report.final_risk or report.ai_risk_level or "RENDAH"

        reasoning = getattr(report, "correction_notes", None) or (
            "\n".join([f"- {v}" for v in report.ai_reasoning.values()])
            if isinstance(report.ai_reasoning, dict)
            else str(report.ai_reasoning or "")
        )

        entry = KnowledgeEntry(
            report_id=rep_id,
            ticket_number=report.ticket_number,
            source_platform=report.content.platform if report.content else "MANUAL",
            account_username=report.content.account.username if report.content and report.content.account else "",
            decision=decision or "VALIDATED",
            final_label=final_label,
            final_risk=final_risk,
            reasoning=reasoning,
            analyst_notes=analyst_notes or report.analyst_notes,
            summary_text=report.ai_summary,
            topic_id=report.topic_id,
            source_id=report.source_id,
            embed_text=embed_text,
            embedding=embedding_vec,
            decided_by=analyst_id or report.reviewer_telegram_id,
            is_active=True,
            created_at=now,
        )
        db.add(entry)

        # Audit log
        db.add(
            AuditLog(
                action="KB_ENTRY_CREATED",
                actor_telegram_id=analyst_id or report.reviewer_telegram_id,
                entity_type="KnowledgeEntry",
                entity_id=str(entry.entry_id),
                details={
                    "report_id": str(rep_id),
                    "decision": decision,
                    "final_label": final_label,
                    "final_risk": final_risk,
                },
                timestamp=now,
            )
        )
        db.commit()
        db.refresh(entry)
        logger.info("Successfully ingested Knowledge Base entry %s for report %s", entry.entry_id, rep_id)
        return entry

    def deactivate_entry(
        self,
        db: Session,
        entry_id: uuid.UUID,
        admin_id: Optional[int] = None,
    ) -> bool:
        """Admin operation: deactivate a false or obsolete knowledge entry."""
        entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_id == entry_id).first()
        if not entry:
            return False

        now = datetime.utcnow()
        entry.is_active = False
        entry.deactivated_by = admin_id
        entry.deactivated_at = now

        db.add(
            AuditLog(
                action="KB_ENTRY_DEACTIVATED",
                actor_telegram_id=admin_id,
                entity_type="KnowledgeEntry",
                entity_id=str(entry.entry_id),
                details={"reason": "Manual deactivation by administrator"},
                timestamp=now,
            )
        )
        db.commit()
        logger.info("Deactivated KB entry %s by admin %s", entry_id, admin_id)
        return True
