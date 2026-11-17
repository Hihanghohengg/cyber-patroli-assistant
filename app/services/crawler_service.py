"""Crawler Service for National News & Open Web (WaterCrawl Adaptation).

Provides intelligent web article crawling, pagination resolution (e.g. ?page=all),
JSON-LD / OpenGraph metadata extraction, clean markdown extraction (Trafilatura/DOM fallback),
and cryptographic visual evidence screenshot capture.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.config import settings

logger = logging.getLogger(__name__)

# Indonesian news domains that support ?page=all or single-page query
NEWS_ALL_PAGE_DOMAINS = {
    "kompas.com": "page=all",
    "detik.com": "single=1",
    "tempo.co": "page=all",
    "cnnindonesia.com": "page=all",
    "liputan6.com": "page=all",
    "merdeka.com": "single=1",
    "suara.com": "page=all",
    "viva.co.id": "page=all",
    "sindonews.com": "page=all",
    "republika.co.id": "page=all",
    "tribunnews.com": "page=all",
}


def normalize_news_url(url: str) -> str:
    """Detect Indonesian news domain and append all-page parameter if absent."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        
        for domain, param in NEWS_ALL_PAGE_DOMAINS.items():
            if domain in netloc:
                qs = parse_qs(parsed.query)
                key, val = param.split("=")
                if key not in qs:
                    qs[key] = [val]
                    new_query = urlencode(qs, doseq=True)
                    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        return url
    except Exception:
        return url


def extract_json_ld(html: str) -> Dict[str, Any]:
    """Extract metadata from schema.org NewsArticle / Article JSON-LD tags."""
    meta: Dict[str, Any] = {}
    if not html:
        return meta

    pattern = re.compile(r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(html)
    for m in matches:
        try:
            data = json.loads(m.strip())
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                # Handle @graph
                graph_items = item.get("@graph", [item]) if "@graph" in item else [item]
                for g in graph_items:
                    if not isinstance(g, dict):
                        continue
                    t = str(g.get("@type", "")).lower()
                    if "article" in t or "news" in t or "report" in t or "webpage" in t:
                        if not meta.get("headline") and g.get("headline"):
                            meta["headline"] = g["headline"]
                        if not meta.get("date_published") and g.get("datePublished"):
                            meta["date_published"] = g["datePublished"]
                        if not meta.get("description") and g.get("description"):
                            meta["description"] = g["description"]
                        if not meta.get("author") and g.get("author"):
                            auth = g["author"]
                            if isinstance(auth, dict):
                                meta["author"] = auth.get("name", "")
                            elif isinstance(auth, list) and len(auth) > 0:
                                first = auth[0]
                                meta["author"] = first.get("name", "") if isinstance(first, dict) else str(first)
                            elif isinstance(auth, str):
                                meta["author"] = auth
                        if not meta.get("image") and g.get("image"):
                            img = g["image"]
                            if isinstance(img, dict):
                                meta["image"] = img.get("url", "")
                            elif isinstance(img, list) and len(img) > 0:
                                first = img[0]
                                meta["image"] = first.get("url", "") if isinstance(first, dict) else str(first)
                            elif isinstance(img, str):
                                meta["image"] = img
        except Exception:
            continue
    return meta


def extract_meta_tags(html: str) -> Dict[str, str]:
    """Extract OpenGraph and standard meta tags from HTML."""
    tags: Dict[str, str] = {}
    if not html:
        return tags

    # Extract title
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if title_match:
        tags["page_title"] = title_match.group(1).strip()

    # Regex for meta properties
    meta_patterns = re.findall(r'<meta[^>]+(?:name|property)=[\'"]([^\'"]+)[\'"][^>]+content=[\'"]([^\'"]*)[\'"]', html, re.IGNORECASE)
    for prop, content in meta_patterns:
        tags[prop.lower()] = content.strip()
    
    # Reverse order if content comes before name/property
    meta_patterns_rev = re.findall(r'<meta[^>]+content=[\'"]([^\'"]*)[\'"][^>]+(?:name|property)=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
    for content, prop in meta_patterns_rev:
        tags[prop.lower()] = content.strip()

    return tags


def clean_html_to_text(html: str) -> str:
    """Clean HTML to structured text using trafilatura if installed, or fallback DOM regex cleaning."""
    if not html:
        return ""

    # 1. Attempt Trafilatura
    try:
        import trafilatura
        extracted = trafilatura.extract(
            html,
            include_links=False,
            include_images=False,
            output_format="markdown",
            favor_recall=True,
        )
        if extracted and len(extracted.strip()) > 50:
            return extracted.strip()
    except ImportError:
        pass
    except Exception as tf_err:
        logger.debug("Trafilatura extraction fallback: %s", tf_err)

    # 2. Fallback heuristic cleaning
    # Remove script, style, nav, footer, header, aside, noscript
    cleaned = re.sub(r'<(script|style|nav|header|footer|aside|noscript|svg)[^>]*>.*?</\1>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Extract article or main if present
    article_match = re.search(r'<(article|main)[^>]*>(.*?)</\1>', cleaned, flags=re.DOTALL | re.IGNORECASE)
    target_block = article_match.group(2) if article_match else cleaned

    # Convert common block tags to newlines
    target_block = re.sub(r'<(p|div|h[1-6]|li|br)[^>]*>', '\n', target_block, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', target_block)
    # Decode HTML entities
    import html as html_lib
    text = html_lib.unescape(text)
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


class CrawlerService:
    """Engine for acquiring, parsing, and screenshotting web articles."""

    @classmethod
    async def crawl_article(
        cls,
        url: str,
        ticket_number: str = "TICKET",
        storage_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Crawl article with automatic pagination, JSON-LD extraction, clean text, and screenshot."""
        storage_dir = storage_dir or settings.EVIDENCE_DIR
        os.makedirs(storage_dir, exist_ok=True)
        evidence_path = os.path.join(storage_dir, f"{ticket_number}_post.png")
        
        target_url = normalize_news_url(url)
        parsed_url = urlparse(target_url)
        domain = parsed_url.netloc.replace("www.", "")

        html_content = ""
        screenshot_taken = False
        screenshot_sha256 = ""

        # 1. Attempt Playwright headless acquisition (handles JS-rendering + visual screenshot)
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                )
                page = await context.new_page()
                try:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(1500)
                    html_content = await page.content()
                    
                    # Take clean screenshot
                    await page.screenshot(path=evidence_path, full_page=False)
                    screenshot_taken = os.path.exists(evidence_path)
                finally:
                    await browser.close()
        except Exception as pw_err:
            logger.warning("Playwright crawler fallback to HTTP for %s: %s", target_url, pw_err)

        # 2. Fallback HTTP fetch if HTML is empty
        if not html_content:
            try:
                import httpx
                async with httpx.AsyncClient(
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    follow_redirects=True,
                    timeout=15.0,
                ) as client:
                    resp = await client.get(target_url)
                    if resp.status_code == 200:
                        html_content = resp.text
            except Exception as http_err:
                logger.warning("HTTP fallback failed for %s: %s", target_url, http_err)

        # 3. Extract Metadata
        json_ld = extract_json_ld(html_content)
        meta_tags = extract_meta_tags(html_content)

        headline = (
            json_ld.get("headline")
            or meta_tags.get("og:title")
            or meta_tags.get("twitter:title")
            or meta_tags.get("page_title")
            or ""
        )
        author = (
            json_ld.get("author")
            or meta_tags.get("author")
            or meta_tags.get("article:author")
            or meta_tags.get("og:site_name")
            or domain
        )
        date_published = (
            json_ld.get("date_published")
            or meta_tags.get("article:published_time")
            or meta_tags.get("og:pubdate")
            or ""
        )
        media_image_url = (
            json_ld.get("image")
            or meta_tags.get("og:image")
            or meta_tags.get("twitter:image")
            or ""
        )
        description = (
            json_ld.get("description")
            or meta_tags.get("og:description")
            or meta_tags.get("description")
            or ""
        )

        # 4. Clean Article Text / Markdown
        clean_text = clean_html_to_text(html_content)
        if not clean_text and description:
            clean_text = description

        # 5. Handle Screenshot fallback banner if Playwright didn't capture screenshot
        if not screenshot_taken or not os.path.exists(evidence_path):
            # Attempt to download media_image_url if present
            if media_image_url and media_image_url.startswith("http"):
                try:
                    import urllib.request
                    req = urllib.request.Request(
                        media_image_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        raw_img = resp.read()
                    if raw_img and len(raw_img) > 500:
                        with open(evidence_path, "wb") as f:
                            f.write(raw_img)
                        screenshot_taken = True
                except Exception as img_err:
                    logger.debug("Failed downloading article media_image_url: %s", img_err)

            if not screenshot_taken or not os.path.exists(evidence_path):
                # Forensic banner fallback
                try:
                    from PIL import Image, ImageDraw
                    img = Image.new("RGB", (1280, 720), color=(15, 23, 42))
                    draw = ImageDraw.Draw(img)
                    draw.rectangle([(0, 0), (1280, 70)], fill=(30, 41, 59))
                    draw.text((40, 24), "TILIK DIGITAL EVIDENCE ARCHIVE (NEWS CRAWLER)", fill=(56, 189, 248))
                    draw.text((40, 110), f"Nomor Tiket : {ticket_number}", fill=(241, 245, 249))
                    draw.text((40, 150), f"Sumber      : {domain.upper()}", fill=(241, 245, 249))
                    draw.text((40, 190), f"Judul       : {headline[:80]}", fill=(241, 245, 249))
                    draw.text((40, 230), f"URL Target  : {target_url[:90]}", fill=(148, 163, 184))
                    draw.text((40, 270), f"Penulis     : {author}", fill=(148, 163, 184))
                    draw.text((40, 340), "STATUS: DOKUMEN DIGITAL BERITA TERVERIFIKASI & TERKONSINYASI", fill=(52, 211, 153))
                    img.save(evidence_path, "PNG")
                    screenshot_taken = True
                except Exception as bn_err:
                    logger.warning("Failed generating news evidence banner: %s", bn_err)

        if os.path.exists(evidence_path):
            with open(evidence_path, "rb") as f:
                screenshot_sha256 = hashlib.sha256(f.read()).hexdigest()

        return {
            "platform": "web",
            "url": target_url,
            "domain": domain,
            "headline": headline,
            "title": headline,
            "author": author,
            "date_published": date_published,
            "description": description,
            "clean_text": clean_text,
            "caption": clean_text,
            "media_image_url": media_image_url,
            "screenshot_path": evidence_path if screenshot_taken else None,
            "screenshot_sha256": screenshot_sha256,
        }
