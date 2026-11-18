"""Extractor implementation for Facebook (facebook.com & fb.watch)."""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.services.extractors.base import BasePlatformExtractor, ExtractedPost


class FacebookExtractor(BasePlatformExtractor):
    platform_name = "facebook"
    supported_domains = ("facebook.com", "fb.watch")

    @classmethod
    def clean_url(cls, url: str) -> str:
        if not url:
            return ""
        try:
            parsed = urlparse(url.strip())
            qs = parse_qs(parsed.query)
            tracking_params = {"fbclid", "ref", "ref_src", "extid", "hc_ref", "fref"}
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

        # Post ID
        post_id = None
        m_post = re.search(r"/(?:posts|videos|reel)/([A-Za-z0-9_-]+)", clean_url)
        if m_post:
            post_id = m_post.group(1)
        else:
            m_id = re.search(r"[?&]story_fbid=([A-Za-z0-9_-]+)", clean_url)
            if m_id:
                post_id = m_id.group(1)

        # Author Username
        author_username = payload.get("username")
        if not author_username or author_username.lower() in ("facebook.com", "anonim"):
            fb_m = re.search(r"facebook\.com/(?:pages/)?([a-zA-Z0-9_\.]{3,30})/(?:posts|videos|reel|\?)", clean_url, re.IGNORECASE)
            if fb_m and fb_m.group(1).lower() not in ["profile.php", "home.php", "watch", "photo", "groups", "reel"]:
                author_username = fb_m.group(1)
            else:
                author_username = "Anonim"

        raw_text = payload.get("caption") or payload.get("notes") or ""
        clean_text = raw_text
        if clean_text:
            clean_text = re.sub(r"[ \t]+", " ", clean_text)
            clean_text = re.sub(r"\n\s*\n\s*\n+", "\n\n", clean_text).strip()

        title = payload.get("title")
        if not title and clean_text:
            first_sent = clean_text.split("\n")[0].split(".")[0].strip()
            title = first_sent[:80] + ("..." if len(first_sent) > 80 else "")

        has_media = bool(payload.get("has_media", False) or payload.get("screenshot_base64"))

        return ExtractedPost(
            platform="facebook",
            canonical_url=clean_url,
            post_id=post_id,
            author_username=author_username,
            author_display_name=payload.get("display_name") or f"@{author_username}",
            title=title,
            clean_text=clean_text,
            should_crawl_server=False,
            has_media=has_media,
            likes_count=payload.get("likes_count"),
            views_count=payload.get("views_count"),
            comments_count=payload.get("comments_count"),
            shares_count=payload.get("shares_count"),
            extra_metadata={"is_facebook_post": bool(post_id)},
        )
