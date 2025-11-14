"""
Pipeline setup utilities for BasePipeline initialization.

Extracted from BasePipeline (P3.1 God Object Refactoring) to reduce line count.
"""

import logging
from pathlib import Path
from typing import Optional

from ..config import get_config
from ..data import DataManager
from ..pipeline.filter_engine import FilterEngine
from ..schema import CURRENT_SCHEMA_VERSION
from ..schema.validation_service import ValidationService
from ..utils.logging_utils import StructuredLogger
from ..utils.security import sanitize_source_name
from .record_builder import RecordBuilder

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
        structured_logger = StructuredLogger(
            name=source, log_file=log_file, json_format=True
        )
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

        raw_dir = (
            config.data.raw_dir
            / f"source={source}"
            / f"date_accessed={date_accessed}"
        )
        staging_dir = (
            config.data.staging_dir
            / f"source={source}"
            / f"date_accessed={date_accessed}"
        )
        processed_dir = (
            config.data.processed_dir
            / f"source={source}"
            / f"date_processed={date_accessed}"
        )

        return raw_dir, staging_dir, processed_dir
