# Schema Versioning Guide

**Working with schema versioning system for Somali dialect classifier silver layer data.**

**Last Updated:** 2025-11-21

## Overview

This guide explains how to work with the schema versioning system for the Somali dialect classifier silver layer data.

## Understanding Schema Versions

Starting with schema v1.0 (introduced 2025-11-11), every silver dataset record includes:
- `schema_version`: The schema version (e.g., "1.0")
- `run_id`: Unique identifier linking to logs and metrics

These fields enable:
- **Provenance tracking**: Know exactly which pipeline run created each record
- **Schema evolution**: Add new fields or modify schemas over time
- **Backward compatibility**: Read and migrate old data as schemas evolve

## Checking Current Schema Version

### In Code

```python
from somali_dialect_classifier.schema import CURRENT_SCHEMA_VERSION, get_current_schema

# Get current version string
print(f"Current schema version: {CURRENT_SCHEMA_VERSION}")  # "1.0"

# Get current schema class
SchemaClass = get_current_schema()
print(f"Schema class: {SchemaClass.__name__}")  # "SchemaV1_0"
```

### In Documentation

See [silver-schema.md](../reference/silver-schema.md) for the current schema version and full field specifications.

## Validating Records

### Automatic Validation

Validation happens automatically during pipeline processing. The `base_pipeline.py` validates every record before writing to silver:

```python
# This happens automatically in BasePipeline.process()
from somali_dialect_classifier.schema import SchemaValidator

validator = SchemaValidator()
is_valid, errors = validator.validate_record(record)

if not is_valid:
    logger.warning(f"Validation failed: {errors}")
    # Record is rejected and not written to silver
```

### Manual Validation

You can manually validate records or DataFrames:

```python
from somali_dialect_classifier.schema import SchemaValidator

validator = SchemaValidator()

# Validate single record
record = {
    "id": "abc123",
    "text": "Sample text",
    "schema_version": "1.0",
    "run_id": "20250115_120000",
    # ... other fields
}

is_valid, errors = validator.validate_record(record)
if not is_valid:
    print(f"Validation errors: {errors}")

# Validate DataFrame
import pandas as pd
df = pd.DataFrame([record1, record2, record3])

all_valid, validated_df = validator.validate_dataframe(df)

# Check invalid records
if not all_valid:
    invalid_df = validated_df[~validated_df["_validation_valid"]]
    print(f"Found {len(invalid_df)} invalid records")
    print(invalid_df["_validation_errors"])
```

### Validation Report

Get detailed validation statistics:

```python
from somali_dialect_classifier.schema import SchemaValidator

validator = SchemaValidator()
all_valid, validated_df = validator.validate_dataframe(df)

report = validator.get_validation_report(validated_df)
print(f"Total records: {report['total_records']}")
print(f"Valid records: {report['valid_records']}")
print(f"Validation rate: {report['validation_rate']:.1f}%")
print(f"Error summary: {report['error_summary']}")
```

## Creating a New Schema Version (For Future Developers)

When you need to add new fields or modify the schema, follow these steps:

### Step 1: Define New Schema Version

Create a new schema class in `src/somali_dialect_classifier/schema/registry.py`:

```python
class SchemaV1_1(BaseModel):
    """
    Silver layer schema version 1.1.

    Changes from v1.0:
    - Added optional 'confidence_scores' field for quality metrics
    """
    # Copy all fields from SchemaV1_0
    id: str = Field(...)
    text: str = Field(...)
    # ... all other fields from v1.0

    # NEW FIELD
    confidence_scores: Optional[str] = Field(
        None,
        description="Quality confidence scores (JSON string)"
    )

    # Update schema_version
    schema_version: Literal["1.1"] = Field(default="1.1")

    # Keep all validators
    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        # ... validator logic
        pass

# Add to registry
SCHEMA_REGISTRY["1.1"] = SchemaV1_1

# Update current version
CURRENT_SCHEMA_VERSION = "1.1"
```

### Step 2: Create Migration

Create migration in `src/somali_dialect_classifier/schema/migrations/`:

```python
# v1_0_to_v1_1.py
from typing import Any
from .base import SchemaMigration

class MigrationV1_0toV1_1(SchemaMigration):
    """Migrate from schema v1.0 to v1.1."""

    @property
    def from_version(self) -> str:
        return "1.0"

    @property
    def to_version(self) -> str:
        return "1.1"

    @property
    def is_breaking(self) -> bool:
        return False  # Adding optional field

    def migrate_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Add confidence_scores field."""
        migrated = record.copy()
        migrated["schema_version"] = "1.1"
        migrated["confidence_scores"] = None  # Default
        return migrated
```

### Step 3: Register Migration

Add migration to `MigrationManager` in `src/somali_dialect_classifier/schema/migrations/manager.py`:

```python
from .v1_0_to_v1_1 import MigrationV1_0toV1_1

class MigrationManager:
    def __init__(self):
        self.migrations = {
            ("1.0", "1.1"): MigrationV1_0toV1_1(),
            # Future migrations...
        }
```

### Step 4: Write Tests

Create tests in `tests/schema/`:

```python
# test_migration_v1_0_to_v1_1.py
def test_migration_v1_0_to_v1_1():
    """Test migration from v1.0 to v1.1."""
    from somali_dialect_classifier.schema.migrations import MigrationManager

    manager = MigrationManager()

    # Create v1.0 record
    df_v10 = pd.DataFrame([{
        "id": "abc",
        "text": "test",
        "schema_version": "1.0",
        # ... other fields
    }])

    # Migrate
    df_v11 = manager.migrate_dataframe(df_v10, "1.0", "1.1")

    assert all(df_v11["schema_version"] == "1.1")
    assert "confidence_scores" in df_v11.columns
```

### Step 5: Update Documentation

Update `docs/reference/silver-schema.md`:
- Add version to version history table
- Document new fields
- Update examples

## Running Migrations

### Automatic Migration on Read

When reading old data, migrations can be applied automatically:

```python
from somali_dialect_classifier.schema.migrations import MigrationManager

manager = MigrationManager()

# Read old v1.0 data
df_old = pd.read_parquet("data/silver/old_data.parquet")

# Migrate to current version
df_new = manager.migrate_dataframe(
    df_old,
    from_version="1.0",
    to_version=CURRENT_SCHEMA_VERSION
)

# Write migrated data
df_new.to_parquet("data/silver/migrated_data.parquet")
```

### Batch Migration Script

For migrating entire datasets, create a script:

```python
# scripts/migrate_schema.py
from pathlib import Path
import pandas as pd
from somali_dialect_classifier.schema.migrations import MigrationManager
from somali_dialect_classifier.schema import CURRENT_SCHEMA_VERSION

def migrate_silver_dataset(silver_dir: Path, target_version: str):
    """Migrate all silver datasets to target version."""
    manager = MigrationManager()

    for parquet_file in silver_dir.rglob("*.parquet"):
        print(f"Processing {parquet_file}...")

        # Read data
        df = pd.read_parquet(parquet_file)

        # Check version
        if "schema_version" not in df.columns:
            print(f"  Skipping: no schema_version field")
            continue

        current_version = df["schema_version"].iloc[0]
        if current_version == target_version:
            print(f"  Already at v{target_version}")
            continue

        # Migrate
        print(f"  Migrating v{current_version} → v{target_version}")
        df_migrated = manager.migrate_dataframe(
            df, current_version, target_version
        )

        # Backup original
        backup_path = parquet_file.with_suffix(".parquet.bak")
        parquet_file.rename(backup_path)

        # Write migrated data
        df_migrated.to_parquet(parquet_file)
        print(f"  ✓ Migrated ({len(df_migrated)} records)")

if __name__ == "__main__":
    migrate_silver_dataset(
        Path("data/silver"),
        target_version=CURRENT_SCHEMA_VERSION
    )
```

## Schema Evolution Best Practices

### Non-Breaking Changes (Recommended)

Non-breaking changes preserve backward compatibility:
- ✅ Add optional fields
- ✅ Relax validation constraints
- ✅ Deprecate fields (but keep them)

Example: Adding optional `confidence_scores` field in v1.1

### Breaking Changes (Use Sparingly)

Breaking changes may lose data or break existing code:
- ⚠️ Remove required fields
- ⚠️ Change field types
- ⚠️ Add required fields without defaults
- ⚠️ Tighten validation constraints

Example: Making `dialect_label` required in v2.0

**When making breaking changes:**
1. Document the breaking change clearly
2. Provide migration path for existing data
3. Consider data loss implications
4. Update all downstream code

### Version Numbering

Follow semantic versioning:
- **Major version** (2.0): Breaking changes
- **Minor version** (1.1): Non-breaking additions
- **Patch version** (1.0.1): Bug fixes (if needed)

## Troubleshooting

### Validation Errors

**Problem**: Records failing validation

**Solution**: Check error messages for specific fields:

```python
is_valid, errors = validator.validate_record(record)
for error in errors:
    print(f"Field error: {error}")
```

Common errors:
- `text cannot be empty`: Text field is empty or whitespace-only
- `source must start with...`: Invalid source identifier
- `tokens cannot be negative`: Invalid token count
- `date must be in ISO 8601 format`: Invalid date format

### Migration Failures

**Problem**: Migration fails with validation errors

**Solution**: Check migration logic and schema compatibility:

```python
migration = MigrationV1_0toV1_1()
print(f"Breaking: {migration.is_breaking}")
print(f"Description: {migration.get_description()}")

# Test on single record first
test_record = {...}
migrated = migration.migrate_record(test_record)
print(f"Migrated record: {migrated}")
```

### Missing schema_version Field

**Problem**: Old data without `schema_version` field

**Solution**: Add schema version manually before validation:

```python
# Assume old data is v1.0
df["schema_version"] = "1.0"
df["run_id"] = "legacy_migration_20250115"

# Then validate
all_valid, validated_df = validator.validate_dataframe(df)
```

## Related Documentation

- [Silver Schema Reference](../reference/silver-schema.md) - Full schema specification
- [Data Pipeline Architecture](../overview/data-pipeline-architecture.md) - Overall pipeline design
- [Quality Filters](quality-filters.md) - Data quality validation

---

---

## Table of Contents

- [Overview](#overview)
- [Understanding Schema Versions](#understanding-schema-versions)
- [Checking Current Schema Version](#checking-current-schema-version)
  - [In Code](#in-code)
  - [In Documentation](#in-documentation)
- [Validating Records](#validating-records)
  - [Automatic Validation](#automatic-validation)
  - [Manual Validation](#manual-validation)
  - [Validation Report](#validation-report)
- [Creating a New Schema Version (For Future Developers)](#creating-a-new-schema-version-for-future-developers)
  - [Step 1: Define New Schema Version](#step-1-define-new-schema-version)
  - [Step 2: Create Migration](#step-2-create-migration)
  - [Step 3: Register Migration](#step-3-register-migration)
  - [Step 4: Write Tests](#step-4-write-tests)
  - [Step 5: Update Documentation](#step-5-update-documentation)
- [Running Migrations](#running-migrations)
  - [Automatic Migration on Read](#automatic-migration-on-read)
  - [Batch Migration Script](#batch-migration-script)
- [Schema Evolution Best Practices](#schema-evolution-best-practices)
  - [Non-Breaking Changes (Recommended)](#non-breaking-changes-recommended)
  - [Breaking Changes (Use Sparingly)](#breaking-changes-use-sparingly)
  - [Version Numbering](#version-numbering)
- [Troubleshooting](#troubleshooting)
  - [Validation Errors](#validation-errors)
  - [Migration Failures](#migration-failures)
  - [Missing schema_version Field](#missing-schemaversion-field)

---

**Maintainers**: Somali NLP Contributors
