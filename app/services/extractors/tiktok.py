"""Extractor implementation for TikTok (tiktok.com)."""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.services.extractors.base import BasePlatformExtractor, ExtractedPost


class TikTokExtractor(BasePlatformExtractor):
    platform_name = "tiktok"
    supported_domains = ("tiktok.com",)

    @classmethod
    def clean_url(cls, url: str) -> str:
        """Strip tracking parameters and clean trailing modal/navigation query strings."""
        if not url:
            return ""
        try:
            parsed = urlparse(url.strip())
            qs = parse_qs(parsed.query)
            tracking_params = {
                "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                "fbclid", "igshid", "si", "ref", "share_id", "is_from_webapp",
                "sender_device", "feature", "tracking_id", "_r", "_d", "checksum",
                "sec_uid", "share_app_id", "share_item_id", "share_link_id",
                "source", "tt_from", "enter_from", "enter_method"
            }
            cleaned_qs = {k: v for k, v in qs.items() if k.lower() not in tracking_params}
            new_query = urlencode(cleaned_qs, doseq=True)
            new_path = parsed.path.rstrip("/") if len(parsed.path) > 1 else parsed.path

            # Clean URL to standard https://www.tiktok.com/@username/video/12345
            tt_match = re.search(r"(/@[a-zA-Z0-9_\.]+(?:/(?:video|photo)/\d+))", new_path, re.IGNORECASE)
            if tt_match:
                new_path = tt_match.group(1)

            netloc = parsed.netloc.lower()
            if netloc.endswith("tiktok.com") and not netloc.startswith("www.") and not netloc.startswith("vt."):
                netloc = f"www.{netloc}"

            return urlunparse((parsed.scheme or "https", netloc or "www.tiktok.com", new_path, parsed.params, new_query, ""))
        except Exception:
            clean = url.strip().rstrip("/")
            tt_m = re.search(r"(https?://(?:www\.)?tiktok\.com/@[a-zA-Z0-9_\.]+(?:/(?:video|photo)/\d+))", clean, re.IGNORECASE)
            return tt_m.group(1) if tt_m else clean

    @classmethod
    def extract(cls, raw_url: str, payload_data: Optional[Dict[str, Any]] = None) -> ExtractedPost:
        clean_url = cls.clean_url(raw_url)
        payload = payload_data or {}

        # 1. Post / Video ID Extraction
        post_id = None
        m_video = re.search(r"/(?:video|photo|v)/(\d+)", clean_url, re.IGNORECASE)
        if m_video:
            post_id = m_video.group(1)

        # 2. Author Username Extraction
        author_username = payload.get("username")
        if not author_username or author_username.lower() in ("tiktok.com", "anonim", "tiktok_user"):
            tt_user_match = re.search(r"tiktok\.com/@([a-zA-Z0-9_\.]{1,50})", clean_url, re.IGNORECASE)
            if tt_user_match:
                author_username = tt_user_match.group(1)
            else:
                author_username = "tiktok_user"

        author_display = payload.get("display_name") or f"@{author_username}"

        # 3. Canonical URL
        if post_id and author_username and author_username != "tiktok_user":
            canonical_url = f"https://www.tiktok.com/@{author_username}/video/{post_id}"
        else:
            canonical_url = clean_url

        # 4. Text and Title Cleaning
        raw_caption = payload.get("caption") or payload.get("dom_text") or payload.get("notes") or ""
        clean_text = raw_caption.strip()
        if clean_text:
            clean_text = re.sub(r"\n\s*\n\s*\n+", "\n\n", clean_text).strip()

        title = payload.get("title")
        if not title and clean_text:
            first_sent = clean_text.split("\n")[0].split(".")[0].strip()
            title = first_sent[:80] + ("..." if len(first_sent) > 80 else "")
        elif not title:
            title = f"TikTok Video by @{author_username}"

        return ExtractedPost(
            platform="tiktok",
            canonical_url=canonical_url,
            post_id=post_id,
            author_username=author_username,
            author_display_name=author_display,
            title=title,
            clean_text=clean_text,
            should_crawl_server=False,
            has_media=True,
            likes_count=payload.get("likes_count"),
            views_count=payload.get("views_count"),
            comments_count=payload.get("comments_count"),
            shares_count=payload.get("shares_count"),
            extra_metadata={"video_id": post_id, "is_tiktok_video": bool(post_id)},
        )
