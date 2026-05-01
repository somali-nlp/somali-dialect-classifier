"""
Base pipeline orchestrator with dependency injection.

Injects: DataManager, FilterEngine, RecordBuilder, ValidationService.
Subclasses implement source-specific logic (download, extract, _extract_records, _create_cleaner).
"""

import json
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..infra.config import get_config
from ..infra.data_manager import DataManager
from ..infra.disk_utils import estimate_required_space
from ..infra.logging_utils import generate_run_id
from ..infra.tracking import MLFlowTracker
from ..quality.filter_engine import FilterEngine
from ..quality.record_builder import RecordBuilder
from ..quality.script_detection import compute_cs_ratio, detect_scripts
from ..quality.silver_writer import SilverDatasetWriter
from ..quality.text_cleaners import TextCleaningPipeline
from ..schema.validation_service import ValidationService
from .data_processor import DataProcessor
from .pipeline_setup import PipelineSetup
from .raw_record import RawRecord

# Checkpoint configuration
CHECKPOINT_INTERVAL = 1000  # Records between checkpoints


class BasePipeline(DataProcessor, ABC):
    """
    Base orchestrator for data pipelines with dependency injection.
    """

    def __init__(
        self,
        source: str,
        log_frequency: int = 100,
        batch_size: Optional[int] = None,
        force: bool = False,
        run_seed: Optional[str] = None,
        data_manager: Optional[DataManager] = None,
        filter_engine: Optional[FilterEngine] = None,
        record_builder: Optional[RecordBuilder] = None,
        validation_service: Optional[ValidationService] = None,
    ):
        """Initialize pipeline with dependency injection for services."""
        self.source = PipelineSetup.sanitize_and_validate_source(source)
        self.run_id = (
            self._build_run_id_from_seed(run_seed) if run_seed else generate_run_id(self.source)
        )
        self.date_accessed = datetime.now(timezone.utc).date().isoformat()

        self.git_commit = self._get_git_commit()
        self.config_hash = self._get_config_hash()
        self.system_context = self._get_system_context()

        self.log_frequency = log_frequency
        self.batch_size = batch_size
        self.force = force
        self.metrics: Optional[Any] = None

        self.logger = PipelineSetup.create_logger(self.source, self.run_id)
        self.data_manager = PipelineSetup.create_data_manager(
            self.source, self.run_id, data_manager
        )
        self.filter_engine = PipelineSetup.create_filter_engine(filter_engine)
        self.record_builder = PipelineSetup.create_record_builder(
            self.source, self.date_accessed, self.run_id, record_builder
        )
        self.validation_service = PipelineSetup.create_validation_service(validation_service)

        if filter_engine is None:
            self._register_filters()

        self.raw_dir, self.staging_dir, self.processed_dir = PipelineSetup.get_directory_paths(
            self.source, self.date_accessed
        )

        self.text_cleaner = self._create_cleaner()
        self.silver_writer = SilverDatasetWriter()
        self.mlflow = MLFlowTracker()

        self.staging_file: Optional[Path] = None
        self.processed_file: Optional[Path] = None
        self.silver_path: Optional[Path] = None

        # Log configuration at startup
        self._log_configuration()

    def _log_configuration(self) -> None:
        """
        Log configuration values at startup with secret redaction.

        Logs all relevant config values at INFO level, ensuring secrets
        (passwords, tokens, API keys) are properly redacted.
        """
        from ..infra.security import redact_secrets

        try:
            config = get_config()

            # Build configuration dictionary with relevant values
            config_dict = {
                "data_dirs": {
                    "raw": str(config.data.raw_dir),
                    "staging": str(config.data.staging_dir),
                    "processed": str(config.data.processed_dir),
                    "silver": str(config.data.silver_dir),
                    "metrics": str(config.data.metrics_dir),
                    "reports": str(config.data.reports_dir),
                },
                "scraping": {
                    "bbc": {
                        "max_articles": config.scraping.bbc.max_articles,
                        "min_delay": config.scraping.bbc.min_delay,
                        "max_delay": config.scraping.bbc.max_delay,
                        "timeout": config.scraping.bbc.timeout,
                    },
                    "wikipedia": {
                        "batch_size": config.scraping.wikipedia.batch_size,
                        "max_articles": config.scraping.wikipedia.max_articles,
                        "timeout": config.scraping.wikipedia.timeout,
                    },
                    "huggingface": {
                        "streaming_batch_size": config.scraping.huggingface.streaming_batch_size,
                        "max_records": config.scraping.huggingface.max_records,
                        "min_length_threshold": config.scraping.huggingface.min_length_threshold,
                    },
                    "sprakbanken": {
                        "batch_size": config.scraping.sprakbanken.batch_size,
                        "max_corpora": config.scraping.sprakbanken.max_corpora,
                        "timeout": config.scraping.sprakbanken.timeout,
                    },
                    "tiktok": {
                        "apify_api_token": config.scraping.tiktok.apify_api_token,  # Will be redacted
                        "max_comments_per_video": config.scraping.tiktok.max_comments_per_video,
                    },
                },
                "database": {
                    "query_timeout": config.database.query_timeout,
                    "min_connections": config.database.min_connections,
                    "max_connections": config.database.max_connections,
                    # Password is NOT included
                },
                "logging": {
                    "level": config.logging.level,
                    "format": config.logging.format,
                },
                "pipeline": {
                    "source": self.source,
                    "run_id": self.run_id,
                    "date_accessed": self.date_accessed,
                    "batch_size": self.batch_size,
                    "force": self.force,
                    "log_frequency": self.log_frequency,
                },
            }

            # Redact secrets from configuration
            redacted_config = redact_secrets(config_dict)

            # Log configuration as formatted JSON
            self.logger.info("=" * 60)
            self.logger.info("Pipeline Configuration:")
            self.logger.info("=" * 60)
            self.logger.info(json.dumps(redacted_config, indent=2))
            self.logger.info("=" * 60)

        except Exception as e:
            # Don't fail pipeline startup if config logging fails
            self.logger.warning(f"Failed to log configuration: {e}")

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

    def _load_checkpoint(self, checkpoint_path: Path) -> int:
        """Load last processed index from checkpoint file."""
        if checkpoint_path.exists():
            try:
                data = json.loads(checkpoint_path.read_text())
                self.logger.info(f"Resuming from checkpoint: record {data['last_index']}")
                return data["last_index"]
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Corrupt checkpoint file, starting fresh: {e}")
                return 0
        return 0

    def _save_checkpoint(self, checkpoint_path: Path, index: int) -> None:
        """Save checkpoint with current progress using atomic write."""
        checkpoint_data = {
            "last_index": index,
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Atomic write: write to temp file, then rename
        try:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

            # Create temp file in same directory as checkpoint for atomic rename
            temp_fd, temp_path = tempfile.mkstemp(
                dir=checkpoint_path.parent, prefix=".checkpoint_", suffix=".tmp"
            )
            temp_file = Path(temp_path)

            try:
                # Write to temp file
                with open(temp_fd, "w", encoding="utf-8") as f:
                    json.dump(checkpoint_data, f)

                # Atomic rename
                temp_file.replace(checkpoint_path)
                self.logger.debug(f"Checkpoint saved at record {index}")
            finally:
                # Clean up temp file if rename failed
                if temp_file.exists():
                    temp_file.unlink()
        except Exception as e:
            self.logger.warning(f"Failed to save checkpoint: {e}")

    def _estimate_processing_space(self) -> int:
        """
        Estimate required disk space for processing phase.

        Subclasses can override for more accurate estimates.
        Default: 2x staging file size.

        Returns:
            Estimated bytes required
        """
        if self.staging_file and self.staging_file.exists():
            staging_size = self.staging_file.stat().st_size
            return staging_size * 2  # Processed text + silver Parquet
        # Fallback estimate
        return estimate_required_space(self.source)

    def _check_disk_space_for_processing(self) -> None:
        """
        Check disk space before processing phase.

        Raises:
            InsufficientDiskSpaceError: If insufficient space
        """
        required = self._estimate_processing_space()
        self.logger.info(
            f"Checking disk space for processing (estimated: {required / (1024**2):.0f}MB)..."
        )
        self.data_manager.ensure_disk_space(required, self.processed_dir)

    def process(self) -> Optional[Path]:
        """
        Orchestrate processing: extract→clean→filter→build→validate→write.

        Returns:
            Path to silver Parquet file, or None if no records to process
        """
        if not self.staging_file or not self.staging_file.exists():
            raise FileNotFoundError(f"Staging file not found: {self.staging_file}")
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        if self.processed_file.exists():
            if not self.force:
                self.logger.info(
                    f"Processed file exists: {self.processed_file}. Use force=True to reprocess"
                )
                return self.processed_file
            self.logger.info(f"Force reprocessing: removing {self.processed_file}")
            self.processed_file.unlink()

        # Check disk space before starting processing
        self._check_disk_space_for_processing()

        self.logger.info("\n" + "=" * 60)
        self.logger.info("PHASE 3: Text Processing & Silver Dataset Creation")
        self.logger.info("=" * 60)

        checkpoint_path, last_processed_index = self._prepare_process_run()

        try:
            with open(self.processed_file, "w", encoding="utf-8") as fout:
                records_processed, records_filtered, records = self._process_record_stream(
                    last_processed_index=last_processed_index,
                    checkpoint_path=checkpoint_path,
                    fout=fout,
                )
            self._finalize_process_run(
                records=records,
                records_processed=records_processed,
                records_filtered=records_filtered,
                checkpoint_path=checkpoint_path,
            )

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            self.mlflow.set_tags(
                {"status": "failed", "error_type": type(e).__name__, "error_message": str(e)}
            )
            raise
        finally:
            # End MLFlow run
            self.mlflow.end_run()

        return self.silver_path if self.silver_path else self.processed_file

    def _prepare_process_run(self) -> tuple[Path, int]:
        """Start tracking and load the process checkpoint."""
        self.mlflow.start_run(run_name=self.run_id)

        tags = {
            "source": self.source,
            "run_id": self.run_id,
            "git_commit": self.git_commit or "unknown",
            "config_hash": self.config_hash,
            "date_accessed": self.date_accessed,
            **self.system_context,
        }
        self.mlflow.set_tags(tags)
        self.mlflow.log_params(
            {
                "source": self.source,
                "run_id": self.run_id,
                "force": self.force,
                "batch_size": self.batch_size,
            }
        )

        checkpoint_path = self.processed_dir / f"{self.run_id}_checkpoint.json"
        last_processed_index = self._load_checkpoint(checkpoint_path)
        return checkpoint_path, last_processed_index

    def _process_record_stream(
        self,
        last_processed_index: int,
        checkpoint_path: Path,
        fout,
    ) -> tuple[int, int, list[dict]]:
        """Stream, clean, filter, validate, and batch records for writing."""
        records_processed = 0
        records_filtered = 0
        records: list[dict] = []
        current_index = 0

        for raw_record in self._extract_records():
            if current_index < last_processed_index:
                current_index += 1
                continue

            current_index += 1
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
            script_info = detect_scripts(cleaned)
            base_meta = self._get_source_metadata()
            augmented_meta = {
                **base_meta,
                "scripts": script_info["scripts"],
                "dominant_script": script_info["dominant_script"],
                "cs_ratio": compute_cs_ratio(cleaned),
            }
            record = self.record_builder.build_silver_record(
                raw_record=raw_record,
                cleaned_text=cleaned,
                filter_metadata=filter_metadata,
                source_type=self._get_source_type(),
                license_str=self._get_license(),
                domain=self._get_domain(),
                register=self._get_register(),
                language=self._get_language(),
                source_metadata=augmented_meta,
            )
            metrics = self.metrics
            is_valid, errors = self.validation_service.validate_record(record, self.source, metrics)
            if not is_valid:
                records_filtered += 1
                continue

            records.append(record)
            records_processed += 1
            self._mark_url_processed(raw_record, record)

            if records_processed % self.log_frequency == 0:
                self.logger.info(f"Progress: {records_processed} records processed...")

            if current_index % CHECKPOINT_INTERVAL == 0:
                self._save_checkpoint(checkpoint_path, current_index)

            if self.batch_size and len(records) >= self.batch_size:
                self._write_batch(records)
                records = []

        return records_processed, records_filtered, records

    def _finalize_process_run(
        self,
        records: list[dict],
        records_processed: int,
        records_filtered: int,
        checkpoint_path: Path,
    ) -> None:
        """Flush final outputs, export metrics, and mark the run successful."""
        self._log_processing_summary(records_processed, records_filtered)
        self._write_final_batch(records)
        self._export_metrics(records_processed, records_filtered)

        quality_pass_rate = 0.0
        if records_processed + records_filtered > 0:
            quality_pass_rate = records_processed / (records_processed + records_filtered)

        self.mlflow.log_metrics(
            {
                "records_processed": records_processed,
                "records_written": records_processed,
                "records_filtered": records_filtered,
                "quality_pass_rate": quality_pass_rate,
            }
        )
        self.mlflow.set_tag("status", "success")
        checkpoint_path.unlink(missing_ok=True)
        self.logger.info("Pipeline completed successfully, checkpoint removed")

    def _record_filter_metric(self, filter_reason: str) -> None:
        """Record filter reason in metrics if available."""
        if self.metrics is not None:
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
        if self.metrics is not None:
            # Update metrics with processing stats
            self.metrics.increment("urls_processed", records_processed)
            self.metrics.increment("records_written", records_processed)
            self.metrics.increment("records_filtered", records_filtered)

            # Export final metrics after processing
            metrics_path = Path("data/metrics") / f"{self.run_id}_processing.json"
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            self.metrics.export_json(metrics_path)
            self.logger.info(f"Processing metrics exported: {metrics_path}")

            # Log metrics to MLFlow
            self.mlflow.log_metrics(
                {
                    "records_processed": records_processed,
                    "records_written": records_processed,
                    "records_filtered": records_filtered,
                }
            )
            self.mlflow.log_artifact(str(metrics_path))

            # Generate final quality report with complete stats
            from ..infra.metrics import QualityReporter

            report_path = Path("data/reports") / f"{self.run_id}_final_quality_report.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            QualityReporter(self.metrics).generate_markdown_report(report_path)
            self.logger.info(f"Final quality report: {report_path}")

    def _write_batch(self, records: list) -> None:
        """Write batch of records to silver dataset."""
        if records:
            self.logger.info(f"Writing batch of {len(records)} records...")
            silver_path = self.silver_writer.write(
                records=records,
                source=self.source,
                date_accessed=self.date_accessed,
                run_id=self.run_id,
            )
            if silver_path:
                self.silver_path = silver_path

    def save(self, processed_data: str) -> None:
        """Save processed data (no-op: handled by process() via SilverDatasetWriter)."""
        pass

    def _build_run_id_from_seed(self, run_seed: str) -> str:
        """
        Build a run_id using a shared orchestrator seed when provided.

        Supports seeds like:
          - run_YYYYMMDD_HHMMSS_uuid
          - YYYYMMDD_HHMMSS_uuid
        Falls back to generate_run_id if parsing fails.
        """
        try:
            seed = run_seed
            if seed.startswith("run_"):
                seed = seed[len("run_") :]
            parts = seed.split("_")
            if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
                timestamp = f"{parts[0]}_{parts[1]}"
                unique = parts[2]
                return f"{timestamp}_{self.source}_{unique}"
        except Exception:
            pass
        return generate_run_id(self.source)

    def _get_config_hash(self) -> str:
        """Generate hash of current configuration state."""
        import hashlib
        import logging

        try:
            config = get_config()
            if hasattr(config, "model_dump_json"):
                config_str = config.model_dump_json()
            else:
                from dataclasses import asdict

                config_str = json.dumps(asdict(config), default=str, sort_keys=True)

            if not isinstance(config_str, (str, bytes)):
                raise TypeError(f"config serialisation returned {type(config_str).__name__}")

            payload = config_str.encode("utf-8") if isinstance(config_str, str) else config_str
            return hashlib.sha256(payload).hexdigest()[:12]
        except Exception as e:
            # Called from __init__ before self.logger is wired up; fall back to a
            # module-level logger so a mocked/partial config cannot wedge the
            # constructor with AttributeError.
            logging.getLogger(__name__).warning("Failed to hash config: %s", e)
            return "unknown"

    def _get_system_context(self) -> dict[str, str]:
        """Get system context (hostname, OS, python version)."""
        import platform
        import socket
        import sys

        return {
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
        }

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=Path(__file__).parent.parent.parent.parent,
            )
            return result.stdout.strip()
        except Exception:
            return None

    def run(self) -> Optional[Path]:
        """
        Template method: download → extract → process.

        Each phase may return None to signal "nothing to do" — Wikipedia's
        download() returns None on 304 Not Modified, TikTok's download()
        returns None when every input video URL is already in the ledger as
        processed, extract() returns None when ledger-level dedup empties
        the article set. We must short-circuit on None at each step or we
        leak paid API calls and divide-by-zero in the empty case.
        """
        if self.download() is None:
            self.logger.info("Pipeline short-circuit at download (no work to do)")
            return None
        if self.extract() is None:
            self.logger.info("Pipeline short-circuit at extract (no work to do)")
            return None
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
            reverse=True,
        )

        for old_file in raw_files[keep_n:]:
            try:
                old_file.unlink()
                self.logger.debug(f"Cleaned up old raw file: {old_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to delete {old_file.name}: {e}")

    def _compute_file_checksum(self, filepath: Path, algorithm: str = "sha256") -> str:
        """Compute file checksum (delegates to DataManager)."""
        return self.data_manager.compute_file_checksum(filepath, algorithm)

    def _export_stage_metrics(self, stage: str):
        """
        Export metrics for a pipeline stage.

        Args:
            stage: Pipeline stage name (discovery, extraction, processing)
        """
        if self.metrics is None:
            return

        try:
            config = get_config()
            metrics_path = config.data.metrics_dir / f"{self.run_id}_{stage}.json"

            self.metrics.export_json(output_path=metrics_path)

            self.logger.info(f"Exported {stage} metrics: {metrics_path}")
        except AttributeError as e:
            # Expected in test environments where metrics may be None
            self.logger.debug(f"Metrics not available (test environment): {e}")
        except Exception as e:
            # Unexpected error - should be visible
            self.logger.warning(f"Failed to export {stage} metrics: {e}")
            # Track failure for monitoring
            if self.metrics:
                try:
                    self.metrics.increment("metrics_export_failed")
                except Exception:
                    pass  # Don't fail on metric tracking failure

    def _generate_quality_report(self, stage: str):
        """
        Generate quality report for a pipeline stage.

        Args:
            stage: Pipeline stage name (discovery, extraction, processing)
        """
        if self.metrics is None:
            return

        from ..infra.metrics import QualityReporter

        config = get_config()
        report_path = config.data.reports_dir / f"{self.run_id}_{stage}_quality_report.md"

        QualityReporter(self.metrics).generate_markdown_report(report_path)

        self.logger.info(f"Generated quality report: {report_path}")

