"""Base interface and data contracts for platform-specific content extractors."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from abc import ABC, abstractmethod


@dataclass
class ExtractedPost:
    """Standardized output contract for all platform extractors."""
    platform: str
    canonical_url: str
    post_id: Optional[str] = None
    author_username: Optional[str] = None
    author_display_name: Optional[str] = None
    title: Optional[str] = None
    clean_text: str = ""
    should_crawl_server: bool = False
    has_media: bool = False
    likes_count: Optional[int] = None
    views_count: Optional[int] = None
    comments_count: Optional[int] = None
    shares_count: Optional[int] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


class BasePlatformExtractor(ABC):
    """Abstract base class for platform-specific extraction rules."""

    platform_name: str = "web"
    supported_domains: Tuple[str, ...] = ()

    @classmethod
    def matches(cls, url: str, platform_hint: Optional[str] = None) -> bool:
        """Return True if URL or platform_hint belongs to this platform."""
        if platform_hint and platform_hint.lower() == cls.platform_name.lower():
            return True
        u_low = (url or "").lower().strip()
        return any(domain in u_low for domain in cls.supported_domains)

    @classmethod
    @abstractmethod
    def extract(cls, raw_url: str, payload_data: Optional[Dict[str, Any]] = None) -> ExtractedPost:
        """Process URL and client payload into standardized ExtractedPost."""
        pass
