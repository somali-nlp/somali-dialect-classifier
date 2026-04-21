"""
Example migration: v1.0 → v1.1

Hypothetical change: Add optional 'confidence_scores' field for quality metrics

NOTE: This is an EXAMPLE for future use. Not needed now since we're starting fresh at v1.0.
      This demonstrates how to write a migration when the time comes.
"""

from typing import Any

from .base import SchemaMigration


class MigrationV1_0toV1_1(SchemaMigration):
    """
    Migrate from schema v1.0 to v1.1.

    Changes in v1.1:
    - Add optional 'confidence_scores' field (JSON string with language_confidence, quality_confidence, etc.)
    - Non-breaking: existing records get empty confidence scores
    """

    @property
    def from_version(self) -> str:
        return "1.0"

    @property
    def to_version(self) -> str:
        return "1.1"

    @property
    def is_breaking(self) -> bool:
        return False  # Adding optional field is non-breaking

    def migrate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Add confidence_scores field with empty default.

        Args:
            record: Record in v1.0 schema

        Returns:
            Record in v1.1 schema
        """
        # Copy record to avoid mutation
        migrated = record.copy()

        # Update schema version
        migrated["schema_version"] = self.to_version

        # Add new optional field (will be populated by future processing)
        migrated["confidence_scores"] = None  # Placeholder, will be computed later

        return migrated
