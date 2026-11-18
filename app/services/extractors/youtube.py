"""Extractor implementation for YouTube (youtube.com & youtu.be)."""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.services.extractors.base import BasePlatformExtractor, ExtractedPost


class YouTubeExtractor(BasePlatformExtractor):
    platform_name = "youtube"
    supported_domains = ("youtube.com", "youtu.be")

    @classmethod
    def clean_url(cls, url: str) -> str:
        if not url:
            return ""
        try:
            parsed = urlparse(url.strip())
            qs = parse_qs(parsed.query)
            # Keep 'v' parameter for video identity
            allowed_params = {"v"}
            cleaned_qs = {k: v for k, v in qs.items() if k in allowed_params}
            new_query = urlencode(cleaned_qs, doseq=True)
            new_path = parsed.path.rstrip("/") if len(parsed.path) > 1 else parsed.path
            return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, new_query, ""))
        except Exception:
            return url.strip().rstrip("/")

    @classmethod
    def extract(cls, raw_url: str, payload_data: Optional[Dict[str, Any]] = None) -> ExtractedPost:
        clean_url = cls.clean_url(raw_url)
        payload = payload_data or {}

        # Video ID (11 chars)
        video_id = None
        m_vid = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", clean_url)
        if m_vid:
            video_id = m_vid.group(1)

        # Author / Channel
        author_username = payload.get("username")
        if not author_username or author_username.lower() in ("youtube.com", "anonim"):
            yt_m = re.search(r"youtube\.com/@([a-zA-Z0-9_\.]+)", clean_url, re.IGNORECASE)
            if yt_m:
                author_username = yt_m.group(1)
            else:
                author_username = "Anonim"

        if video_id:
            canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            canonical_url = clean_url

        raw_text = payload.get("caption") or payload.get("notes") or ""
        clean_text = raw_text.strip()
        title = payload.get("title") or (clean_text[:80] if clean_text else "Video YouTube")

        return ExtractedPost(
            platform="youtube",
            canonical_url=canonical_url,
            post_id=video_id,
            author_username=author_username,
            author_display_name=payload.get("display_name") or f"@{author_username}",
            title=title,
            clean_text=clean_text,
            should_crawl_server=True,  # YouTubeScraper yt-dlp enrichment is fast and safe
            has_media=True,
            likes_count=payload.get("likes_count"),
            views_count=payload.get("views_count"),
            comments_count=payload.get("comments_count"),
            shares_count=payload.get("shares_count"),
            extra_metadata={"video_id": video_id},
        )
