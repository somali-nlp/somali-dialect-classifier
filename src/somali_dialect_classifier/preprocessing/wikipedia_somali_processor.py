"""
Wikipedia Somali data processor.

Orchestrates downloading, extracting, and processing Somali Wikipedia dumps.
Uses BasePipeline for shared orchestration and composable utilities.
"""

import bz2
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Optional

import requests
from tqdm import tqdm

from ..config import get_config
from ..utils.http import HTTPSessionFactory
from ..utils.logging_utils import Timer, set_context
from ..utils.metrics import MetricsCollector, PipelineType, QualityReporter
from .base_pipeline import BasePipeline, RawRecord
from .crawl_ledger import get_ledger
from .dedup import DedupConfig, DedupEngine
from .text_cleaners import TextCleaningPipeline, create_wikipedia_cleaner

# Constants for buffer management
BUFFER_CHUNK_SIZE_MB = 1  # Read 1MB chunks from compressed file
BUFFER_MAX_SIZE_MB = 10  # Max buffer size before truncation
BUFFER_TRUNCATE_SIZE_MB = 1  # Keep last 1MB when truncating
LOG_FREQUENCY_PAGES = 1000  # Log extraction progress every N pages


class WikipediaSomaliProcessor(BasePipeline):
    """
    Processor for downloading, extracting, and cleaning Somali Wikipedia data.

    Inherits shared orchestration from BasePipeline and implements
    Wikipedia-specific logic (XML parsing, URL resolution).
    """

    def __init__(self, force: bool = False):
        # Load config FIRST
        config = get_config()
        self.config = config

        # Initialize deduplication BEFORE BasePipeline (which generates run_id)
        dedup_config = DedupConfig(
            hash_fields=["text", "url"], enable_minhash=True, similarity_threshold=0.85
        )
        self.dedup = DedupEngine(dedup_config)
        self.ledger = get_ledger()
        self.metrics = None  # Will be initialized in download()

        # Initialize BasePipeline with source name (this generates run_id and StructuredLogger)
        super().__init__(source="wikipedia-somali", force=force)

        # Note: StructuredLogger is now initialized in BasePipeline
        # Use self.logger for all logging (it's now a structured logger with JSON output)

        # Wikimedia language code for Somali is "so" → "sowiki". Some users expect "somwiki";
        # we support both, preferring sowiki.
        self.wiki_codes = ("sowiki", "somwiki")
        self.current_code = self.wiki_codes[0]
        self.dump_base = f"https://dumps.wikimedia.org/{self.current_code}/latest/"
        # Default attempt; will auto-resolve if 404
        self.dump_url = self.dump_base + f"{self.current_code}-latest-pages-articles.xml.bz2"
        self.dump_file = self.raw_dir / f"{self.current_code}-latest-pages-articles.xml.bz2"

        # Override staging and processed file paths for Wikipedia-specific naming
        # Pattern: {source_slug}_{run_id}_{layer}_{descriptive_name}.{ext}
        self.staging_file = (
            self.staging_dir / f"wikipedia-somali_{self.run_id}_staging_extracted.txt"
        )
        self.processed_file = (
            self.processed_dir / f"wikipedia-somali_{self.run_id}_processed_cleaned.txt"
        )

        # XML parsing patterns
        self.page_pattern = re.compile(r"<page>.*?</page>", re.DOTALL)
        self.title_pattern = re.compile(r"<title>(.*?)</title>")
        self.text_pattern = re.compile(r"<text[^>]*>(.*?)</text>", re.DOTALL)
        self.timestamp_pattern = re.compile(r"<timestamp>(.*?)</timestamp>")
        self.skip_prefixes = (
            "Special:",
            "Template:",
            "File:",
            "Category:",
            "Help:",
            "User:",
            "Talk:",
            "Wikipedia:",
            "MediaWiki:",
        )
        # Use a unique marker that cannot collide with wiki text headings
        self.page_marker_prefix = "\x1e PAGE:"

    def _register_filters(self) -> None:
        """Register Wikipedia-specific filters."""
        from .filters import langid_filter, min_length_filter

        # Minimum length threshold for articles
        self.filter_engine.register_filter((min_length_filter, {"threshold": 50}))

        # Language filter (Somali only with relaxed confidence threshold)
        # Threshold lowered to 0.3 due to heuristic-based detection
        self.filter_engine.register_filter(
            (langid_filter, {"allowed_langs": {"so"}, "confidence_threshold": 0.3})
        )

    def _create_cleaner(self) -> TextCleaningPipeline:
        """Create Wikipedia-specific text cleaner."""
        return create_wikipedia_cleaner()

    def _get_source_type(self) -> str:
        """Return source type for silver records."""
        return "wiki"

    def _get_license(self) -> str:
        """Return license information for silver records."""
        return "CC-BY-SA-3.0"

    def _get_language(self) -> str:
        """Return language code for silver records."""
        return "so"

    def _get_source_metadata(self) -> dict[str, Any]:
        """Return Wikipedia-specific metadata for silver records."""
        return {
            "wiki_code": self.current_code,
            "dump_url": self.dump_url,
            "dump_file": str(self.dump_file.name),
        }

    def _get_domain(self) -> str:
        """Return content domain for silver records."""
        return "encyclopedia"

    def _get_register(self) -> str:
        """
        Return linguistic register for silver records.

        Returns:
            Register string ("formal", "informal", "colloquial")

        Note:
            Wikipedia articles are encyclopedic content classified as "formal"
        """
        return "formal"

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
        """Download Wikipedia dump if not already present."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        # Set context using run_id from base_pipeline
        set_context(run_id=self.run_id, source="wikipedia-somali", phase="download")

        # Initialize metrics with run_id from base_pipeline
        self.metrics = MetricsCollector(
            self.run_id, "Wikipedia-Somali", pipeline_type=PipelineType.FILE_PROCESSING
        )

        if self.dump_file.exists():
            self.logger.info(f"Dump already exists: {self.dump_file}")
            return self.dump_file

        self.logger.info(f"Downloading from: {self.dump_url}")
        session = self._get_http_session()

        # Track download timing and bytes
        with Timer() as timer:
            response = session.get(self.dump_url, stream=True, timeout=30)
            if response.status_code == 404:
                self.logger.warning(
                    "Default dump URL returned 404. Resolving correct filename from index..."
                )
                self.current_code, self.dump_url = self._resolve_dump_url(session)
                # Update base and output filename to match the resolved URL
                self.dump_base = f"https://dumps.wikimedia.org/{self.current_code}/latest/"
                resolved_name = self.dump_url.rstrip("/").split("/")[-1]
                self.dump_file = self.raw_dir / resolved_name
                response = session.get(self.dump_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("Content-Length", 0))

            # Track URL discovery and file discovery
            self.ledger.discover_url(
                self.dump_url,
                "wikipedia",
                metadata={"wiki_code": self.current_code, "file_size": total_size},
            )
            self.metrics.increment("files_discovered")

            with open(self.dump_file, "wb") as f:
                with tqdm(total=total_size, unit="B", unit_scale=True, desc="Downloading") as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
                            self.metrics.increment("bytes_downloaded", len(chunk))

        # Record download metrics
        self.metrics.record_fetch_duration(timer.get_elapsed_ms())
        self.metrics.increment("files_processed")
        self.metrics.record_http_status(200)

        # Mark as fetched in ledger
        self.ledger.mark_fetched(
            url=self.dump_url, http_status=200, content_length=total_size, source=self.source
        )

        self.logger.info(f"Download completed: {self.dump_file}")

        # Export metrics
        self._export_stage_metrics("discovery")

        return self.dump_file

    def extract(self) -> Path:
        """Extract raw text from Wikipedia XML dump with memory-efficient streaming."""
        if not self.dump_file.exists():
            raise FileNotFoundError(f"Dump file not found: {self.dump_file}")
        self.staging_dir.mkdir(parents=True, exist_ok=True)

        # Set context for extraction phase using run_id from base_pipeline
        set_context(run_id=self.run_id, source="wikipedia-somali", phase="extract")

        # Resume or create metrics with run_id from base_pipeline
        if self.metrics is None:
            self.metrics = MetricsCollector(
                self.run_id, "Wikipedia-Somali", pipeline_type=PipelineType.FILE_PROCESSING
            )

        if self.staging_file.exists() and not self.force:
            self.logger.info(f"Staging file already exists: {self.staging_file}")
            self.logger.info("Use force=True to re-extract")
            return self.staging_file

        if self.staging_file.exists() and self.force:
            self.logger.info(f"Force re-extracting: removing existing file {self.staging_file}")
            self.staging_file.unlink()

        self.logger.info("Extracting text from XML dump...")

        # PHASE 1: Collect all articles with metadata (for incremental filtering)
        self.logger.info("Phase 1: Parsing XML and collecting article metadata...")
        raw_articles = []
        buffer = ""
        buffer_size_threshold = BUFFER_MAX_SIZE_MB * 1024 * 1024

        with bz2.open(self.dump_file, "rt", encoding="utf-8") as fin:
            while True:
                chunk = fin.read(BUFFER_CHUNK_SIZE_MB * 1024 * 1024)
                if not chunk:
                    # Process remaining buffer
                    if buffer:
                        pages = self.page_pattern.findall(buffer)
                        for page in pages:
                            article = self._parse_article_metadata(page)
                            if article:
                                raw_articles.append(article)
                    break

                buffer += chunk

                # Process complete pages from buffer
                pages = self.page_pattern.findall(buffer)
                if pages:
                    for page in pages:
                        article = self._parse_article_metadata(page)
                        if article:
                            raw_articles.append(article)

                    # Remove processed pages from buffer
                    buffer = self.page_pattern.sub("", buffer, count=len(pages))

                # Safety check: if buffer exceeds threshold, warn and truncate oldest data
                if len(buffer) > buffer_size_threshold:
                    self.logger.warning(
                        f"Buffer size exceeded {BUFFER_MAX_SIZE_MB}MB. "
                        f"Truncating to prevent memory issues. Some malformed pages may be skipped."
                    )
                    # Keep only the last chunk to maintain page boundary context
                    buffer = buffer[-(BUFFER_TRUNCATE_SIZE_MB * 1024 * 1024) :]

        self.logger.info(f"Collected {len(raw_articles)} articles from XML dump")

        # PHASE 2: Incremental filtering (skip unchanged articles)
        self.logger.info("Phase 2: Filtering articles based on last processing time...")
        articles_to_process, filter_stats = self._filter_new_articles(raw_articles)

        # Track incremental filtering metrics
        self.metrics.add_custom_metric("incremental_filtering", filter_stats)

        # PHASE 3: Process and write filtered articles
        self.logger.info(f"Phase 3: Processing {len(articles_to_process)} articles...")
        page_count = 0

        # Track extraction timing
        with Timer() as timer:
            with open(self.staging_file, "w", encoding="utf-8") as fout:
                for article in articles_to_process:
                    title = article["title"]
                    text = article["text"]
                    page_url = article["url"]

                    # Track URL discovery
                    self.ledger.discover_url(
                        page_url, "wikipedia", metadata={"title": title, "timestamp": article.get("timestamp")}
                    )

                    # Compute hash and check for duplicates
                    text_hash = self._compute_text_hash(text, page_url)

                    # Check if exact duplicate
                    if not self.dedup.is_duplicate_hash(text_hash):
                        # Not a duplicate - write and record
                        fout.write(f"{self.page_marker_prefix} {title}\n{text}\n\n")
                        page_count += 1
                        self.metrics.record_text_length(len(text))
                        # Store hash→URL mapping for future duplicate detection
                        self.dedup.add_known_hash(text_hash, page_url)
                    else:
                        # Duplicate found - get canonical URL
                        canonical_url = self.dedup.get_canonical_url(text_hash)
                        self.logger.debug(
                            f"Duplicate page detected: {title} matches {canonical_url}"
                        )
                        self.ledger.mark_duplicate(
                            page_url,
                            canonical_url or page_url,  # Fallback to self if not found
                        )
                        self.metrics.increment("urls_deduplicated")

                    if page_count % LOG_FREQUENCY_PAGES == 0:
                        self.logger.info(f"Extracted {page_count} pages so far...")
                        # Track metrics during extraction
                        self.metrics.increment("records_extracted", LOG_FREQUENCY_PAGES)

        # Record extraction timing (use process_duration for extraction phase)
        self.metrics.record_process_duration(timer.get_elapsed_ms())

        # Track final page count if not already tracked
        remainder = page_count % LOG_FREQUENCY_PAGES
        if remainder > 0:
            self.metrics.increment("records_extracted", remainder)

        self.logger.info(f"Extraction completed: {page_count} pages -> {self.staging_file}")

        # Export metrics and generate extraction report
        self._export_stage_metrics("extraction")
        self._generate_quality_report("extraction")

        return self.staging_file

    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Extract records from staging file.

        Yields RawRecord objects for each Wikipedia page.
        BasePipeline.process() handles the rest (cleaning, writing, logging).
        """
        current_title = None
        current_lines = []

        with open(self.staging_file, encoding="utf-8") as fin:
            for line in fin:
                if line.startswith(self.page_marker_prefix + " "):
                    # Yield previous page if exists
                    if current_title is not None:
                        yield RawRecord(
                            title=current_title,
                            text="".join(current_lines),
                            url=self._title_to_url(current_title),
                            metadata={},
                        )

                    # Start new page
                    raw_line = line.rstrip("\n")
                    title_part = raw_line[len(self.page_marker_prefix) + 1 :]
                    current_title = title_part.strip()
                    if not current_title:
                        current_title = None
                        current_lines = []
                        continue
                    current_lines = []
                else:
                    current_lines.append(line)

            # Yield last page
            if current_title is not None:
                yield RawRecord(
                    title=current_title,
                    text="".join(current_lines),
                    url=self._title_to_url(current_title),
                    metadata={},
                )

    def _get_http_session(self) -> requests.Session:
        """Create a requests session with retry policy for robustness."""
        return HTTPSessionFactory.create_session(
            max_retries=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

    def _resolve_dump_url(self, session: requests.Session) -> tuple[str, str]:
        """
        Resolve the correct dump URL by scraping the 'latest' index page.

        Tries known wiki codes in order, prefers multistream variant.

        Returns:
            (wiki_code, resolved_url)
        """
        for code in self.wiki_codes:
            base = f"https://dumps.wikimedia.org/{code}/latest/"
            try:
                idx = session.get(base, timeout=30)
                if idx.status_code == 404:
                    continue
                idx.raise_for_status()
                html = idx.text
            except Exception:
                continue

            # Prefer multistream if present
            for filename in (
                f"{code}-latest-pages-articles-multistream.xml.bz2",
                f"{code}-latest-pages-articles.xml.bz2",
            ):
                if filename in html:
                    resolved = base + filename
                    self.logger.info(f"Resolved dump URL: {resolved}")
                    return code, resolved

        # If not found, surface a helpful error
        raise RuntimeError(
            "Could not locate a suitable dump file on the 'latest' pages for codes "
            f"{self.wiki_codes}. Please check manually on https://dumps.wikimedia.org/."
        )

    def _title_to_url(self, title: str) -> str:
        """Convert Wikipedia title to URL."""
        base = (
            "https://so.wikipedia.org/wiki/"
            if self.current_code.startswith("so")
            else f"https://{self.current_code.replace('wiki', '')}.wikipedia.org/wiki/"
        )
        return base + title.replace(" ", "_")

    def _parse_article_metadata(self, page_xml: str) -> Optional[dict[str, Any]]:
        """
        Parse article metadata from page XML.

        Extracts title, text, timestamp for incremental filtering.

        Args:
            page_xml: Raw XML string for a single page

        Returns:
            Dictionary with article metadata, or None if parsing fails
        """
        title_match = self.title_pattern.search(page_xml)
        text_match = self.text_pattern.search(page_xml)
        timestamp_match = self.timestamp_pattern.search(page_xml)

        if not (title_match and text_match):
            return None

        title = title_match.group(1)

        # Skip namespace pages
        if any(title.startswith(prefix) for prefix in self.skip_prefixes):
            return None

        text = text_match.group(1)
        timestamp = timestamp_match.group(1) if timestamp_match else None

        return {
            "title": title,
            "text": text,
            "url": self._title_to_url(title),
            "timestamp": timestamp,
        }

    def _get_last_processing_time(self) -> Optional["datetime"]:
        """
        Get last successful processing time from ledger.

        Returns:
            datetime of last processing, or None if first run
        """
        from datetime import datetime

        try:
            return self.ledger.get_last_processing_time(self.source)
        except Exception as e:
            self.logger.warning(f"Failed to get last processing time: {e}")
            return None

    def _filter_new_articles(
        self, articles: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Filter articles to only those newer than last processing.

        Implements incremental processing by comparing article timestamps
        with the last successful processing time from the ledger.

        Args:
            articles: List of extracted articles with metadata

        Returns:
            Tuple of (filtered_articles, stats_dict)

        Stats include:
            - total: Total articles examined
            - new: New articles to process
            - skipped: Articles skipped (unchanged)
            - last_processing_time: Last processing timestamp (if available)
        """
        from datetime import datetime

        last_time = self._get_last_processing_time()

        if last_time is None:
            self.logger.info("First run detected - processing all articles")
            return articles, {
                "total": len(articles),
                "new": len(articles),
                "skipped": 0,
                "last_processing_time": None,
            }

        self.logger.info(f"Filtering articles newer than {last_time.isoformat()}")

        new_articles = []
        for article in articles:
            # Parse article timestamp from metadata
            article_time_str = article.get("timestamp")
            if not article_time_str:
                # No timestamp - process to be safe (fail-safe approach)
                new_articles.append(article)
                continue

            try:
                # Parse ISO 8601 timestamp (Wikipedia format: 2015-08-03T06:50:15Z)
                article_time = datetime.fromisoformat(article_time_str.replace("Z", "+00:00"))
                if article_time > last_time:
                    new_articles.append(article)
            except (ValueError, AttributeError) as e:
                # Invalid timestamp - process to be safe
                self.logger.warning(f"Invalid timestamp format: {article_time_str}, error: {e}")
                new_articles.append(article)

        stats = {
            "total": len(articles),
            "new": len(new_articles),
            "skipped": len(articles) - len(new_articles),
            "last_processing_time": last_time.isoformat() if last_time else None,
        }

        self.logger.info(
            f"Filtered {stats['skipped']} unchanged articles, {stats['new']} new articles"
        )

        return new_articles, stats
