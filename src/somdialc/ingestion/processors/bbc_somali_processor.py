"""
BBC Somali news processor.

Ethically scrapes BBC Somali for news articles following best practices:
- Respects robots.txt
- Implements rate limiting and random delays
- Uses retry logic with exponential backoff
- Inherits shared orchestration from BasePipeline
"""

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Optional

import feedparser
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

from ...infra.config import get_config
from ...infra.rate_limiter import AdaptiveRateLimiter, RateLimitConfig
from ...quality.text_cleaners import TextCleaningPipeline, create_html_cleaner
from ..base_pipeline import BasePipeline, RawRecord
from ..crawl_ledger import get_ledger
from ..pipeline_setup import PipelineSetup
from ..processor_registry import register_processor
from .bbc.discovery import (
    discover_topic_sections,
    extract_article_links_from_soup,
    scrape_homepage,
    scrape_topic_sections,
)
from .bbc.discovery import (
    download as download_bbc_articles,
)
from .bbc.extraction import (
    compute_text_hash,
    extract_async,
    extract_sync,
    get_http_session,
    parse_article_from_html,
    scrape_article,
)


@register_processor("bbc")
class BBCSomaliProcessor(BasePipeline):
    """
    Processor for scraping, extracting, and cleaning BBC Somali news articles.

    Inherits shared orchestration from BasePipeline and implements
    BBC-specific scraping logic with ethical rate limiting.
    """

    def __init__(
        self,
        max_articles: Optional[int] = None,
        delay_range: tuple = (1, 3),
        force: bool = False,
        run_seed: Optional[str] = None,
        ledger=None,
    ):
        """
        Initialize BBC Somali processor.

        Args:
            max_articles: Maximum number of articles to scrape (None = unlimited, scrapes all discovered)
            delay_range: (min, max) seconds to wait between requests
            force: Force reprocessing even if output files exist (default: False)
        """
        # Load config FIRST (before super().__init__())
        config = get_config()
        self.config = config

        # Initialize deduplication BEFORE BasePipeline (now uses centralized config)
        self.dedup = PipelineSetup.create_dedup_engine()
        self.ledger = ledger if ledger is not None else get_ledger()
        self.metrics = None  # Will be initialized in download()

        # Initialize BasePipeline with source name (this generates run_id and StructuredLogger)
        super().__init__(source="bbc-somali", log_frequency=10, force=force, run_seed=run_seed)

        # Note: StructuredLogger is now initialized in BasePipeline
        # Use self.logger for all logging (it's now a structured logger with JSON output)

        # BBC-specific configuration
        self.base_url = "https://www.bbc.com/somali"
        self.headers = {
            "User-Agent": "SomaliNLPBot/1.0 (Educational Research; +https://github.com/somali-nlp/somali-dialect-classifier)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "so,en;q=0.9",
        }
        self.max_articles = max_articles
        self.delay_range = delay_range

        # Configure adaptive rate limiter from config
        bbc_config = config.scraping.bbc
        rate_config = RateLimitConfig(
            min_delay=self.delay_range[0],
            max_delay=self.delay_range[1],
            backoff_multiplier=bbc_config.backoff_multiplier,
            max_backoff=bbc_config.max_backoff,
            requests_per_hour=bbc_config.max_requests_per_hour,
            jitter=bbc_config.jitter,
            adaptive=True,
        )
        self.rate_limiter = AdaptiveRateLimiter(rate_config)

        # File paths (BBC-specific naming)
        # Pattern: {source_slug}_{run_id}_{layer}_{descriptive_name}.{ext}
        self.article_links_file = self.raw_dir / f"bbc-somali_{self.run_id}_raw_article-links.json"
        self.staging_file = self.staging_dir / f"bbc-somali_{self.run_id}_staging_articles.jsonl"
        self.processed_file = self.processed_dir / f"bbc-somali_{self.run_id}_processed_cleaned.txt"

    def _register_filters(self) -> None:
        """Register BBC-specific filters."""
        from ...quality.filter_functions import (
            langid_filter,
            min_length_filter,
            topic_lexicon_enrichment_filter,
        )

        # Minimum length threshold for articles
        self.filter_engine.register_filter(min_length_filter, {"threshold": 50})

        # Language filter (Somali only with relaxed confidence threshold)
        # Threshold lowered to 0.3 due to heuristic-based detection
        self.filter_engine.register_filter(
            langid_filter, {"allowed_langs": {"so"}, "confidence_threshold": 0.3}
        )

        # Topic lexicon enrichment (NOT dialect detection)
        # Enriches records with topic markers for downstream analysis
        topic_lexicons = {
            "sports": ["kubadda", "ciyaaryahan", "kooxda", "tartanka", "garoonka"],
            "politics": ["xukuumad", "madaxweyne", "baarlamaan", "doorasho", "siyaasad"],
            "economy": ["dhaqaale", "ganacsiga", "suuq", "lacagta", "ganacsi"],
        }

        self.filter_engine.register_filter(
            topic_lexicon_enrichment_filter,
            {
                "ruleset": topic_lexicons,
                "enrich_only": True,  # Don't filter, just enrich metadata
            },
        )

    def _create_cleaner(self) -> TextCleaningPipeline:
        """Create HTML text cleaner for BBC articles."""
        return create_html_cleaner()

    def _get_source_type(self) -> str:
        """Return source type for silver records."""
        return "news"

    def _get_license(self) -> str:
        """Return license information for silver records."""
        return "BBC Terms of Use"

    def _get_language(self) -> str:
        """Return language code for silver records."""
        return "so"

    def _get_source_metadata(self) -> dict[str, Any]:
        """Return BBC-specific metadata for silver records."""
        return {
            "base_url": self.base_url,
            "max_articles": self.max_articles,
        }

    def _get_domain(self) -> str:
        """Return content domain for silver records."""
        return "news"

    def _get_register(self) -> str:
        """
        Return linguistic register for silver records.

        Returns:
            Content-type register string for BBC Somali news articles.
        """
        return "news"

    def _scrape_rss_feeds(self) -> list[str]:
        """
        Scrape RSS feeds for article URLs.

        Returns:
            List of article URLs from RSS feeds
        """
        from ...infra.metrics import MetricsCollector, PipelineType
        from ...infra.security import validate_url_for_source

        if self.metrics is None:
            self.metrics = MetricsCollector(
                self.run_id, self.source, pipeline_type=PipelineType.WEB_SCRAPING
            )

        bbc_config = self.config.scraping.bbc
        feeds = bbc_config.rss_feeds
        max_items = bbc_config.max_items_per_feed
        check_frequency_hours = bbc_config.check_frequency_hours

        # BBC domain whitelist for SSRF protection
        bbc_allowed_domains = {"bbc.com", "bbc.co.uk"}

        article_urls = []

        self.logger.info(f"Scraping {len(feeds)} RSS feeds...")

        for feed_url in feeds:
            # Validate RSS feed URL before fetching (SSRF protection)
            is_valid, error_msg = validate_url_for_source(feed_url, "bbc", bbc_allowed_domains)
            if not is_valid:
                self.logger.warning(f"  ✗ Rejected RSS feed URL: {feed_url} ({error_msg})")
                self.metrics.increment("urls_rejected_security")
                continue

            # Check throttling
            if not self.ledger.should_fetch_rss(feed_url, min_hours=check_frequency_hours):
                self.logger.info(f"  ⊘ Skipping RSS feed (throttled): {feed_url}")
                continue

            try:
                # Fetch and parse RSS
                self.logger.info(f"  → Fetching RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)

                # Extract article URLs
                items = feed.entries[:max_items] if max_items else feed.entries
                for entry in items:
                    url = entry.get("link")
                    if not url:
                        continue

                    # Validate article URL before adding (SSRF protection)
                    is_valid, error_msg = validate_url_for_source(url, "bbc", bbc_allowed_domains)
                    if not is_valid:
                        self.logger.debug(f"  ⊘ Rejected article URL: {url} ({error_msg})")
                        self.metrics.increment("urls_rejected_security")
                        continue

                    # Additional BBC-specific checks
                    if "/somali/" in url and "/articles/" in url:
                        article_urls.append(url)

                # Record fetch
                self.ledger.record_rss_fetch(feed_url, len(items))
                self.metrics.increment("rss_feeds_fetched")
                self.metrics.increment("rss_items_found", len(items))
                self.logger.info(f"  ✓ Found {len(items)} items in feed")

            except Exception as e:
                self.logger.error(f"  ✗ Failed to parse RSS feed {feed_url}: {e}")
                self.metrics.increment("rss_feeds_failed")

        self.logger.info(
            f"RSS scraping complete: {len(article_urls)} articles from {len(feeds)} feeds"
        )
        return article_urls

    def _compute_text_hash(self, text: str, url: str) -> str:
        """Compute SHA256 hash of text content."""
        return compute_text_hash(self, text, url)

    def download(self) -> Path:
        """Discover and download article links (respects robots.txt)."""
        return download_bbc_articles(self)

    async def _fetch_article_async(
        self, session: "aiohttp.ClientSession", url: str, semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        """
        Fetch single article asynchronously.

        Args:
            session: aiohttp ClientSession
            url: Article URL to fetch
            semaphore: Semaphore to limit concurrent requests

        Returns:
            Dictionary with article data or error information
        """
        async with semaphore:
            try:
                # Get conditional headers from ledger
                conditional_headers = self.ledger.get_conditional_headers(url)
                headers = {**self.headers, **conditional_headers}

                async with session.get(url, headers=headers, timeout=30) as response:
                    # Handle 304 Not Modified
                    if response.status == 304:
                        self.logger.info(f"Article not modified: {url}")
                        self.metrics.increment("urls_not_modified")
                        return {"url": url, "status": 304, "not_modified": True}

                    response.raise_for_status()

                    # Extract ETag and Last-Modified for future requests
                    etag = response.headers.get("ETag")
                    last_modified = response.headers.get("Last-Modified")

                    html = await response.text()
                    return {
                        "url": url,
                        "html": html,
                        "status": response.status,
                        "etag": etag,
                        "last_modified": last_modified,
                    }

            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout fetching {url}")
                return {"url": url, "error": "timeout", "status": None}

            except aiohttp.ClientError as e:
                error_msg = str(e)
                self.logger.warning(f"Client error fetching {url}: {error_msg}")
                return {"url": url, "error": error_msg, "status": getattr(e, "status", None)}

            except Exception as e:
                self.logger.error(f"Unexpected error fetching {url}: {e}")
                return {"url": url, "error": str(e), "status": None}

    async def _fetch_all_articles_async(
        self, urls: list[str], max_concurrent: int = 10
    ) -> list[dict]:
        """
        Fetch multiple articles concurrently using async HTTP.

        Args:
            urls: List of article URLs to fetch
            max_concurrent: Maximum number of concurrent requests (default: 10)

        Returns:
            List of article data dictionaries
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        # Configure aiohttp session with timeout
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [self._fetch_article_async(session, url, semaphore) for url in urls]

            # Use tqdm for progress tracking
            results = []
            for coro in tqdm(
                asyncio.as_completed(tasks),
                total=len(tasks),
                desc="Fetching articles (async)",
                unit="article",
            ):
                result = await coro
                results.append(result)

            return results

    def _parse_article_from_html(self, html: str, url: str) -> Optional[dict]:
        """Parse article content from HTML."""
        return parse_article_from_html(self, html, url)

    def _extract_async(self) -> Path:
        """Scrape articles using async HTTP (3-5x faster than sync)."""
        return extract_async(self)

    def extract(self) -> Path:
        """
        Scrape articles from discovered links.

        Uses async HTTP if aiohttp is available (3-5x faster), otherwise falls back to sync.

        Returns:
            Path to scraped articles file
        """
        # Try async first if available
        if AIOHTTP_AVAILABLE:
            try:
                self.logger.info("Using async HTTP for extraction (3-5x faster)")
                return self._extract_async()
            except Exception as e:
                self.logger.warning(f"Async extraction failed: {e}")
                self.logger.info("Falling back to synchronous extraction")

        # Fallback to synchronous extraction
        self.logger.info("Using synchronous HTTP for extraction")
        return self._extract_sync()

    def _extract_sync(self) -> Path:
        """Scrape articles from discovered links (synchronous version)."""
        return extract_sync(self)

    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Extract records from staging file (JSONL format).

        Yields RawRecord objects for each BBC article.
        BasePipeline.process() handles the rest (cleaning, writing, logging).
        """
        # Stream articles from JSONL staging file
        import re as _re

        _bbc_slug_pattern = _re.compile(r"/articles/([a-z0-9]+)(?:[/?#]|$)", _re.IGNORECASE)

        with open(self.staging_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                article = json.loads(line)
                url = article["url"]

                # Extract BBC article slug (e.g. "c8d5dd4l0ryo") from URL as source_id
                slug_match = _bbc_slug_pattern.search(url)
                article_id = slug_match.group(1) if slug_match else ""

                yield RawRecord(
                    title=article["title"],
                    text=article["text"],
                    url=url,
                    metadata={
                        "date_published": article.get("date"),
                        "category": article.get("category", "news"),
                        "scraped_at": article.get("scraped_at"),
                        "minhash_signature": article.get(
                            "minhash_signature"
                        ),  # Pass through for ledger
                        "source_id": article_id,  # BBC article slug (TD-022)
                    },
                )

    def _check_robots_txt(self):
        """
        Check robots.txt for scraping permissions.

        Raises:
            ValueError: If robots.txt disallows scraping BBC Somali paths
        """
        from urllib.robotparser import RobotFileParser

        robots_url = f"{self.base_url}/robots.txt"
        try:
            # Use RobotFileParser for proper robots.txt parsing
            robot_parser = RobotFileParser()
            robot_parser.set_url(robots_url)
            robot_parser.read()

            # Check if our user agent can fetch Somali pages
            test_paths = ["/somali/", "/somali/topics/", "/somali/articles/"]
            user_agent = self.headers.get("User-Agent", "*")

            disallowed_paths = []
            for path in test_paths:
                if not robot_parser.can_fetch(user_agent, f"{self.base_url}{path}"):
                    disallowed_paths.append(path)

            if disallowed_paths:
                error_msg = (
                    f"robots.txt disallows scraping for user agent '{user_agent}' on paths: {disallowed_paths}. "
                    f"Please review {robots_url} and ensure ethical compliance."
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            self.logger.info(f"✓ robots.txt compliance check passed: {robots_url}")

        except ValueError:
            # Re-raise ValueError for robots.txt violations
            raise
        except (requests.RequestException, OSError) as e:
            # Log warning but don't fail (robots.txt might be temporarily unavailable)
            self.logger.warning(
                f"Could not fetch robots.txt: {e}. "
                "Proceeding with scraping but please ensure manual compliance."
            )

    def _discover_topic_sections(self, soup: BeautifulSoup) -> list[tuple]:
        """Dynamically discover unique topic section URLs from navigation menu."""
        return discover_topic_sections(self, soup)

    def _extract_article_links_from_soup(self, soup: BeautifulSoup) -> set:
        """Extract BBC Somali article links from parsed HTML."""
        return extract_article_links_from_soup(self, soup)

    def _scrape_homepage(self, session: requests.Session) -> tuple[set, Optional[BeautifulSoup]]:
        """Scrape BBC Somali homepage for article links."""
        return scrape_homepage(self, session)

    def _scrape_topic_sections(
        self, session: requests.Session, homepage_soup: BeautifulSoup
    ) -> set:
        """Scrape topic sections discovered from homepage."""
        return scrape_topic_sections(self, session, homepage_soup)

    def _scrape_sitemap(self, session: requests.Session) -> set:
        """
        Parse BBC Somali sitemap for article URLs.

        Args:
            session: Requests session with retry logic

        Returns:
            Set of article URLs found in sitemap

        Security:
            - Uses html.parser instead of xml parser to avoid XXE vulnerabilities
            - Sitemaps are valid HTML and don't require XML-specific features
        """
        article_links = set()
        self.logger.info("Scraping sitemap...")

        try:
            response = session.get(f"{self.base_url}/sitemap.xml", headers=self.headers, timeout=30)
            response.raise_for_status()

            # Use html.parser instead of xml to avoid XXE vulnerabilities (SEC-MED-002)
            # Sitemaps are valid HTML and html.parser is XXE-safe by default
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract URLs from sitemap
            for loc in soup.find_all("loc"):
                url = loc.text.strip()
                # Only include recent articles with /articles/ pattern
                if "/somali/" in url and "articles" in url and "bbc.com" in url:
                    # Convert old bbc.co.uk URLs to bbc.com
                    url = url.replace("bbc.co.uk", "bbc.com")
                    article_links.add(url)

            self.logger.info(f"  ✓ Sitemap: +{len(article_links)} articles")

        except (requests.RequestException, ValueError) as e:
            self.logger.warning(f"  ✗ Sitemap: {e}")

        return article_links

    def _get_article_links(self) -> list[str]:
        """
        Discover article links from BBC Somali homepage, sections, and sitemap.

        Returns:
            List of article URLs
        """
        session = self._get_http_session()

        self.logger.info("=" * 60)
        self.logger.info("PHASE 1: Article Discovery")
        self.logger.info("=" * 60)

        # Strategy 1: Scrape homepage
        homepage_links, homepage_soup = self._scrape_homepage(session)

        # Strategy 2: Scrape topic sections (if homepage succeeded)
        section_links = set()
        if homepage_soup:
            section_links = self._scrape_topic_sections(session, homepage_soup)

        # Strategy 3: Parse sitemap
        sitemap_links = self._scrape_sitemap(session)

        # Combine all discovered links
        all_links = homepage_links | section_links | sitemap_links

        self.logger.info("=" * 60)
        self.logger.info(f"Total articles discovered: {len(all_links)}")
        self.logger.info("=" * 60)

        # Sort links for deterministic scraping order
        return sorted(all_links)

    def _scrape_article(self, session: requests.Session, url: str) -> Optional[dict]:
        """Scrape a single BBC Somali article with conditional requests support."""
        return scrape_article(self, session, url)

    def _get_http_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        return get_http_session(self)
