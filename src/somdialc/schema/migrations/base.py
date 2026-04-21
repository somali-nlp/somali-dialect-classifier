"""
Base class for schema migrations.

Future migrations (v1.0 → v1.1, v1.1 → v2.0) will inherit from this.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class SchemaMigration(ABC):
    """
    Base class for schema migrations.

    Subclasses implement specific migrations between versions.
    """

    @property
    @abstractmethod
    def from_version(self) -> str:
        """Source schema version."""
        pass

    @property
    @abstractmethod
    def to_version(self) -> str:
        """Target schema version."""
        pass

    @property
    @abstractmethod
    def is_breaking(self) -> bool:
        """
        Is this a breaking change?

        Breaking changes:
        - Removing required fields
        - Changing field types
        - Adding required fields without defaults

        Non-breaking changes:
        - Adding optional fields
        - Deprecating fields (but keeping them)
        - Relaxing validation constraints
        """
        pass

    @abstractmethod
    def migrate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Migrate a single record from source to target schema.

        Args:
            record: Record in source schema

        Returns:
            Record in target schema

        Raises:
            ValueError: If record cannot be migrated
        """
        pass

    def migrate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Migrate entire DataFrame from source to target schema.

        Args:
            df: DataFrame in source schema

        Returns:
            DataFrame in target schema

        Raises:
            ValueError: If DataFrame cannot be migrated
        """
        logger.info(f"Migrating {len(df)} records from v{self.from_version} to v{self.to_version}")

        # Check source schema version
        if "schema_version" in df.columns:
            versions = df["schema_version"].unique()
            if len(versions) > 1:
                logger.warning(
                    f"Multiple schema versions in DataFrame: {versions}. "
                    f"Expected only v{self.from_version}"
                )
            elif versions[0] != self.from_version:
                raise ValueError(
                    f"Cannot migrate: expected v{self.from_version}, got v{versions[0]}"
                )

        migrated_records = []
        failed_count = 0

        for idx, row in df.iterrows():
            try:
                migrated = self.migrate_record(row.to_dict())
                migrated_records.append(migrated)
            except Exception as e:
                logger.error(f"Failed to migrate record at index {idx}: {e}")
                failed_count += 1
                # Optionally: skip or fail fast based on strategy
                # For now, we skip failed records

        if failed_count > 0:
            logger.warning(
                f"Migration completed with {failed_count} failures. "
                f"Successfully migrated {len(migrated_records)}/{len(df)} records"
            )

        return pd.DataFrame(migrated_records)

    def validate_migration(self, original_df: pd.DataFrame, migrated_df: pd.DataFrame) -> bool:
        """
        Validate migration was successful.

        Args:
            original_df: Original data before migration
            migrated_df: Migrated data

        Returns:
            True if migration valid, False otherwise
        """
        # Basic checks
        if len(migrated_df) == 0:
            logger.error("Migration produced empty DataFrame")
            return False

        # Check record count (allow for some loss if migration is breaking)
        if self.is_breaking:
            # Breaking migrations may lose records
            if len(migrated_df) < len(original_df) * 0.9:
                logger.error(
                    f"Migration lost too many records: "
                    f"{len(original_df)} → {len(migrated_df)} "
                    f"(> 10% loss)"
                )
                return False
        else:
            # Non-breaking migrations should preserve all records
            if len(migrated_df) != len(original_df):
                logger.error(
                    f"Non-breaking migration changed record count: "
                    f"{len(original_df)} → {len(migrated_df)}"
                )
                return False

        # Ensure schema_version updated
        if "schema_version" not in migrated_df.columns:
            logger.error("Migrated DataFrame missing schema_version column")
            return False

        if not all(migrated_df["schema_version"] == self.to_version):
            logger.error(
                f"Schema version not updated correctly. "
                f"Expected all v{self.to_version}, got: "
                f"{migrated_df['schema_version'].unique()}"
            )
            return False

        logger.info("Migration validation passed")
        return True

    def get_description(self) -> str:
        """
        Get human-readable description of migration.

        Returns:
            Migration description string
        """
        return (
            f"Migration v{self.from_version} → v{self.to_version} "
            f"({'breaking' if self.is_breaking else 'non-breaking'})"
        )
