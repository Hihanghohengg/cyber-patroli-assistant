"""Extractor implementation for Instagram (instagram.com)."""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.services.extractors.base import BasePlatformExtractor, ExtractedPost


class InstagramExtractor(BasePlatformExtractor):
    platform_name = "instagram"
    supported_domains = ("instagram.com",)

    @classmethod
    def clean_url(cls, url: str) -> str:
        """Strip social tracking parameters and modal suffixes (/liked_by, /comments)."""
        if not url:
            return ""
        try:
            parsed = urlparse(url.strip())
            qs = parse_qs(parsed.query)
            tracking_params = {
                "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                "fbclid", "igshid", "xmt", "si", "ref", "share_id", "is_from_webapp",
                "sender_device", "feature", "tracking_id", "img_index"
            }
            cleaned_qs = {k: v for k, v in qs.items() if k.lower() not in tracking_params}
            new_query = urlencode(cleaned_qs, doseq=True)
            new_path = parsed.path.rstrip("/") if len(parsed.path) > 1 else parsed.path

            # Clean modal dialog suffixes (/liked_by, /comments, /embed)
            ig_post_match = re.search(r"/(p|reel|reels|tv)/([A-Za-z0-9_-]+)", new_path, re.IGNORECASE)
            if ig_post_match:
                new_path = f"/{ig_post_match.group(1).lower()}/{ig_post_match.group(2)}"

            return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, new_query, ""))
        except Exception:
            clean = url.strip().rstrip("/")
            ig_m = re.search(r"(https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/[A-Za-z0-9_-]+)", clean, re.IGNORECASE)
            return ig_m.group(1) if ig_m else clean

    @classmethod
    def extract(cls, raw_url: str, payload_data: Optional[Dict[str, Any]] = None) -> ExtractedPost:
        clean_url = cls.clean_url(raw_url)
        payload = payload_data or {}

        # 1. Post ID Extraction
        post_id = None
        m_post = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", clean_url, re.IGNORECASE)
        if m_post:
            post_id = m_post.group(1)

        # 2. Author Username Extraction
        author_username = payload.get("username")
        if not author_username or author_username.lower() in ("instagram.com", "anonim"):
            ig_match = re.search(r"instagram\.com/([a-zA-Z0-9_\.]{1,30})/(?:p|reel|reels)/", clean_url, re.IGNORECASE)
            if ig_match and ig_match.group(1).lower() not in ["p", "reel", "reels", "stories", "explore", "direct"]:
                author_username = ig_match.group(1)
            else:
                author_username = "Anonim"

        # 3. Canonical URL
        if post_id:
            seg = "reel" if "/reel/" in clean_url or "/reels/" in clean_url else "p"
            canonical_url = f"https://www.instagram.com/{seg}/{post_id}/"
        else:
            canonical_url = clean_url

        # 4. Clean text
        raw_text = payload.get("caption") or payload.get("notes") or ""
        clean_text = raw_text
        if clean_text:
            clean_text = re.sub(r"^(?:[a-zA-Z0-9_\.]{2,30})?(?:Ikuti|Mengikuti|Follow|Following)\s*(?:[a-zA-Z0-9_\.]{2,30})?\s*\d+\s*(?:jam|hari|menit|detik|m|h|d|w|minggu)?\s*", "", clean_text, flags=re.IGNORECASE).strip()
            clean_text = re.sub(r"^(?:Ikuti|Mengikuti|Follow|Following)\s*", "", clean_text, flags=re.IGNORECASE).strip()
            if author_username and author_username != "Anonim":
                clean_text = re.sub(rf"^{re.escape(author_username)}\s*", "", clean_text, flags=re.IGNORECASE).strip()
            clean_text = re.sub(r"^\d+\s*(?:menit|jam|hari|minggu|detik|m|h|d|w)\s*", "", clean_text, flags=re.IGNORECASE).strip()
            for marker in ["Lihat terjemahan", "See translation", "View translation", "Lihat semua komentar", "View all comments"]:
                if marker in clean_text:
                    clean_text = clean_text.split(marker)[0].strip()
            clean_text = re.sub(r"Disukai oleh.*?lainnya", " ", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"Liked by.*?others", " ", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"[ \t]+", " ", clean_text)
            clean_text = re.sub(r"\n\s*\n\s*\n+", "\n\n", clean_text).strip()

        title = payload.get("title")
        if not title and clean_text:
            first_sent = clean_text.split("\n")[0].split(".")[0].strip()
            title = first_sent[:80] + ("..." if len(first_sent) > 80 else "")

        has_media = bool(payload.get("has_media", True) or payload.get("screenshot_base64"))

        # If incoming from browser extension with client content/screenshot, bypass server scrape
        is_client_ext = payload.get("source_channel") == "BROWSER_EXTENSION"
        should_crawl = not is_client_ext and not clean_text

        return ExtractedPost(
            platform="instagram",
            canonical_url=canonical_url,
            post_id=post_id,
            author_username=author_username,
            author_display_name=payload.get("display_name") or f"@{author_username}",
            title=title,
            clean_text=clean_text,
            should_crawl_server=should_crawl,
            has_media=has_media,
            likes_count=payload.get("likes_count"),
            views_count=payload.get("views_count"),
            comments_count=payload.get("comments_count"),
            shares_count=payload.get("shares_count"),
            extra_metadata={"is_instagram_post": bool(post_id)},
        )
