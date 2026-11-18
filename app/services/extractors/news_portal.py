"""Extractor implementation for news portals and open web articles."""

from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.services.extractors.base import BasePlatformExtractor, ExtractedPost


class NewsPortalExtractor(BasePlatformExtractor):
    platform_name = "web"
    supported_domains = ()  # Default fallback for any http/https URL

    @classmethod
    def clean_url(cls, url: str) -> str:
        if not url:
            return ""
        try:
            parsed = urlparse(url.strip())
            qs = parse_qs(parsed.query)
            tracking_params = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "ref"}
            cleaned_qs = {k: v for k, v in qs.items() if k.lower() not in tracking_params}
            new_query = urlencode(cleaned_qs, doseq=True)
            new_path = parsed.path.rstrip("/") if len(parsed.path) > 1 else parsed.path
            return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, new_query, ""))
        except Exception:
            return url.strip().rstrip("/")

    @classmethod
    def extract(cls, raw_url: str, payload_data: Optional[Dict[str, Any]] = None) -> ExtractedPost:
        clean_url = cls.clean_url(raw_url)
        payload = payload_data or {}

        parsed = urlparse(clean_url)
        domain = parsed.netloc.replace("www.", "")

        author_username = payload.get("username") or domain or "Anonim"
        raw_text = payload.get("caption") or payload.get("notes") or ""
        clean_text = raw_text.strip()

        title = payload.get("title") or (clean_text[:80] if clean_text else domain)

        # Decide if server Playwright crawl is needed
        is_client_ext = payload.get("source_channel") == "BROWSER_EXTENSION"
        has_client_content = bool(len(clean_text) >= 30 or payload.get("screenshot_base64"))
        should_crawl = not (is_client_ext and has_client_content)

        return ExtractedPost(
            platform="web",
            canonical_url=clean_url,
            post_id=clean_url,
            author_username=author_username,
            author_display_name=payload.get("display_name") or author_username,
            title=title,
            clean_text=clean_text,
            should_crawl_server=should_crawl,
            has_media=bool(payload.get("screenshot_base64") or payload.get("has_media")),
            likes_count=payload.get("likes_count"),
            views_count=payload.get("views_count"),
            comments_count=payload.get("comments_count"),
            shares_count=payload.get("shares_count"),
            extra_metadata={"domain": domain},
        )
