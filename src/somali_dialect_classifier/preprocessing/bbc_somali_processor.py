"""
BBC Somali news processor.

Ethically scrapes BBC Somali for news articles following best practices:
- Respects robots.txt
- Implements rate limiting and random delays
- Uses retry logic with exponential backoff
- Inherits shared orchestration from BasePipeline
"""

from pathlib import Path
import time
import random
from typing import List, Optional, Dict, Any, Iterator, Tuple
from datetime import datetime, timezone
import json

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from tqdm import tqdm
import feedparser

from .base_pipeline import BasePipeline, RawRecord
from .text_cleaners import create_html_cleaner, TextCleaningPipeline
from .crawl_ledger import get_ledger, CrawlState
from .dedup import DedupEngine, DedupConfig
from ..utils.logging_utils import StructuredLogger, set_context, Timer, log_event, LogEvent
from ..utils.metrics import MetricsCollector, QualityReporter, PipelineType
from ..utils.rate_limiter import AdaptiveRateLimiter, RateLimitConfig, TimedRequest
from ..config import get_config


class BBCSomaliProcessor(BasePipeline):
    """
    Processor for scraping, extracting, and cleaning BBC Somali news articles.

    Inherits shared orchestration from BasePipeline and implements
    BBC-specific scraping logic with ethical rate limiting.
    """

    def __init__(self, max_articles: Optional[int] = None, delay_range: tuple = (3, 6), force: bool = False):
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

        # Initialize deduplication BEFORE BasePipeline (which generates run_id)
        dedup_config = DedupConfig(
            hash_fields=["text", "url"],
            enable_minhash=True,
            similarity_threshold=0.85
        )
        self.dedup = DedupEngine(dedup_config)
        self.ledger = get_ledger()
        self.metrics = None  # Will be initialized in download()

        # Initialize BasePipeline with source name (this generates run_id and StructuredLogger)
        super().__init__(source="BBC-Somali", log_frequency=10, force=force)

        # Note: StructuredLogger is now initialized in BasePipeline
        # Use self.logger for all logging (it's now a structured logger with JSON output)

        # BBC-specific configuration
        self.base_url = "https://www.bbc.com/somali"
        self.headers = {
            'User-Agent': 'SomaliNLPBot/1.0 (Educational Research; +https://github.com/somali-nlp/somali-dialect-classifier)',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'so,en;q=0.9',
        }
        self.max_articles = max_articles
        self.delay_range = delay_range

        # Configure adaptive rate limiter from config
        bbc_config = config.scraping.bbc
        rate_config = RateLimitConfig(
            min_delay=bbc_config.delay_range[0],
            max_delay=bbc_config.delay_range[1],
            backoff_multiplier=bbc_config.backoff_multiplier,
            max_backoff=bbc_config.max_backoff,
            requests_per_hour=bbc_config.max_requests_per_hour,
            jitter=bbc_config.jitter,
            adaptive=True
        )
        self.rate_limiter = AdaptiveRateLimiter(rate_config)

        # File paths (BBC-specific naming)
        # Pattern: {source_slug}_{run_id}_{layer}_{descriptive_name}.{ext}
        self.article_links_file = self.raw_dir / f"bbc-somali_{self.run_id}_raw_article-links.json"
        self.staging_file = self.staging_dir / f"bbc-somali_{self.run_id}_staging_articles.jsonl"
        self.processed_file = self.processed_dir / f"bbc-somali_{self.run_id}_processed_cleaned.txt"

    def _register_filters(self) -> None:
        """Register BBC-specific filters."""
        from .filters import min_length_filter, langid_filter, dialect_heuristic_filter

        # Minimum length threshold for articles
        self.record_filters.append((min_length_filter, {"threshold": 50}))

        # Language filter (Somali only with relaxed confidence threshold)
        # Threshold lowered to 0.3 due to heuristic-based detection
        self.record_filters.append((langid_filter, {
            "allowed_langs": {"so"},
            "confidence_threshold": 0.3
        }))

        # Dialect/topic heuristics for enrichment
        # These help with downstream dialect scoring without filtering
        topic_lexicons = {
            "sports": ["kubadda", "ciyaaryahan", "kooxda", "tartanka", "garoonka"],
            "politics": ["xukuumad", "madaxweyne", "baarlamaan", "doorasho", "siyaasad"],
            "economy": ["dhaqaale", "ganacsiga", "suuq", "lacagta", "ganacsi"],
        }

        self.record_filters.append((dialect_heuristic_filter, {
            "ruleset": topic_lexicons,
            "enrich_only": True  # Don't filter, just enrich metadata
        }))

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

    def _get_source_metadata(self) -> Dict[str, Any]:
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
            Register string ("formal", "informal", "colloquial")

        Note:
            BBC news articles are professional journalism classified as "formal"
        """
        return "formal"

    def _scrape_rss_feeds(self) -> List[str]:
        """
        Scrape RSS feeds for article URLs.

        Returns:
            List of article URLs from RSS feeds
        """
        bbc_config = self.config.scraping.bbc
        feeds = bbc_config.rss_feeds
        max_items = bbc_config.max_items_per_feed
        check_frequency_hours = bbc_config.check_frequency_hours

        article_urls = []

        self.logger.info(f"Scraping {len(feeds)} RSS feeds...")

        for feed_url in feeds:
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
                    url = entry.get('link')
                    if url and '/somali/' in url and '/articles/' in url:
                        article_urls.append(url)

                # Record fetch
                self.ledger.record_rss_fetch(feed_url, len(items))
                self.metrics.increment('rss_feeds_fetched')
                self.metrics.increment('rss_items_found', len(items))
                self.logger.info(f"  ✓ Found {len(items)} items in feed")

            except Exception as e:
                self.logger.error(f"  ✗ Failed to parse RSS feed {feed_url}: {e}")
                self.metrics.increment('rss_feeds_failed')

        self.logger.info(f"RSS scraping complete: {len(article_urls)} articles from {len(feeds)} feeds")
        return article_urls

    def _compute_text_hash(self, text: str, url: str) -> str:
        """
        Compute SHA256 hash of text content.

        Args:
            text: Text content to hash
            url: URL of the content

        Returns:
            Hexadecimal hash string
        """
        return self.dedup.hasher.compute_hash(text=text, url=url)

    def download(self) -> Path:
        """
        Discover and download article links (respects robots.txt).

        Returns:
            Path to article links file
        """
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        # Set context using run_id from base_pipeline
        set_context(run_id=self.run_id, source="BBC-Somali", phase="discovery")

        # Initialize metrics collector with run_id from base_pipeline
        self.metrics = MetricsCollector(self.run_id, "BBC-Somali", pipeline_type=PipelineType.WEB_SCRAPING)

        # Check if cached links exist and are still valid
        if self.article_links_file.exists() and not self.force:
            # Load cached metadata to check if parameters match
            with open(self.article_links_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            cached_max_articles = cached_data.get('max_articles_limit')

            # If parameters match, reuse cache
            if cached_max_articles == self.max_articles:
                self.logger.info(f"Article links already exist with matching parameters: {self.article_links_file}")
                return self.article_links_file
            else:
                self.logger.info(
                    f"Parameter mismatch: cached max_articles={cached_max_articles}, "
                    f"current max_articles={self.max_articles}. Re-discovering articles..."
                )

        # Check robots.txt
        self._check_robots_txt()

        # Strategy 1: RSS feeds (primary)
        rss_links = self._scrape_rss_feeds()
        self.logger.info(f"RSS feeds discovered: {len(rss_links)} articles")

        # Strategy 2: Web scraping (fallback if RSS yields few results)
        if len(rss_links) < 50:  # Threshold for fallback
            self.logger.info("RSS yielded few results, falling back to web scraping...")
            web_links = self._get_article_links()
            # Combine and deduplicate
            article_links = list(set(rss_links + web_links))
            self.logger.info(f"Combined discovery: {len(article_links)} total articles")
        else:
            article_links = rss_links

        # Mark URLs as discovered in ledger
        for url in article_links:
            self.ledger.discover_url(url, "bbc", metadata={"discovered_at": self.date_accessed})
            self.metrics.increment('urls_discovered')

        # Apply max_articles limit if specified (for scraping phase)
        links_to_scrape = article_links[:self.max_articles] if self.max_articles else article_links

        # Save all discovered links with metadata
        with open(self.article_links_file, 'w', encoding='utf-8') as f:
            json.dump({
                'links': links_to_scrape,
                'total_discovered': len(article_links),
                'total_to_scrape': len(links_to_scrape),
                'discovered_at': self.date_accessed,
                'max_articles_limit': self.max_articles,
                'run_id': self.run_id,
            }, f, ensure_ascii=False, indent=2)

        if self.max_articles and len(article_links) > self.max_articles:
            self.logger.info(
                f"Limiting scrape to {self.max_articles} of {len(article_links)} discovered articles"
            )

        self.logger.info(f"Saved {len(links_to_scrape)} article links -> {self.article_links_file}")

        # Export metrics
        metrics_path = Path("data/metrics") / f"{self.run_id}_discovery.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics.export_json(metrics_path)

        return self.article_links_file

    def extract(self) -> Path:
        """
        Scrape articles from discovered links.

        Returns:
            Path to scraped articles file
        """
        if not self.article_links_file.exists():
            raise FileNotFoundError(f"Article links not found: {self.article_links_file}")

        self.staging_dir.mkdir(parents=True, exist_ok=True)

        if self.staging_file.exists() and not self.force:
            self.logger.info(f"Staging file already exists: {self.staging_file}")
            self.logger.info("Use force=True to re-scrape")
            return self.staging_file

        if self.staging_file.exists() and self.force:
            self.logger.info(f"Force re-scraping: removing existing file {self.staging_file}")
            self.staging_file.unlink()

        # Load links
        with open(self.article_links_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            links = data['links']

        # Set context for extraction phase using run_id from base_pipeline
        set_context(run_id=self.run_id, source="BBC-Somali", phase="fetch")

        # Resume metrics or create new with run_id from base_pipeline
        if self.metrics is None:
            self.metrics = MetricsCollector(self.run_id, "BBC-Somali", pipeline_type=PipelineType.WEB_SCRAPING)

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("PHASE 2: Article Extraction")
        self.logger.info("=" * 60)

        articles_count = 0
        session = self._get_http_session()

        # Open staging file for streaming JSONL writes to avoid memory spike
        with open(self.staging_file, 'w', encoding='utf-8') as staging_out:
            # Use tqdm for progress tracking
            with tqdm(total=len(links), desc="Scraping articles", unit="article") as pbar:
                for i, link in enumerate(links, 1):
                    # Check if should fetch (skip if already processed/failed)
                    if not self.ledger.should_fetch_url(link, force=self.force):
                        pbar.update(1)
                        self.metrics.increment('urls_skipped')
                        continue

                    # Use TimedRequest for adaptive rate limiting
                    with TimedRequest(self.rate_limiter) as timer:
                        try:
                            # Scrape article with conditional headers
                            article = self._scrape_article(session, link)

                            if article and article.get('text'):
                                # Process duplicates with combined exact and near-duplicate detection
                                is_dup, dup_type, similar_url, text_hash, minhash_sig = self.dedup.process_document(
                                    article['text'],
                                    link
                                )

                                if is_dup:
                                    self.logger.info(
                                        f"{dup_type.capitalize()} duplicate detected: {link} "
                                        f"(similar to {similar_url})"
                                    )
                                    self.ledger.mark_duplicate(link, similar_url)
                                    # Increment correct metric based on duplicate type
                                    if dup_type == "exact":
                                        self.metrics.increment('urls_deduplicated')
                                    elif dup_type == "near":
                                        self.metrics.increment('near_duplicates')
                                    pbar.update(1)
                                    continue

                                # Store hash and signature in article
                                article['text_hash'] = text_hash
                                article['minhash_signature'] = minhash_sig

                                # Mark as fetched in ledger
                                self.ledger.mark_fetched(
                                    url=link,
                                    http_status=200,
                                    content_length=len(article['text'])
                                )
                                self.metrics.increment('urls_fetched')
                                self.metrics.record_http_status(200)
                                self.metrics.record_text_length(len(article['text']))

                                # Write to staging JSONL (streaming to avoid memory spike)
                                staging_out.write(json.dumps(article, ensure_ascii=False) + '\n')
                                articles_count += 1

                                # Save incrementally (resilience against failures)
                                # Pattern: {source_slug}_{run_id}_raw_article-{num}.json
                                individual_file = self.raw_dir / f"bbc-somali_{self.run_id}_raw_article-{i:04d}.json"
                                with open(individual_file, 'w', encoding='utf-8') as f:
                                    json.dump(article, f, ensure_ascii=False, indent=2)
                            else:
                                # Mark as failed
                                self.ledger.mark_failed(link, "Failed to scrape or empty text")
                                self.metrics.increment('urls_failed')
                                self.metrics.record_error("scrape_failed")

                        except requests.HTTPError as e:
                            # Handle HTTP 429 (Too Many Requests)
                            if e.response.status_code == 429:
                                retry_after = e.response.headers.get('Retry-After')
                                self.rate_limiter.handle_429(retry_after)
                                self.metrics.record_http_status(429)
                                self.metrics.increment('rate_limit_errors')
                                pbar.update(1)
                                continue
                            else:
                                # Other HTTP errors
                                self.ledger.mark_failed(link, f"HTTP {e.response.status_code}")
                                self.metrics.record_http_status(e.response.status_code)
                                self.metrics.increment('urls_failed')
                                pbar.update(1)
                                continue

                    # Record fetch duration
                    self.metrics.record_fetch_duration(timer.get_elapsed_ms())

                    # Update progress bar
                    pbar.update(1)
                    pbar.set_postfix({"extracted": articles_count})

        self.logger.info("=" * 60)
        self.logger.info(f"Extraction complete: {articles_count}/{len(links)} articles extracted")
        self.logger.info("=" * 60)

        # Export metrics and generate extraction quality report
        metrics_path = Path("data/metrics") / f"{self.run_id}_extraction.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics.export_json(metrics_path)

        # Generate extraction quality report (shows extraction phase only)
        report_path = Path("data/reports") / f"{self.run_id}_extraction_quality_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        QualityReporter(self.metrics).generate_markdown_report(report_path)

        self.logger.info(f"Metrics exported: {metrics_path}")
        self.logger.info(f"Extraction quality report: {report_path}")

        return self.staging_file

    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Extract records from staging file (JSONL format).

        Yields RawRecord objects for each BBC article.
        BasePipeline.process() handles the rest (cleaning, writing, logging).
        """
        # Stream articles from JSONL staging file
        with open(self.staging_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                article = json.loads(line)
                yield RawRecord(
                    title=article['title'],
                    text=article['text'],
                    url=article['url'],
                    metadata={
                        "date_published": article.get('date'),
                        "category": article.get('category', 'news'),
                        "scraped_at": article.get('scraped_at'),
                        "minhash_signature": article.get('minhash_signature'),  # Pass through for ledger
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
            test_paths = ['/somali/', '/somali/topics/', '/somali/articles/']
            user_agent = self.headers.get('User-Agent', '*')

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

    def _discover_topic_sections(self, soup: BeautifulSoup) -> List[tuple]:
        """
        Dynamically discover unique topic section URLs from navigation menu.

        Args:
            soup: BeautifulSoup object of homepage

        Returns:
            List of unique (url, name) tuples for topic sections
        """
        seen_urls = set()
        sections = []

        # Find navigation links with /topics/ pattern
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/somali/topics/' in href:
                # Build full URL
                full_url = f"https://www.bbc.com{href}" if href.startswith('/') else href

                # Skip duplicates
                if full_url in seen_urls:
                    continue

                seen_urls.add(full_url)

                # Extract section name from link text
                section_name = link.get_text(strip=True)
                sections.append((full_url, section_name))

        return sections

    def _extract_article_links_from_soup(self, soup: BeautifulSoup) -> set:
        """
        Extract BBC Somali article links from parsed HTML.

        Args:
            soup: BeautifulSoup parsed HTML content

        Returns:
            Set of article URLs found in the page
        """
        links = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            # BBC Somali articles have /somali/articles/ in URL
            if '/somali/' in href and '/articles/' in href:
                full_url = f"https://www.bbc.com{href}" if href.startswith('/') else href
                links.add(full_url)
        return links

    def _scrape_homepage(self, session: requests.Session) -> Tuple[set, Optional[BeautifulSoup]]:
        """
        Scrape BBC Somali homepage for article links.

        Args:
            session: Requests session with retry logic

        Returns:
            Tuple of (article_links set, homepage soup or None if failed)
        """
        article_links = set()
        self.logger.info("Scraping homepage...")

        try:
            response = session.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()

            homepage_soup = BeautifulSoup(response.content, 'html.parser')
            article_links = self._extract_article_links_from_soup(homepage_soup)

            self.logger.info(f"  ✓ Homepage: {len(article_links)} articles")
            time.sleep(random.uniform(2, 4))

            return article_links, homepage_soup

        except (requests.RequestException, ValueError) as e:
            self.logger.error(f"  ✗ Homepage failed: {e}")
            return article_links, None

    def _scrape_topic_sections(self, session: requests.Session, homepage_soup: BeautifulSoup) -> set:
        """
        Scrape topic sections discovered from homepage.

        Args:
            session: Requests session with retry logic
            homepage_soup: Parsed homepage HTML

        Returns:
            Set of article URLs found across all topic sections
        """
        article_links = set()
        topic_sections = self._discover_topic_sections(homepage_soup)

        if not topic_sections:
            return article_links

        self.logger.info(f"Scraping {len(topic_sections)} topic sections...")

        for section_url, section_name in topic_sections:
            try:
                response = session.get(section_url, headers=self.headers, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')
                before_count = len(article_links)

                # Extract article links from this section
                section_links = self._extract_article_links_from_soup(soup)
                article_links.update(section_links)

                added = len(article_links) - before_count
                self.logger.info(f"  ✓ {section_name}: +{added} articles")

                time.sleep(random.uniform(2, 4))

            except (requests.RequestException, ValueError) as e:
                self.logger.warning(f"  ✗ {section_name}: {e}")

        return article_links

    def _scrape_sitemap(self, session: requests.Session) -> set:
        """
        Parse BBC Somali sitemap for article URLs.

        Args:
            session: Requests session with retry logic

        Returns:
            Set of article URLs found in sitemap
        """
        article_links = set()
        self.logger.info("Scraping sitemap...")

        try:
            response = session.get(f"{self.base_url}/sitemap.xml", headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'xml')

            # Extract URLs from sitemap
            for loc in soup.find_all('loc'):
                url = loc.text.strip()
                # Only include recent articles with /articles/ pattern
                if '/somali/' in url and 'articles' in url and 'bbc.com' in url:
                    # Convert old bbc.co.uk URLs to bbc.com
                    url = url.replace('bbc.co.uk', 'bbc.com')
                    article_links.add(url)

            self.logger.info(f"  ✓ Sitemap: +{len(article_links)} articles")

        except (requests.RequestException, ValueError) as e:
            self.logger.warning(f"  ✗ Sitemap: {e}")

        return article_links

    def _get_article_links(self) -> List[str]:
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

    def _scrape_article(self, session: requests.Session, url: str) -> Optional[Dict]:
        """
        Scrape a single BBC Somali article with conditional requests support.

        Args:
            session: Requests session with retry logic
            url: Article URL

        Returns:
            Dictionary with article data or None if failed/not modified
        """
        try:
            # Get conditional headers from ledger
            conditional_headers = self.ledger.get_conditional_headers(url)
            headers = {**self.headers, **conditional_headers}

            response = session.get(url, headers=headers, timeout=30)

            # Handle 304 Not Modified
            if response.status_code == 304:
                self.logger.info(f"Article not modified: {url}")
                self.metrics.increment('urls_not_modified')
                return None

            response.raise_for_status()

            # Extract ETag and Last-Modified for future requests
            etag = response.headers.get('ETag')
            last_modified = response.headers.get('Last-Modified')

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title_tag = soup.find('h1')
            title = title_tag.text.strip() if title_tag else "No title"

            # Extract article body using semantic selectors (more stable than transient CSS classes)
            # Strategy 1: Try semantic role="main" or <main> tag
            main_content = soup.find('main') or soup.find(role='main')

            if main_content:
                # Extract paragraphs from main content area
                paragraphs = main_content.find_all('p')
                text = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
            else:
                # Strategy 2: Try <article> tag (semantic HTML5)
                article_tag = soup.find('article')
                if article_tag:
                    paragraphs = article_tag.find_all('p')
                    text = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
                else:
                    # Strategy 3: Fall back to data-component or specific article selectors
                    article_body = soup.find(attrs={'data-component': 'text-block'})
                    if article_body:
                        paragraphs = article_body.find_all('p')
                        text = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])
                    else:
                        # Strategy 4: Final fallback - all paragraphs (least reliable)
                        paragraphs = soup.find_all('p')
                        text = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])

            # Warn if text is empty (possible scraper regression)
            if not text:
                self.logger.warning(f"Empty text extracted from {url} - BBC may have changed their HTML structure")

            # Extract metadata
            date_tag = soup.find('time')
            date_published = date_tag['datetime'] if date_tag and date_tag.has_attr('datetime') else None

            article_data = {
                'url': url,
                'title': title,
                'text': text,
                'date': date_published,
                'scraped_at': datetime.now(timezone.utc).isoformat(),
                'category': 'news',  # Could be extracted from URL or meta tags
            }

            # Update ledger with HTTP metadata for future conditional requests
            if etag or last_modified:
                self.ledger.mark_fetched(
                    url=url,
                    http_status=200,
                    etag=etag,
                    last_modified=last_modified,
                    content_length=len(text)
                )

            return article_data

        except requests.HTTPError as e:
            if e.response.status_code == 304:
                # Not modified (redundant check, but safe)
                return None
            raise  # Re-raise for handling in extract()

        except (requests.RequestException, ValueError, KeyError) as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return None

    def _get_http_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retries = Retry(
            total=3,  # Fewer retries for scraping vs downloading dumps
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
