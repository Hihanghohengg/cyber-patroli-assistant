"""Extractor implementation for Threads (threads.net & threads.com)."""

import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.services.extractors.base import BasePlatformExtractor, ExtractedPost


def is_threads_login_boilerplate(text: Optional[str]) -> bool:
    """Detect Instagram/Meta login-wall marketing boilerplate on Threads."""
    if not text:
        return False
    lower = text.lower()
    patterns = [
        "log in with your instagram",
        "masuk dengan akun instagram",
        "log in to see photos and videos",
        "login to see photos and videos",
        "masuk untuk melihat foto dan video",
        "create an account or log in",
        "buat akun atau masuk",
        "log in to threads",
        "masuk ke threads",
        "join groups, ask questions",
        "lihat lainnya dari threads",
        "see more from threads",
    ]
    return any(p in lower for p in patterns)


class ThreadsExtractor(BasePlatformExtractor):
    platform_name = "threads"
    supported_domains = ("threads.net", "threads.com")

    @classmethod
    def clean_url(cls, url: str) -> str:
        """Strip tracking parameters and clean trailing slashes."""
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
            return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, new_query, ""))
        except Exception:
            return url.strip().rstrip("/")

    @classmethod
    def extract(cls, raw_url: str, payload_data: Optional[Dict[str, Any]] = None) -> ExtractedPost:
        clean_url = cls.clean_url(raw_url)
        payload = payload_data or {}

        # 1. Post ID Extraction
        post_id = None
        m_post = re.search(r"/(?:post|t)/([A-Za-z0-9_-]+)", clean_url, re.IGNORECASE)
        if m_post:
            post_id = m_post.group(1)

        # 2. Author Username Extraction
        author_username = payload.get("username")
        if not author_username or author_username.lower() in ("threads.net", "threads.com", "anonim"):
            th_match = re.search(r"threads\.(?:net|com)/@?([a-zA-Z0-9_\.]+)", clean_url, re.IGNORECASE)
            if th_match and th_match.group(1).lower() not in ["post", "search", "activity", "t"]:
                author_username = th_match.group(1)
            else:
                author_username = "Anonim"

        # 3. Canonical URL Normalization
        if post_id:
            if author_username and author_username != "Anonim":
                canonical_url = f"https://www.threads.net/@{author_username}/post/{post_id}"
            else:
                canonical_url = f"https://www.threads.net/post/{post_id}"
        else:
            canonical_url = clean_url

        # 4. Clean narrative text (Anti Login-Wall)
        raw_text = payload.get("caption") or payload.get("notes") or ""
        if is_threads_login_boilerplate(raw_text):
            raw_text = ""

        # Filter UI buttons
        clean_text = raw_text
        if clean_text:
            clean_text = re.sub(r"^(?:Ikuti|Mengikuti|Follow|Following)\s*", "", clean_text, flags=re.IGNORECASE).strip()
            if author_username and author_username != "Anonim":
                clean_text = re.sub(rf"^@?{re.escape(author_username)}\s*", "", clean_text, flags=re.IGNORECASE).strip()
            clean_text = re.sub(r"^\d+\s*(?:j|jam|h|m|menit|d|hari|w|minggu|detik)\s*", "", clean_text, flags=re.IGNORECASE).strip()
            clean_text = re.sub(r"\b(?:Suka|Balas|Posting ulang|Bagikan|Like|Reply|Repost|Share)\b.*$", "", clean_text, flags=re.IGNORECASE).strip()
            clean_text = re.sub(r"[ \t]+", " ", clean_text)
            clean_text = re.sub(r"\n\s*\n\s*\n+", "\n\n", clean_text).strip()

        # 5. Title synthesis
        title = payload.get("title")
        if not title and clean_text:
            first_sent = clean_text.split("\n")[0].split(".")[0].strip()
            title = first_sent[:80] + ("..." if len(first_sent) > 80 else "")

        has_media = bool(payload.get("has_media", False) or payload.get("screenshot_base64"))

        return ExtractedPost(
            platform="threads",
            canonical_url=canonical_url,
            post_id=post_id,
            author_username=author_username,
            author_display_name=payload.get("display_name") or f"@{author_username}",
            title=title,
            clean_text=clean_text,
            should_crawl_server=False,  # Bypass Playwright to prevent login wall / timeout
            has_media=has_media,
            likes_count=payload.get("likes_count"),
            views_count=payload.get("views_count"),
            comments_count=payload.get("comments_count"),
            shares_count=payload.get("shares_count"),
            extra_metadata={"is_threads_post": bool(post_id)},
        )
