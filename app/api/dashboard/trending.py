"""Trending Topics API endpoints.

Lists, inspects, and analyzes detected trending issues, their timelines,
keyword clouds, associated social contents, and accounts.
"""

import logging
from typing import List, Optional, Set, Dict, Any
from uuid import UUID
from collections import Counter, defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.intelligence import IssueCluster, IssueContent, TopicSnapshot, ContentAnalysis
from app.models.report import Content, Account, Report
from app.auth.dependencies import get_current_user
from app.services.intelligence.trending_engine import TrendingEngine
from app.schemas.dashboard import (
    TrendingTopicItem,
    TopicRelatedContent,
    TrendingDetailResponse,
    TopicTimelinePoint,
    KeywordCloudItem,
    SourceItem,
    ContentListItem,
    WordCloudItem,
    HotActorItem,
    TrendingDashboardResponse,
)

router = APIRouter(prefix="/trending", tags=["Dashboard Trending Topics"])


@router.get("", response_model=TrendingDashboardResponse)
def list_trending_topics(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title or keyword"),
    status: str = Query("ACTIVE", description="ACTIVE, ARCHIVED, or ALL"),
    issue_type: Optional[str] = Query(None, description="Filter by issue type: AKTUAL, KRITIKAL, TEMATIK, or ALL"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List trending topics sorted by trending score and recency with word cloud and hot actors."""
    import re
    # Normalize when invoked directly as function in unit tests
    eff_status = status if isinstance(status, str) else "ACTIVE"
    eff_category = category if isinstance(category, str) else None
    eff_search = search if isinstance(search, str) else None
    eff_issue_type = issue_type if isinstance(issue_type, str) else None
    eff_limit = limit if isinstance(limit, int) else 50

    query = db.query(IssueCluster)

    # Filter ketat: Eksklusikan kategori Non-Isu dari Radar Isu Nasional kecuali dicari spesifik
    if not eff_category or eff_category.upper() != "NON-ISU":
        query = query.filter(IssueCluster.category != "Non-Isu")

    if eff_status != "ALL":
        query = query.filter(IssueCluster.status == eff_status)

    if eff_category and eff_category.upper() != "ALL":
        query = query.filter(IssueCluster.category == eff_category)

    # Sort by last_seen_at desc (ambil kumpulan kandidat aktif)
    issues = query.order_by(desc(IssueCluster.last_seen_at)).limit(eff_limit).all()

    # Batch query for linked contents across the retrieved issues
    issue_ids = [issue.issue_id for issue in issues]
    issue_contents_map = {iid: [] for iid in issue_ids}
    issue_actors_map: Dict[Any, Set[str]] = defaultdict(set)

    prominent_actors_dict = {
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

    if issue_ids:
        try:
            links = (
                db.query(
                    IssueContent.issue_id,
                    Content.content_id,
                    Content.title,
                    Content.caption_text,
                    Content.platform,
                    Account.username,
                    Report.ai_risk_level,
                )
                .join(Content, IssueContent.content_id == Content.content_id)
                .outerjoin(Account, Content.account_id == Account.account_id)
                .outerjoin(Report, Content.content_id == Report.content_id)
                .filter(IssueContent.issue_id.in_(issue_ids))
                .order_by(IssueContent.similarity_score.desc())
                .all()
            )
            for row in links:
                iid = row[0]
                # Deteksi tokoh terkait dari teks judul/narasi konten
                c_title_raw = row[2] or ""
                c_caption_raw = row[3] or ""
                combined_txt = f"{c_title_raw} {c_caption_raw}".lower()
                for act_name, pats in prominent_actors_dict.items():
                    if any(re.search(pat, combined_txt, re.IGNORECASE) for pat in pats):
                        issue_actors_map[iid].add(act_name)

                if len(issue_contents_map[iid]) < 4:
                    cid = row[1]
                    if any(rc.content_id == cid for rc in issue_contents_map[iid]):
                        continue
                    c_title = row[2] or (row[3][:70] + "..." if row[3] else "Temuan Tanpa Judul")
                    plat = row[4] or "web"
                    uname = row[5] or "anon"
                    risk = row[6] or "SEDANG"
                    urgency = 4.5 if risk == "TINGGI" else (3.0 if risk == "SEDANG" else 2.0)
                    issue_contents_map[iid].append(
                        TopicRelatedContent(
                            content_id=cid,
                            title=c_title,
                            platform=plat,
                            author_username=uname,
                            urgency_score=urgency,
                        )
                    )
        except Exception as ex:
            logger.warning("Gagal memuat related_contents isu: %s", ex)

    engine = TrendingEngine()
    items: List[TrendingTopicItem] = []
    junk_patterns = [
        r"^#?non-?isu", r"^#?(politik|keamanan|sosial|ekonomi|budaya|ideologi|pertahanan)$",
        r"relevant\s+people", r"disukai\s+oleh", r"follkative", r"zgtyriwul",
        r"\bvivanews\b", r"\bisu\s+(am|pm|meet|url)\b", r"instagram post [a-z0-9_-]+"
    ]

    for issue in issues:
        # Filter keluar judul sampah scraping UI
        if any(re.search(pat, issue.title or "", re.IGNORECASE) for pat in junk_patterns):
            continue
        try:
            m = engine.calculate_issue_metrics(db, issue.issue_id, window_hours=24)
            dominant_sent = "NETRAL"
            if m.get("sentiment_distribution"):
                dominant_sent = max(m["sentiment_distribution"], key=m["sentiment_distribution"].get)

            # Extract hashtag from title or top_hashtags
            hashtag_val = None
            h_match = re.search(r"(#[a-zA-Z0-9_]+)", issue.title or "")
            if h_match:
                hashtag_val = h_match.group(1)
            elif issue.hashtags and len(issue.hashtags) > 0:
                hashtag_val = issue.hashtags[0]
            else:
                cat_clean = re.sub(r"[^\w]", "", issue.category or "Isu")
                hashtag_val = f"#{cat_clean}"

            detected_actors = sorted(list(issue_actors_map.get(issue.issue_id, set())))
            cluster_entities = sorted(list(set((issue.named_entities or []) + detected_actors)))

            items.append(
                TrendingTopicItem(
                    issue_id=issue.issue_id,
                    title=issue.title,
                    canonical_name=issue.canonical_name,
                    category=issue.category or "Lainnya",
                    status=issue.status,
                    trending_score=m["trending_score"],
                    content_count=m["total_count"],
                    platform_count=m["platform_count"],
                    growth_rate=m["growth_rate"],
                    velocity=m["velocity"],
                    first_seen_at=issue.first_seen_at,
                    last_seen_at=issue.last_seen_at,
                    top_keywords=issue.keywords[:5] if issue.keywords else [],
                    top_hashtags=issue.hashtags[:5] if issue.hashtags else [],
                    sentiment_dominant=dominant_sent,
                    escalation_label=m["escalation_label"],
                    avg_urgency=m["avg_urgency"],
                    recent_count_24h=m["recent_count_24h"],
                    total_interactions=m["total_interactions"],
                    issue_type=m.get("issue_type", "AKTUAL"),
                    issue_type_reason=m.get("issue_type_reason"),
                    hashtag=hashtag_val,
                    named_entities=cluster_entities,
                    actors=detected_actors,
                    related_contents=issue_contents_map.get(issue.issue_id, []),
                )
            )
        except Exception as ex:
            logger.warning("Gagal menghitung HotScore isu %s: %s", issue.issue_id, ex)
            cat_tag = re.sub(r'[^a-zA-Z0-9_]', '', issue.category or 'Isu')
            fallback_h = f"#{cat_tag}"
            detected_actors_fb = sorted(list(issue_actors_map.get(issue.issue_id, set())))
            cluster_entities_fb = sorted(list(set((issue.named_entities or []) + detected_actors_fb)))
            items.append(
                TrendingTopicItem(
                    issue_id=issue.issue_id,
                    title=issue.title,
                    canonical_name=issue.canonical_name,
                    category=issue.category or "Lainnya",
                    status=issue.status,
                    trending_score=50.0,
                    content_count=1,
                    platform_count=1,
                    growth_rate=0.0,
                    velocity=0.0,
                    first_seen_at=issue.first_seen_at,
                    last_seen_at=issue.last_seen_at,
                    top_keywords=issue.keywords[:5] if issue.keywords else [],
                    top_hashtags=issue.hashtags[:5] if issue.hashtags else [],
                    sentiment_dominant="NETRAL",
                    escalation_label="PANTAU",
                    avg_urgency=2.5,
                    recent_count_24h=0,
                    total_interactions=0,
                    issue_type="AKTUAL",
                    issue_type_reason="Isu publik umum.",
                    hashtag=fallback_h,
                    named_entities=cluster_entities_fb,
                    actors=detected_actors_fb,
                    related_contents=issue_contents_map.get(issue.issue_id, []),
                )
            )

    # Sort by trending score descending
    items.sort(key=lambda x: x.trending_score, reverse=True)

    # Assign sequential rank 1..N
    for idx, itm in enumerate(items, 1):
        itm.rank = idx

    # Calculate Pilar Totals before filtering by issue_type or search
    total_critical = sum(1 for it in items if it.issue_type == "KRITIKAL")
    total_actual = sum(1 for it in items if it.issue_type == "AKTUAL")
    total_thematic = sum(1 for it in items if it.issue_type == "TEMATIK")

    # Filter by issue_type if specified and not 'ALL'
    filtered_items = items
    if eff_issue_type and eff_issue_type.upper() != "ALL":
        filtered_items = [it for it in filtered_items if it.issue_type.upper() == eff_issue_type.upper()]

    # Filter by search if specified (flexible match across multiple fields)
    if eff_search:
        s_low = eff_search.lower().strip()
        filtered_items = [
            it for it in filtered_items
            if s_low in it.title.lower()
            or s_low in it.canonical_name.lower()
            or any(s_low in kw.lower() for kw in it.top_keywords)
            or (it.hashtag and s_low in it.hashtag.lower())
            or any(s_low in (rc.title or "").lower() for rc in it.related_contents)
        ]

    # Extract dynamic Word Cloud and Hot Actors
    word_cloud_raw = engine.extract_word_cloud(db, limit=28)
    word_cloud_items = [WordCloudItem(**wc) for wc in word_cloud_raw]

    hot_actors_raw = engine.extract_hot_actors(db, limit=8)
    hot_actor_items = [HotActorItem(**ha) for ha in hot_actors_raw]

    return TrendingDashboardResponse(
        topics=filtered_items,
        word_cloud=word_cloud_items,
        hot_actors=hot_actor_items,
        total_topics=len(items),
        total_critical=total_critical,
        total_actual=total_actual,
        total_thematic=total_thematic,
    )


@router.get("/{issue_id}", response_model=TrendingDetailResponse)
def get_trending_topic_detail(
    issue_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Retrieve in-depth details of a specific issue topic with aggregated 5W+1H."""
    issue = db.query(IssueCluster).filter(IssueCluster.issue_id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Topik tidak ditemukan")

    # Fetch snapshots for timeline
    snapshots = (
        db.query(TopicSnapshot)
        .filter(TopicSnapshot.issue_id == issue_id)
        .order_by(TopicSnapshot.snapshot_time.asc())
        .limit(48)
        .all()
    )

    last_snap = snapshots[-1] if snapshots else None

    # Fetch connected contents and analyses for 5W+1H synthesis
    contents_junction = (
        db.query(IssueContent, Content)
        .join(Content, IssueContent.content_id == Content.content_id)
        .filter(IssueContent.issue_id == issue_id)
        .all()
    )

    content_ids = [c.content_id for _, c in contents_junction]
    analyses = (
        db.query(ContentAnalysis)
        .filter(ContentAnalysis.content_id.in_(content_ids))
        .all()
    ) if content_ids else []

    # Synthesize 5W+1H
    w5h1 = {
        "what": None,
        "who": None,
        "when_info": None,
        "where_info": None,
        "why": None,
        "how": None,
    }
    all_keywords: List[str] = []
    platform_counts: dict = {}
    sentiment_counts: dict = {"POSITIF": 0, "NEGATIF": 0, "NETRAL": 0, "CAMPURAN": 0}

    for _, c in contents_junction:
        p = (c.platform or "other").lower()
        platform_counts[p] = platform_counts.get(p, 0) + 1

    for a in analyses:
        for k in ["what", "who", "when_info", "where_info", "why", "how"]:
            val = getattr(a, k, None)
            if val and not w5h1[k]:
                w5h1[k] = val
        if a.keywords:
            all_keywords.extend(a.keywords)
        s = (a.sentiment or "NETRAL").upper()
        sentiment_counts[s] = sentiment_counts.get(s, 0) + 1

    # Fallback to issue description if what is empty
    if not w5h1["what"]:
        w5h1["what"] = issue.description or issue.title

    # Keyword cloud
    kw_counter = Counter(all_keywords)
    cloud_items = [
        KeywordCloudItem(text=k, value=v)
        for k, v in kw_counter.most_common(25)
    ]

    # Timeline points
    timeline_pts = [
        TopicTimelinePoint(
            snapshot_time=s.snapshot_time,
            content_count=s.content_count,
            trending_score=s.trending_score,
            growth_rate=s.growth_rate,
            velocity=s.velocity,
            platform_distribution=s.platform_distribution or {},
            sentiment_distribution=s.sentiment_distribution or {},
        )
        for s in snapshots
    ]

    # Top sources / accounts
    source_items: List[SourceItem] = []
    author_counts = Counter(c.account_id for _, c in contents_junction if c.account_id)
    for acc_id, count in author_counts.most_common(10):
        acc = db.query(Account).filter(Account.account_id == acc_id).first()
        if acc:
            source_items.append(
                SourceItem(
                    source_name=acc.username or acc.display_name or "Anonim",
                    platform=acc.platform,
                    content_count=count,
                    url=acc.profile_url if hasattr(acc, 'profile_url') else None,
                )
            )

    issue_item = TrendingTopicItem(
        issue_id=issue.issue_id,
        title=issue.title,
        canonical_name=issue.canonical_name,
        category=issue.category or "Lainnya",
        status=issue.status,
        trending_score=last_snap.trending_score if last_snap else 50.0,
        content_count=len(contents_junction),
        platform_count=len(platform_counts),
        growth_rate=last_snap.growth_rate if last_snap else 0.0,
        velocity=last_snap.velocity if last_snap else 0.0,
        first_seen_at=issue.first_seen_at,
        last_seen_at=issue.last_seen_at,
        top_keywords=issue.keywords[:8] if issue.keywords else [],
        top_hashtags=issue.hashtags[:8] if issue.hashtags else [],
        sentiment_dominant="NETRAL",
    )

    return TrendingDetailResponse(
        issue=issue_item,
        description=issue.description,
        named_entities=issue.named_entities or [],
        w5h1_summary=w5h1,
        platform_breakdown=platform_counts,
        sentiment_breakdown=sentiment_counts,
        timeline=timeline_pts,
        keywords=cloud_items,
        sources=source_items,
    )


@router.get("/{issue_id}/contents", response_model=List[ContentListItem])
def get_contents_for_topic(
    issue_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Fetch all contents grouped under this issue cluster."""
    junctions = (
        db.query(IssueContent, Content)
        .join(Content, IssueContent.content_id == Content.content_id)
        .filter(IssueContent.issue_id == issue_id)
        .order_by(desc(Content.created_at))
        .all()
    )

    items: List[ContentListItem] = []
    for _, c in junctions:
        analysis = (
            db.query(ContentAnalysis)
            .filter(ContentAnalysis.content_id == c.content_id)
            .first()
        )
        author = db.query(Account).filter(Account.account_id == c.account_id).first() if c.account_id else None

        caption_str = getattr(c, "caption_text", "") or ""
        caption_snip = (caption_str[:150] + "...") if len(caption_str) > 150 else caption_str

        items.append(
            ContentListItem(
                content_id=c.content_id,
                platform=c.platform,
                url=c.canonical_url or "",
                title=c.title or "Tanpa Judul",
                caption_snippet=caption_snip,
                author_username=author.username if author else None,
                status="VALIDATED" if getattr(c, "status", None) == "VALIDATED" else "ACTIVE",
                category=analysis.category if analysis else "Lainnya",
                sentiment=analysis.sentiment if analysis else "NETRAL",
                risk_level="RENDAH",
                created_at=c.created_at,
                screenshot_url=f"/api/dashboard/contents/{c.content_id}/screenshot",
                issue_title=None,
            )
        )
    return items


@router.post("/recalculate")
def trigger_trending_recalculation(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manually trigger recalculation of trending scores across all active issues."""
    engine = TrendingEngine()
    snapshots = engine.recalculate_all_active_issues(db, window_hours=24)
    return {
        "status": "success",
        "message": f"Berhasil menghitung ulang skor trending untuk {len(snapshots)} isu aktif.",
        "snapshots_generated": len(snapshots),
    }
