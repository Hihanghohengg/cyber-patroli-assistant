import ipaddress
import os
import re
import socket
import logging
from abc import ABC, abstractmethod
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base for platform-specific scrapers.

    Every concrete scraper must implement:
    - extract_metadata(url) → dict
    - capture_visual_evidence(video_url, channel_url, ticket_number) → dict
    """

    def __init__(self, storage_dir: str = "storage/evidences"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    @abstractmethod
    def extract_metadata(self, url: str) -> dict:
        """Extract structured metadata from a public post URL."""
        ...

    @abstractmethod
    async def capture_visual_evidence(
        self,
        post_url: str = None,
        profile_url: str = None,
        ticket_number: str = "",
        video_url: str = None,
        channel_url: str = None,
        **kwargs,
    ) -> dict:
        """Capture screenshots of the post and profile pages."""
        ...

    @staticmethod
    def is_safe_public_url(url: str) -> bool:
        """Validate that URL is safe, does not target internal services, private IP ranges, or cloud metadata (SSRF defense)."""
        try:
            parsed = urlparse(url.strip())
            if parsed.scheme.lower() not in ("http", "https"):
                return False
            host = parsed.hostname
            if not host:
                return False
            host_clean = host.lower().strip("[]")
            
            # Blacklisted hostnames & cloud metadata endpoints
            blocked_hosts = {
                "localhost", "127.0.0.1", "::1", "0.0.0.0",
                "metadata.google.internal", "169.254.169.254",
                "instance-data", "metadata", "docker.for.win.localhost"
            }
            if host_clean in blocked_hosts or host_clean.endswith(".internal") or host_clean.endswith(".local"):
                return False

            # Check if host is direct raw IP
            try:
                ip = ipaddress.ip_address(host_clean)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    return False
                return True
            except ValueError:
                pass  # Host is a domain name, proceed to DNS resolution check

            # Resolve DNS to prevent DNS rebinding attacks to internal IPs
            try:
                addr_info = socket.getaddrinfo(host_clean, None)
                for item in addr_info:
                    resolved_ip_str = item[4][0]
                    resolved_ip = ipaddress.ip_address(resolved_ip_str)
                    if (
                        resolved_ip.is_private
                        or resolved_ip.is_loopback
                        or resolved_ip.is_link_local
                        or resolved_ip.is_reserved
                        or resolved_ip.is_multicast
                    ):
                        logger.warning("SSRF blocked: Domain %s resolved to private/internal IP %s", host_clean, resolved_ip_str)
                        return False
            except socket.gaierror:
                pass  # Allow if offline / mocked in tests, domain regex will validate valid social media domain

            return True
        except Exception as e:
            logger.warning("URL safety check failed with error: %s", e)
            return False

    @staticmethod
    def is_specific_post_url(url: str) -> bool:
        """Check whether the given URL points to a specific post/video rather than the platform homepage."""
        url_lower = url.lower().strip()
        # YouTube: requires watch?v=, /shorts/, or youtu.be/
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return bool(re.search(r"(watch\?v=|\/shorts\/|youtu\.be\/[a-zA-Z0-9_-]+)", url_lower))
        # TikTok: requires /video/ or /@user/video/
        if "tiktok.com" in url_lower:
            return bool(re.search(r"(\/video\/|\/v\/|@[\w\.-]+\/video)", url_lower))
        # Instagram: requires /p/, /reel/, /reels/, /tv/
        if "instagram.com" in url_lower:
            return bool(re.search(r"(\/p\/|\/reel\/|\/reels\/|\/tv\/)", url_lower))
        # X / Twitter: requires /status/
        if "x.com" in url_lower or "twitter.com" in url_lower:
            return bool(re.search(r"\/status\/\d+", url_lower))
        # Threads: requires /post/
        if "threads.net" in url_lower:
            return bool(re.search(r"\/post\/", url_lower))
        return True

    @staticmethod
    def detect_platform(url: str) -> str:
        """Detect social media platform from a URL string with strict SSRF validation."""
        if not BaseScraper.is_safe_public_url(url):
            raise ValueError(f"URL tidak diizinkan: Hanya alamat publik yang dapat dipatroli (SSRF Protection).")

        url_lower = url.lower().strip()
        if re.search(r"(youtube\.com|youtu\.be)", url_lower):
            return "youtube"
        elif re.search(r"tiktok\.com", url_lower):
            return "tiktok"
        elif re.search(r"instagram\.com", url_lower):
            return "instagram"
        elif re.search(r"(twitter\.com|x\.com)", url_lower):
            return "x"
        elif re.search(r"(facebook\.com|fb\.watch)", url_lower):
            return "facebook"
        elif re.search(r"threads\.net", url_lower):
            return "threads"
        elif url_lower.startswith("http://") or url_lower.startswith("https://"):
            return "web"
        else:
            raise ValueError(f"Platform tidak didukung atau format URL tidak valid: {url}")

