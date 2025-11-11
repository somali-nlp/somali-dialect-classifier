"""
ValidationService: Schema validation for pipeline records.

Responsibilities:
- Validate records against schema
- Track validation failures
- Provide detailed error messages
- Support metrics integration

Extracted from BasePipeline (P3.1 God Object Refactoring).
"""

import logging
from typing import Any, Optional

from .validator import SchemaValidator

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Validates records against schema and tracks failures.

    Decouples validation logic from pipeline orchestration.
    Provides integration with metrics tracking.

    Example:
        >>> service = ValidationService()
        >>> is_valid, errors = service.validate_record(
        ...     record={"id": "abc", "text": "hello", ...},
        ...     source="BBC-Somali"
        ... )
        >>> if not is_valid:
        ...     print(f"Validation errors: {errors}")
    """

    def __init__(self, schema_version: Optional[str] = None):
        """
        Initialize validation service.

        Args:
            schema_version: Schema version to validate against (default: current)
        """
        self.validator = SchemaValidator()
        self.schema_version = schema_version
        self.validation_failures = 0

    def validate_record(
        self,
        record: dict[str, Any],
        source: str = "",
        metrics_collector: Optional[Any] = None
    ) -> tuple[bool, list[str]]:
        """
        Validate record against schema.

        Args:
            record: Record dictionary to validate
            source: Source identifier for logging (optional)
            metrics_collector: Optional MetricsCollector for tracking failures

        Returns:
            Tuple of (is_valid, error_messages)
                - is_valid: True if record passes validation
                - error_messages: List of validation error messages (empty if valid)

        Example:
            >>> is_valid, errors = service.validate_record(
            ...     record={"id": "abc", "text": "hello", ...},
            ...     source="BBC-Somali"
            ... )
        """
        is_valid, errors = self.validator.validate_record(record, version=self.schema_version)

        if not is_valid:
            self.validation_failures += 1

            # Log validation errors with context
            if source:
                title = record.get("title", "")[:50]
                logger.warning(
                    f"Record validation failed for '{title}...' from {source}: {errors}"
                )
            else:
                logger.warning(f"Record validation failed: {errors}")

            # Record filter reason in metrics if available
            if metrics_collector is not None:
                metrics_collector.record_filter_reason("schema_validation_failed")

        return is_valid, errors

    def get_validation_errors(self, record: dict[str, Any]) -> list[str]:
        """
        Get detailed validation errors for a record.

        Args:
            record: Record dictionary to validate

        Returns:
            List of validation error messages

        Example:
            >>> errors = service.get_validation_errors(record)
            >>> for error in errors:
            ...     print(f"  - {error}")
        """
        _, errors = self.validator.validate_record(record, version=self.schema_version)
        return errors

    def get_failure_count(self) -> int:
        """
        Get total number of validation failures.

        Returns:
            Count of validation failures since initialization

        Example:
            >>> count = service.get_failure_count()
            >>> print(f"Total validation failures: {count}")
        """
        return self.validation_failures

    def reset_failures(self) -> None:
        """Reset validation failure counter (useful for testing or batch processing)."""
        self.validation_failures = 0
