"""Extractor implementation for X / Twitter (x.com & twitter.com)."""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.services.extractors.base import BasePlatformExtractor, ExtractedPost


class TwitterXExtractor(BasePlatformExtractor):
    platform_name = "x"
    supported_domains = ("x.com", "twitter.com")

    @classmethod
    def clean_url(cls, url: str) -> str:
        """Strip analytics tracking and normalizes domain to x.com."""
        if not url:
            return ""
        try:
            parsed = urlparse(url.strip())
            qs = parse_qs(parsed.query)
            tracking_params = {"s", "t", "ref_src", "ref_url", "utm_source", "utm_medium"}
            cleaned_qs = {k: v for k, v in qs.items() if k.lower() not in tracking_params}
            new_query = urlencode(cleaned_qs, doseq=True)
            netloc = "x.com" if "twitter.com" in parsed.netloc.lower() else parsed.netloc
            new_path = parsed.path.rstrip("/") if len(parsed.path) > 1 else parsed.path
            return urlunparse((parsed.scheme, netloc, new_path, parsed.params, new_query, ""))
        except Exception:
            return url.strip().rstrip("/")

    @classmethod
    def extract(cls, raw_url: str, payload_data: Optional[Dict[str, Any]] = None) -> ExtractedPost:
        clean_url = cls.clean_url(raw_url)
        payload = payload_data or {}

        # 1. Post ID Extraction
        post_id = None
        m_post = re.search(r"/status/(\d+)", clean_url)
        if m_post:
            post_id = m_post.group(1)

        # 2. Author Username Extraction
        author_username = payload.get("username")
        if not author_username or author_username.lower() in ("x.com", "twitter.com", "anonim"):
            x_match = re.search(r"(?:twitter\.com|x\.com)/([a-zA-Z0-9_]{1,30})(?:/status|\b)", clean_url, re.IGNORECASE)
            if x_match and x_match.group(1).lower() not in ["home", "explore", "notifications", "messages", "search", "i"]:
                author_username = x_match.group(1)
            else:
                author_username = "Anonim"

        # 3. Canonical URL
        if post_id and author_username and author_username != "Anonim":
            canonical_url = f"https://x.com/{author_username}/status/{post_id}"
        elif post_id:
            canonical_url = f"https://x.com/i/status/{post_id}"
        else:
            canonical_url = clean_url

        # 4. Clean text
        raw_text = payload.get("caption") or payload.get("notes") or ""
        clean_text = raw_text
        if clean_text:
            if author_username and author_username != "Anonim":
                clean_text = re.sub(rf"^(?:[^\n@]{{0,50}})?@?{re.escape(author_username)}\s*", "", clean_text, flags=re.IGNORECASE).strip()
            clean_text = re.sub(r"Terjemahkan postingan|Translate post", "", clean_text, flags=re.IGNORECASE).strip()
            clean_text = re.sub(r"\d{1,2}:\d{2}\s*[\/|\\]\s*\d{1,2}:\d{2}", " ", clean_text)
            clean_text = re.sub(r"\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*[·•\u00b7\u2022]\s*[A-Za-z]{3}\s*\d{1,2},\s*\d{4}", " ", clean_text)
            clean_text = re.sub(r"[·•\u00b7\u2022\s]*\d+[\d\.,]*[KkMm]?\s*(?:Views|View quotes|views|quotes|suka|likes|Retweets|reposts|Bookmarks|bookmarked)(?=[^a-zA-Z]|$)", " ", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"[ \t]+", " ", clean_text)
            clean_text = re.sub(r"\n\s*\n\s*\n+", "\n\n", clean_text).strip()

        title = payload.get("title")
        if not title and clean_text:
            first_sent = clean_text.split("\n")[0].split(".")[0].strip()
            title = first_sent[:80] + ("..." if len(first_sent) > 80 else "")

        has_media = bool(payload.get("has_media", False) or payload.get("screenshot_base64"))

        return ExtractedPost(
            platform="x",
            canonical_url=canonical_url,
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
            extra_metadata={"is_x_post": bool(post_id)},
        )
