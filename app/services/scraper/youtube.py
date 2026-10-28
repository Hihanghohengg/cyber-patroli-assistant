import os
import asyncio
import logging
from datetime import datetime

try:
    import yt_dlp  # type: ignore
except ImportError:
    yt_dlp = None

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

from app.services.scraper.base import BaseScraper
from app.services.crypto_service import CryptoService

logger = logging.getLogger(__name__)

# Minimum valid screenshot size (20 KB)
MIN_SCREENSHOT_BYTES = 20 * 1024


class YouTubeScraper(BaseScraper):
    """High-reliability YouTube scraper & visual evidence engine.

    Extracts comprehensive metadata via yt-dlp and captures deterministic,
    high-resolution Full HD visual evidence via Playwright with anti-blank validation.
    """

    def extract_metadata(self, url: str) -> dict:
        """Extract structured video and channel metadata via yt-dlp."""
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            upload_date = None
            if info.get("upload_date"):
                try:
                    upload_date = datetime.strptime(info["upload_date"], "%Y%m%d")
                except Exception:
                    pass
            elif info.get("timestamp"):
                try:
                    upload_date = datetime.utcfromtimestamp(info["timestamp"])
                except Exception:
                    pass

            # Duration formatting
            duration_sec = info.get("duration", 0) or 0
            if duration_sec:
                mins, secs = divmod(int(duration_sec), 60)
                hrs, mins = divmod(mins, 60)
                duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"
            else:
                duration_str = "N/A"

            # Channel / handle extraction
            uploader_id = info.get("uploader_id") or ""
            channel_name = info.get("uploader") or info.get("channel") or "YouTube Creator"
            channel_url = info.get("uploader_url") or info.get("channel_url") or ""

            # Standardize handle
            handle = uploader_id if uploader_id.startswith("@") else (f"@{uploader_id}" if uploader_id else channel_name)

            tags = info.get("tags") or []
            categories = info.get("categories") or []
            video_id = info.get("id") or ""

            # Extract spoken dialogue transcript (Indonesian / English)
            transcript_text = self._extract_transcript(video_id, info)

            return {
                "platform": "youtube",
                "canonical_url": info.get("webpage_url", url),
                "platform_content_id": video_id,
                "title": info.get("title", ""),
                "caption": info.get("description", ""),
                "transcript": transcript_text,
                "duration": duration_str,
                "duration_seconds": duration_sec,
                "likes_count": info.get("like_count", 0) or 0,
                "views_count": info.get("view_count", 0) or 0,
                "comments_count": info.get("comment_count", 0) or 0,
                "tags": tags,
                "categories": categories,
                "posted_at": upload_date,
                "account": {
                    "username": handle,
                    "display_name": channel_name,
                    "profile_url": channel_url,
                    "subscribers_count": info.get("channel_follower_count", 0) or 0,
                    "total_posts": 0,
                    "is_verified": False,
                },
            }

    def _extract_transcript(self, video_id: str, info: dict) -> str:
        """Extract full spoken dialogue transcript in Indonesian or English with multi-tier fallback."""
        if not video_id:
            return ""

        # Tier 1: youtube-transcript-api
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            ytt = YouTubeTranscriptApi()
            transcript_list = ytt.list(video_id)
            
            chosen_transcript = None
            for pref in ["id", "id-orig", "en", "en-orig"]:
                try:
                    chosen_transcript = transcript_list.find_transcript([pref])
                    if chosen_transcript:
                        break
                except Exception:
                    continue
            
            if not chosen_transcript:
                for t in transcript_list:
                    chosen_transcript = t
                    break

            if chosen_transcript:
                data = chosen_transcript.fetch()
                parts = [item.text for item in data if item.text and item.text.strip()]
                extracted = " ".join(parts).strip()
                if extracted:
                    logger.info("Successfully extracted transcript (%d chars) via YouTubeTranscriptApi for %s", len(extracted), video_id)
                    return extracted
        except Exception as api_err:
            logger.debug("YouTubeTranscriptApi note for %s: %s", video_id, api_err)

        # Tier 2: yt-dlp subtitles & automatic_captions json3 stream
        try:
            import urllib.request
            import json
            all_subs = {**(info.get("automatic_captions") or {}), **(info.get("subtitles") or {})}
            sub_url = None
            for lang in ["id", "id-orig", "en", "en-orig"]:
                if lang in all_subs:
                    for fmt in all_subs[lang]:
                        if fmt.get("ext") == "json3":
                            sub_url = fmt.get("url")
                            break
                if sub_url:
                    break
            
            if not sub_url and all_subs:
                for _, fmts in all_subs.items():
                    for fmt in fmts:
                        if fmt.get("ext") == "json3":
                            sub_url = fmt.get("url")
                            break
                    if sub_url:
                        break

            if sub_url:
                req = urllib.request.Request(sub_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=6) as r:
                    data = json.loads(r.read().decode("utf-8", errors="ignore"))
                    lines = []
                    for ev in data.get("events", []):
                        text = "".join([s.get("utf8", "") for s in ev.get("segs", [])]).strip()
                        if text and text != "\n":
                            lines.append(text)
                    extracted = " ".join(lines).strip()
                    if extracted:
                        logger.info("Successfully extracted transcript (%d chars) via yt-dlp json3 stream for %s", len(extracted), video_id)
                        return extracted
        except Exception as sub_err:
            logger.debug("yt-dlp subtitle stream note for %s: %s", video_id, sub_err)

        return ""

    async def _dismiss_consent_and_overlays(self, page):
        """Dismiss Google/YouTube consent dialogs and hide distracting popups."""
        consent_selectors = [
            "button[aria-label*='Accept']",
            "button[aria-label*='Setuju']",
            "button[aria-label*='Agree']",
            "button[aria-label*='Reject']",
            "button[aria-label*='Tolak']",
            "ytd-button-renderer#dismiss-button",
            "tp-yt-paper-button#button[aria-label*='Reject']",
            "form[action*='consent'] button",
            ".eom-button-row button",
        ]
        for sel in consent_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    logger.info("Dismissing consent popup with selector: %s", sel)
                    await btn.click()
                    await asyncio.sleep(0.5)
                    break
            except Exception:
                pass

        # Hide any leftover overlay elements
        try:
            await page.evaluate("""
                () => {
                    const selectors = ['tp-yt-paper-dialog', 'ytd-consent-bump-v2-lightbox', '#dialog', '.opened'];
                    selectors.forEach(s => {
                        document.querySelectorAll(s).forEach(el => el.style.display = 'none');
                    });
                }
            """)
        except Exception:
            pass

    async def _navigate_and_wait(self, page, target_url: str, required_selectors: list[str], timeout_ms: int = 15000):
        """Navigate with networkidle fallback and wait for explicit content elements."""
        logger.info("Navigating to: %s", target_url)
        try:
            await page.goto(target_url, wait_until="networkidle", timeout=timeout_ms)
        except Exception as e:
            logger.warning("networkidle timed out on %s (%s), trying domcontentloaded", target_url, e)
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception as nav_err:
                logger.warning("domcontentloaded navigation warning: %s", nav_err)

        await self._dismiss_consent_and_overlays(page)

        # Wait for key DOM elements
        for sel in required_selectors:
            try:
                await page.wait_for_selector(sel, state="visible", timeout=timeout_ms)
                logger.info("Found required element: %s", sel)
                break
            except Exception:
                continue

        # Settle render
        await asyncio.sleep(2)

    async def _capture_with_validation(self, page, file_path: str, retry_action=None) -> str:
        """Capture screenshot and enforce anti-blank validation (> 20 KB)."""
        await page.screenshot(path=file_path, full_page=False)
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        logger.info("Captured screenshot: %s (size: %d bytes)", file_path, size)

        if size < MIN_SCREENSHOT_BYTES:
            logger.warning("Screenshot size %d bytes is below 20KB threshold. Retrying 1x...", size)
            await asyncio.sleep(2)
            if retry_action:
                await retry_action()
            await page.screenshot(path=file_path, full_page=False)
            size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            logger.info("Post-retry screenshot size: %d bytes", size)

            if size < MIN_SCREENSHOT_BYTES:
                raise ValueError(
                    f"Screenshot visual rusak/blank (ukuran: {size} bytes < 20 KB). "
                    "Halaman gagal dirender secara sempurna."
                )

        return file_path

    async def capture_visual_evidence(
        self,
        video_url: str = None,
        channel_url: str = None,
        ticket_number: str = "",
        post_url: str = None,
        profile_url: str = None,
        **kwargs,
    ) -> dict:
        """Capture standardized Full HD visual evidence for video and channel."""
        actual_video_url = video_url or post_url
        actual_channel_url = channel_url or profile_url

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            # Standardized Full HD Viewport (1920x1080, scale=1)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            # --- 1. Video / Post Screenshot ---
            video_filename = f"{ticket_number}_post.png"
            video_path = os.path.join(self.storage_dir, video_filename)

            video_selectors = [
                "ytd-watch-flexy",
                "#movie_player",
                "h1.title yt-formatted-string",
                "#primary-inner",
                "#player",
            ]
            await self._navigate_and_wait(page, actual_video_url, video_selectors, timeout_ms=15000)

            # Ensure player is ready or unpaused slightly if needed
            async def retry_video():
                await self._dismiss_consent_and_overlays(page)
                await asyncio.sleep(1)

            await self._capture_with_validation(page, video_path, retry_action=retry_video)
            logger.info("Valid video screenshot saved: %s", video_path)

            # --- 2. Channel / Profile Screenshot ---
            channel_filename = f"{ticket_number}_profile.png"
            channel_path = os.path.join(self.storage_dir, channel_filename)
            captured_channel_path = None

            if actual_channel_url and actual_channel_url != actual_video_url:
                try:
                    channel_selectors = [
                        "#channel-header",
                        "#page-header",
                        "ytd-channel-name",
                        "#channel-container",
                        "#contentContainer",
                    ]
                    await self._navigate_and_wait(page, actual_channel_url, channel_selectors, timeout_ms=15000)
                    await self._capture_with_validation(page, channel_path)
                    captured_channel_path = channel_path
                    logger.info("Valid channel screenshot saved: %s", channel_path)
                except Exception as ch_err:
                    logger.warning("Channel screenshot capture failed: %s", ch_err)
                    captured_channel_path = None

            await browser.close()

        # Compute forensic SHA-256 hashes
        video_hash = CryptoService.calculate_sha256(video_path)
        channel_hash = (
            CryptoService.calculate_sha256(captured_channel_path)
            if captured_channel_path
            else None
        )

        return {
            "post_screenshot_path": video_path,
            "post_screenshot_hash": video_hash,
            "profile_screenshot_path": captured_channel_path,
            "profile_screenshot_hash": channel_hash,
        }
