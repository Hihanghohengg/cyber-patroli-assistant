"""Topic clustering service for grouping related content items into IssueClusters.

Uses TF-IDF feature extraction, cosine similarity matching, and keyword overlap
to cluster incoming patrol findings and detect narrative threads across platforms.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.intelligence import IssueCluster, IssueContent, ContentAnalysis
from app.models.report import Content
from app.services.intelligence.text_processor import IndonesianTextProcessor

logger = logging.getLogger(__name__)

# Fallback TF-IDF or Jaccard
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("scikit-learn not available. Falling back to Jaccard similarity.")

# Thresholds
DEFAULT_SIMILARITY_THRESHOLD = 0.30
HIGH_CONFIDENCE_THRESHOLD = 0.55


class TopicClusteringService:
    """Clustering service that matches contents to existing issues or creates new ones."""

    def __init__(self, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD):
        self.similarity_threshold = similarity_threshold
        self.processor = IndonesianTextProcessor()

    def _prepare_corpus_text(
        self,
        title: str = "",
        text: str = "",
        keywords: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        main_topic: str = "",
    ) -> str:
        """Combine all text signals into a single normalized document representation."""
        kw_str = " ".join(keywords or [])
        ht_str = " ".join(hashtags or [])
        combined = f"{main_topic} {title} {text} {kw_str} {ht_str}"
        return self.processor.clean_text(combined).lower()

    def assign_content_to_cluster(
        self,
        db: Session,
        content_id: uuid.UUID,
        analysis: Optional[ContentAnalysis] = None,
    ) -> Tuple[IssueCluster, float, bool]:
        """Match a content item to an existing active IssueCluster or spawn a new one.

        Args:
            db: SQLAlchemy session
            content_id: UUID of the content item
            analysis: Optional pre-fetched ContentAnalysis record

        Returns:
            Tuple of (assigned_issue, similarity_score, is_new_cluster)
        """
        # 1. Fetch content
        content = db.query(Content).filter(Content.content_id == content_id).first()
        if not content:
            raise ValueError(f"Content {content_id} not found")

        # Check if already assigned
        existing_link = (
            db.query(IssueContent)
            .filter(IssueContent.content_id == content_id)
            .first()
        )
        if existing_link:
            existing_issue = db.query(IssueCluster).filter(IssueCluster.issue_id == existing_link.issue_id).first()
            if existing_issue:
                logger.info("Content %s already linked to issue %s", content_id, existing_issue.canonical_name)
                return existing_issue, existing_link.similarity_score, False

        # If analysis not passed, attempt query
        if not analysis:
            analysis = (
                db.query(ContentAnalysis)
                .filter(ContentAnalysis.content_id == content_id)
                .first()
            )

        # 2. Extract content text representation
        title = content.title or ""
        body = content.caption or ""
        keywords = analysis.keywords if analysis and analysis.keywords else self.processor.extract_keywords(f"{title} {body}")
        hashtags = analysis.hashtags if analysis and analysis.hashtags else self.processor.extract_hashtags(body)
        main_topic = analysis.main_topic if analysis and analysis.main_topic else ""
        category = analysis.category if analysis and analysis.category else "Lainnya"

        target_text = self._prepare_corpus_text(
            title=title,
            text=body,
            keywords=keywords,
            hashtags=hashtags,
            main_topic=main_topic,
        )

        # 3. Retrieve active clusters
        active_clusters = (
            db.query(IssueCluster)
            .filter(IssueCluster.status == "ACTIVE")
            .order_by(desc(IssueCluster.last_seen_at))
            .limit(100)
            .all()
        )

        best_cluster: Optional[IssueCluster] = None
        best_score: float = 0.0

        if active_clusters and target_text.strip():
            # Build cluster representation texts
            cluster_texts = []
            for c in active_clusters:
                c_text = self._prepare_corpus_text(
                    title=c.title,
                    text=c.description or "",
                    keywords=c.keywords,
                    hashtags=c.hashtags,
                    main_topic=c.title,
                )
                cluster_texts.append(c_text)

            if HAS_SKLEARN:
                try:
                    all_docs = [target_text] + cluster_texts
                    vectorizer = TfidfVectorizer(min_df=1, stop_words=list(self.processor.stopwords))
                    tfidf_matrix = vectorizer.fit_transform(all_docs)
                    cosine_sims = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

                    for idx, score in enumerate(cosine_sims):
                        if score > best_score:
                            best_score = float(score)
                            best_cluster = active_clusters[idx]
                except Exception as e:
                    logger.warning("TF-IDF similarity calculation failed: %s; falling back to Jaccard", e)
                    best_cluster, best_score = self._match_by_jaccard(target_text, active_clusters)
            else:
                best_cluster, best_score = self._match_by_jaccard(target_text, active_clusters)

        # 4. Decision: Link to best cluster or Create new cluster
        now = datetime.utcnow()
        if best_cluster and best_score >= self.similarity_threshold:
            # Match found! Attach to existing cluster
            logger.info(
                "Matched content %s to cluster '%s' with score %.3f",
                content_id,
                best_cluster.title,
                best_score,
            )

            # Update cluster metadata if novel items exist
            self._enrich_cluster_metadata(best_cluster, keywords, hashtags, analysis)
            best_cluster.last_seen_at = now
            best_cluster.updated_at = now

            junction = IssueContent(
                issue_id=best_cluster.issue_id,
                content_id=content_id,
                similarity_score=round(best_score, 4),
                created_at=now,
            )
            db.add(junction)
            db.commit()
            db.refresh(best_cluster)
            return best_cluster, best_score, False
        else:
            # No sufficient match: Create a new IssueCluster
            cluster_title = main_topic or (title[:120] if title else body[:120]) or "Isu Patroli Baru"
            slug = self.processor.to_canonical_slug(cluster_title)

            # Ensure canonical slug uniqueness
            unique_slug = slug
            counter = 1
            while db.query(IssueCluster).filter(IssueCluster.canonical_name == unique_slug).first():
                unique_slug = f"{slug}-{counter}"
                counter += 1

            new_cluster = IssueCluster(
                title=cluster_title.strip(),
                canonical_name=unique_slug,
                description=analysis.summary if analysis else body[:300],
                category=category,
                keywords=list(set(keywords[:10])) if keywords else [],
                hashtags=list(set(hashtags[:10])) if hashtags else [],
                named_entities=list(set(analysis.named_entities[:10])) if analysis and analysis.named_entities else [],
                status="ACTIVE",
                first_seen_at=content.created_at or now,
                last_seen_at=content.created_at or now,
                created_at=now,
                updated_at=now,
            )
            db.add(new_cluster)
            db.flush()

            junction = IssueContent(
                issue_id=new_cluster.issue_id,
                content_id=content_id,
                similarity_score=1.0,
                created_at=now,
            )
            db.add(junction)
            db.commit()
            db.refresh(new_cluster)

            logger.info("Spawned new issue cluster: '%s' (slug: %s)", new_cluster.title, unique_slug)
            return new_cluster, 1.0, True

    def _match_by_jaccard(
        self,
        target_text: str,
        clusters: List[IssueCluster],
    ) -> Tuple[Optional[IssueCluster], float]:
        """Fallback token overlap matching."""
        best_cluster = None
        best_score = 0.0
        for c in clusters:
            c_text = self._prepare_corpus_text(
                title=c.title,
                text=c.description or "",
                keywords=c.keywords,
                hashtags=c.hashtags,
                main_topic=c.title,
            )
            score = self.processor.compute_jaccard_similarity(target_text, c_text)
            if score > best_score:
                best_score = score
                best_cluster = c
        return best_cluster, best_score

    def _enrich_cluster_metadata(
        self,
        cluster: IssueCluster,
        new_keywords: Optional[List[str]],
        new_hashtags: Optional[List[str]],
        analysis: Optional[ContentAnalysis],
    ) -> None:
        """Merge newly discovered keywords, hashtags, and named entities."""
        existing_kw = set(cluster.keywords or [])
        if new_keywords:
            for kw in new_keywords:
                if len(existing_kw) < 25:
                    existing_kw.add(kw)
        cluster.keywords = list(existing_kw)

        existing_ht = set(cluster.hashtags or [])
        if new_hashtags:
            for ht in new_hashtags:
                if len(existing_ht) < 25:
                    existing_ht.add(ht)
        cluster.hashtags = list(existing_ht)

        if analysis and analysis.named_entities:
            existing_ne = set(cluster.named_entities or [])
            for ne in analysis.named_entities:
                if len(existing_ne) < 25:
                    existing_ne.add(ne)
            cluster.named_entities = list(existing_ne)
