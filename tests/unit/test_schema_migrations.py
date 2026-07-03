"""Unit tests for somdialc.schema.migrations.

Exercises SchemaMigration's shared migrate_dataframe()/validate_migration()
logic through the concrete MigrationV1_0toV1_1 example migration.
"""

import pandas as pd

from somdialc.schema.migrations.v1_0_to_v1_1 import MigrationV1_0toV1_1


class TestMigrationV1_0toV1_1Properties:
    def test_version_properties(self):
        migration = MigrationV1_0toV1_1()
        assert migration.from_version == "1.0"
        assert migration.to_version == "1.1"
        assert migration.is_breaking is False

    def test_get_description(self):
        migration = MigrationV1_0toV1_1()
        assert migration.get_description() == "Migration v1.0 → v1.1 (non-breaking)"


class TestMigrateRecord:
    def test_adds_confidence_scores_and_bumps_version(self):
        migration = MigrationV1_0toV1_1()
        record = {"id": "abc", "schema_version": "1.0", "text": "hello"}

        migrated = migration.migrate_record(record)

        assert migrated["schema_version"] == "1.1"
        assert migrated["confidence_scores"] is None
        assert migrated["text"] == "hello"

    def test_does_not_mutate_original_record(self):
        migration = MigrationV1_0toV1_1()
        record = {"id": "abc", "schema_version": "1.0"}

        migration.migrate_record(record)

        assert record["schema_version"] == "1.0"
        assert "confidence_scores" not in record


class TestMigrateDataframe:
    def test_migrates_all_records(self):
        migration = MigrationV1_0toV1_1()
        df = pd.DataFrame(
            [
                {"id": "1", "schema_version": "1.0", "text": "a"},
                {"id": "2", "schema_version": "1.0", "text": "b"},
            ]
        )

        migrated = migration.migrate_dataframe(df)

        assert len(migrated) == 2
        assert all(migrated["schema_version"] == "1.1")
        assert all(migrated["confidence_scores"].isna())

    def test_raises_on_unexpected_source_version(self):
        migration = MigrationV1_0toV1_1()
        df = pd.DataFrame([{"id": "1", "schema_version": "2.0"}])

        import pytest

        with pytest.raises(ValueError, match="Cannot migrate"):
            migration.migrate_dataframe(df)

    def test_works_without_schema_version_column(self):
        migration = MigrationV1_0toV1_1()
        df = pd.DataFrame([{"id": "1", "text": "no version column"}])

        migrated = migration.migrate_dataframe(df)

        assert len(migrated) == 1
        assert migrated.iloc[0]["schema_version"] == "1.1"


class TestValidateMigration:
    def test_valid_non_breaking_migration(self):
        migration = MigrationV1_0toV1_1()
        original = pd.DataFrame([{"id": "1", "schema_version": "1.0"}])
        migrated = migration.migrate_dataframe(original)

        assert migration.validate_migration(original, migrated) is True

    def test_empty_migrated_dataframe_is_invalid(self):
        migration = MigrationV1_0toV1_1()
        original = pd.DataFrame([{"id": "1", "schema_version": "1.0"}])
        empty = pd.DataFrame()

        assert migration.validate_migration(original, empty) is False

    def test_record_count_mismatch_invalid_for_non_breaking(self):
        migration = MigrationV1_0toV1_1()
        original = pd.DataFrame(
            [
                {"id": "1", "schema_version": "1.1"},
                {"id": "2", "schema_version": "1.1"},
            ]
        )
        migrated = pd.DataFrame([{"id": "1", "schema_version": "1.1"}])

        assert migration.validate_migration(original, migrated) is False

    def test_missing_schema_version_column_invalid(self):
        migration = MigrationV1_0toV1_1()
        original = pd.DataFrame([{"id": "1"}])
        migrated = pd.DataFrame([{"id": "1"}])

        assert migration.validate_migration(original, migrated) is False

    def test_wrong_schema_version_value_invalid(self):
        migration = MigrationV1_0toV1_1()
        original = pd.DataFrame([{"id": "1", "schema_version": "1.0"}])
        migrated = pd.DataFrame([{"id": "1", "schema_version": "1.0"}])

        assert migration.validate_migration(original, migrated) is False
