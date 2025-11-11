"""
Språkbanken Somali corpora processor.

Processes 66 Somali language corpora from University of Gothenburg's Språkbanken.
Each corpus contains domain-specific content (news, literature, science, etc.)
with rich metadata including dates, authors, and publishers.

Corpora domains:
- General: Various general content corpora
- News: BBC Somali, CB News, Wardheer News, Haatuf News (2002-2009)
- Literature: Stories, poetry, translated works
- Science: Science education materials across decades
- Health: Health education materials
- Education: Mathematics textbooks from various regions
- Immigrant: Diaspora content from Canada

All corpora use CC BY 4.0 license and XML format (bz2 compressed).
"""

import bz2
import json
import logging
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import datetime, timezone
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
from .text_cleaners import TextCleaningPipeline, create_html_cleaner

logger = logging.getLogger(__name__)


# Corpus metadata mapping - Complete 66 Somali corpora from Språkbanken
CORPUS_INFO = {
    "somali-1993-94": {"domain": "general", "period": "1993-1994"},
    "somali-as-2016": {"domain": "general", "period": "2016", "region": "Somalia"},
    "somali-caafimaad-1983": {"domain": "health", "period": "1983", "topic": "health"},
    "somali-1971-79": {"domain": "general", "period": "1971-1979"},
    "somali-as-2001": {"domain": "general", "period": "2001", "region": "Somalia"},
    "somali-2001": {"domain": "general", "period": "2001", "region": "Somalia"},
    "somali-itoobiya": {"domain": "general", "region": "Ethiopia"},
    "somali-hargeysa-2010": {"domain": "general", "period": "2010", "region": "Somaliland"},
    "somali-as-2013": {"domain": "general", "period": "2013", "region": "Somalia"},
    "somali-as-2018": {"domain": "general", "period": "2018", "region": "Somalia"},
    "somali-ah-1992-02-kanada": {"domain": "immigrant", "period": "1992-2002", "region": "Canada"},
    "somali-ah-2010-19": {"domain": "immigrant", "period": "2010-2019", "region": "Canada"},
    "somali-bbc": {"domain": "news", "source": "BBC Somali"},
    "somali-caafimaad-1972-79": {"domain": "health", "period": "1972-1979", "topic": "health"},
    "somali-caafimaad-1994": {"domain": "health", "period": "1994", "topic": "health"},
    "somali-cilmi": {"domain": "science", "topic": "knowledge/science"},
    "somali-cb": {"domain": "news", "source": "CB News"},
    "somali-cb-1980-89": {"domain": "news", "period": "1980-1989", "region": "Somalia"},
    "somali-hargeysa": {"domain": "general", "region": "Somaliland"},
    "somali-cb-2001-03-soomaaliya": {"domain": "news", "period": "2001-2003", "region": "Somalia"},
    "somali-cb-2010": {"domain": "news", "period": "2010", "region": "Somalia"},
    "somali-cb-2011": {"domain": "news", "period": "2011", "region": "Somalia"},
    "somali-cb-2016": {"domain": "news", "period": "2016", "region": "Somalia"},
    "somali-cb-2018": {"domain": "news", "period": "2018", "region": "Somalia"},
    "somali-cd-2012-itoobiya": {"domain": "news", "period": "2012", "region": "Ethiopia"},
    "somali-wakiillada": {"domain": "news", "source": "Wakiillada"},
    "somali-haatuf-news-2002": {"domain": "news", "period": "2002", "region": "Somaliland"},
    "somali-haatuf-news-2003": {"domain": "news", "period": "2003", "region": "Somaliland"},
    "somali-haatuf-news-2004": {"domain": "news", "period": "2004", "region": "Somaliland"},
    "somali-haatuf-news-2005": {"domain": "news", "period": "2005", "region": "Somaliland"},
    "somali-haatuf-news-2006": {"domain": "news", "period": "2006", "region": "Somaliland"},
    "somali-haatuf-news-2007": {"domain": "news", "period": "2007", "region": "Somaliland"},
    "somali-haatuf-news-2008": {"domain": "news", "period": "2008", "region": "Somaliland"},
    "somali-haatuf-news-2009": {"domain": "news", "period": "2009", "region": "Somaliland"},
    "somali-mk-1972-79": {"domain": "general", "period": "1972-1979"},
    "somali-ogaden": {"domain": "general", "region": "Ogaden"},
    "somali-qoraallo": {"domain": "general", "topic": "literature"},
    "somali-radioden2014": {"domain": "news", "period": "2014", "region": "Somalia"},
    "somali-radioswe2014": {"domain": "news", "period": "2014", "region": "Somalia"},
    "somali-radiomuq": {"domain": "news", "region": "Somalia"},
    "somali-saynis-1972-77": {"domain": "science", "period": "1972-1977", "topic": "science"},
    "somali-saynis-1980-89": {"domain": "science", "period": "1980-1989", "topic": "science"},
    "somali-saynis-1994-96": {"domain": "science", "period": "1994-1996", "topic": "science"},
    "somali-saynis": {"domain": "science", "topic": "science"},
    "somali-saynis-2001": {"domain": "science", "period": "2001", "topic": "science"},
    "somali-saynis-2011-soomaaliya": {
        "domain": "science",
        "period": "2011",
        "region": "Somalia",
        "topic": "science",
    },
    "somali-saynis-2016": {
        "domain": "science",
        "period": "2016",
        "region": "Somalia",
        "topic": "science",
    },
    "somali-saynis-2018": {
        "domain": "science",
        "period": "2018",
        "region": "Somalia",
        "topic": "science",
    },
    "somali-sheekooyin": {"domain": "literature", "topic": "folklore"},
    "somali-sheekooyin-carruureed": {"domain": "literature", "topic": "children's stories"},
    "somali-sheekooying": {"domain": "literature", "topic": "children's stories"},
    "somali-suugaan": {"domain": "literature", "topic": "poetry"},
    "somali-suugaan-turjuman": {"domain": "literature", "topic": "translated poetry"},
    "somali-suugaan2": {"domain": "literature", "topic": "poetry"},
    "somali-tid-turjuman": {"domain": "literature", "topic": "translated literature"},
    "somali-wksi": {"domain": "general", "region": "Somalia"},
    "somali-wksk": {"domain": "general", "region": "Somalia"},
    "somali-wardheer": {"domain": "news", "source": "Wardheer News"},
    "somali-xeerar": {"domain": "general", "topic": "law"},
    "somali-xisaab-1971-79": {"domain": "education", "period": "1971-1979", "topic": "mathematics"},
    "somali-xisaab-1994-97": {"domain": "education", "period": "1994-1997", "topic": "mathematics"},
    "somali-xisaab-2001-hargeysa": {
        "domain": "education",
        "period": "2001",
        "region": "Hargeysa",
        "topic": "mathematics",
    },
    "somali-xisaab-2001-nayroobi": {
        "domain": "education",
        "period": "2001",
        "region": "Nairobi",
        "topic": "mathematics",
    },
    "somali-xisaab-2011-itoobiya": {
        "domain": "education",
        "period": "2011",
        "region": "Ethiopia",
        "topic": "mathematics",
    },
    "somali-xisaab-2016-somaliland": {
        "domain": "education",
        "period": "2016",
        "region": "Somaliland",
        "topic": "mathematics",
    },
    "somali-xisaab-2018-soomaaliya": {
        "domain": "education",
        "period": "2018",
        "region": "Somalia",
        "topic": "mathematics",
    },
}


class SprakbankenSomaliProcessor(BasePipeline):
    """
    Processor for Språkbanken Somali corpora.

    Handles downloading, extracting, and processing of 66 XML corpora
    with domain-specific metadata enrichment.
    """

    def __init__(
        self,
        corpus_id: str = "all",
        force: bool = False,
        batch_size: Optional[int] = 5000,
    ):
        """
        Initialize Språkbanken processor.

        Args:
            corpus_id: Specific corpus ID or "all" for all 66 corpora
            force: Force reprocessing even if output files exist
            batch_size: Batch size for silver dataset writing
        """
        self.corpus_id = corpus_id
        # Support comma-separated corpus IDs: "somali-cilmi,somali-cb"
        if corpus_id == "all":
            self.corpora_to_process = list(CORPUS_INFO.keys())
        elif "," in corpus_id:
            self.corpora_to_process = [c.strip() for c in corpus_id.split(",")]
        else:
            self.corpora_to_process = [corpus_id]

        # Validate each corpus ID in the list
        for cid in self.corpora_to_process:
            if cid not in CORPUS_INFO:
                raise ValueError(
                    f"Unknown corpus_id: {cid}. Available: {list(CORPUS_INFO.keys())} or 'all'"
                )

        # Load config FIRST
        config = get_config()
        self.config = config
        self.sprakbanken_config = config.scraping.sprakbanken

        # Determine source name (use "sprakbanken" for consistency with allowed sources)
        # Corpus ID will be stored in source_id field for querying
        source_name = "sprakbanken"

        # Initialize deduplication BEFORE BasePipeline (which generates run_id)
        dedup_config = DedupConfig(
            hash_fields=["text"],
            enable_minhash=True,
            similarity_threshold=0.85
        )
        self.dedup = DedupEngine(dedup_config)
        self.ledger = get_ledger()
        self.metrics = None  # Will be initialized in download()

        # Initialize BasePipeline (this generates run_id and StructuredLogger)
        super().__init__(
            source=source_name,
            log_frequency=1000,
            batch_size=batch_size,
            force=force,
        )

        # Note: StructuredLogger is now initialized in BasePipeline
        # Use self.logger for all logging (it's now a structured logger with JSON output)

        # Override file paths with run_id
        # Pattern: sprakbanken-{corpus_id}_{run_id}_{layer}_{descriptive_name}.{ext}
        corpus_slug = corpus_id if corpus_id != "all" else "all"
        self.manifest_file = (
            self.raw_dir / f"sprakbanken-{corpus_slug}_{self.run_id}_raw_manifest.json"
        )
        self.staging_file = (
            self.staging_dir / f"sprakbanken-{corpus_slug}_{self.run_id}_staging_extracted.jsonl"
        )
        self.processed_file = (
            self.processed_dir / f"sprakbanken-{corpus_slug}_{self.run_id}_processed_cleaned.txt"
        )

        # Corpus state tracking
        self.current_corpus_metadata = {}

    def _register_filters(self) -> None:
        """Register Språkbanken-specific filters."""
        from .filters import langid_filter, min_length_filter

        # Minimum length threshold (from config)
        self.filter_engine.register_filter(
            (min_length_filter, {"threshold": self.sprakbanken_config.min_length_threshold})
        )

        # Language filter with relaxed threshold (from config)
        self.filter_engine.register_filter(
            (
                langid_filter,
                {
                    "allowed_langs": {"so"},
                    "confidence_threshold": self.sprakbanken_config.langid_confidence_threshold,
                },
            )
        )

    def _create_cleaner(self) -> TextCleaningPipeline:
        """Create text cleaner for Språkbanken content."""
        return create_html_cleaner()  # Handles general text cleaning

    def _get_source_type(self) -> str:
        """Return source type for silver records."""
        # Varies by corpus, but use general category
        return "corpus"

    def _get_license(self) -> str:
        """Return license information for silver records."""
        return "CC BY 4.0"

    def _get_language(self) -> str:
        """Return language code for silver records."""
        return "so"

    def _get_source_metadata(self) -> dict[str, Any]:
        """Return Språkbanken-specific metadata for silver records."""
        return {
            "repository": "Språkbanken",
            "institution": "University of Gothenburg",
            "corpus_count": len(self.corpora_to_process),
            **self.current_corpus_metadata,  # Add corpus-specific metadata
        }

    def _get_domain(self) -> str:
        """
        Return content domain for silver records.

        Uses current corpus metadata to determine domain.
        """
        return self.current_corpus_metadata.get("domain", "general")

    def _get_register(self) -> str:
        """
        Return linguistic register for silver records.

        Returns:
            Register string ("formal", "informal", "colloquial")

        Note:
            Språkbanken corpora are academic/institutional content classified as "formal"
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

    def _extract_corpus_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract corpus ID from Språkbanken URL.

        Supports multiple URL formats:
        - Korp: https://spraakbanken.gu.se/korp/?mode=somali#?corpus=CORPUS_ID
        - Download: https://spraakbanken.gu.se/lb/resurser/meningsmangder/CORPUS_ID.xml.bz2

        Args:
            url: Språkbanken URL

        Returns:
            Corpus ID string, or None if not found
        """
        import re

        # Try Korp URL format
        match = re.search(r'corpus=([a-z0-9-]+)', url)
        if match:
            return match.group(1)

        # Try download URL format
        match = re.search(r'/meningsmangder/([a-z0-9-]+)\.xml\.bz2', url)
        if match:
            return match.group(1)

        return None

    def _get_processed_corpus_ids(self) -> set[str]:
        """
        Get set of already-processed corpus IDs from ledger.

        Enables incremental processing by identifying which corpora have
        already been successfully processed and can be skipped.

        Returns:
            Set of corpus IDs that have been processed
        """
        if not hasattr(self, 'ledger') or self.ledger is None:
            return set()

        try:
            # Get all processed URLs for this source
            processed_records = self.ledger.get_processed_urls(source=self.source, limit=None)

            corpus_ids = set()
            for record in processed_records:
                url = record.get('url', '')
                corpus_id = self._extract_corpus_id_from_url(url)
                if corpus_id:
                    corpus_ids.add(corpus_id)

            return corpus_ids

        except Exception as e:
            self.logger.warning(f"Failed to query ledger for processed corpus IDs: {e}")
            return set()

    def _get_downloaded_corpus_ids(self) -> set[str]:
        """
        Query ledger for corpus IDs that have been downloaded.

        DEPRECATED: Use _get_processed_corpus_ids() instead.

        Returns:
            Set of corpus IDs already in ledger
        """
        # Delegate to new method for consistency
        return self._get_processed_corpus_ids()

    def _filter_new_corpora(
        self, corpus_urls: list[str]
    ) -> tuple[list[str], dict[str, Any]]:
        """
        Filter corpus URLs to only unprocessed ones.

        Implements incremental processing by comparing requested corpora
        with the list of already-processed corpora in the ledger.

        Args:
            corpus_urls: List of corpus download URLs

        Returns:
            Tuple of (filtered_urls, stats_dict)

        Stats include:
            - total: Total corpora requested
            - new: New corpora to download
            - skipped: Corpora skipped (already processed)
            - processed_corpus_ids: List of corpus IDs already processed
        """
        processed_ids = self._get_processed_corpus_ids()

        if not processed_ids:
            self.logger.info("First run detected - processing all corpora")
            return corpus_urls, {
                "total": len(corpus_urls),
                "new": len(corpus_urls),
                "skipped": 0,
                "processed_corpus_ids": [],
            }

        self.logger.info(f"Already processed: {processed_ids}")

        new_urls = []
        for url in corpus_urls:
            corpus_id = self._extract_corpus_id_from_url(url)
            if corpus_id and corpus_id not in processed_ids:
                new_urls.append(url)
            elif not corpus_id:
                # Can't determine ID - process to be safe (fail-safe approach)
                new_urls.append(url)

        stats = {
            "total": len(corpus_urls),
            "new": len(new_urls),
            "skipped": len(corpus_urls) - len(new_urls),
            "processed_corpus_ids": list(processed_ids),
        }

        self.logger.info(
            f"Filtered {stats['skipped']} already-processed corpora, {stats['new']} new corpora"
        )

        return new_urls, stats

    def download(self) -> Path:
        """
        Download all specified Språkbanken corpora.

        Returns:
            Path to manifest file listing all downloaded corpora
        """
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        # Set context using run_id from base_pipeline
        set_context(run_id=self.run_id, source=self.source, phase="discovery")

        # Initialize metrics with run_id from base_pipeline
        self.metrics = MetricsCollector(
            self.run_id, self.source, pipeline_type=PipelineType.FILE_PROCESSING
        )

        # Check if manifest exists
        if self.manifest_file.exists() and not self.force:
            with open(self.manifest_file, encoding="utf-8") as f:
                manifest = json.load(f)

            # Check if the requested corpora match
            if set(manifest.get("corpora_ids", [])) == set(self.corpora_to_process):
                self.logger.info(f"Corpora already downloaded: {self.manifest_file}")
                return self.manifest_file

        # PHASE 1: Incremental Processing - Filter out already-processed corpora
        self.logger.info("=" * 60)
        self.logger.info("PHASE 1: Incremental Corpus Filtering")
        self.logger.info("=" * 60)

        # Build full download URLs for filtering
        corpus_urls = [
            f"https://spraakbanken.gu.se/lb/resurser/meningsmangder/{corpus_id}.xml.bz2"
            for corpus_id in self.corpora_to_process
        ]

        # Filter to only new corpora
        new_corpus_urls, filter_stats = self._filter_new_corpora(corpus_urls)

        # Track incremental filtering metrics
        self.metrics.add_custom_metric("incremental_filtering", filter_stats)

        # If ALL corpora already processed, skip everything
        if not new_corpus_urls:
            self.logger.info(
                f"Incremental processing: All {len(self.corpora_to_process)} corpora "
                f"already processed, skipping download and extraction"
            )
            return None  # Signal to run() to skip extraction and processing

        self.logger.info("=" * 60)
        self.logger.info("PHASE 2: Downloading New Corpora")
        self.logger.info("=" * 60)
        self.logger.info(f"Corpora requested: {filter_stats['total']}")
        self.logger.info(f"Corpora to download (new): {filter_stats['new']}")
        self.logger.info(f"Corpora skipped (already processed): {filter_stats['skipped']}")

        # Extract corpus IDs from filtered URLs for download
        corpora_to_download = []
        for url in new_corpus_urls:
            corpus_id = self._extract_corpus_id_from_url(url)
            if corpus_id:
                corpora_to_download.append(corpus_id)

        manifest = {
            "corpora_ids": self.corpora_to_process,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,  # Store run_id for continuity
            "corpora": [],
        }

        session = self._get_http_session()

        # Download only new corpora (not already in ledger)
        for corpus_id in tqdm(corpora_to_download, desc="Downloading corpora"):
            # Track discovery (use files_discovered for file processing)
            self.metrics.increment("files_discovered")

            corpus_file = self.raw_dir / f"{corpus_id}.xml.bz2"
            download_url = (
                f"https://spraakbanken.gu.se/lb/resurser/meningsmangder/{corpus_id}.xml.bz2"
            )

            # Download if not exists
            if not corpus_file.exists() or self.force:
                try:
                    self.logger.info(f"Downloading {corpus_id}...")
                    response = session.get(download_url, stream=True, timeout=30)
                    response.raise_for_status()

                    int(response.headers.get("Content-Length", 0))
                    with open(corpus_file, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    self.logger.info(f"  ✓ Downloaded: {corpus_file.name}")
                    self.metrics.increment("files_processed")

                except requests.RequestException as e:
                    self.logger.error(f"  ✗ Failed to download {corpus_id}: {e}")
                    self.metrics.increment("corpora_failed")
                    continue

            # Add to manifest
            if corpus_file.exists():
                manifest["corpora"].append(
                    {
                        "id": corpus_id,
                        "file": corpus_file.name,
                        "url": download_url,
                        "size": corpus_file.stat().st_size,
                        **CORPUS_INFO.get(corpus_id, {}),
                    }
                )

        # Save manifest
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        self.logger.info("=" * 60)
        self.logger.info(f"Downloaded {len(manifest['corpora'])} corpora")
        self.logger.info(f"Manifest saved: {self.manifest_file}")
        self.logger.info("=" * 60)

        # Export metrics
        self._export_stage_metrics("discovery")

        return self.manifest_file

    def extract(self) -> Path:
        """
        Extract text from all downloaded XML corpora.

        Returns:
            Path to staging file with extracted records
        """
        if not self.manifest_file.exists():
            raise FileNotFoundError(
                f"Manifest not found: {self.manifest_file}. Run download() first."
            )

        self.staging_dir.mkdir(parents=True, exist_ok=True)

        # Load manifest
        with open(self.manifest_file, encoding="utf-8") as f:
            manifest = json.load(f)

        # Set context using run_id from base_pipeline
        set_context(run_id=self.run_id, source=self.source, phase="extract")

        # Resume or create metrics with run_id from base_pipeline
        if self.metrics is None:
            self.metrics = MetricsCollector(
                self.run_id, self.source, pipeline_type=PipelineType.FILE_PROCESSING
            )

        if self.staging_file.exists() and not self.force:
            self.logger.info(f"Staging file already exists: {self.staging_file}")
            return self.staging_file

        self.logger.info("=" * 60)
        self.logger.info("PHASE 3: Extracting Text from XML Corpora")
        self.logger.info("=" * 60)

        total_texts = 0
        total_sentences = 0

        # Track extraction timing
        with Timer() as timer:
            # Open staging file for writing
            with open(self.staging_file, "w", encoding="utf-8") as out_f:
                for corpus_info in tqdm(manifest["corpora"], desc="Extracting corpora"):
                    corpus_id = corpus_info["id"]
                    corpus_file = self.raw_dir / corpus_info["file"]

                    if not corpus_file.exists():
                        self.logger.warning(f"Corpus file not found: {corpus_file}")
                        continue

                    self.logger.info(f"Extracting {corpus_id}...")

                    # Extract sentences from XML
                    with Timer() as corpus_timer:
                        texts_count, sentences_count = self._extract_corpus(
                            corpus_file, corpus_info, out_f
                        )

                    # Record metrics for this corpus
                    self.metrics.record_process_duration(corpus_timer.get_elapsed_ms())
                    self.metrics.increment("records_extracted", texts_count)
                    self.metrics.increment("sentences_extracted", sentences_count)

                    total_texts += texts_count
                    total_sentences += sentences_count

                    self.logger.info(
                        f"  ✓ {corpus_id}: {texts_count} texts, {sentences_count} sentences"
                    )

        # Record total extraction timing (use process_duration for extraction phase)
        self.metrics.record_process_duration(timer.get_elapsed_ms())

        self.logger.info("=" * 60)
        self.logger.info(f"Extraction complete: {total_texts} texts, {total_sentences} sentences")
        self.logger.info(f"Staging file: {self.staging_file}")
        self.logger.info("=" * 60)

        # Export metrics and generate extraction quality report
        self._export_stage_metrics("extraction")
        self._generate_quality_report("extraction")

        return self.staging_file

    def _extract_corpus(
        self, corpus_file: Path, corpus_info: dict[str, Any], out_file
    ) -> tuple[int, int]:
        """
        Extract text from a single corpus XML file.

        Handles two corpus structures:
        1. Multi-text: Multiple <text> elements (each is a document)
        2. Single-text: One <text> with multiple <page> elements (each page is a document)

        Args:
            corpus_file: Path to compressed XML file
            corpus_info: Metadata about the corpus
            out_file: Output file handle for writing JSONL records

        Returns:
            Tuple of (text_count, sentence_count)
        """
        texts_count = 0
        sentences_count = 0

        try:
            # Open and parse compressed XML
            with bz2.open(corpus_file, "rt", encoding="utf-8") as f:
                tree = ET.parse(f)
                root = tree.getroot()

                # Get corpus ID from root element
                corpus_id = root.get("id", corpus_info["id"])

                # ADAPTIVE PARSING: Detect corpus structure
                text_elems = root.findall(".//text")

                if len(text_elems) == 1:
                    # Single-text corpus: Check if it has pages
                    pages = text_elems[0].findall(".//page")

                    if pages:
                        # Single-text with pages: Treat each page as a document
                        self.logger.info(
                            f"  Detected single-text corpus with {len(pages)} pages"
                        )
                        text_metadata = self._extract_text_metadata(text_elems[0])

                        for page_index, page in enumerate(pages, start=1):
                            result = self._process_page_as_document(
                                page,
                                corpus_id,
                                page_index,
                                text_metadata,
                                corpus_info,
                                out_file
                            )
                            if result:
                                texts_count += 1
                                sentences_count += result
                    else:
                        # Single-text without pages: Process as one document
                        result = self._process_text_element(
                            text_elems[0],
                            corpus_id,
                            1,
                            corpus_info,
                            out_file
                        )
                        if result:
                            texts_count += 1
                            sentences_count += result
                else:
                    # Multi-text corpus: Process each text as a document
                    self.logger.info(
                        f"  Detected multi-text corpus with {len(text_elems)} texts"
                    )

                    for text_index, text_elem in enumerate(text_elems, start=1):
                        result = self._process_text_element(
                            text_elem,
                            corpus_id,
                            text_index,
                            corpus_info,
                            out_file
                        )
                        if result:
                            texts_count += 1
                            sentences_count += result

        except Exception as e:
            self.logger.error(f"Error extracting {corpus_file}: {e}")

        return texts_count, sentences_count

    def _process_page_as_document(
        self,
        page_elem: ET.Element,
        corpus_id: str,
        page_index: int,
        text_metadata: dict[str, Any],
        corpus_info: dict[str, Any],
        out_file
    ) -> Optional[int]:
        """
        Process a single page element as an individual document.

        Args:
            page_elem: Page XML element
            corpus_id: Corpus identifier
            page_index: Sequential page number
            text_metadata: Metadata from parent text element
            corpus_info: Corpus-level metadata
            out_file: Output file handle

        Returns:
            Number of sentences extracted, or None if no content
        """
        # Extract page metadata
        page_n = page_elem.get("n", f"page_{page_index}")
        page_url = page_elem.get("purl", "")

        # Collect sentences from this page
        sentences = []
        for sentence in page_elem.findall(".//sentence"):
            sentence_text = self._extract_sentence_text(sentence)
            if sentence_text:
                sentences.append(sentence_text)

        if not sentences:
            return None

        # Build URL (prefer page URL if available, otherwise construct from corpus)
        if page_url:
            url = page_url
        else:
            url = f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus={corpus_id}&page={page_n}"

        text_content = " ".join(sentences)

        # Process duplicates with combined exact and near-duplicate detection
        is_dup, dup_type, similar_url, text_hash, minhash_sig = (
            self.dedup.process_document(text_content, url)
        )

        if not is_dup:
            # Create record for this page
            record = {
                "corpus_id": corpus_id,
                "title": f"{corpus_id} - {page_n}",
                "text": text_content,
                "text_hash": text_hash,
                "minhash_signature": minhash_sig,
                "metadata": {
                    **corpus_info,  # Domain, period, etc.
                    **text_metadata,  # Year, source, publisher from text element
                    "page_id": page_n,
                    "page_url": page_url,
                    "sentence_count": len(sentences),
                },
            }

            # Write to JSONL
            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")

            # Track text length metrics
            self.metrics.record_text_length(len(text_content))

            return len(sentences)
        else:
            # Duplicate detected
            self.logger.debug(
                f"{dup_type.capitalize()} duplicate detected in {corpus_id}: {similar_url}"
            )
            # Increment correct metric based on duplicate type
            if dup_type == "exact":
                self.metrics.increment("texts_deduplicated")
            elif dup_type == "near":
                self.metrics.increment("near_duplicates")

            return None

    def _process_text_element(
        self,
        text_elem: ET.Element,
        corpus_id: str,
        text_index: int,
        corpus_info: dict[str, Any],
        out_file
    ) -> Optional[int]:
        """
        Process a single text element as an individual document.

        Args:
            text_elem: Text XML element
            corpus_id: Corpus identifier
            text_index: Sequential text number
            corpus_info: Corpus-level metadata
            out_file: Output file handle

        Returns:
            Number of sentences extracted, or None if no content
        """
        text_metadata = self._extract_text_metadata(text_elem)

        # Collect sentences from all pages in this text
        sentences = []
        for page in text_elem.findall(".//page"):
            for sentence in page.findall(".//sentence"):
                sentence_text = self._extract_sentence_text(sentence)
                if sentence_text:
                    sentences.append(sentence_text)

        if not sentences:
            return None

        # Build URL for this text with unique identifier
        text_id = f"{text_index}"
        url = f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus={corpus_id}&text={text_id}"
        text_content = " ".join(sentences)

        # Process duplicates with combined exact and near-duplicate detection
        is_dup, dup_type, similar_url, text_hash, minhash_sig = (
            self.dedup.process_document(text_content, url)
        )

        if not is_dup:
            # Create record for this text
            record = {
                "corpus_id": corpus_id,
                "title": text_metadata.get(
                    "title", f"{corpus_id}_text_{text_index}"
                ),
                "text": text_content,
                "text_hash": text_hash,
                "minhash_signature": minhash_sig,
                "metadata": {
                    **corpus_info,  # Domain, period, etc.
                    **text_metadata,  # Author, date, publisher, etc.
                    "sentence_count": len(sentences),
                },
            }

            # Write to JSONL
            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")

            # Track text length metrics
            self.metrics.record_text_length(len(text_content))

            return len(sentences)
        else:
            # Duplicate detected
            self.logger.debug(
                f"{dup_type.capitalize()} duplicate detected in {corpus_id}: {similar_url}"
            )
            # Increment correct metric based on duplicate type
            if dup_type == "exact":
                self.metrics.increment("texts_deduplicated")
            elif dup_type == "near":
                self.metrics.increment("near_duplicates")

            return None

    def _extract_text_metadata(self, text_elem: ET.Element) -> dict[str, Any]:
        """Extract metadata from text element."""
        metadata = {}

        # Extract all attributes
        for attr, value in text_elem.attrib.items():
            if value and value != "None":
                metadata[attr] = value

        return metadata

    def _extract_sentence_text(self, sentence_elem: ET.Element) -> str:
        """
        Extract text from sentence element.

        Språkbanken XML uses <token> tags for word tokens.
        Example: <sentence><token>Nickolay</token><token>Mladenov</token>...</sentence>
        """
        tokens = []
        # Use 'token' tag for Språkbanken XML format
        for word_elem in sentence_elem.findall("token"):
            word = word_elem.text or ""
            if word:
                tokens.append(word)
        return " ".join(tokens)

    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Extract records from staging file.

        Yields RawRecord objects for each text in the corpora.
        """
        if not self.staging_file.exists():
            raise FileNotFoundError(f"Staging file not found: {self.staging_file}")

        with open(self.staging_file, encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)

                # Update current corpus metadata for _get_domain()
                self.current_corpus_metadata = record["metadata"]

                # Build URL
                corpus_id = record["corpus_id"]
                url = f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus={corpus_id}"

                # Store corpus_id in metadata to pass to source_id field
                # Also include minhash_signature and text_hash for ledger tracking
                metadata_with_corpus_id = {
                    **record["metadata"],
                    "corpus_id": corpus_id,  # Will be used to populate source_id
                }

                # Include dedup metadata if present (for ledger.mark_processed)
                if "minhash_signature" in record:
                    metadata_with_corpus_id["minhash_signature"] = record["minhash_signature"]
                if "text_hash" in record:
                    metadata_with_corpus_id["text_hash"] = record["text_hash"]

                yield RawRecord(
                    title=record["title"],
                    text=record["text"],
                    url=url,
                    metadata=metadata_with_corpus_id,
                )

    def _get_http_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        return HTTPSessionFactory.create_session(
            max_retries=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )


def list_available_corpora() -> list[str]:
    """
    List all available Språkbanken corpus IDs.

    Returns:
        List of corpus IDs
    """
    return list(CORPUS_INFO.keys())


def get_corpus_info(corpus_id: str) -> dict[str, Any]:
    """
    Get metadata for a specific corpus.

    Args:
        corpus_id: Corpus identifier

    Returns:
        Dictionary with corpus metadata
    """
    return CORPUS_INFO.get(corpus_id, {})
