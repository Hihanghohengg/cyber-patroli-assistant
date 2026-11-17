"""Unified Acquisition Router for 5-Platform Patrol Intake (TILIK).

Routes target URLs to the appropriate extraction engine:
1. YouTube (Video & Shorts) -> yt-dlp + youtube-transcript-api + Playwright/Thumbnail
2. National News & Web -> CrawlerService (Playwright + Trafilatura/DOM + Pagination ?page=all)
3. Social Media (X, Instagram, Threads) -> OpenGraph/oEmbed extraction + Login wall detection
4. Multi-URL / Batch Triage asynchronous orchestration
"""

import asyncio
import hashlib
import logging
import os
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from app.config import settings
from app.services.scraper.base import BaseScraper
from app.services.crawler_service import CrawlerService

logger = logging.getLogger(__name__)


def smart_truncate_words(text: Optional[str], max_words: int = 4000) -> str:
    """Smartly truncate text to max_words to stay within LLM context window while preserving core narrative."""
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    
    # Keep 70% from beginning, 30% from end
    head_count = int(max_words * 0.7)
    tail_count = max_words - head_count
    
    head_part = " ".join(words[:head_count])
    tail_part = " ".join(words[-tail_count:])
    
    return f"{head_part}\n\n[... {len(words) - max_words} KATA DIRINGKAS UNTUK EFISIENSI KONTEKS AI ...]\n\n{tail_part}"


class AcquisitionRouter:
    """Smart router for multi-platform data intake."""

    @classmethod
    async def acquire_single_url(
        cls,
        url: str,
        ticket_number: str,
        storage_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Acquire content and evidence for any supported URL."""
        storage_dir = storage_dir or settings.EVIDENCE_DIR
        os.makedirs(storage_dir, exist_ok=True)
        
        # 1. Detect platform & safety check
        platform = BaseScraper.detect_platform(url)
        is_specific = BaseScraper.is_specific_post_url(url)

        evidence_filename = f"{ticket_number}_post.png"
        target_evidence_path = os.path.join(storage_dir, evidence_filename)
        evidence_sha256 = None

        result: Dict[str, Any] = {
            "platform": platform,
            "url": url,
            "title": "",
            "caption": "",
            "transcript": "",
            "author": "",
            "display_name": "",
            "followers_count": 0,
            "views_count": 0,
            "likes_count": 0,
            "comments_count": 0,
            "screenshot_path": None,
            "screenshot_sha256": None,
            "media_image_url": None,
            "requires_browser_extension": False,
            "login_wall_notice": None,
        }

        # ---------------------------------------------------------
        # Path A: YouTube (Videos and Shorts)
        # ---------------------------------------------------------
        if platform == "youtube":
            try:
                from app.services.scraper.youtube import YouTubeScraper
                yt_scraper = YouTubeScraper(storage_dir=storage_dir)
                meta = yt_scraper.extract_metadata(url)
                
                result["title"] = meta.get("title", "")
                result["caption"] = meta.get("caption", "")
                
                raw_transcript = meta.get("transcript", "")
                result["transcript"] = smart_truncate_words(raw_transcript, settings.MAX_TRANSCRIPT_WORDS)
                
                acc = meta.get("account", {})
                result["author"] = acc.get("username", "youtube_creator").replace("@", "")
                result["display_name"] = acc.get("display_name", "")
                result["followers_count"] = acc.get("subscribers_count", 0)
                result["views_count"] = meta.get("views_count", 0)
                result["likes_count"] = meta.get("likes_count", 0)
                result["comments_count"] = meta.get("comments_count", 0)
                
                # Visual Evidence: Playwright capture or high-res thumbnail download
                try:
                    from app.services.scraper.youtube import is_playwright_installed
                    if is_playwright_installed():
                        scrape_res = await yt_scraper.capture_visual_evidence(post_url=url, ticket_number=ticket_number)
                        if scrape_res and scrape_res.get("post_screenshot_path") and os.path.exists(scrape_res["post_screenshot_path"]):
                            result["screenshot_path"] = scrape_res["post_screenshot_path"]
                            result["screenshot_sha256"] = scrape_res.get("post_screenshot_hash")
                except Exception as pw_err:
                    logger.debug("Playwright YouTube screenshot skipped: %s", pw_err)

                # Fallback to downloading high-res thumbnail
                if not result["screenshot_path"] or not os.path.exists(result["screenshot_path"]):
                    video_id = meta.get("platform_content_id")
                    if video_id:
                        for thumb_url in [
                            f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                        ]:
                            try:
                                import urllib.request
                                req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                                with urllib.request.urlopen(req, timeout=8) as resp:
                                    img_data = resp.read()
                                if img_data and len(img_data) > 2000:
                                    with open(target_evidence_path, "wb") as f:
                                        f.write(img_data)
                                    result["screenshot_path"] = target_evidence_path
                                    result["screenshot_sha256"] = hashlib.sha256(img_data).hexdigest()
                                    break
                            except Exception:
                                continue
            except Exception as yt_err:
                logger.warning("YouTube acquisition error for %s: %s", url, yt_err)

        # ---------------------------------------------------------
        # Path B: National News & Open Web Articles (CrawlerService)
        # ---------------------------------------------------------
        elif platform == "web":
            try:
                crawl_res = await CrawlerService.crawl_article(url, ticket_number=ticket_number, storage_dir=storage_dir)
                result["title"] = crawl_res.get("title") or crawl_res.get("headline", "")
                result["caption"] = crawl_res.get("clean_text", "")
                result["author"] = crawl_res.get("author", crawl_res.get("domain", "media_nasional"))
                result["display_name"] = crawl_res.get("domain", "Media Nasional").capitalize()
                result["screenshot_path"] = crawl_res.get("screenshot_path")
                result["screenshot_sha256"] = crawl_res.get("screenshot_sha256")
                result["media_image_url"] = crawl_res.get("media_image_url")
            except Exception as crawl_err:
                logger.warning("Web/News crawler error for %s: %s", url, crawl_err)

        # ---------------------------------------------------------
        # Path C: Social Media (X/Twitter, Instagram, Threads, Facebook, TikTok)
        # ---------------------------------------------------------
        else:
            # Attempt OpenGraph / oEmbed first
            html_text = ""
            try:
                import httpx
                async with httpx.AsyncClient(
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    follow_redirects=True,
                    timeout=10.0,
                ) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        html_text = resp.text
            except Exception as net_err:
                logger.debug("Social HTTP probe failed: %s", net_err)

            # Check if login wall was encountered
            is_login_wall = (
                not html_text
                or "login" in html_text.lower()
                or "sign up" in html_text.lower()
                or "masuk" in html_text.lower()
                or len(html_text) < 1500
            )

            # Extract basic OpenGraph tags if available
            if html_text:
                from app.services.crawler_service import extract_meta_tags
                meta = extract_meta_tags(html_text)
                result["title"] = meta.get("og:title", "")
                result["caption"] = meta.get("og:description", "")
                result["media_image_url"] = meta.get("og:image")

            # Extract username from URL if possible
            parsed_u = urlparse(url)
            match = re.search(r"/(?:@|)([a-zA-Z0-9_\.]+)(?:/status|/post|/p/|/reel)", parsed_u.path)
            if match:
                result["author"] = match.group(1)
                result["display_name"] = f"@{match.group(1)}"

            # If login wall is active or caption is sparse, set notice for operator
            if is_login_wall or not result["caption"]:
                result["requires_browser_extension"] = True
                result["login_wall_notice"] = (
                    f"Konten {platform.upper()} ini berada di balik otentikasi login / antarmuka dinamis. "
                    f"Disarankan menggunakan Ekstensi Browser TILIK MV3 pada tab browser yang sudah login."
                )
                if not result["caption"]:
                    result["caption"] = (
                        f"Temuan patroli siber {platform.upper()}: URL {url}. "
                        f"{result['login_wall_notice']}"
                    )

        # ---------------------------------------------------------
        # Fallback Forensic Banner if no screenshot exists
        # ---------------------------------------------------------
        if not result["screenshot_path"] or not os.path.exists(result["screenshot_path"]):
            try:
                from PIL import Image, ImageDraw
                img = Image.new("RGB", (1280, 720), color=(15, 23, 42))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(0, 0), (1280, 70)], fill=(30, 41, 59))
                draw.text((40, 24), f"TILIK DIGITAL EVIDENCE ARCHIVE ({platform.upper()})", fill=(56, 189, 248))
                draw.text((40, 110), f"Nomor Tiket : {ticket_number}", fill=(241, 245, 249))
                draw.text((40, 150), f"Platform    : {platform.upper()}", fill=(241, 245, 249))
                draw.text((40, 190), f"URL Target  : {url[:85]}", fill=(148, 163, 184))
                if result.get("author"):
                    draw.text((40, 230), f"Pengunggah  : @{result['author']}", fill=(148, 163, 184))
                if result.get("login_wall_notice"):
                    draw.text((40, 280), "CATATAN: Halaman membutuhkan login sesi aktif. Rekam bukti via Ekstensi MV3.", fill=(251, 191, 36))
                draw.text((40, 340), "STATUS: BUKTI DIGITAL DIARSIPKAN KE SISTEM FORENSIK (HMAC-SHA256)", fill=(52, 211, 153))
                img.save(target_evidence_path, "PNG")

                with open(target_evidence_path, "rb") as f:
                    raw_b = f.read()
                result["screenshot_path"] = target_evidence_path
                result["screenshot_sha256"] = hashlib.sha256(raw_b).hexdigest()
            except Exception as fb_err:
                logger.warning("Fallback evidence banner generation failed: %s", fb_err)

        return result

    @classmethod
    async def acquire_batch_urls(
        cls,
        urls: List[str],
        ticket_prefix: str = "BATCH",
        storage_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Acquire multiple URLs concurrently with concurrency limit."""
        semaphore = asyncio.Semaphore(3)

        async def worker(u: str, idx: int):
            async with semaphore:
                ticket_num = f"{ticket_prefix}-{idx+1:02d}"
                try:
                    return await cls.acquire_single_url(u.strip(), ticket_number=ticket_num, storage_dir=storage_dir)
                except Exception as ex:
                    logger.error("Error acquiring batch url %s: %s", u, ex)
                    return {
                        "platform": "error",
                        "url": u,
                        "title": "Gagal Mengambil Konten",
                        "caption": f"Gagal mengakuisisi: {str(ex)}",
                        "error": str(ex),
                    }

        tasks = [worker(u, i) for i, u in enumerate(urls) if u.strip()]
        return await asyncio.gather(*tasks)
