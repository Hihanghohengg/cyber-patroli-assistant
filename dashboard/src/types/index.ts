export interface User {
  user_id: string;
  username: string;
  full_name?: string;
  role: string;
  is_active: boolean;
}

export interface PlatformStat {
  platform: string;
  count: number;
  percentage: number;
}

export interface SentimentStat {
  sentiment: string;
  count: number;
  percentage: number;
}

export interface CategoryStat {
  category: string;
  count: number;
}

export interface TrendingTopicItem {
  issue_id: string;
  title: string;
  canonical_name: string;
  category: string;
  status: string;
  trending_score: number;
  content_count: number;
  platform_count: number;
  growth_rate: number;
  velocity: number;
  first_seen_at?: string;
  last_seen_at?: string;
  top_keywords: string[];
  top_hashtags: string[];
  sentiment_dominant: string;
}

export interface OverviewStats {
  total_contents: number;
  contents_last_24h: number;
  active_issues_count: number;
  pending_validations_count: number;
  high_risk_contents_count: number;
  platforms: PlatformStat[];
  sentiments: SentimentStat[];
  top_categories: CategoryStat[];
  latest_trending: TrendingTopicItem[];
}

export interface TopicTimelinePoint {
  snapshot_time: string;
  content_count: number;
  trending_score: number;
  growth_rate: number;
  velocity: number;
  platform_distribution: Record<string, number>;
  sentiment_distribution: Record<string, number>;
}

export interface KeywordCloudItem {
  text: string;
  value: number;
}

export interface SourceItem {
  source_name: string;
  platform: string;
  content_count: number;
  url?: string;
}

export interface TrendingDetail {
  issue: TrendingTopicItem;
  description?: string;
  named_entities: string[];
  w5h1_summary: {
    what?: string;
    who?: string;
    when_info?: string;
    where_info?: string;
    why?: string;
    how?: string;
  };
  platform_breakdown: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
  timeline: TopicTimelinePoint[];
  keywords: KeywordCloudItem[];
  sources: SourceItem[];
}

export interface Analysis5W1H {
  what?: string;
  who?: string;
  when_info?: string;
  where_info?: string;
  why?: string;
  how?: string;
  summary?: string;
  main_topic?: string;
  sub_topics: string[];
  keywords: string[];
  hashtags: string[];
  named_entities: string[];
  sentiment?: string;
  tone?: string;
  category?: string;
  relevance_score: number;
  urgency_score: number;
  confidence_score: number;
  misinfo_indicators: string[];
}

export interface ContentItem {
  content_id: string;
  platform: string;
  url: string;
  title?: string;
  caption_snippet?: string;
  author_username?: string;
  status: string;
  category?: string;
  sentiment?: string;
  risk_level?: string;
  created_at: string;
  screenshot_url?: string;
  issue_title?: string;
}

export interface ContentDetail {
  content_id: string;
  platform: string;
  url: string;
  title?: string;
  caption?: string;
  transcript?: string;
  author: {
    username?: string;
    display_name?: string;
    profile_url?: string;
    followers_count?: number;
    is_verified?: boolean;
    bio?: string;
  };
  interaction: {
    likes_count?: number;
    views_count?: number;
    comments_count?: number;
    shares_count?: number;
  };
  created_at: string;
  status: string;
  report_id?: string;
  ai_patrol?: {
    status?: string;
    predicted_label?: string;
    risk_level?: string;
    confidence_score?: number;
    summary?: string;
    reasoning?: any;
    ticket_number?: string;
    human_decision?: string;
    final_label?: string;
    final_risk?: string;
    correction_notes?: string;
    validated_at?: string;
  };
  analysis_5w1h?: Analysis5W1H;
  evidences: Array<{
    evidence_id: string;
    source_type: string;
    sha256: string;
    storage_path: string;
    mime_type: string;
    created_at?: string;
  }>;
  assigned_issue?: {
    issue_id: string;
    title: string;
    category: string;
    similarity_score: number;
  };
}

export interface DashboardV1Summary {
  total_laporan: number;
  distribusi_kategori: Record<string, number>;
  distribusi_risiko: Record<string, number>;
  distribusi_platform: Record<string, number>;
  rasio_persetujuan_ai: {
    setuju_pct: number;
    ubah_pct: number;
    tolak_pct: number;
    total_dievaluasi: number;
  };
}

export interface TopEntityItem {
  id: string;
  name: string;
  category: string;
  count: number;
  status?: string;
}

export interface KnowledgeEntryItem {
  entry_id: string;
  ticket_number: string;
  content_summary: string;
  verified_category: string;
  verified_risk: string;
  analyst_decision: string;
  analyst_notes?: string;
  source_platform?: string;
  has_embedding: boolean;
  is_active: boolean;
  created_at?: string;
}

export interface EntityItem {
  entity_id: string;
  canonical_name: string;
  entity_type: 'TOPIC' | 'ACTOR' | 'SOURCE';
  category?: string;
  status: 'APPROVED' | 'PENDING_REVIEW' | 'MERGED';
  merged_into_id?: string;
  aliases: string[];
  created_at?: string;
}

export interface PatrolUserItem {
  id: string;
  telegram_id: number;
  username?: string;
  full_name?: string;
  role: 'OPERATOR' | 'ANALYST' | 'ADMIN';
  is_active: boolean;
  created_at?: string;
}

export interface AuditLogItem {
  id: string;
  user_id?: string;
  actor_username?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: any;
  ip_address?: string;
  timestamp: string;
}


