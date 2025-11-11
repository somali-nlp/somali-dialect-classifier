"""
Schema Migration Manager.

Handles running migrations and tracking migration status.
"""

import logging
from typing import Optional

import pandas as pd

from .base import SchemaMigration

# Future imports (when migrations are created):
# from .v1_0_to_v1_1 import MigrationV1_0toV1_1
# from .v1_1_to_v2_0 import MigrationV1_1toV2_0

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Manages schema migrations.

    Provides:
    - Migration registry
    - Migration path finding (single and multi-hop)
    - DataFrame migration execution
    """

    def __init__(self):
        """Initialize migration manager with registry."""
        # Migration registry (to be populated as migrations are created)
        # Key: (from_version, to_version) tuple
        # Value: Migration instance
        self.migrations: dict[tuple[str, str], SchemaMigration] = {
            # Future migrations will be registered here:
            # ("1.0", "1.1"): MigrationV1_0toV1_1(),
            # ("1.1", "2.0"): MigrationV1_1toV2_0(),
        }

    def register_migration(self, migration: SchemaMigration) -> None:
        """
        Register a migration.

        Args:
            migration: Migration instance to register
        """
        key = (migration.from_version, migration.to_version)
        if key in self.migrations:
            logger.warning(
                f"Overwriting existing migration {migration.from_version} → "
                f"{migration.to_version}"
            )
        self.migrations[key] = migration
        logger.debug(f"Registered migration: {migration.get_description()}")

    def get_migration(
        self, from_version: str, to_version: str
    ) -> Optional[SchemaMigration]:
        """
        Get direct migration between versions.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            Migration instance if exists, None otherwise
        """
        return self.migrations.get((from_version, to_version))

    def get_migration_path(
        self, from_version: str, to_version: str
    ) -> list[SchemaMigration]:
        """
        Get sequence of migrations needed to go from one version to another.

        Uses BFS to find shortest migration path.

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            List of migrations to apply in sequence

        Raises:
            ValueError: If no migration path exists
        """
        if from_version == to_version:
            return []

        # Check for direct migration first
        direct = self.get_migration(from_version, to_version)
        if direct:
            return [direct]

        # BFS to find shortest path
        from collections import deque

        queue = deque([(from_version, [])])
        visited = {from_version}

        while queue:
            current_version, path = queue.popleft()

            # Find all migrations from current version
            for (src, dst), migration in self.migrations.items():
                if src == current_version and dst not in visited:
                    new_path = path + [migration]

                    if dst == to_version:
                        # Found path to target
                        return new_path

                    queue.append((dst, new_path))
                    visited.add(dst)

        # No path found
        raise ValueError(
            f"No migration path found from v{from_version} to v{to_version}. "
            f"Available migrations: {list(self.migrations.keys())}"
        )

    def migrate_dataframe(
        self, df: pd.DataFrame, from_version: str, to_version: str
    ) -> pd.DataFrame:
        """
        Migrate DataFrame through necessary migrations.

        Args:
            df: DataFrame to migrate
            from_version: Current schema version
            to_version: Target schema version

        Returns:
            Migrated DataFrame

        Raises:
            ValueError: If migration fails or no path exists
        """
        if from_version == to_version:
            logger.info("No migration needed (same version)")
            return df

        # Get migration path
        migrations = self.get_migration_path(from_version, to_version)

        logger.info(
            f"Migrating DataFrame: v{from_version} → v{to_version} "
            f"({len(migrations)} step(s))"
        )

        # Apply migrations in sequence
        current_df = df.copy()
        for migration in migrations:
            logger.info(f"Applying: {migration.get_description()}")

            # Warn if breaking change
            if migration.is_breaking:
                logger.warning(
                    f"Breaking migration: {migration.from_version} → "
                    f"{migration.to_version}. Some data may be lost."
                )

            # Perform migration
            migrated_df = migration.migrate_dataframe(current_df)

            # Validate migration
            if not migration.validate_migration(current_df, migrated_df):
                raise ValueError(
                    f"Migration validation failed: {migration.from_version} → "
                    f"{migration.to_version}"
                )

            current_df = migrated_df

        logger.info(
            f"Migration complete: {len(df)} → {len(current_df)} records "
            f"(v{from_version} → v{to_version})"
        )

        return current_df

    def list_migrations(self) -> list[tuple[str, str, bool]]:
        """
        List all registered migrations.

        Returns:
            List of tuples (from_version, to_version, is_breaking)
        """
        return [
            (m.from_version, m.to_version, m.is_breaking)
            for m in self.migrations.values()
        ]

    def get_available_versions(self) -> set[str]:
        """
        Get all schema versions that have migrations (source or target).

        Returns:
            Set of version strings
        """
        versions = set()
        for from_v, to_v in self.migrations.keys():
            versions.add(from_v)
            versions.add(to_v)
        return versions
