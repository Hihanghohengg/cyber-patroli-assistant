import os
import re
import asyncio
import logging

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

from app.services.scraper.base import BaseScraper
from app.services.crypto_service import CryptoService

logger = logging.getLogger(__name__)


class InstagramScraper(BaseScraper):
    """Instagram scraper with Playwright visual evidence capture."""

    def extract_metadata(self, url: str) -> dict:
        """Extract Instagram post metadata and shortcode identifier."""
        shortcode_match = re.search(r"/(?:p|reel|reels|tv)/([^/?#&]+)", url)
        shortcode = shortcode_match.group(1) if shortcode_match else "post"
        clean_url = f"https://www.instagram.com/p/{shortcode}/"

        return {
            "platform": "instagram",
            "canonical_url": clean_url,
            "platform_content_id": shortcode,
            "title": f"Instagram Post {shortcode}",
            "caption": f"Instagram public post [ID: {shortcode}]",
            "likes_count": 0,
            "views_count": 0,
            "comments_count": 0,
            "posted_at": None,
            "account": {
                "username": f"instagram_user_{shortcode[:8]}",
                "display_name": "Pengguna Instagram",
                "profile_url": clean_url,
                "subscribers_count": 0,
            },
        }

    async def capture_visual_evidence(
        self,
        post_url: str = None,
        profile_url: str = None,
        ticket_number: str = "",
        video_url: str = None,
        channel_url: str = None,
        **kwargs,
    ) -> dict:
        """Capture Instagram post screenshot via Playwright."""
        actual_post_url = post_url or video_url
        actual_profile_url = profile_url or channel_url

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            post_filename = f"{ticket_number}_post.png"
            post_path = os.path.join(self.storage_dir, post_filename)
            logger.info("Capturing Instagram post screenshot: %s", actual_post_url)
            try:
                await page.goto(actual_post_url, wait_until="domcontentloaded", timeout=20_000)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error("Instagram page navigation failed: %s", e)
                await browser.close()
                raise ConnectionError(
                    f"Koneksi ke Instagram timeout/terputus oleh jaringan ISP lokal ({e})."
                )

            await page.screenshot(path=post_path, full_page=False)

            # Enforce proposal validation (> 20 KB) with max 1 retry
            min_bytes = 20 * 1024
            size = os.path.getsize(post_path) if os.path.exists(post_path) else 0
            if size <= min_bytes:
                logger.warning("Instagram screenshot size %d <= 20KB. Retrying 1x...", size)
                try:
                    await asyncio.sleep(2)
                    await page.goto(actual_post_url, wait_until="networkidle", timeout=15_000)
                    await page.screenshot(path=post_path, full_page=False)
                    size = os.path.getsize(post_path) if os.path.exists(post_path) else 0
                except Exception as retry_err:
                    logger.warning("Instagram screenshot retry failed: %s", retry_err)

            if size <= min_bytes:
                await browser.close()
                raise ValueError(
                    f"Screenshot visual Instagram rusak/blank (ukuran: {size} bytes <= 20 KB). "
                    "Terhalang login-wall atau proteksi overlay."
                )

            profile_path = None
            profile_hash = None
            if actual_profile_url and actual_profile_url != actual_post_url and "@" in actual_profile_url:
                profile_filename = f"{ticket_number}_profile.png"
                profile_path = os.path.join(self.storage_dir, profile_filename)
                try:
                    await page.goto(actual_profile_url, wait_until="domcontentloaded", timeout=20_000)
                    await asyncio.sleep(2)
                    await page.screenshot(path=profile_path, full_page=False)
                    profile_hash = CryptoService.calculate_sha256(profile_path)
                except Exception as p_err:
                    logger.warning("Profile screenshot skipped: %s", p_err)
                    profile_path = None

            await browser.close()

        post_hash = CryptoService.calculate_sha256(post_path)

        return {
            "post_screenshot_path": post_path,
            "post_screenshot_hash": post_hash,
            "profile_screenshot_path": profile_path,
            "profile_screenshot_hash": profile_hash,
        }
