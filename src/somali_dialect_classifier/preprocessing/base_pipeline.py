"""
Base pipeline orchestrator with dependency injection (P3.1 refactoring).

Injects: DataManager (P2.2), FilterEngine, RecordBuilder, ValidationService (P3.1).
Subclasses implement source-specific logic (download, extract, _extract_records, _create_cleaner).
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from ..config import get_config
from ..data import DataManager
from ..pipeline.filter_engine import FilterEngine
from ..schema.validation_service import ValidationService
from ..utils.logging_utils import generate_run_id
from .data_processor import DataProcessor
from .pipeline_setup import PipelineSetup
from .raw_record import RawRecord
from .record_builder import RecordBuilder
from .silver_writer import SilverDatasetWriter
from .text_cleaners import TextCleaningPipeline


class BasePipeline(DataProcessor, ABC):
    """
    Base orchestrator for data pipelines with dependency injection.

    Subclasses implement: download, extract, _extract_records, _create_cleaner,
    _get_source_type, _get_license, _get_language, _get_domain, _get_register.
    """

    def __init__(
        self,
        source: str,
        log_frequency: int = 100,
        batch_size: Optional[int] = None,
        force: bool = False,
        data_manager: Optional[DataManager] = None,
        filter_engine: Optional[FilterEngine] = None,
        record_builder: Optional[RecordBuilder] = None,
        validation_service: Optional[ValidationService] = None,
    ):
        """Initialize pipeline with dependency injection for services."""
        # Sanitize source and generate IDs
        self.source = PipelineSetup.sanitize_and_validate_source(source)
        self.run_id = generate_run_id(self.source)
        self.date_accessed = datetime.now(timezone.utc).date().isoformat()

        # Configuration
        self.log_frequency = log_frequency
        self.batch_size = batch_size
        self.force = force

        # Setup services (P3.1: dependency injection with sensible defaults)
        self.logger = PipelineSetup.create_logger(self.source, self.run_id)
        self.data_manager = PipelineSetup.create_data_manager(
            self.source, self.run_id, data_manager
        )
        self.filter_engine = PipelineSetup.create_filter_engine(filter_engine)
        self.record_builder = PipelineSetup.create_record_builder(
            self.source, self.date_accessed, self.run_id, record_builder
        )
        self.validation_service = PipelineSetup.create_validation_service(
            validation_service
        )

        # Register filters (subclass hook)
        if filter_engine is None:
            self._register_filters()

        # Directory structure (backward compatibility)
        self.raw_dir, self.staging_dir, self.processed_dir = (
            PipelineSetup.get_directory_paths(self.source, self.date_accessed)
        )

        # Shared utilities
        self.text_cleaner = self._create_cleaner()
        self.silver_writer = SilverDatasetWriter()

        # Subclasses set these paths
        self.staging_file: Optional[Path] = None
        self.processed_file: Optional[Path] = None
        self.silver_path: Optional[Path] = None

    def _register_filters(self) -> None:
        """Register quality filters with self.filter_engine. Subclasses override to add filters."""
        pass
    @abstractmethod
    def _extract_records(self) -> Iterator[RawRecord]:
        """Extract records from staging format. Yield RawRecord objects."""
        pass
    @abstractmethod
    def _create_cleaner(self) -> TextCleaningPipeline:
        """Create text cleaner instance (e.g., create_html_cleaner, create_wiki_cleaner)."""
        pass
    @abstractmethod
    def _get_source_type(self) -> str:
        """Return source type (wiki, news, social, corpus, web)."""
        pass
    @abstractmethod
    def _get_license(self) -> str:
        """Return license (e.g., CC-BY-SA-3.0, ODC-BY-1.0)."""
        pass
    @abstractmethod
    def _get_language(self) -> str:
        """Return ISO 639-1 language code (default: so)."""
        return "so"
    @abstractmethod
    def _get_source_metadata(self) -> dict[str, Any]:
        """Return source-specific metadata dict."""
        pass
    @abstractmethod
    def _get_domain(self) -> str:
        """Return content domain (news, encyclopedia, web, etc.)."""
        pass
    @abstractmethod
    def _get_register(self) -> str:
        """Return linguistic register (formal, informal, colloquial)."""
        pass

    def process(self) -> Path:
        """Orchestrate processing: extract→clean→filter→build→validate→write. Returns silver Parquet path."""
        if not self.staging_file or not self.staging_file.exists():
            raise FileNotFoundError(f"Staging file not found: {self.staging_file}")
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        if self.processed_file.exists():
            if not self.force:
                self.logger.info(f"Processed file exists: {self.processed_file}. Use force=True to reprocess")
                return self.processed_file
            self.logger.info(f"Force reprocessing: removing {self.processed_file}")
            self.processed_file.unlink()
        self.logger.info("\n" + "=" * 60)
        self.logger.info("PHASE 3: Text Processing & Silver Dataset Creation")
        self.logger.info("=" * 60)
        records_processed = 0
        records_filtered = 0
        records = []
        with open(self.processed_file, "w", encoding="utf-8") as fout:
            for raw_record in self._extract_records():
                cleaned = self.text_cleaner.clean(raw_record.text)
                if not cleaned:
                    records_filtered += 1
                    self._record_filter_metric("empty_after_cleaning")
                    continue
                passed, failed_filter, filter_metadata = self.filter_engine.apply_filters(
                    cleaned, raw_record.title
                )
                if not passed:
                    records_filtered += 1
                    self._record_filter_metric(failed_filter)
                    continue
                fout.write(f"=== {raw_record.title} ===\n{cleaned}\n\n")
                record = self.record_builder.build_silver_record(
                    raw_record=raw_record,
                    cleaned_text=cleaned,
                    filter_metadata=filter_metadata,
                    source_type=self._get_source_type(),
                    license_str=self._get_license(),
                    domain=self._get_domain(),
                    register=self._get_register(),
                    language=self._get_language(),
                    source_metadata=self._get_source_metadata(),
                )
                metrics = self.metrics if hasattr(self, "metrics") else None
                is_valid, errors = self.validation_service.validate_record(
                    record, self.source, metrics
                )
                if not is_valid:
                    records_filtered += 1
                    continue
                records.append(record)
                records_processed += 1
                self._mark_url_processed(raw_record, record)
                if records_processed % self.log_frequency == 0:
                    self.logger.info(f"Progress: {records_processed} records processed...")
                if self.batch_size and len(records) >= self.batch_size:
                    self._write_batch(records)
                    records = []
        self._log_processing_summary(records_processed, records_filtered)
        self._write_final_batch(records)
        self._export_metrics(records_processed, records_filtered)
        return self.silver_path if self.silver_path else self.processed_file

    def _record_filter_metric(self, filter_reason: str) -> None:
        """Record filter reason in metrics if available."""
        if hasattr(self, "metrics") and self.metrics is not None:
            self.metrics.record_filter_reason(filter_reason)

    def _mark_url_processed(self, raw_record: RawRecord, record: dict) -> None:
        """Mark URL as processed in ledger if available."""
        if hasattr(self, "ledger") and self.ledger is not None:
            minhash_sig = raw_record.metadata.get("minhash_signature")
            self.ledger.mark_processed(
                url=raw_record.url,
                text_hash=record["text_hash"],
                silver_id=record["id"],
                minhash_signature=minhash_sig,
                source=self.source,
            )

    def _log_processing_summary(self, records_processed: int, records_filtered: int) -> None:
        """Log processing summary with filter statistics."""
        self.logger.info("=" * 60)
        self.logger.info(f"Processing complete: {records_processed} records")

        if records_filtered > 0:
            self.logger.info(f"Filtered: {records_filtered} records")

            # Get human-readable filter statistics
            readable_stats = self.filter_engine.get_human_readable_stats()
            if readable_stats:
                self.logger.info("Filter statistics:")
                for _, (label, count) in readable_stats.items():
                    self.logger.info(f"  {label}: {count} records")

        self.logger.info("=" * 60)

    def _write_final_batch(self, records: list) -> None:
        """Write final batch to silver dataset."""
        if records:
            silver_path = self.silver_writer.write(
                records=records,
                source=self.source,
                date_accessed=self.date_accessed,
                run_id=self.run_id,
            )
            if silver_path:
                self.silver_path = silver_path

    def _export_metrics(self, records_processed: int, records_filtered: int) -> None:
        """Export processing metrics and generate quality report."""
        if hasattr(self, "metrics") and self.metrics is not None:
            # Update metrics with processing stats
            self.metrics.increment("urls_processed", records_processed)
            self.metrics.increment("records_written", records_processed)
            self.metrics.increment("records_filtered", records_filtered)

            # Export final metrics after processing
            metrics_path = Path("data/metrics") / f"{self.run_id}_processing.json"
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            self.metrics.export_json(metrics_path)
            self.logger.info(f"Processing metrics exported: {metrics_path}")

            # Generate final quality report with complete stats
            from ..utils.metrics import QualityReporter

            report_path = Path("data/reports") / f"{self.run_id}_final_quality_report.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            QualityReporter(self.metrics).generate_markdown_report(report_path)
            self.logger.info(f"Final quality report: {report_path}")

    def _write_batch(self, records: list) -> None:
        """Write batch of records to silver dataset."""
        if records:
            self.logger.info(f"Writing batch of {len(records)} records...")
            silver_path = self.silver_writer.write(
                records=records, source=self.source,
                date_accessed=self.date_accessed, run_id=self.run_id
            )
            if silver_path:
                self.silver_path = silver_path

    def save(self, processed_data: str) -> None:
        """Save processed data (no-op: handled by process() via SilverDatasetWriter)."""
        pass

    def run(self) -> Path:
        """Template method: download→extract→process. Returns silver Parquet path."""
        self.download()
        self.extract()
        return self.process()

    def _cleanup_old_raw_files(self):
        """Clean up old raw files, keeping only recent N files (config: raw_files_to_keep)."""
        config = get_config()
        keep_n = getattr(config.preprocessing, "raw_files_to_keep", 3)

        if not self.raw_dir.exists():
            return

        raw_files = sorted(
            [f for f in self.raw_dir.iterdir() if f.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for old_file in raw_files[keep_n:]:
            try:
                old_file.unlink()
                self.logger.debug(f"Cleaned up old raw file: {old_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to delete {old_file.name}: {e}")

    def _compute_file_checksum(self, filepath: Path, algorithm: str = 'sha256') -> str:
        """Compute file checksum (delegates to DataManager). P2.2 refactoring."""
        return self.data_manager.compute_file_checksum(filepath, algorithm)

    def _export_stage_metrics(self, stage: str):
        """
        Export metrics for a pipeline stage.

        Args:
            stage: Pipeline stage name (discovery, extraction, processing)
        """
        if not hasattr(self, "metrics") or self.metrics is None:
            return

        from ..config import get_config
        config = get_config()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        metrics_path = config.data.metrics_dir / f"{timestamp}_{self.source}_{self.run_id}_{stage}.json"

        self.metrics.export_json(
            output_file=metrics_path,
            source=self.source,
            stage=stage
        )

        self.logger.info(f"Exported {stage} metrics: {metrics_path}")

    def _generate_quality_report(self, stage: str):
        """
        Generate quality report for a pipeline stage.

        Args:
            stage: Pipeline stage name (discovery, extraction, processing)
        """
        if not hasattr(self, "metrics") or self.metrics is None:
            return

        from ..config import get_config
        from ..utils.metrics import QualityReporter

        config = get_config()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_path = config.data.reports_dir / f"{timestamp}_{self.source}_{self.run_id}_{stage}_quality_report.md"

        QualityReporter(self.metrics).generate_markdown_report(report_path)

        self.logger.info(f"Generated quality report: {report_path}")

    def _validate_directory(self, path: Path, create: bool = True) -> bool:
        """
        Validate directory exists or create it.

        Args:
            path: Directory path to validate
            create: Create directory if it doesn't exist

        Returns:
            True if directory exists or was created, False otherwise
        """
        if not path.exists():
            if create:
                path.mkdir(parents=True, exist_ok=True)
                return True
            return False
        return path.is_dir()

    def _file_exists_and_valid(self, path: Path, min_size: int = 0) -> bool:
        """
        Check if file exists and meets minimum size requirement.

        Args:
            path: File path to check
            min_size: Minimum file size in bytes (default: 0)

        Returns:
            True if file exists and meets size requirement
        """
        return path.exists() and path.stat().st_size >= min_size

    def _safe_write_staging(self, data: Any, filename: str, format: str = "jsonl") -> bool:
        """
        Safely write data to staging with error handling.

        Args:
            data: Data to write
            filename: Output filename
            format: Data format (jsonl, txt)

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            if format == "jsonl":
                self.data_manager.write_to_staging(data, filename, format="jsonl")
            elif format == "txt":
                self.data_manager.write_to_staging(data, filename, format="txt")
            else:
                raise ValueError(f"Unsupported format: {format}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write staging file {filename}: {e}")
            return False
