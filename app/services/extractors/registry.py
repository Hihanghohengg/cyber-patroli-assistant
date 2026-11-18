"""Registry dispatcher for platform content extractors."""

import logging
from typing import Optional, Dict, Any, List, Type

from app.services.extractors.base import BasePlatformExtractor, ExtractedPost
from app.services.extractors.threads import ThreadsExtractor
from app.services.extractors.instagram import InstagramExtractor
from app.services.extractors.twitter_x import TwitterXExtractor
from app.services.extractors.facebook import FacebookExtractor
from app.services.extractors.youtube import YouTubeExtractor
from app.services.extractors.news_portal import NewsPortalExtractor

logger = logging.getLogger(__name__)


class ExtractorRegistry:
    """Central registry and dispatcher for all platform extractors."""

    _EXTRACTORS: List[Type[BasePlatformExtractor]] = [
        ThreadsExtractor,
        InstagramExtractor,
        TwitterXExtractor,
        FacebookExtractor,
        YouTubeExtractor,
        NewsPortalExtractor,  # Fallback default
    ]

    @classmethod
    def get_extractor(cls, url: str, platform_hint: Optional[str] = None) -> Type[BasePlatformExtractor]:
        """Find the matching extractor class based on platform_hint or URL pattern."""
        norm_hint = (platform_hint or "").lower().strip()
        # Direct hint matching
        if norm_hint:
            for ext in cls._EXTRACTORS:
                if ext.platform_name.lower() == norm_hint:
                    return ext

        # Domain pattern matching
        u_low = (url or "").lower().strip()
        for ext in cls._EXTRACTORS[:-1]:  # Exclude generic news_portal fallback
            if ext.matches(u_low, norm_hint):
                return ext

        return NewsPortalExtractor

    @classmethod
    def detect_platform(cls, url: str, platform_hint: Optional[str] = None) -> str:
        """Quickly detect the normalized platform name without full extraction."""
        extractor = cls.get_extractor(url, platform_hint)
        return extractor.platform_name

    @classmethod
    def clean_url(cls, url: str, platform_hint: Optional[str] = None) -> str:
        """Clean and normalize URL for deduplication."""
        extractor = cls.get_extractor(url, platform_hint)
        if hasattr(extractor, "clean_url"):
            return extractor.clean_url(url)
        return url.strip().rstrip("/")

    @classmethod
    def resolve(
        cls,
        raw_url: str,
        platform_hint: Optional[str] = None,
        payload_data: Optional[Dict[str, Any]] = None,
    ) -> ExtractedPost:
        """Resolve raw URL and payload data through the appropriate platform extractor."""
        extractor = cls.get_extractor(raw_url, platform_hint)
        extracted = extractor.extract(raw_url, payload_data)
        logger.debug(
            "[ExtractorRegistry] Resolved URL %s via %s -> platform=%s, post_id=%s",
            raw_url[:60],
            extractor.__name__,
            extracted.platform,
            extracted.post_id,
        )
        return extracted
