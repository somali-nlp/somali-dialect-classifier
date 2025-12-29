"""
Pipeline setup utilities for BasePipeline initialization.
"""

import logging
from pathlib import Path
from typing import Optional

import requests

from ..infra.config import get_config
from ..infra.data_manager import DataManager
from ..infra.http import HTTPSessionFactory
from ..infra.logging_utils import StructuredLogger
from ..infra.security import sanitize_source_name
from ..quality.filter_engine import FilterEngine
from ..quality.record_builder import RecordBuilder
from ..schema import CURRENT_SCHEMA_VERSION
from ..schema.validation_service import ValidationService

# Import dedup module for type hints
try:
    from .dedup import DedupConfig, DedupEngine

    DEDUP_AVAILABLE = True
except ImportError:
    DEDUP_AVAILABLE = False
    DedupConfig = None
    DedupEngine = None

logger = logging.getLogger(__name__)


class PipelineSetup:
    """
    Handles pipeline initialization and dependency injection.

    Decouples setup logic from BasePipeline orchestration.
    """

    @staticmethod
    def sanitize_and_validate_source(source: str) -> str:
        """
        Sanitize source name for security.

        Args:
            source: User-provided source name

        Returns:
            Sanitized source name

        Raises:
            ValueError: If source name is invalid
        """
        try:
            return sanitize_source_name(source)
        except ValueError as e:
            raise ValueError(f"Invalid source name: {e}") from e

    @staticmethod
    def create_logger(source: str, run_id: str) -> logging.Logger:
        """
        Create structured logger for pipeline.

        Args:
            source: Source identifier
            run_id: Run identifier

        Returns:
            Logger instance
        """
        log_file = Path("logs") / f"{run_id}.log"
        structured_logger = StructuredLogger(name=source, log_file=log_file, json_format=True)
        return structured_logger.get_logger()

    @staticmethod
    def create_data_manager(
        source: str, run_id: str, data_manager: Optional[DataManager] = None
    ) -> DataManager:
        """
        Create or inject DataManager.

        Args:
            source: Source identifier
            run_id: Run identifier
            data_manager: Optional injected DataManager

        Returns:
            DataManager instance
        """
        if data_manager is not None:
            return data_manager

        config = get_config()
        base_dir = config.data.raw_dir.parent
        return DataManager(source=source, run_id=run_id, base_dir=base_dir)

    @staticmethod
    def create_filter_engine(
        filter_engine: Optional[FilterEngine] = None,
    ) -> FilterEngine:
        """
        Create or inject FilterEngine.

        Args:
            filter_engine: Optional injected FilterEngine

        Returns:
            FilterEngine instance
        """
        if filter_engine is not None:
            return filter_engine

        return FilterEngine()

    @staticmethod
    def create_record_builder(
        source: str,
        date_accessed: str,
        run_id: str,
        record_builder: Optional[RecordBuilder] = None,
    ) -> RecordBuilder:
        """
        Create or inject RecordBuilder.

        Args:
            source: Source identifier
            date_accessed: Date accessed
            run_id: Run identifier
            record_builder: Optional injected RecordBuilder

        Returns:
            RecordBuilder instance
        """
        if record_builder is not None:
            return record_builder

        return RecordBuilder(
            source=source,
            date_accessed=date_accessed,
            run_id=run_id,
            schema_version=CURRENT_SCHEMA_VERSION,
        )

    @staticmethod
    def create_validation_service(
        validation_service: Optional[ValidationService] = None,
    ) -> ValidationService:
        """
        Create or inject ValidationService.

        Args:
            validation_service: Optional injected ValidationService

        Returns:
            ValidationService instance
        """
        if validation_service is not None:
            return validation_service

        return ValidationService()

    @staticmethod
    def create_dedup_engine(dedup_engine: Optional["DedupEngine"] = None) -> Optional["DedupEngine"]:
        """
        Create DedupEngine with centralized configuration.

        Args:
            dedup_engine: Optional injected DedupEngine

        Returns:
            DedupEngine instance configured from central config, or None if dedup unavailable

        Example:
            >>> engine = PipelineSetup.create_dedup_engine()
            >>> # Uses SDC_DEDUP__* environment variables or defaults
        """
        if dedup_engine is not None:
            return dedup_engine

        if not DEDUP_AVAILABLE:
            logger.warning("DedupEngine not available (dedup module not imported)")
            return None

        # Load centralized dedup configuration
        config = get_config()
        dedup_settings = config.dedup

        # Create DedupConfig from centralized settings
        dedup_config = DedupConfig(
            hash_fields=dedup_settings.hash_fields,
            enable_minhash=dedup_settings.enable_minhash,
            similarity_threshold=dedup_settings.similarity_threshold,
            num_shards=dedup_settings.num_shards,
        )

        return DedupEngine(dedup_config)

    @staticmethod
    def create_default_http_session(
        max_retries: int = 5,
        backoff_factor: float = 0.5,
        timeout: int = 30,
        status_forcelist: Optional[list[int]] = None,
        allowed_methods: Optional[list[str]] = None,
    ) -> requests.Session:
        """
        Create HTTP session with standard retry configuration.

        Args:
            max_retries: Maximum retry attempts for failed requests
            backoff_factor: Exponential backoff multiplier
            timeout: Request timeout in seconds
            status_forcelist: HTTP status codes to retry (default: 429, 500, 502, 503, 504)
            allowed_methods: HTTP methods to retry (default: HEAD, GET, OPTIONS)

        Returns:
            Configured requests.Session with retry adapter

        Example:
            >>> session = PipelineSetup.create_default_http_session()
            >>> # Uses default retry parameters (5 retries, 0.5 backoff)

            >>> session = PipelineSetup.create_default_http_session(max_retries=3, backoff_factor=1.0)
            >>> # Custom retry configuration for scraping scenarios
        """
        if status_forcelist is None:
            status_forcelist = [429, 500, 502, 503, 504]
        if allowed_methods is None:
            allowed_methods = ["HEAD", "GET", "OPTIONS"]

        return HTTPSessionFactory.create_session(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=allowed_methods,
            timeout=timeout,
        )

    @staticmethod
    def get_directory_paths(source: str, date_accessed: str) -> tuple[Path, Path, Path]:
        """
        Get directory paths for raw, staging, processed layers.

        Args:
            source: Source identifier
            date_accessed: Date accessed

        Returns:
            Tuple of (raw_dir, staging_dir, processed_dir)
        """
        config = get_config()

        raw_dir = config.data.raw_dir / f"source={source}" / f"date_accessed={date_accessed}"
        staging_dir = (
            config.data.staging_dir / f"source={source}" / f"date_accessed={date_accessed}"
        )
        processed_dir = (
            config.data.processed_dir / f"source={source}" / f"date_processed={date_accessed}"
        )

        return raw_dir, staging_dir, processed_dir
