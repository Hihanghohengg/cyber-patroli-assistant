"""Trending topic calculation engine for Social Intelligence.

Calculates multi-factor weighted trending scores based on volume, growth rate,
velocity, platform/source diversity, recency decay, and analyst relevance.
Stores historical snapshots in TopicSnapshot for timeline visualization.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.intelligence import IssueCluster, IssueContent, TopicSnapshot, ContentAnalysis
from app.models.report import Content

logger = logging.getLogger(__name__)


class TrendingEngine:
    """Calculates weighted trending scores and generates periodic snapshots."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or getattr(settings, "TRENDING_WEIGHTS", {
            "volume": 0.30,
            "growth": 0.30,
            "velocity": 0.15,
            "source_diversity": 0.10,
            "recency": 0.10,
            "relevance": 0.05,
        })

    def calculate_issue_metrics(
        self,
        db: Session,
        issue_id: uuid.UUID,
        window_hours: int = 24,
    ) -> Dict:
        """Compute all component metrics for an IssueCluster over a time window."""
        now = datetime.utcnow()
        current_window_start = now - timedelta(hours=window_hours)
        previous_window_start = now - timedelta(hours=window_hours * 2)

        # 1. Seluruh temuan yang terhubung dalam klaster isu
        all_links = (
            db.query(IssueContent, Content)
            .join(Content, IssueContent.content_id == Content.content_id)
            .filter(IssueContent.issue_id == issue_id)
            .all()
        )
        total_count = len(all_links)

        # 2. Temuan baru dalam rentang jendela waktu aktif (24 jam terakhir)
        current_links = [
            (link, content)
            for link, content in all_links
            if content.created_at and content.created_at >= current_window_start
        ]
        current_count = len(current_links)

        # 3. Temuan pada jendela waktu sebelumnya (untuk menghitung laju pertumbuhan)
        prev_count = (
            db.query(func.count(IssueContent.id))
            .join(Content, IssueContent.content_id == Content.content_id)
            .filter(IssueContent.issue_id == issue_id)
            .filter(Content.created_at >= previous_window_start)
            .filter(Content.created_at < current_window_start)
            .scalar() or 0
        )

        if prev_count > 0:
            growth_rate = ((current_count - prev_count) / float(prev_count)) * 100.0
        else:
            growth_rate = 100.0 if current_count > 0 else 0.0

        # Kecepatan temuan per jam
        velocity = round(current_count / float(max(1, window_hours)), 2)

        # 4. Sebaran Platform & Akun Unik
        platform_dist: Dict[str, int] = {}
        unique_authors = set()
        total_interactions = 0

        for _, content in all_links:
            plat = (content.platform or "other").lower()
            platform_dist[plat] = platform_dist.get(plat, 0) + 1
            if content.account_id:
                unique_authors.add(content.account_id)
            
            # Hitung total interaksi digital
            total_interactions += (
                (content.likes_count or 0)
                + (content.views_count or 0)
                + (content.shares_count or 0)
                + (content.comments_count or 0)
            )

        unique_sources_count = len(unique_authors)
        platform_count = len(platform_dist)

        # 5. Distribusi Sentimen
        sentiments: Dict[str, int] = {"POSITIF": 0, "NEGATIF": 0, "NETRAL": 0, "CAMPURAN": 0}
        content_ids = [c.content_id for _, c in all_links]

        # -------------------------------------------------------------------------
        # FORMULA SKOR ISU HANGAT (HotScore 0-100) — 4 SINYAL OPERASIONAL NYATA
        # -------------------------------------------------------------------------
        from app.models.report import Report

        reports_map = {}
        analyses_map = {}
        if content_ids:
            rep_list = db.query(Report).filter(Report.content_id.in_(content_ids)).all()
            reports_map = {r.content_id: r for r in rep_list}

            ana_list = db.query(ContentAnalysis).filter(ContentAnalysis.content_id.in_(content_ids)).all()
            analyses_map = {a.content_id: a for a in ana_list}
            for a in ana_list:
                s = (a.sentiment or "NETRAL").upper()
                sentiments[s] = sentiments.get(s, 0) + 1

        # Sinyal 1: Urgensi Tervalidasi (35%)
        # Rata-rata urgency_score (1-5) dengan pembobotan 1.5x untuk konten HITL APPROVED/VALIDATED
        weighted_urgency_sum = 0.0
        weight_sum = 0.0
        for cid in content_ids:
            rep = reports_map.get(cid)
            ana = analyses_map.get(cid)

            # Ekstraksi urgensi 1-5
            u = 2.0
            if ana and ana.urgency_score is not None:
                raw_u = float(ana.urgency_score)
                u = (raw_u * 5.0) if raw_u <= 1.0 else raw_u
            elif rep and rep.ai_output and isinstance(rep.ai_output, dict) and rep.ai_output.get("urgency_score"):
                u = float(rep.ai_output["urgency_score"])
            elif rep and rep.ai_risk_level:
                u = 4.0 if rep.ai_risk_level == "TINGGI" else (3.0 if rep.ai_risk_level == "SEDANG" else 2.0)
            
            u = max(1.0, min(5.0, u))

            # Bobot 1.5x untuk konten yang tervalidasi analis manusia
            w = 1.0
            if rep and (rep.review_decision in ["APPROVED", "VALIDATED"] or rep.status == Report.STATUS_VALIDATED):
                w = 1.5

            weighted_urgency_sum += (u * w)
            weight_sum += w

        avg_urgency = (weighted_urgency_sum / max(1.0, weight_sum)) if weight_sum > 0 else 2.5
        score_urgency = min(100.0, max(0.0, (avg_urgency / 5.0) * 100.0))

        # Sinyal 2: Sebaran Lintas Platform (25%)
        # Jumlah platform unik dibagi 5 kanal target (X, Instagram, YouTube, Threads, Media)
        score_platform = min(100.0, max(0.0, (platform_count / 5.0) * 100.0))

        # Sinyal 3: Laju Tangkapan Baru / Velocity (25%)
        # Rasio temuan baru 24 jam terakhir terhadap total temuan dalam klaster
        score_velocity = min(100.0, max(0.0, (float(current_count) / float(max(1, total_count))) * 100.0))

        # Sinyal 4: Otoritas Sumber & Interaksi (15%)
        # Bonus +30 jika terdapat sumber media nasional + normalisasi logaritmik interaksi (maks 70)
        has_media = any(p in ["media", "news", "kompas", "detik", "tribun", "tempo"] for p in platform_dist.keys())
        media_bonus = 30.0 if has_media else 0.0
        interaction_norm = min(70.0, math.log1p(total_interactions) * 7.0)
        score_authority = min(100.0, max(0.0, media_bonus + interaction_norm))

        # Total HotScore Tertimbang (0-100)
        hot_score = (
            (0.35 * score_urgency)
            + (0.25 * score_platform)
            + (0.25 * score_velocity)
            + (0.15 * score_authority)
        )
        final_score = round(max(0.0, min(100.0, hot_score)), 1)

        # Label Status Eskalasi Berdasarkan Ambang Batas
        if final_score >= 75.0:
            escalation_label = "ESKALASI TINGGI"
        elif final_score >= 50.0:
            escalation_label = "MENGHANGAT"
        else:
            escalation_label = "PANTAU"

        # Tentukan Tiga Pilar Isu Pemerintahan (Aktual, Kritikal, Tematik)
        issue_obj = db.query(IssueCluster).filter(IssueCluster.issue_id == issue_id).first()
        type_info = TrendingEngine.determine_issue_type(issue_obj, {
            "avg_urgency": avg_urgency,
            "escalation_label": escalation_label,
            "trending_score": final_score,
        })

        return {
            "issue_id": issue_id,
            "total_count": total_count,
            "current_count": current_count,
            "recent_count_24h": current_count,
            "unique_sources": unique_sources_count,
            "platform_count": platform_count,
            "growth_rate": round(growth_rate, 2),
            "velocity": velocity,
            "trending_score": final_score,
            "escalation_label": escalation_label,
            "avg_urgency": round(avg_urgency, 2),
            "total_interactions": total_interactions,
            "platform_distribution": platform_dist,
            "sentiment_distribution": sentiments,
            "recency_score": round(score_velocity, 2),
            "snapshot_time": now,
            "issue_type": type_info["issue_type"],
            "issue_type_reason": type_info["issue_type_reason"],
        }

    @staticmethod
    def determine_issue_type(issue: Optional[IssueCluster], metrics: Dict) -> Dict[str, str]:
        """Tiga Pilar Isu Pemerintahan:
        1. AKTUAL: Masalah publik yang sedang hangat diperbincangkan saat ini dan butuh respons cepat (Velocity & HotScore Tinggi).
        2. KRITIKAL: Masalah krusial dengan tingkat bahaya atau urgensi tinggi (>= 3.8/5) yang dapat melumpuhkan tata kelola pemerintahan bila tidak segera ditangani.
        3. TEMATIK: Topik besar payung perencanaan strategis dan agenda fokus program bersama lintas instansi (RKP, Reformasi Birokrasi, Perubahan Iklim/Karhutla, Pendidikan/Inovasi).
        """
        avg_urgency = float(metrics.get("avg_urgency", 2.5))
        escalation_label = str(metrics.get("escalation_label", "PANTAU"))

        title = (getattr(issue, "title", None) or "").lower() if issue else ""
        cat = (getattr(issue, "category", None) or "").lower() if issue else ""
        keywords = (getattr(issue, "keywords", []) or []) if issue else []
        kws_str = " ".join(keywords).lower()
        combined = f"{title} {cat} {kws_str}"

        # 1. Kriteria KRITIKAL (Bahaya & Prioritas Mitigasi Risiko Tata Kelola/Keamanan Negara)
        critical_keywords = [
            "penyadapan", "korupsi", "tersangka", "makar", "hacked", "kejahatan siber",
            "judol", "judi online", "pinjol", "ancaman bom", "senjata", "pembunuhan",
            "separatis", "separatisme", "biometric records", "c-4", "wiretapping",
            "tangkap tangan", "pencucian uang", "invasi"
        ]
        is_critical = (
            avg_urgency >= 3.8
            or escalation_label == "ESKALASI TINGGI"
            or any(ck in combined for ck in critical_keywords)
        )

        if is_critical:
            return {
                "issue_type": "KRITIKAL",
                "issue_type_reason": "Tingkat risiko krusial dan ancaman stabilitas tata kelola pemerintahan (Rerata Urgensi >= 3.8/5).",
            }

        # 2. Kriteria TEMATIK (Payung Perencanaan & Agenda Program Kerja Nasional)
        thematic_keywords = [
            "karhutla", "kebakaran hutan", "kabut asap", "asap", "iklim", "krisis iklim",
            "climate", "lingkungan", "bencana alam", "bencana", "itb", "teknologi",
            "inovasi", "emjm", "erasmus", "beasiswa", "kampus", "pendidikan", "mahasiswa",
            "rkp", "reformasi birokrasi", "pangan", "investasi", "asean", "ktt asean",
            "musrenbang", "kemiskinan", "disabilitas"
        ]
        is_thematic = any(tk in combined for tk in thematic_keywords)

        if is_thematic:
            return {
                "issue_type": "TEMATIK",
                "issue_type_reason": "Payung perencanaan strategis & tema fokus program kerja pembangunan lintas instansi.",
            }

        # 3. Default: AKTUAL (Isu Hangat Publik / Top Trending)
        return {
            "issue_type": "AKTUAL",
            "issue_type_reason": "Masalah publik yang sedang hangat diperbincangkan saat ini dan memerlukan pemantauan respons cepat.",
        }

    def generate_and_save_snapshot(
        self,
        db: Session,
        issue_id: uuid.UUID,
        window_hours: int = 24,
    ) -> TopicSnapshot:
        """Calculate metrics and record a TopicSnapshot entry in the database."""
        metrics = self.calculate_issue_metrics(db, issue_id, window_hours=window_hours)

        snapshot = TopicSnapshot(
            issue_id=issue_id,
            snapshot_time=metrics["snapshot_time"],
            content_count=metrics["current_count"],
            unique_sources=metrics["unique_sources"],
            platform_count=metrics["platform_count"],
            growth_rate=metrics["growth_rate"],
            velocity=metrics["velocity"],
            trending_score=metrics["trending_score"],
            platform_distribution=metrics["platform_distribution"],
            sentiment_distribution=metrics["sentiment_distribution"],
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    def recalculate_all_active_issues(
        self,
        db: Session,
        window_hours: int = 24,
    ) -> List[TopicSnapshot]:
        """Run batch recalculation for all active issue clusters and generate snapshots."""
        active_issues = (
            db.query(IssueCluster)
            .filter(IssueCluster.status == "ACTIVE")
            .all()
        )
        snapshots = []
        for issue in active_issues:
            try:
                snap = self.generate_and_save_snapshot(db, issue.issue_id, window_hours=window_hours)
                snapshots.append(snap)
            except Exception as e:
                logger.error("Failed to generate snapshot for issue %s: %s", issue.issue_id, e)
                db.rollback()

        logger.info("Successfully generated snapshots for %d issues.", len(snapshots))
        return snapshots

    def extract_word_cloud(self, db: Session, limit: int = 28) -> List[Dict]:
        """Extract top N prominent unigram and bigram keywords with category and average urgency.
        Prioritizes formal Indonesian narratives and filters out all bilingual stopwords and UI noise.
        """
        import re
        from collections import Counter
        from app.models.report import Report
        from app.services.intelligence.text_processor import STOPWORDS_ID_EN

        reports = db.query(Report).all()
        kw_counter = Counter()
        kw_urg = {}
        kw_cat = {}

        # English translation dictionary mapping for common terms
        en_to_id = {
            "fires": "Kebakaran", "forest": "Hutan", "wildfire": "Kebakaran Hutan",
            "wildfires": "Kebakaran Hutan", "haze": "Kabut Asap", "transboundary": "Lintas Batas",
            "president": "Presiden", "singapore": "Singapura", "malaysia": "Malaysia",
            "indonesia": "Indonesia", "asean": "ASEAN", "apologised": "Meminta Maaf",
            "apologises": "Meminta Maaf", "blazes": "Kebakaran", "companies": "Perusahaan",
            "action": "Tindakan Tegas", "policy": "Kebijakan", "resignation": "Pengunduran Diri",
            "letter": "Surat Resmi"
        }

        extended_stops = set(STOPWORDS_ID_EN) | {
            "tersebut", "dalam", "menjadi", "sebagai", "bahwa", "pada", "untuk", "dari",
            "yang", "dan", "dengan", "atas", "oleh", "juga", "telah", "bisa", "akan",
            "dapat", "adalah", "ini", "itu", "atau", "secara", "antara", "saat", "belum",
            "sudah", "masih", "namun", "tetapi", "tentang", "mengenai", "yakni", "yaitu",
            "saja", "pun", "deh", "kok", "sih", "dong", "kan", "nih", "tuh", "kah", "lah",
            "nya", "konten", "membahas", "indikator", "terkait", "kait", "satu", "dua",
            "tiga", "banyak", "orang", "pihak", "hal", "kata", "bila", "karena", "agar",
            "bukan", "hanya", "bagi", "lalu", "maka", "tanpa", "selalu", "kembali",
            # Additional English noise & temporal words
            "here", "fast", "via", "amid", "says", "say", "will", "one", "two", "three",
            "first", "last", "year", "years", "month", "months", "day", "days", "week",
            "weeks", "time", "times", "still", "come", "get", "well", "good", "all"
        }

        # Canonical entity mapping to consolidate overlapping keywords
        entity_canonical_map = {
            "prabowo": "Prabowo Subianto",
            "subianto": "Prabowo Subianto",
            "prabowo subianto": "Prabowo Subianto",
            "presiden prabowo": "Prabowo Subianto",
            "gibran": "Gibran Rakabuming",
            "rakabuming": "Gibran Rakabuming",
            "gibran rakabuming": "Gibran Rakabuming",
            "wapres gibran": "Gibran Rakabuming",
            "listyo": "Jenderal Listyo Sigit",
            "listyo sigit": "Jenderal Listyo Sigit",
            "sigit prabowo": "Jenderal Listyo Sigit",
            "suyudi": "Kapolri Suyudi",
            "suyudi ario": "Kapolri Suyudi",
            "suyudi ario seto": "Kapolri Suyudi",
            "kapolri jenderal": "Kapolri Suyudi",
            "itb": "Institut Teknologi Bandung",
            "teknologi bandung": "Institut Teknologi Bandung",
            "kpu": "KPU RI",
            "pemilihan umum": "KPU RI",
            "kebakaran hutan": "Kebakaran Hutan",
            "kebakaran lahan": "Kebakaran Hutan",
            "hutan lahan": "Kebakaran Hutan",
            "kabut asap": "Kabut Asap",
            "asap karhutla": "Kabut Asap",
            "dugaan penyadapan": "Dugaan Penyadapan",
            "penyadapan presiden": "Dugaan Penyadapan",
            "pinjol ilegal": "Pinjol Ilegal",
            "judi online": "Judi Online",
            "judol": "Judi Online",
        }

        for r in reports:
            # Filter ketat: Eksklusikan temuan Non-Isu dan status REJECTED
            if (r.ai_predicted_label and r.ai_predicted_label == "Non-Isu") or r.status == "REJECTED" or r.review_decision == "REJECTED":
                continue

            u = 3.0
            if r.ai_output and isinstance(r.ai_output, dict):
                u = float(r.ai_output.get("urgency_score", 3.0))
            elif r.ai_risk_level == "TINGGI":
                u = 4.0
            elif r.ai_risk_level == "SEDANG":
                u = 3.0
            cat = r.ai_predicted_label or "Politik"

            text = (str(r.indonesian_content or "") + " " + str(r.ai_summary or "")).strip()
            if not text:
                continue

            clean = re.sub(r"[^\w\s-]", " ", text)
            raw_tokens = clean.split()

            tokens = []
            for t in raw_tokens:
                tl = t.lower()
                if tl in en_to_id:
                    tokens.append(en_to_id[tl])
                elif len(t) >= 3 and tl not in extended_stops and not t.isdigit():
                    norm = t.capitalize() if t.islower() else (t if t.isupper() else t.capitalize())
                    if norm.lower() not in extended_stops:
                        tokens.append(norm)

            for tok in tokens:
                if len(tok) < 3 or tok.lower() in extended_stops:
                    continue
                # Apply canonical entity consolidation
                final_term = entity_canonical_map.get(tok.lower(), tok)
                kw_counter[final_term] += 1
                kw_cat[final_term] = cat
                if final_term not in kw_urg:
                    kw_urg[final_term] = []
                kw_urg[final_term].append(u)

            for i in range(len(tokens) - 1):
                t1, t2 = tokens[i], tokens[i + 1]
                if t1.lower() not in extended_stops and t2.lower() not in extended_stops and t1.lower() != t2.lower():
                    raw_bg = f"{t1} {t2}"
                    final_bg = entity_canonical_map.get(raw_bg.lower(), raw_bg)
                    kw_counter[final_bg] += 1
                    kw_cat[final_bg] = cat
                    if final_bg not in kw_urg:
                        kw_urg[final_bg] = []
                    kw_urg[final_bg].append(u)

        # Deduplicate generic unigrams if a specific bigram containing it is already prevalent
        sorted_candidates = kw_counter.most_common(limit * 2)
        final_items = []
        selected_terms = set()

        for term, cnt in sorted_candidates:
            term_l = term.lower()
            # If term is a single word and already contained in an existing multi-word term with count >= 2
            is_subsumed = False
            if " " not in term:
                for sel in selected_terms:
                    if " " in sel and term_l in sel.lower():
                        is_subsumed = True
                        break
            if is_subsumed:
                continue

            selected_terms.add(term)
            avg_u = round(sum(kw_urg[term]) / max(1, len(kw_urg[term])), 1)
            final_items.append({
                "text": term,
                "count": cnt,
                "avg_urgency": avg_u,
                "category": kw_cat.get(term, "Politik"),
            })
            if len(final_items) >= limit:
                break

        return final_items

    def extract_hot_actors(self, db: Session, limit: int = 8) -> List[Dict]:
        """Extract top prominent political, governmental, and institutional actors
        from 5W+1H summaries and verified content narratives.
        """
        import re
        from collections import Counter
        from app.models.report import Report

        reports = db.query(Report).all()
        actors_dict = {
            "Presiden Prabowo Subianto": [r"\bprabowo\b", r"\bprabowo subianto\b", r"\bpresiden prabowo\b"],
            "Gibran Rakabuming Raka": [r"\bgibran\b", r"\bgibran rakabuming\b", r"\bwapres gibran\b"],
            "Jenderal Listyo Sigit Prabowo": [r"\blistyo\b", r"\blistyo sigit\b"],
            "Kapolri Jenderal Suyudi Ario Seto": [r"\bsuyudi\b", r"\bsuyudi ario seto\b"],
            "Ganjar Pranowo": [r"\bganjar\b", r"\bganjar pranowo\b"],
            "Institut Teknologi Bandung (ITB)": [r"\bitb\b", r"\binstitut teknologi bandung\b"],
            "Komisi Pemilihan Umum (KPU)": [r"\bkpu\b", r"\bkomisi pemilihan umum\b"],
            "Bareskrim Polri": [r"\bbareskrim\b", r"\bbareskrim polri\b"],
            "BNPB Indonesia": [r"\bbnpb\b", r"\bbadan nasional penanggulangan bencana\b"],
            "Paspampres RI": [r"\bpaspampres\b"],
            "Kementerian Lingkungan Hidup": [r"\bklhk\b", r"\bkementerian lingkungan hidup\b"],
            "Google Developer Groups (GDGoC)": [r"\bgdgoc\b", r"\bgoogle developer groups\b"],
            "Kementerian Luar Negeri RI": [r"\bkemlu\b", r"\bkementerian luar negeri\b"],
        }

        counts = Counter()
        actor_urg = {}
        actor_cat = {}

        for r in reports:
            # Filter ketat: Eksklusikan temuan Non-Isu dan status REJECTED
            if (r.ai_predicted_label and r.ai_predicted_label == "Non-Isu") or r.status == "REJECTED" or r.review_decision == "REJECTED":
                continue

            u = 3.0
            if r.ai_output and isinstance(r.ai_output, dict):
                u = float(r.ai_output.get("urgency_score", 3.0))
            elif r.ai_risk_level == "TINGGI":
                u = 4.0
            cat = r.ai_predicted_label or "Politik"

            text_c = str(r.indonesian_content or "") + " " + str(r.ai_summary or "")
            who_f = ""
            if r.ai_output and isinstance(r.ai_output, dict):
                who_f = str(r.ai_output.get("summary_5w1h", {}).get("who") or "")

            combined = (who_f + " " + text_c).lower()

            for actor_name, patterns in actors_dict.items():
                matched = False
                for pat in patterns:
                    if re.search(pat, combined, re.IGNORECASE):
                        matched = True
                        break
                if matched:
                    counts[actor_name] += 1
                    actor_cat[actor_name] = cat
                    if actor_name not in actor_urg:
                        actor_urg[actor_name] = []
                    actor_urg[actor_name].append(u)

        items = []
        for act, cnt in counts.most_common(limit):
            avg_u = round(sum(actor_urg[act]) / max(1, len(actor_urg[act])), 1)
            items.append({
                "name": act,
                "mentions": cnt,
                "category": actor_cat.get(act, "Politik"),
                "avg_urgency": avg_u,
            })
        return items
