"""
Wikipedia Somali data processor.

Orchestrates downloading, extracting, and processing Somali Wikipedia dumps.
Uses BasePipeline for shared orchestration and composable utilities.
"""

from pathlib import Path
import bz2
import re
from typing import Iterator, Dict, Any, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

from .base_pipeline import BasePipeline, RawRecord
from .text_cleaners import create_wikipedia_cleaner, TextCleaningPipeline
from .crawl_ledger import get_ledger
from .dedup import DedupEngine, DedupConfig
from ..utils.logging_utils import StructuredLogger, set_context, Timer
from ..utils.metrics import MetricsCollector, QualityReporter, PipelineType
from ..config import get_config

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
            hash_fields=["text", "url"],
            enable_minhash=True,
            similarity_threshold=0.85
        )
        self.dedup = DedupEngine(dedup_config)
        self.ledger = get_ledger()
        self.metrics = None  # Will be initialized in download()

        # Initialize BasePipeline with source name (this generates run_id and StructuredLogger)
        super().__init__(source="Wikipedia-Somali", force=force)

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
        self.staging_file = self.staging_dir / f"wikipedia-somali_{self.run_id}_staging_extracted.txt"
        self.processed_file = self.processed_dir / f"wikipedia-somali_{self.run_id}_processed_cleaned.txt"

        # XML parsing patterns
        self.page_pattern = re.compile(r'<page>.*?</page>', re.DOTALL)
        self.title_pattern = re.compile(r'<title>(.*?)</title>')
        self.text_pattern = re.compile(r'<text[^>]*>(.*?)</text>', re.DOTALL)
        self.skip_prefixes = (
            'Special:', 'Template:', 'File:', 'Category:', 'Help:', 'User:', 'Talk:', 'Wikipedia:', 'MediaWiki:'
        )
        # Use a unique marker that cannot collide with wiki text headings
        self.page_marker_prefix = "\x1E PAGE:"

    def _register_filters(self) -> None:
        """Register Wikipedia-specific filters."""
        from .filters import min_length_filter, langid_filter

        # Minimum length threshold for articles
        self.record_filters.append((min_length_filter, {"threshold": 50}))

        # Language filter (Somali only with relaxed confidence threshold)
        # Threshold lowered to 0.3 due to heuristic-based detection
        self.record_filters.append((langid_filter, {
            "allowed_langs": {"so"},
            "confidence_threshold": 0.3
        }))

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

    def _get_source_metadata(self) -> Dict[str, Any]:
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
        set_context(run_id=self.run_id, source="Wikipedia-Somali", phase="download")

        # Initialize metrics with run_id from base_pipeline
        self.metrics = MetricsCollector(self.run_id, "Wikipedia-Somali", pipeline_type=PipelineType.FILE_PROCESSING)

        if self.dump_file.exists():
            self.logger.info(f"Dump already exists: {self.dump_file}")
            return self.dump_file

        self.logger.info(f"Downloading from: {self.dump_url}")
        session = self._get_http_session()

        # Track download timing and bytes
        with Timer() as timer:
            response = session.get(self.dump_url, stream=True, timeout=30)
            if response.status_code == 404:
                self.logger.warning("Default dump URL returned 404. Resolving correct filename from index...")
                self.current_code, self.dump_url = self._resolve_dump_url(session)
                # Update base and output filename to match the resolved URL
                self.dump_base = f"https://dumps.wikimedia.org/{self.current_code}/latest/"
                resolved_name = self.dump_url.rstrip('/').split('/')[-1]
                self.dump_file = self.raw_dir / resolved_name
                response = session.get(self.dump_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("Content-Length", 0))

            # Track URL discovery and file discovery
            self.ledger.discover_url(
                self.dump_url,
                "wikipedia",
                metadata={"wiki_code": self.current_code, "file_size": total_size}
            )
            self.metrics.increment('files_discovered')

            with open(self.dump_file, "wb") as f:
                with tqdm(total=total_size, unit="B", unit_scale=True, desc="Downloading") as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
                            self.metrics.increment('bytes_downloaded', len(chunk))

        # Record download metrics
        self.metrics.record_fetch_duration(timer.get_elapsed_ms())
        self.metrics.increment('files_processed')
        self.metrics.record_http_status(200)

        # Mark as fetched in ledger
        self.ledger.mark_fetched(
            url=self.dump_url,
            http_status=200,
            content_length=total_size
        )

        self.logger.info(f"Download completed: {self.dump_file}")

        # Export metrics
        metrics_path = Path("data/metrics") / f"{self.run_id}_discovery.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics.export_json(metrics_path)

        return self.dump_file

    def extract(self) -> Path:
        """Extract raw text from Wikipedia XML dump with memory-efficient streaming."""
        if not self.dump_file.exists():
            raise FileNotFoundError(f"Dump file not found: {self.dump_file}")
        self.staging_dir.mkdir(parents=True, exist_ok=True)

        # Set context for extraction phase using run_id from base_pipeline
        set_context(run_id=self.run_id, source="Wikipedia-Somali", phase="extract")

        # Resume or create metrics with run_id from base_pipeline
        if self.metrics is None:
            self.metrics = MetricsCollector(self.run_id, "Wikipedia-Somali", pipeline_type=PipelineType.FILE_PROCESSING)

        if self.staging_file.exists() and not self.force:
            self.logger.info(f"Staging file already exists: {self.staging_file}")
            self.logger.info("Use force=True to re-extract")
            return self.staging_file

        if self.staging_file.exists() and self.force:
            self.logger.info(f"Force re-extracting: removing existing file {self.staging_file}")
            self.staging_file.unlink()
        self.logger.info("Extracting text from XML dump...")
        buffer = ""
        page_count = 0
        buffer_size_threshold = BUFFER_MAX_SIZE_MB * 1024 * 1024

        # Track extraction timing
        with Timer() as timer:
            with bz2.open(self.dump_file, 'rt', encoding='utf-8') as fin, \
                 open(self.staging_file, 'w', encoding='utf-8') as fout:
                while True:
                    chunk = fin.read(BUFFER_CHUNK_SIZE_MB * 1024 * 1024)
                    if not chunk:
                        # Process remaining buffer
                        if buffer:
                            pages = self.page_pattern.findall(buffer)
                            for page in pages:
                                title_match = self.title_pattern.search(page)
                                text_match = self.text_pattern.search(page)
                                if title_match and text_match:
                                    title = title_match.group(1)
                                    text = text_match.group(1)
                                    if not any(title.startswith(prefix) for prefix in self.skip_prefixes):
                                        fout.write(f"{self.page_marker_prefix} {title}\n{text}\n\n")
                                        page_count += 1
                        break

                    buffer += chunk

                    # Process complete pages from buffer
                    pages = self.page_pattern.findall(buffer)
                    if pages:
                        for page in pages:
                            title_match = self.title_pattern.search(page)
                            text_match = self.text_pattern.search(page)
                            if title_match and text_match:
                                title = title_match.group(1)
                                text = text_match.group(1)
                                if not any(title.startswith(prefix) for prefix in self.skip_prefixes):
                                    # Build URL for this page
                                    page_url = self._title_to_url(title)

                                    # Track URL discovery
                                    self.ledger.discover_url(
                                        page_url,
                                        "wikipedia",
                                        metadata={"title": title}
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
                                            canonical_url or page_url  # Fallback to self if not found
                                        )
                                        self.metrics.increment('urls_deduplicated')

                        # Remove processed pages from buffer
                        buffer = self.page_pattern.sub('', buffer, count=len(pages))

                        if page_count % LOG_FREQUENCY_PAGES == 0:
                            self.logger.info(f"Extracted {page_count} pages so far...")
                            # Track metrics during extraction
                            self.metrics.increment('records_extracted', LOG_FREQUENCY_PAGES)

                    # Safety check: if buffer exceeds threshold, warn and truncate oldest data
                    if len(buffer) > buffer_size_threshold:
                        self.logger.warning(
                            f"Buffer size exceeded {BUFFER_MAX_SIZE_MB}MB. "
                            f"Truncating to prevent memory issues. Some malformed pages may be skipped."
                        )
                        # Keep only the last chunk to maintain page boundary context
                        buffer = buffer[-(BUFFER_TRUNCATE_SIZE_MB * 1024 * 1024):]

        # Record extraction timing (use process_duration for extraction phase)
        self.metrics.record_process_duration(timer.get_elapsed_ms())

        # Track final page count if not already tracked
        remainder = page_count % LOG_FREQUENCY_PAGES
        if remainder > 0:
            self.metrics.increment('records_extracted', remainder)

        self.logger.info(f"Extraction completed: {page_count} pages -> {self.staging_file}")

        # Export metrics and generate extraction report
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
        Extract records from staging file.

        Yields RawRecord objects for each Wikipedia page.
        BasePipeline.process() handles the rest (cleaning, writing, logging).
        """
        current_title = None
        current_lines = []

        with open(self.staging_file, 'r', encoding='utf-8') as fin:
            for line in fin:
                if line.startswith(self.page_marker_prefix + ' '):
                    # Yield previous page if exists
                    if current_title is not None:
                        yield RawRecord(
                            title=current_title,
                            text=''.join(current_lines),
                            url=self._title_to_url(current_title),
                            metadata={},
                        )

                    # Start new page
                    raw_line = line.rstrip('\n')
                    title_part = raw_line[len(self.page_marker_prefix) + 1:]
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
                    text=''.join(current_lines),
                    url=self._title_to_url(current_title),
                    metadata={},
                )

    def _get_http_session(self) -> requests.Session:
        """Create a requests session with retry policy for robustness."""
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _resolve_dump_url(self, session: requests.Session) -> Tuple[str, str]:
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
        base = "https://so.wikipedia.org/wiki/" if self.current_code.startswith("so") else f"https://{self.current_code.replace('wiki','')}.wikipedia.org/wiki/"
        return base + title.replace(' ', '_')
