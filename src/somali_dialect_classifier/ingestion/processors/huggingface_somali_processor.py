"""
HuggingFace Datasets processor for streaming large-scale datasets.

Supports streaming from HuggingFace Hub with:
- Manifest-based versioning (dataset/config/split/revision)
- JSONL batching for resume capability
- Field mapping for heterogeneous schemas
- Pushdown filters for efficient streaming
- Last offset tracking for resumable extraction

Example sources:
- mc4 (multilingual C4)
- oscar-corpus/OSCAR-2301
- allenai/madlad400
- allenai/gdelt
"""

import json
import logging
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from datasets import DownloadConfig, IterableDataset, load_dataset

    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False
    IterableDataset = None
    DownloadConfig = None

from ...infra.config import get_config
from ...infra.logging_utils import Timer, set_context
from ...infra.metrics import MetricsCollector, PipelineType, QualityReporter
from ...quality.schema_mappers import get_schema_mapper
from ...quality.text_cleaners import create_html_cleaner
from ..base_pipeline import BasePipeline, RawRecord
from ..crawl_ledger import get_ledger
from ..dedup import DedupConfig, DedupEngine

logger = logging.getLogger(__name__)


class HuggingFaceSomaliProcessor(BasePipeline):
    """
    Streaming processor for HuggingFace datasets.

    Handles large-scale datasets efficiently via:
    1. Manifest creation (no data pull until extract)
    2. JSONL batching with resume capability
    3. Field mapping for heterogeneous schemas
    4. Shared quality filters before silver write

    Example:
        processor = HuggingFaceSomaliProcessor(
            dataset_name="mc4",
            dataset_config="so",
            split="train",
            text_field="text",
            batch_size=5000
        )
        processor.process()
    """

    def __init__(
        self,
        dataset_name: str,
        dataset_config: Optional[str] = None,
        split: Optional[str] = "train",
        text_field: str = "text",
        title_field: Optional[str] = None,
        url_field: Optional[str] = None,
        metadata_fields: Optional[list[str]] = None,
        pushdown_filters: Optional[dict[str, Any]] = None,
        data_files: Optional[dict[str, str]] = None,
        streaming_batch_size: int = 5000,
        max_records: Optional[int] = None,
        force: bool = False,
        run_seed: Optional[str] = None,
    ):
        """
        Initialize HuggingFace datasets processor.

        Args:
            dataset_name: HF dataset name (e.g., "mc4", "oscar-corpus/OSCAR-2301", "parquet")
            dataset_config: Dataset configuration/subset (e.g., "so" for Somali)
            split: Dataset split (default: "train", can be None when using data_files)
            text_field: Field containing text content (default: "text")
            title_field: Field containing title (optional, generates default if None)
            url_field: Field containing URL (optional, generates default if None)
            metadata_fields: Additional fields to include in metadata (optional)
            pushdown_filters: Filters applied during streaming (e.g., {"language": ["so"]})
            data_files: Parquet/data file paths (e.g., {"train": "hf://datasets/..."})
            streaming_batch_size: Records per JSONL batch file (default: 5000)
            max_records: Maximum records to process (None = unlimited)
            force: Force reprocessing even if output exists
        """
        if not DATASETS_AVAILABLE:
            raise ImportError("datasets library not available. Install with: pip install datasets")

        # Set instance attributes BEFORE super().__init__()
        # because _register_filters() is called during initialization
        self.dataset_name = dataset_name
        self.dataset_config = dataset_config
        self.split = split
        self.text_field = text_field
        self.title_field = title_field
        self.url_field = url_field
        self.metadata_fields = metadata_fields or []
        self.pushdown_filters = pushdown_filters or {}
        self.data_files = data_files
        self.streaming_batch_size = streaming_batch_size
        self.max_records = max_records
        self.display_name = None  # Can be overridden for custom display names

        # Load config FIRST (before Phase 0 initialization)
        config = get_config()
        self.config = config
        self.hf_config = config.scraping.huggingface

        # Construct source name - use filesystem-friendly format (no spaces/parentheses)
        # Format: HuggingFace-Somali_dataset or HuggingFace-Somali_dataset-config
        # Examples: HuggingFace-Somali_c4, HuggingFace-Somali_madlad-400-som
        dataset_slug = dataset_name.split("/")[
            -1
        ]  # Extract last part (e.g., "c4" from "allenai/c4")

        if dataset_config and dataset_config != dataset_name:
            # Include config in slug: HuggingFace-Somali_mc4-so
            source = f"HuggingFace-Somali_{dataset_slug}-{dataset_config}"
        elif pushdown_filters and "languages" in pushdown_filters:
            # For MADLAD-400 which uses languages parameter
            langs = pushdown_filters["languages"]
            if isinstance(langs, list) and langs:
                # HuggingFace-Somali_madlad-400-som
                source = f"HuggingFace-Somali_{dataset_slug}-{langs[0]}"
        else:
            # Simple format: HuggingFace-Somali_c4
            source = f"HuggingFace-Somali_{dataset_slug}"

        # Initialize deduplication BEFORE BasePipeline (which generates run_id)
        # PHASE 3: Enable LSH persistence for cross-run near-duplicate detection
        dedup_config = DedupConfig(
            hash_fields=["text", "url"],
            enable_minhash=True,
            similarity_threshold=0.85,
        )
        self.dedup = DedupEngine(dedup_config)
        self.ledger = get_ledger()
        self.metrics = None  # Will be initialized in download()

        # Initialize schema mapper for field mapping
        dataset_slug = dataset_name.split("/")[-1]
        self.schema_mapper = get_schema_mapper(dataset_slug)

        # Initialize BasePipeline with source name (this generates run_id and StructuredLogger)
        super().__init__(
            source=source,
            log_frequency=1000,
            batch_size=streaming_batch_size,
            force=force,
            run_seed=run_seed,
        )

        # Note: StructuredLogger is now initialized in BasePipeline
        # Use self.logger for all logging (it's now a structured logger with JSON output)

        # Set processed_file for human-readable text dump (aligns with other pipelines)
        # Pattern: {dataset_slug}_{run_id}_processed_cleaned.txt
        dataset_slug = self.dataset_name.split("/")[-1]
        self.processed_file = (
            self.processed_dir / f"{dataset_slug}_{self.run_id}_processed_cleaned.txt"
        )

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
        Create manifest without downloading data.

        Writes dataset metadata (name, config, split, revision, filters) to
        data/raw/source=HF-<name>/date_accessed=<date>/<dataset>_manifest.json

        Returns:
            Path to manifest file
        """
        raw_dir = self.raw_dir

        # Generate descriptive manifest filename with run_id
        # Pattern: {dataset_slug}_{run_id}_raw_manifest.json
        dataset_slug = self.dataset_name.split("/")[
            -1
        ]  # Get last part (e.g., "c4" from "allenai/c4")
        manifest_path = raw_dir / f"{dataset_slug}_{self.run_id}_raw_manifest.json"

        # Create raw directory if it doesn't exist
        raw_dir.mkdir(parents=True, exist_ok=True)

        # Set context using run_id from base_pipeline
        set_context(run_id=self.run_id, source=self.source, phase="discovery")

        # Initialize metrics with run_id from base_pipeline
        self.metrics = MetricsCollector(
            self.run_id, self.source, pipeline_type=PipelineType.STREAM_PROCESSING
        )

        # Check if manifest exists and not forcing
        if manifest_path.exists() and not self.force:
            self.logger.info(f"Manifest already exists: {manifest_path}")
            return manifest_path

        self.logger.info(f"Creating manifest for {self.dataset_name}")

        # Load dataset to get revision info (doesn't download data in streaming mode)
        try:
            load_kwargs = {
                "streaming": True,
            }

            # Add revision pinning from config (Phase 2 feature)
            pinned_revision = self.hf_config.revision
            if pinned_revision:
                load_kwargs["revision"] = pinned_revision
                self.logger.info(f"Pinning dataset to revision: {pinned_revision}")

            # Add data_files if specified (for Parquet loading)
            if self.data_files:
                load_kwargs["data_files"] = self.data_files

            # Note: trust_remote_code is deprecated in datasets 4.2.x
            # Modern datasets (MC4, OSCAR, etc.) use standard Parquet format
            # and don't need this flag

            if self.dataset_config:
                dataset = load_dataset(
                    self.dataset_name, self.dataset_config, split=self.split, **load_kwargs
                )
            else:
                dataset = load_dataset(self.dataset_name, split=self.split, **load_kwargs)

            # Get revision if available (actual revision used, not just config)
            revision = getattr(dataset, "revision", None) or load_kwargs.get("revision", "latest")
            commit_hash = (
                getattr(dataset, "commit_hash", None) if hasattr(dataset, "commit_hash") else None
            )
            dataset_info = getattr(dataset, "info", None)

        except Exception as e:
            self.logger.error(f"Failed to load dataset metadata: {e}")
            revision = "unknown"
            commit_hash = None
            dataset_info = None

        # Track discovery (use datasets_opened for stream processing)
        self.metrics.increment("datasets_opened")

        # Create manifest
        manifest = {
            "dataset_name": self.dataset_name,
            "dataset_config": self.dataset_config,
            "split": self.split,
            "revision": revision,
            "commit_hash": commit_hash,  # Track exact commit for reproducibility
            "text_field": self.text_field,
            "title_field": self.title_field,
            "url_field": self.url_field,
            "metadata_fields": self.metadata_fields,
            "pushdown_filters": self.pushdown_filters,
            "data_files": self.data_files,
            "display_name": self.display_name,
            "streaming_batch_size": self.streaming_batch_size,
            "max_records": self.max_records,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_offset": 0,  # Track resume position
            "batches_completed": [],  # Track completed batch files
            "total_records_extracted": 0,  # Audit: total records pulled from HF
            "total_batches": 0,  # Audit: total batch files written
            "manifest_version": "1.0",  # For future schema evolution
            "run_id": self.run_id,  # Store run_id for continuity
        }

        # Add dataset info if available
        if dataset_info:
            manifest["dataset_info"] = {
                "description": getattr(dataset_info, "description", None),
                "license": getattr(dataset_info, "license", None),
                "features": str(getattr(dataset_info, "features", None)),
            }

        # Write manifest
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Manifest created: {manifest_path}")

        # Export metrics
        metrics_path = Path("data/metrics") / f"{self.run_id}_discovery.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics.export_json(metrics_path)

        return manifest_path

    def extract(self) -> Path:
        """
        Stream dataset and write JSONL batches to staging.

        Chunks the iterator into JSONL batch files for resume capability.
        Updates manifest with last_offset and completed batches.

        Returns:
            Path to staging directory containing JSONL batches
        """
        staging_dir = self.staging_dir
        staging_dir.mkdir(parents=True, exist_ok=True)

        # Load manifest (search for file with run_id pattern)
        dataset_slug = self.dataset_name.split("/")[-1]
        # Pattern: {dataset_slug}_{run_id}_raw_manifest.json or old {dataset_slug}_manifest.json
        manifest_files = list(self.raw_dir.glob(f"{dataset_slug}_*_raw_manifest.json"))

        if not manifest_files:
            raise FileNotFoundError(f"Manifest not found in {self.raw_dir}. Run download() first.")

        # Use the most recent manifest (sorted by modification time)
        manifest_path = sorted(manifest_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        self.logger.info(f"Using manifest: {manifest_path.name}")

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        # Set context using run_id from base_pipeline
        set_context(run_id=self.run_id, source=self.source, phase="fetch")

        # Resume or create metrics with run_id from base_pipeline
        if self.metrics is None:
            self.metrics = MetricsCollector(
                self.run_id, self.source, pipeline_type=PipelineType.STREAM_PROCESSING
            )

        # Check quota availability before processing
        quota_limit = self.config.orchestration.get_quota("huggingface")
        has_quota, remaining = self.ledger.check_quota_available("huggingface", quota_limit)

        if not has_quota:
            self.logger.warning(
                f"Daily quota already reached for HuggingFace: {quota_limit} records"
            )
            self.metrics.increment("quota_hit")
            return staging_dir

        # Apply quota limit to max_records if needed
        effective_max_records = self.max_records
        if quota_limit is not None:
            if effective_max_records is None:
                effective_max_records = remaining
            else:
                effective_max_records = min(effective_max_records, remaining)
            self.logger.info(
                f"Quota enforcement: processing max {effective_max_records} records "
                f"(quota: {quota_limit} records/day, remaining: {remaining})"
            )
        else:
            self.logger.info("Processing records (quota: unlimited)")

        # Check if extraction already complete and not forcing
        extraction_complete_marker = staging_dir / ".extraction_complete"
        if extraction_complete_marker.exists() and not self.force:
            self.logger.info(f"Extraction already complete: {staging_dir}")
            return staging_dir

        # PHASE 1: Discovery-Stage Deduplication for HuggingFace
        # Load set of already-processed URLs from ledger to skip in stream
        # This prevents re-downloading the same records on subsequent runs
        processed_urls = set()
        if not self.force and hasattr(self, "ledger") and self.ledger is not None:
            try:
                processed_urls = self._get_processed_urls()
                self.logger.info(
                    f"PHASE 1 DEDUP: Loaded {len(processed_urls)} already-processed URLs from ledger"
                )
            except Exception as e:
                self.logger.warning(f"Failed to load processed URLs from ledger: {e}")

        # PHASE 5: Load checkpoint for resumption
        # Try checkpoint file first (more frequent saves), fallback to manifest
        checkpoint = None if self.force else self._load_checkpoint()
        start_offset = 0
        if checkpoint:
            start_offset = checkpoint.get("last_index", 0)
            self.logger.info(f"Resuming from checkpoint: offset={start_offset}")
        else:
            # Fallback to manifest-based offset
            start_offset = manifest.get("last_offset", 0)
            if start_offset > 0:
                self.logger.info(f"Resuming from manifest: offset={start_offset}")

        batches_completed = set(manifest.get("batches_completed", []))

        self.logger.info(
            f"Streaming {self.dataset_name} (config={self.dataset_config}, "
            f"split={self.split}, start_offset={start_offset})"
        )

        # Load dataset in streaming mode
        load_kwargs = {
            "streaming": True,
        }

        # Add data_files if specified (for Parquet loading)
        if self.data_files:
            load_kwargs["data_files"] = self.data_files

        # Add split if specified (not needed when using data_files with split in dict)
        if self.split:
            load_kwargs["split"] = self.split

        # Add pushdown filters to load_kwargs if specified
        if self.pushdown_filters:
            load_kwargs.update(self.pushdown_filters)

        # Add config as second positional arg if provided
        if self.dataset_config:
            dataset = load_dataset(self.dataset_name, self.dataset_config, **load_kwargs)
        else:
            dataset = load_dataset(self.dataset_name, **load_kwargs)

        # Stream and batch
        batch = []
        batch_num = start_offset // self.streaming_batch_size
        current_offset = start_offset
        total_processed = 0
        stopped_at_limit = False  # Track if we stopped due to max_records limit

        # Track metrics path for checkpointing
        metrics_path = Path("data/metrics") / f"{self.run_id}_extraction.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            for i, record in enumerate(dataset):
                # Skip already processed records
                if i < start_offset:
                    continue

                # Check max_records limit (with quota enforcement)
                if effective_max_records and total_processed >= effective_max_records:
                    reason = (
                        "quota limit"
                        if quota_limit and effective_max_records == remaining
                        else "max_records limit"
                    )
                    self.logger.info(f"Reached {reason}: {effective_max_records}")
                    stopped_at_limit = True
                    break

                # Time the record fetch
                with Timer() as timer:
                    # Validate record using schema mapper
                    if not self.schema_mapper.validate_record(record):
                        self.metrics.increment("records_invalid_schema")
                        continue

                    # Map record using schema mapper
                    mapped_record = self.schema_mapper.map_record(record, index=i)
                    text = mapped_record.get("text")
                    url = mapped_record.get("url")

                    # PHASE 1: Skip if URL already processed in previous runs
                    if url and url in processed_urls:
                        self.metrics.increment("records_skipped_discovery_dedup")
                        continue

                    # Track text length
                    if text:
                        self.metrics.record_text_length(len(text))

                    # Check for duplicates via hash
                    if text and url:
                        # Process duplicates with combined exact and near-duplicate detection
                        is_dup, dup_type, similar_url, text_hash, minhash_sig = (
                            self.dedup.process_document(text, url)
                        )

                        if is_dup:
                            self.logger.debug(
                                f"{dup_type.capitalize()} duplicate detected: {url} "
                                f"(similar to {similar_url})"
                            )
                            self.ledger.mark_duplicate(url, similar_url)
                            # Increment correct metric based on duplicate type
                            if dup_type == "exact":
                                self.metrics.increment("records_deduplicated")
                            elif dup_type == "near":
                                self.metrics.increment("near_duplicates")
                            continue

                        # Add hash and signature to record
                        record["_text_hash"] = text_hash
                        record["_minhash_signature"] = minhash_sig

                    batch.append(record)

                # Record fetch duration
                self.metrics.record_fetch_duration(timer.get_elapsed_ms())
                self.metrics.increment("records_fetched")

                # Increment quota counter
                if quota_limit is not None:
                    self.ledger.increment_daily_quota(
                        source="huggingface", count=1, quota_limit=quota_limit
                    )

                current_offset = i + 1
                total_processed += 1

                # PHASE 5: Save checkpoint every 1000 records
                if total_processed % 1000 == 0:
                    self._save_checkpoint(
                        {
                            "last_index": current_offset,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "processed_count": total_processed,
                        }
                    )
                    self.metrics.increment(
                        "records_skipped_checkpoint"
                    )  # Track checkpoint frequency

                # Write batch when full
                if len(batch) >= self.streaming_batch_size:
                    # Pattern: {dataset_slug}_{run_id}_staging_batch-{num}.jsonl
                    batch_file = (
                        staging_dir
                        / f"{dataset_slug}_{self.run_id}_staging_batch-{batch_num:06d}.jsonl"
                    )

                    # Skip if batch already completed
                    if batch_file.name not in batches_completed:
                        self._write_batch(batch, batch_file)
                        batches_completed.add(batch_file.name)

                        # Track batch completion
                        self.metrics.increment("batches_completed")

                        # Update manifest with progress
                        manifest["last_offset"] = current_offset
                        manifest["batches_completed"] = list(batches_completed)
                        self._update_manifest(manifest_path, manifest)

                        # Checkpoint metrics
                        self.metrics.export_json(metrics_path)

                        self.logger.info(
                            f"Batch {batch_num} complete: {len(batch)} records "
                            f"(total: {total_processed})"
                        )

                    batch = []
                    batch_num += 1

            # Write final partial batch
            if batch:
                # Pattern: {dataset_slug}_{run_id}_staging_batch-{num}.jsonl
                batch_file = (
                    staging_dir
                    / f"{dataset_slug}_{self.run_id}_staging_batch-{batch_num:06d}.jsonl"
                )
                if batch_file.name not in batches_completed:
                    self._write_batch(batch, batch_file)
                    batches_completed.add(batch_file.name)

                    manifest["last_offset"] = current_offset
                    manifest["batches_completed"] = list(batches_completed)
                    self._update_manifest(manifest_path, manifest)

                    self.logger.info(f"Final batch {batch_num} complete: {len(batch)} records")

            # Mark extraction as complete ONLY if we exhausted the dataset
            # (not if we stopped at max_records limit - there's more data to stream)
            if not stopped_at_limit:
                extraction_complete_marker.touch()
                self.logger.info("Dataset exhausted - marking extraction as complete")
            else:
                # Check if we stopped due to quota limit
                if quota_limit is not None and effective_max_records == remaining:
                    # Quota hit - mark in ledger
                    # Note: We can't calculate exact items_remaining for infinite streams,
                    # so we mark it as unknown (-1)
                    self.ledger.mark_quota_hit(
                        source="huggingface",
                        items_remaining=-1,  # Unknown for infinite dataset streams
                        quota_limit=quota_limit,
                    )
                    self.logger.info(
                        f"Quota hit: {quota_limit} records processed, "
                        f"more data available to stream from offset {current_offset}"
                    )
                    self.metrics.increment("quota_hit")
                else:
                    self.logger.info(
                        f"Stopped at max_records limit - more data available to stream from offset {current_offset}"
                    )

            # PHASE 5: Save final checkpoint and clean up
            self._save_checkpoint(
                {
                    "last_index": current_offset,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "processed_count": total_processed,
                    "completed": True,
                }
            )
            self.logger.info(f"Final checkpoint saved at offset {current_offset}")

            # Update manifest with final audit counts
            manifest["total_records_extracted"] = total_processed
            manifest["total_batches"] = batch_num + 1
            self._update_manifest(manifest_path, manifest)

            self.logger.info(
                f"Extraction complete: {total_processed} records in {batch_num + 1} batches"
            )

            # Export final metrics and generate extraction quality report
            self.metrics.export_json(metrics_path)

            # Generate extraction quality report (shows extraction phase only)
            report_path = Path("data/reports") / f"{self.run_id}_extraction_quality_report.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            QualityReporter(self.metrics).generate_markdown_report(report_path)

            self.logger.info(f"Metrics exported: {metrics_path}")
            self.logger.info(f"Extraction quality report: {report_path}")

            # Set staging_file for BasePipeline.process() validation
            # Point to staging directory so process() can find JSONL files
            self.staging_file = staging_dir

        except Exception as e:
            self.logger.error(f"Extraction failed at offset {current_offset}: {e}")
            # Save progress before raising
            manifest["last_offset"] = current_offset
            manifest["batches_completed"] = list(batches_completed)
            self._update_manifest(manifest_path, manifest)
            raise

        return staging_dir

    def _write_batch(self, batch: list[dict[str, Any]], batch_file: Path) -> None:
        """Write batch of records to JSONL file."""
        with open(batch_file, "w", encoding="utf-8") as f:
            for record in batch:
                # Convert non-serializable types (datetime, etc.) to strings
                serializable_record = self._make_json_serializable(record)
                f.write(json.dumps(serializable_record, ensure_ascii=False) + "\n")

    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Recursively convert non-JSON-serializable objects to serializable types.

        Handles:
        - datetime objects → ISO format strings
        - date objects → ISO format strings
        - bytes → base64 encoded strings
        - sets → lists
        - Other objects → str() representation
        """
        import base64
        from datetime import date, datetime

        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        else:
            # For any other type, convert to string
            return str(obj)

    def _update_manifest(self, manifest_path: Path, manifest: dict[str, Any]) -> None:
        """Update manifest file with progress."""
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def process(self) -> Path:
        """
        Process staged JSONL batches and write to silver dataset.

        Overrides BasePipeline.process() to handle multi-batch staging format,
        but uses the same enrichment logic.

        Returns:
            Path to silver dataset directory
        """
        from collections import Counter

        from ...quality.record_utils import build_silver_record

        # Check that extraction has been performed
        staging_dir = self.staging_dir
        if not staging_dir.exists():
            raise FileNotFoundError(
                f"Staging directory not found: {staging_dir}. Run extract() first."
            )

        # NOTE: We don't check for .extraction_complete marker anymore because
        # it's only created when the dataset is exhausted, not when stopping at max_records.
        # The process() method can run as long as JSONL files exist in staging.

        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("PHASE 3: Text Processing & Silver Dataset Creation")
        self.logger.info("=" * 60)

        records_processed = 0
        records_filtered = 0
        filter_stats = Counter()
        silver_records = []

        # PHASE 1: Load already-processed URLs for cross-run deduplication
        processed_urls = set()
        if not self.force and hasattr(self, "ledger") and self.ledger is not None:
            try:
                processed_urls = self._get_processed_urls()
                self.logger.info(
                    f"PHASE 1 DEDUP (process): Loaded {len(processed_urls)} already-processed URLs from ledger"
                )
            except Exception as e:
                self.logger.warning(f"Failed to load processed URLs from ledger: {e}")

        for raw_record in self._extract_records():
            # PHASE 1: Skip if URL already processed in previous runs
            if raw_record.url and raw_record.url in processed_urls:
                self.metrics.increment("records_skipped_discovery_dedup")
                continue

            # Shared text cleaning
            cleaned = self.text_cleaner.clean(raw_record.text)

            if not cleaned:
                records_filtered += 1
                filter_stats["empty_after_cleaning"] += 1

                # Record filter reason in metrics if available
                if hasattr(self, "metrics") and self.metrics is not None:
                    self.metrics.record_filter_reason("empty_after_cleaning")
                continue

            # Execute record filters using FilterEngine API
            passed, failed_filter, filter_metadata = self.filter_engine.apply_filters(
                cleaned, raw_record.title
            )

            if not passed:
                records_filtered += 1
                filter_stats[f"filtered_by_{failed_filter}"] += 1

                # Record filter reason in metrics if available
                if hasattr(self, "metrics") and self.metrics is not None:
                    self.metrics.record_filter_reason(failed_filter)
                continue

            # Merge metadata
            source_meta = self._get_source_metadata()
            merged_metadata = {**source_meta, **raw_record.metadata, **filter_metadata}

            # Build enriched silver record
            record = build_silver_record(
                text=cleaned,
                title=raw_record.title,
                source=self.source,
                url=raw_record.url,
                date_accessed=self.date_accessed,
                source_type=self._get_source_type(),
                language=self._get_language(),
                license_str=self._get_license(),
                pipeline_version="2.1.0",  # Updated for schema v2.1
                source_metadata=merged_metadata,
                date_published=raw_record.metadata.get("date_published"),
                topic=raw_record.metadata.get("topic"),
                domain=self._get_domain(),
                embedding=None,  # Placeholder for future embeddings
                register=self._get_register(),  # v2.1: Linguistic register
            )

            # PHASE 1: Mark URL as processed in ledger for cross-run deduplication
            if hasattr(self, "ledger") and self.ledger is not None:
                try:
                    # Get minhash_signature from metadata if available
                    minhash_sig = raw_record.metadata.get("minhash_signature")
                    # Use URL from silver record (has correct URL from JSONL)
                    record_url = record["url"]
                    self.ledger.mark_processed(
                        url=record_url,
                        text_hash=record["text_hash"],
                        silver_id=record["id"],
                        minhash_signature=minhash_sig,
                        source=self.source,
                    )
                except Exception as e:
                    self.logger.error(f"Failed to mark URL as processed in ledger: {e}")

            silver_records.append(record)
            records_processed += 1

            # Log progress
            if records_processed % self.log_frequency == 0:
                self.logger.info(
                    f"Processed {records_processed:,} records (filtered: {records_filtered:,})"
                )

        # Write human-readable text dump (aligns with other pipelines)
        if not silver_records:
            self.logger.error("No records passed filters!")
            self.logger.error("")
            self.logger.error("=" * 60)
            self.logger.error("PROCESSING FAILED - NO DATA")
            self.logger.error("=" * 60)
            self.logger.error(f"Total processed: {records_processed:,}")
            self.logger.error(f"Total filtered:  {records_filtered:,}")
            if filter_stats:
                self.logger.error("\nFilter breakdown:")
                for filter_name, count in filter_stats.most_common():
                    self.logger.error(f"  {filter_name}: {count:,}")
            raise ValueError(
                f"No records passed filters. Total extracted: {records_processed:,}, "
                f"Total filtered: {records_filtered:,}. Check filter configuration."
            )

        # Write processed text file for human inspection
        with open(self.processed_file, "w", encoding="utf-8") as f:
            for record in silver_records:
                # Format: <title>\n<text>\n\n (separator between records)
                f.write(f"{record['title']}\n")
                f.write(f"{record['text']}\n")
                f.write("\n")  # Blank line separator

        self.logger.info(
            f"✓ Processed text written: {self.processed_file} ({records_processed:,} records)"
        )

        # Write to silver dataset (Parquet)
        silver_path = self.silver_writer.write(
            records=silver_records,
            source=self.source,
            date_accessed=self.date_accessed,
            run_id=self.run_id,
        )
        self.logger.info(f"✓ Silver dataset written: {silver_path}")

        # Export processing metrics and final quality report (aligns with base_pipeline.py)
        if hasattr(self, "metrics") and self.metrics is not None:
            self.metrics.increment("records_processed", records_processed)
            self.metrics.increment("records_written", records_processed)

            metrics_path = Path("data/metrics") / f"{self.run_id}_processing.json"
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            self.metrics.export_json(metrics_path)
            self.logger.info(f"Processing metrics exported: {metrics_path}")

            from ...infra.metrics import QualityReporter

            report_path = Path("data/reports") / f"{self.run_id}_final_quality_report.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            QualityReporter(self.metrics).generate_markdown_report(report_path)
            self.logger.info(f"Final quality report: {report_path}")

        # Log final stats
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("PROCESSING COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Total processed: {records_processed:,}")
        self.logger.info(f"Total filtered:  {records_filtered:,}")
        if filter_stats:
            self.logger.info("\nFilter breakdown:")
            for filter_name, count in filter_stats.most_common():
                self.logger.info(f"  {filter_name}: {count:,}")

        return silver_path

    def _extract_records(self) -> Iterator[RawRecord]:
        """
        Replay staged JSONL batches and map to RawRecords.

        Yields:
            RawRecord with fields mapped from HF dataset schema
        """
        staging_dir = self.staging_dir

        if not staging_dir.exists():
            raise FileNotFoundError(
                f"Staging directory not found: {staging_dir}. Run extract() first."
            )

        # Find all batch files (support both old and new naming for backward compat)
        batch_files = sorted(staging_dir.glob("*_staging_batch-*.jsonl"))
        if not batch_files:
            # Fallback to old naming
            batch_files = sorted(staging_dir.glob("batch_*.jsonl"))

        if not batch_files:
            self.logger.warning(f"No batch files found in {staging_dir}")
            return

        self.logger.info(f"Replaying {len(batch_files)} JSONL batches")

        for batch_file in batch_files:
            with open(batch_file, encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    yield self._map_to_raw_record(record)

    def _map_to_raw_record(self, record: dict[str, Any]) -> RawRecord:
        """
        Map HF dataset record to RawRecord.

        Args:
            record: HF dataset record (dictionary)

        Returns:
            RawRecord with title, text, url, and metadata
        """
        # Extract text (required)
        text = record.get(self.text_field, "")

        # Extract title (optional, generate default if not specified)
        if self.title_field and self.title_field in record:
            title = record[self.title_field]
        else:
            # Generate default title from text (first 50 chars)
            title = text[:50] + "..." if len(text) > 50 else text

        # Extract URL (optional, generate default if not specified)
        if self.url_field and self.url_field in record:
            url = record[self.url_field]
        else:
            # Generate placeholder URL
            url = f"hf://{self.dataset_name}/{self.dataset_config or 'default'}"

        # Extract metadata fields
        metadata = {}
        for field in self.metadata_fields:
            if field in record:
                metadata[field] = record[field]

        # Add dataset source info
        metadata["hf_dataset"] = self.dataset_name
        metadata["hf_config"] = self.dataset_config
        metadata["hf_split"] = self.split

        # Preserve dedup metadata if present (for ledger tracking)
        if "_minhash_signature" in record:
            metadata["minhash_signature"] = record["_minhash_signature"]
        if "_text_hash" in record:
            metadata["text_hash"] = record["_text_hash"]

        return RawRecord(
            title=title,
            text=text,
            url=url,
            metadata=metadata,
        )

    def _create_cleaner(self):
        """Create HTML cleaner for HF datasets (most contain HTML)."""
        return create_html_cleaner()

    def _register_filters(self) -> None:
        """Register quality filters for HF datasets."""
        from ...quality.filter_functions import langid_filter, min_length_filter

        # Load filter config
        min_length = self.hf_config.min_length_threshold
        confidence = self.hf_config.langid_confidence_threshold

        self.filter_engine.register_filter(min_length_filter, {"threshold": min_length})
        self.filter_engine.register_filter(
            langid_filter,
            {
                "allowed_langs": {"so"},
                "confidence_threshold": confidence,
            },
        )

    def _get_source_type(self) -> str:
        """Return source type."""
        # Try to infer from dataset name
        if "news" in self.dataset_name.lower() or "gdelt" in self.dataset_name.lower():
            return "news"
        elif "social" in self.dataset_name.lower() or "twitter" in self.dataset_name.lower():
            return "social"
        else:
            return "web"  # Default for web-scraped corpora

    def _get_license(self) -> str:
        """Return license from manifest or default."""
        dataset_slug = self.dataset_name.split("/")[-1]
        # Try to find manifest with run_id pattern
        manifest_files = list(self.raw_dir.glob(f"{dataset_slug}_*_raw_manifest.json"))
        if not manifest_files:
            manifest_files = list(self.raw_dir.glob(f"{dataset_slug}_manifest.json"))

        if manifest_files:
            manifest_path = manifest_files[0]
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
                dataset_info = manifest.get("dataset_info", {})
                license = dataset_info.get("license")
                if license:
                    return license

        # Default licenses by dataset
        if "c4" in self.dataset_name.lower() or "mc4" in self.dataset_name.lower():
            return "ODC-BY-1.0"
        elif "oscar" in self.dataset_name.lower():
            return "CC0-1.0"
        elif "madlad" in self.dataset_name.lower():
            return "ODC-BY-1.0"
        else:
            return "Unknown"

    def _get_language(self) -> str:
        """Return ISO 639-1 language code."""
        return "so"  # Somali

    def _get_source_metadata(self) -> dict[str, Any]:
        """
        Return source-specific metadata.

        Note: The source slug is filesystem-friendly (e.g., HuggingFace-Somali_c4-so).
        We include the original dataset name here for human-readable display.
        """
        # Use custom display_name if set, otherwise build from dataset_name
        if self.display_name:
            pretty_name = self.display_name
        else:
            pretty_name = f"{self.dataset_name}"
            if self.dataset_config:
                pretty_name += f" ({self.dataset_config})"

        return {
            "dataset_name": self.dataset_name,
            "dataset_config": self.dataset_config,
            "split": self.split,
            "display_name": pretty_name,  # Human-readable name with original dataset info
        }

    def _get_domain(self) -> str:
        """Return content domain for silver records."""
        # Infer from dataset name
        dataset_lower = self.dataset_name.lower()
        if "news" in dataset_lower or "gdelt" in dataset_lower:
            return "news"
        elif "social" in dataset_lower or "twitter" in dataset_lower:
            return "social_media"
        elif "wiki" in dataset_lower:
            return "encyclopedia"
        elif "academic" in dataset_lower or "arxiv" in dataset_lower:
            return "academic"
        else:
            # Default for web-scraped corpora like MC4, OSCAR
            return "web"

    def _get_register(self) -> str:
        """
        Return linguistic register for silver records.

        Returns:
            Register string ("formal", "informal", "colloquial")

        Note:
            - MC4 and other web-scraped corpora are classified as "formal"
            - Future social media sources (TikTok) would use "informal"
        """
        # Infer from source type
        source_type = self._get_source_type()
        if source_type == "social":
            return "informal"
        else:
            # MC4 and web corpora are formal written text
            return "formal"

    def _get_processed_urls(self) -> set[str]:
        """
        Get set of already-processed URLs from ledger.

        PHASE 1: Discovery-Stage Deduplication helper for HuggingFace streaming.
        Similar to Språkbanken's _get_downloaded_corpus_ids() approach.

        Returns:
            Set of URLs already in PROCESSED state in the ledger
        """
        if not hasattr(self, "ledger") or self.ledger is None:
            return set()

        try:
            # Get processed URLs for this source from ledger
            # Use source name that matches what's stored in ledger
            processed_urls_list = self.ledger.get_processed_urls(source=self.source)
            # FIX: get_processed_urls returns list[dict], extract 'url' field
            processed_urls = {record["url"] for record in processed_urls_list}
            self.logger.info(
                f"Loaded {len(processed_urls)} processed URLs from ledger for source '{self.source}'"
            )
            return processed_urls
        except Exception as e:
            self.logger.warning(f"Failed to query ledger for processed URLs: {e}")
            return set()

    def _load_checkpoint(self) -> Optional[dict]:
        """
        Load processing checkpoint from disk.

        Used for incremental processing to resume from last processed index.

        Returns:
            Checkpoint dict with 'last_index' key, or None if no checkpoint
        """
        checkpoint_file = self.raw_dir / "checkpoint.json"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, encoding="utf-8") as f:
                    checkpoint = json.load(f)
                    self.logger.info(
                        f"Loaded checkpoint: last_index={checkpoint.get('last_index', 0)}"
                    )
                    return checkpoint
            except Exception as e:
                self.logger.warning(f"Failed to load checkpoint: {e}")
                return None
        return None

    def _save_checkpoint(self, checkpoint: dict):
        """
        Save processing checkpoint to disk.

        Used for incremental processing to track progress.

        Args:
            checkpoint: Dict containing 'last_index' and metadata
        """
        checkpoint_file = self.raw_dir / "checkpoint.json"
        try:
            checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Checkpoint saved: index={checkpoint['last_index']}")
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")


# Factory functions for common datasets


def create_mc4_processor(
    max_records: Optional[int] = None, force: bool = False
) -> HuggingFaceSomaliProcessor:
    """
    Create processor for allenai/c4 (Multilingual C4) Somali subset.

    Note: The old 'mc4' dataset is deprecated. Use 'allenai/c4' instead.

    Args:
        max_records: Maximum records to process (None = unlimited)
        force: Force reprocessing

    Returns:
        Configured HuggingFaceSomaliProcessor
    """
    return HuggingFaceSomaliProcessor(
        dataset_name="allenai/c4",
        dataset_config="so",
        split="train",
        text_field="text",
        url_field="url",
        metadata_fields=["timestamp"],
        max_records=max_records,
        force=force,
    )


# ============================================================================
# REMOVED: OSCAR and MADLAD-400 Processors
# ============================================================================
#
# The following processors have been REMOVED from the codebase:
#
# 1. create_oscar_processor() - REMOVED
#    Reason: Requires authentication, has less data than MC4
#    Decision: docs/decisions/001-oscar-exclusion.md
#
# 2. create_madlad400_processor() - REMOVED
#    Reason: Incompatible with datasets>=3.0 (uses deprecated dataset scripts)
#    Decision: docs/decisions/003-madlad-400-exclusion.md
#    Technical Report: MADLAD400_STATUS.md
#
# Use create_mc4_processor() instead - it has MORE data, works with datasets>=3.0,
# and requires NO authentication or workarounds.
#
# See docs/HUGGINGFACE_DATASETS.md for detailed comparison and rationale.
# ============================================================================
