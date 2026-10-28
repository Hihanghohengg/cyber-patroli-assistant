import os
import re
import logging
from abc import ABC, abstractmethod

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
    def detect_platform(url: str) -> str:
        """Detect social media platform from a URL string."""
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

