"""
Språkbanken Somali corpora processor.

Processes 23 Somali language corpora from University of Gothenburg's Språkbanken.
Each corpus contains domain-specific content (news, literature, science, etc.)
with rich metadata including dates, authors, and publishers.

Corpora available:
- News: as-2001, as-2016, ah-2010-19, cb-*, ogaden
- Literature: sheekooyin*, suugaan*
- Science: cilmi, saynis-1980-89
- Health: caafimaad-1972-79
- Radio: radioden2014, radioswe2014
- Translations: turjuman variants
- Historical: 1971-79, 1993-94, 2001
- QA: kqa

All corpora use CC BY 4.0 license and XML format (bz2 compressed).
"""

import bz2
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

from .base_pipeline import BasePipeline, RawRecord
from .text_cleaners import create_html_cleaner, TextCleaningPipeline
from .crawl_ledger import get_ledger
from .dedup import DedupEngine, DedupConfig
from ..utils.logging_utils import StructuredLogger, set_context, Timer
from ..utils.metrics import MetricsCollector, QualityReporter, PipelineType
from ..config import get_config


logger = logging.getLogger(__name__)


# Corpus metadata mapping
CORPUS_INFO = {
    "1993-94": {"domain": "general", "period": "1993-1994"},
    "as-2016": {"domain": "news", "period": "2016", "source": "Arlaadi Soomaaliyeed"},
    "1971-79": {"domain": "historical", "period": "1971-1979"},
    "as-2001": {"domain": "news", "period": "2001", "source": "Arlaadi Soomaaliyeed"},
    "2001": {"domain": "general", "period": "2001"},
    "ah-2010-19": {"domain": "news", "period": "2010-2019", "source": "Afhayeenka"},
    "caafimaad-1972-79": {"domain": "health", "period": "1972-1979", "topic": "health"},
    "cilmi": {"domain": "science", "topic": "knowledge/science"},
    "cb": {"domain": "news", "source": "CB News"},
    "cb-2001-03-soomaaliya": {"domain": "news", "period": "2001-2003", "region": "Somalia"},
    "cb-2016": {"domain": "news", "period": "2016", "source": "CB News"},
    "kqa": {"domain": "qa", "format": "question-answer"},
    "mk-1972-79": {"domain": "general", "period": "1972-1979"},
    "radioden2014": {"domain": "radio", "period": "2014", "source": "Radio Denmark"},
    "radioswe2014": {"domain": "radio", "period": "2014", "source": "Radio Sweden"},
    "saynis-1980-89": {"domain": "science", "period": "1980-1989", "topic": "science"},
    "sheekooyin": {"domain": "literature", "genre": "stories"},
    "sheekooyin-carruureed": {"domain": "children", "genre": "children's stories"},
    "sheekooying": {"domain": "literature", "genre": "stories"},
    "suugaan-turjuman": {"domain": "literature_translation", "genre": "literature", "type": "translation"},
    "suugaan": {"domain": "literature", "genre": "literature/poetry"},
    "tid-turjuman": {"domain": "translation", "type": "translation"},
    "ogaden": {"domain": "news_regional", "region": "Ogaden"},
}


class SprakbankenSomaliProcessor(BasePipeline):
    """
    Processor for Språkbanken Somali corpora.

    Handles downloading, extracting, and processing of 23 XML corpora
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
            corpus_id: Specific corpus ID or "all" for all 23 corpora
            force: Force reprocessing even if output files exist
            batch_size: Batch size for silver dataset writing
        """
        # Validate corpus_id
        if corpus_id != "all" and corpus_id not in CORPUS_INFO:
            raise ValueError(
                f"Unknown corpus_id: {corpus_id}. "
                f"Available: {list(CORPUS_INFO.keys())} or 'all'"
            )

        self.corpus_id = corpus_id
        self.corpora_to_process = (
            list(CORPUS_INFO.keys()) if corpus_id == "all" else [corpus_id]
        )

        # Load config FIRST
        config = get_config()
        self.config = config
        self.sprakbanken_config = config.scraping.sprakbanken

        # Determine source name (always "Sprakbanken-Somali" for consistency)
        # Corpus ID will be stored in source_id field for querying
        source_name = "Sprakbanken-Somali"

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
        self.manifest_file = self.raw_dir / f"sprakbanken-{corpus_slug}_{self.run_id}_raw_manifest.json"
        self.staging_file = self.staging_dir / f"sprakbanken-{corpus_slug}_{self.run_id}_staging_extracted.jsonl"
        self.processed_file = self.processed_dir / f"sprakbanken-{corpus_slug}_{self.run_id}_processed_cleaned.txt"

        # Corpus state tracking
        self.current_corpus_metadata = {}

    def _register_filters(self) -> None:
        """Register Språkbanken-specific filters."""
        from .filters import min_length_filter, langid_filter

        # Minimum length threshold (from config)
        self.record_filters.append((min_length_filter, {
            "threshold": self.sprakbanken_config.min_length_threshold
        }))

        # Language filter with relaxed threshold (from config)
        self.record_filters.append((langid_filter, {
            "allowed_langs": {"so"},
            "confidence_threshold": self.sprakbanken_config.langid_confidence_threshold
        }))

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

    def _get_source_metadata(self) -> Dict[str, Any]:
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
        self.metrics = MetricsCollector(self.run_id, self.source, pipeline_type=PipelineType.FILE_PROCESSING)

        # Check if manifest exists
        if self.manifest_file.exists() and not self.force:
            with open(self.manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Check if the requested corpora match
            if set(manifest.get("corpora_ids", [])) == set(self.corpora_to_process):
                self.logger.info(f"Corpora already downloaded: {self.manifest_file}")
                return self.manifest_file

        self.logger.info("=" * 60)
        self.logger.info("PHASE 1: Downloading Språkbanken Corpora")
        self.logger.info("=" * 60)
        self.logger.info(f"Corpora to download: {len(self.corpora_to_process)}")

        manifest = {
            "corpora_ids": self.corpora_to_process,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,  # Store run_id for continuity
            "corpora": [],
        }

        session = self._get_http_session()

        for corpus_id in tqdm(self.corpora_to_process, desc="Downloading corpora"):
            # Track discovery (use files_discovered for file processing)
            self.metrics.increment('files_discovered')

            corpus_file = self.raw_dir / f"somali-{corpus_id}.xml.bz2"
            download_url = f"https://spraakbanken.gu.se/lb/resurser/meningsmangder/somali-{corpus_id}.xml.bz2"

            # Download if not exists
            if not corpus_file.exists() or self.force:
                try:
                    self.logger.info(f"Downloading {corpus_id}...")
                    response = session.get(download_url, stream=True, timeout=30)
                    response.raise_for_status()

                    total_size = int(response.headers.get("Content-Length", 0))
                    with open(corpus_file, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    self.logger.info(f"  ✓ Downloaded: {corpus_file.name}")
                    self.metrics.increment('files_processed')

                except requests.RequestException as e:
                    self.logger.error(f"  ✗ Failed to download {corpus_id}: {e}")
                    self.metrics.increment('corpora_failed')
                    continue

            # Add to manifest
            if corpus_file.exists():
                manifest["corpora"].append({
                    "id": corpus_id,
                    "file": corpus_file.name,
                    "url": download_url,
                    "size": corpus_file.stat().st_size,
                    **CORPUS_INFO.get(corpus_id, {}),
                })

        # Save manifest
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        self.logger.info("=" * 60)
        self.logger.info(f"Downloaded {len(manifest['corpora'])} corpora")
        self.logger.info(f"Manifest saved: {self.manifest_file}")
        self.logger.info("=" * 60)

        # Export metrics
        metrics_path = Path("data/metrics") / f"{self.run_id}_discovery.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics.export_json(metrics_path)

        return self.manifest_file

    def extract(self) -> Path:
        """
        Extract text from all downloaded XML corpora.

        Returns:
            Path to staging file with extracted records
        """
        if not self.manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_file}. Run download() first.")

        self.staging_dir.mkdir(parents=True, exist_ok=True)

        # Load manifest
        with open(self.manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Set context using run_id from base_pipeline
        set_context(run_id=self.run_id, source=self.source, phase="extract")

        # Resume or create metrics with run_id from base_pipeline
        if self.metrics is None:
            self.metrics = MetricsCollector(self.run_id, self.source, pipeline_type=PipelineType.FILE_PROCESSING)

        if self.staging_file.exists() and not self.force:
            self.logger.info(f"Staging file already exists: {self.staging_file}")
            return self.staging_file

        self.logger.info("=" * 60)
        self.logger.info("PHASE 2: Extracting Text from XML Corpora")
        self.logger.info("=" * 60)

        total_texts = 0
        total_sentences = 0

        # Track extraction timing
        with Timer() as timer:
            # Open staging file for writing
            with open(self.staging_file, 'w', encoding='utf-8') as out_f:
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
                    self.metrics.increment('records_extracted', texts_count)
                    self.metrics.increment('sentences_extracted', sentences_count)

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

    def _extract_corpus(
        self,
        corpus_file: Path,
        corpus_info: Dict[str, Any],
        out_file
    ) -> Tuple[int, int]:
        """
        Extract text from a single corpus XML file.

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
            with bz2.open(corpus_file, 'rt', encoding='utf-8') as f:
                tree = ET.parse(f)
                root = tree.getroot()

                # Get corpus ID from root element
                corpus_id = root.get('id', corpus_info['id'])

                # Iterate through texts
                for text_elem in root.findall('.//text'):
                    text_metadata = self._extract_text_metadata(text_elem)

                    # Collect sentences from all pages
                    sentences = []
                    for page in text_elem.findall('.//page'):
                        for sentence in page.findall('.//sentence'):
                            sentence_text = self._extract_sentence_text(sentence)
                            if sentence_text:
                                sentences.append(sentence_text)
                                sentences_count += 1

                    if sentences:
                        # Build URL for this text
                        url = f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus={corpus_id}"
                        text_content = " ".join(sentences)

                        # Process duplicates with combined exact and near-duplicate detection
                        is_dup, dup_type, similar_url, text_hash, minhash_sig = self.dedup.process_document(text_content, url)

                        if not is_dup:
                            # Create record for this text
                            record = {
                                "corpus_id": corpus_id,
                                "title": text_metadata.get("title", f"{corpus_id}_text_{texts_count}"),
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
                            out_file.write(json.dumps(record, ensure_ascii=False) + '\n')
                            texts_count += 1

                            # Track text length metrics
                            self.metrics.record_text_length(len(text_content))
                        else:
                            # Duplicate detected
                            self.logger.debug(
                                f"{dup_type.capitalize()} duplicate detected in {corpus_id}: {similar_url}"
                            )
                            # Increment correct metric based on duplicate type
                            if dup_type == "exact":
                                self.metrics.increment('texts_deduplicated')
                            elif dup_type == "near":
                                self.metrics.increment('near_duplicates')

        except Exception as e:
            self.logger.error(f"Error extracting {corpus_file}: {e}")

        return texts_count, sentences_count

    def _extract_text_metadata(self, text_elem: ET.Element) -> Dict[str, Any]:
        """Extract metadata from text element."""
        metadata = {}

        # Extract all attributes
        for attr, value in text_elem.attrib.items():
            if value and value != "None":
                metadata[attr] = value

        return metadata

    def _extract_sentence_text(self, sentence_elem: ET.Element) -> str:
        """Extract text from sentence element."""
        tokens = []
        for token in sentence_elem.findall('.//token'):
            word = token.get('word', '')
            if word:
                tokens.append(word)
        return ' '.join(tokens)

    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Extract records from staging file.

        Yields RawRecord objects for each text in the corpora.
        """
        if not self.staging_file.exists():
            raise FileNotFoundError(f"Staging file not found: {self.staging_file}")

        with open(self.staging_file, 'r', encoding='utf-8') as f:
            for line in f:
                record = json.loads(line)

                # Update current corpus metadata for _get_domain()
                self.current_corpus_metadata = record["metadata"]

                # Build URL
                corpus_id = record["corpus_id"]
                url = f"https://spraakbanken.gu.se/korp/?mode=somali#?corpus={corpus_id}"

                # Store corpus_id in metadata to pass to source_id field
                metadata_with_corpus_id = {
                    **record["metadata"],
                    "corpus_id": corpus_id,  # Will be used to populate source_id
                }

                yield RawRecord(
                    title=record["title"],
                    text=record["text"],
                    url=url,
                    metadata=metadata_with_corpus_id,
                )

    def _get_http_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
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


def list_available_corpora() -> List[str]:
    """
    List all available Språkbanken corpus IDs.

    Returns:
        List of corpus IDs
    """
    return list(CORPUS_INFO.keys())


def get_corpus_info(corpus_id: str) -> Dict[str, Any]:
    """
    Get metadata for a specific corpus.

    Args:
        corpus_id: Corpus identifier

    Returns:
        Dictionary with corpus metadata
    """
    return CORPUS_INFO.get(corpus_id, {})