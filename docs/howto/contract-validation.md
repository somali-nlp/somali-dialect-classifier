# Contract Validation Guide

**Comprehensive guide to ingestion output contract validation and schema enforcement.**

**Last Updated:** 2025-12-29

---

## Table of Contents

- [Overview](#overview)
- [Ingestion Output Contract Schema](#ingestion-output-contract-schema)
- [CLI Usage: somali-validate-silver](#cli-usage-somali-validate-silver)
- [Programmatic Validation Examples](#programmatic-validation-examples)
- [Schema Versioning](#schema-versioning)
- [Validation Error Troubleshooting](#validation-error-troubleshooting)
- [Best Practices](#best-practices)
- [Related Documentation](#related-documentation)

---

## Overview

The **Ingestion Output Contract** (IngestionOutputV1) defines the schema that all records MUST conform to when written to silver Parquet files. This contract ensures data quality and consistency across all pipeline stages.

### Key Features

- **Strict fail-fast validation**: No patching or defaulting of invalid records
- **8 required fields**: Enforces provenance tracking and deduplication
- **Schema versioning**: Enables future schema evolution and migration
- **CLI tool**: `somali-validate-silver` for automated validation
- **Programmatic API**: Python functions for custom validation workflows

### Why Contracts Matter

Without contracts, downstream systems (preprocessing, model training) cannot trust the data structure:

**Without Contract** ❌:
```python
# Unsafe - might fail at runtime
text = record['text']  # KeyError if missing
tokens = record.get('tokens', 0)  # Silent default, wrong assumptions
```

**With Contract** ✅:
```python
# Safe - validated before storage
is_valid, errors = validate_ingestion_output(record)
if not is_valid:
    raise ValidationError(f"Invalid record: {errors}")

# Now safe to use
text = record['text']  # Guaranteed to exist
tokens = record['tokens']  # Guaranteed to be int >= 0
```

---

## Ingestion Output Contract Schema

### Required Fields (8 total)

All records written to silver Parquet files **MUST** include these fields with non-null values:

| Field | Type | Description | Validation Rules |
|-------|------|-------------|------------------|
| `id` | str | Unique identifier | Non-empty string, globally unique |
| `text` | str | Cleaned text content | Non-empty string, whitespace trimmed |
| `source` | str | Source identifier | Non-empty string (e.g., "wikipedia-somali") |
| `run_id` | str | Pipeline run identifier | Non-empty string (e.g., "20251229_100000_wikipedia") |
| `schema_version` | str | Schema version | Must be exactly "1.0" |
| `tokens` | int | Token count | Integer >= 0 |
| `text_hash` | str | Content hash for dedup | Non-empty SHA256 hash string |
| `linguistic_register` | str | Formality level | Must be "formal", "informal", or "colloquial" |

**Note**: `linguistic_register` is the canonical field name in the contract. In Parquet storage, it's stored as `register` due to PyArrow schema constraints. The validation accepts both names for compatibility.

### Optional Fields

These fields MAY be present depending on the data source:

| Field | Type | Description |
|-------|------|-------------|
| `topic` | str | Content category (if inferred) |
| `detected_lang` | str | Language detection result (ISO 639 code) |
| `lang_confidence` | float | Language confidence score (0.0-1.0) |
| `url` | str | Source URL (for web-based sources) |
| `timestamp` | str | Record creation timestamp (ISO 8601) |

### Example Valid Record

```json
{
  "id": "abc123def456",
  "text": "Soomaaliya waa dal ku yaalla geeska Afrika",
  "source": "wikipedia-somali",
  "run_id": "20251229_100000_wikipedia_abc123",
  "schema_version": "1.0",
  "tokens": 8,
  "text_hash": "5f3a8b9c2d1e0f4a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
  "linguistic_register": "formal",
  "topic": "geography",
  "detected_lang": "so",
  "lang_confidence": 0.95,
  "url": "https://so.wikipedia.org/wiki/Soomaaliya",
  "timestamp": "2025-12-29T10:00:00Z"
}
```

### Example Invalid Records

**Missing required field**:
```json
{
  "id": "abc123",
  "text": "Sample text",
  "source": "wikipedia-somali"
  // ERROR: Missing run_id, schema_version, tokens, text_hash, linguistic_register
}
```

**Invalid schema_version**:
```json
{
  "id": "abc123",
  "text": "Sample text",
  "source": "wikipedia-somali",
  "run_id": "20251229_100000",
  "schema_version": "1.1",  // ERROR: Must be exactly "1.0"
  "tokens": 2,
  "text_hash": "hash123",
  "linguistic_register": "formal"
}
```

**Invalid linguistic_register**:
```json
{
  "id": "abc123",
  "text": "Sample text",
  "source": "wikipedia-somali",
  "run_id": "20251229_100000",
  "schema_version": "1.0",
  "tokens": 2,
  "text_hash": "hash123",
  "linguistic_register": "casual"  // ERROR: Must be formal, informal, or colloquial
}
```

---

## CLI Usage: somali-validate-silver

The `somali-validate-silver` command validates silver Parquet files against the contract.

### Basic Usage

```bash
# Validate all silver datasets
somali-validate-silver --input data/processed/silver/

# Validate specific source
somali-validate-silver --input data/processed/silver/source=Wikipedia-Somali/

# Validate specific partition
somali-validate-silver --input data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-12-29/
```

### Command Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input` | `-i` | Path to Parquet file or directory | (required) |
| `--fail-fast` | | Stop on first validation error | False |
| `--source` | `-s` | Filter by source identifier | None (all sources) |
| `--verbose` | `-v` | Show detailed error messages | False |
| `--output` | `-o` | Write validation results to JSON file | None (stdout) |

### Examples

**Validate with detailed errors**:
```bash
somali-validate-silver \
  --input data/processed/silver/ \
  --verbose
```

**Fail fast on first error**:
```bash
somali-validate-silver \
  --input data/processed/silver/ \
  --fail-fast
```

**Filter by source**:
```bash
somali-validate-silver \
  --input data/processed/silver/ \
  --source Wikipedia-Somali
```

**Export validation report**:
```bash
somali-validate-silver \
  --input data/processed/silver/ \
  --output validation_report.json
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All records valid |
| 1 | Validation errors found |
| 2 | System error (file not found, permission denied, etc.) |

### Output Format

**Console output**:
```
Validating: data/processed/silver/
Fail-fast mode: False

Validating all partitions in directory...

================================================================================
VALIDATION RESULTS
================================================================================

✓ PASS source=Wikipedia-Somali/date_accessed=2025-12-29/
  Valid: 15234, Invalid: 0

✗ FAIL source=BBC-Somali/date_accessed=2025-12-29/
  Valid: 498, Invalid: 2
  Errors:
    - Record 100 (id=abc123): Field 'linguistic_register' has invalid value: 'neutral' (must be one of ['colloquial', 'formal', 'informal'])
    - Record 245 (id=def456): Field 'tokens' has invalid value: -5 (must be >= 0)

================================================================================
OVERALL SUMMARY
================================================================================
Total partitions: 2
Total valid records: 15732
Total invalid records: 2

✗ Validation FAILED: 2 invalid records found

Error type distribution:
   1x Field 'linguistic_register' has invalid value: 'neutral' (must be one of ['colloquial', 'formal', 'informal'])
   1x Field 'tokens' has invalid value: -5 (must be >= 0)
```

**JSON output** (`--output validation_report.json`):
```json
{
  "summary": {
    "total_partitions": 2,
    "total_valid": 15732,
    "total_invalid": 2
  },
  "partitions": {
    "source=Wikipedia-Somali/date_accessed=2025-12-29/": {
      "valid": 15234,
      "invalid": 0,
      "errors": []
    },
    "source=BBC-Somali/date_accessed=2025-12-29/": {
      "valid": 498,
      "invalid": 2,
      "errors": [
        {
          "record_index": 100,
          "record_id": "abc123",
          "errors": [
            "Field 'linguistic_register' has invalid value: 'neutral' (must be one of ['colloquial', 'formal', 'informal'])"
          ]
        },
        {
          "record_index": 245,
          "record_id": "def456",
          "errors": [
            "Field 'tokens' has invalid value: -5 (must be >= 0)"
          ]
        }
      ]
    }
  }
}
```

---

## Programmatic Validation Examples

### Basic Validation

```python
from somali_dialect_classifier.contracts.ingestion_output import validate_ingestion_output

# Create test record
record = {
    "id": "abc123",
    "text": "Soomaaliya waa dal ku yaalla geeska Afrika",
    "source": "wikipedia-somali",
    "run_id": "20251229_100000_wikipedia",
    "schema_version": "1.0",
    "tokens": 8,
    "text_hash": "5f3a8b9c2d1e0f4a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
    "linguistic_register": "formal"
}

# Validate
is_valid, errors = validate_ingestion_output(record)

if is_valid:
    print("✓ Record is valid")
else:
    print(f"✗ Validation failed: {'; '.join(errors)}")
```

### Validate Parquet File

```python
from pathlib import Path
from somali_dialect_classifier.preprocessing.validator import validate_silver_parquet

# Validate entire Parquet partition
silver_path = Path("data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-12-29/")
valid_count, invalid_count, errors = validate_silver_parquet(silver_path, fail_fast=False)

print(f"Valid: {valid_count}, Invalid: {invalid_count}")

if invalid_count > 0:
    print("\nError details:")
    for err in errors[:5]:  # Show first 5 errors
        print(f"  Record {err['record_index']} (id={err['record_id']}): {'; '.join(err['errors'])}")
```

### Validate Directory

```python
from pathlib import Path
from somali_dialect_classifier.preprocessing.validator import validate_silver_directory

# Validate all partitions in directory
silver_dir = Path("data/processed/silver/")
results = validate_silver_directory(silver_dir, fail_fast=False, source_filter="Wikipedia-Somali")

# Process results
for partition_path, (valid, invalid, errors) in results.items():
    status = "✓ PASS" if invalid == 0 else "✗ FAIL"
    print(f"{status} {partition_path}: Valid={valid}, Invalid={invalid}")
```

### Custom Validation Logic

```python
from somali_dialect_classifier.contracts.ingestion_output import (
    validate_ingestion_output,
    REQUIRED_FIELDS,
    VALID_REGISTERS
)

def validate_with_custom_rules(record: dict) -> tuple[bool, list[str]]:
    """Validate record with additional custom rules."""
    # First, run standard validation
    is_valid, errors = validate_ingestion_output(record)

    if not is_valid:
        return is_valid, errors

    # Add custom validation rules
    custom_errors = []

    # Rule 1: Text must be at least 10 tokens
    if record.get('tokens', 0) < 10:
        custom_errors.append("Text too short: must be at least 10 tokens")

    # Rule 2: Formal register should have high language confidence
    if record.get('linguistic_register') == 'formal':
        lang_conf = record.get('lang_confidence', 0.0)
        if lang_conf < 0.7:
            custom_errors.append(
                f"Formal text should have high language confidence (got {lang_conf}, expected >= 0.7)"
            )

    return (len(custom_errors) == 0, custom_errors)

# Use custom validation
record = {...}  # Your record
is_valid, errors = validate_with_custom_rules(record)
```

---

## Schema Versioning

### Current Version: 1.0

The current schema version is `"1.0"`. All records MUST have `schema_version` field set to exactly `"1.0"`.

### Version Evolution Strategy

Schema versions follow **semantic versioning**:

- **Major version** (1.x → 2.x): Breaking changes requiring migration scripts
- **Minor version** (1.0 → 1.1): Backward-compatible additions (new optional fields only)

### Future Version Examples

**v1.1 (minor, backward-compatible)**:
```python
# Adds new optional fields, existing records still valid
{
    "schema_version": "1.1",
    # ... all v1.0 fields ...
    "quality_score": 0.85,  # NEW optional field
    "dialect_hints": ["sports", "news"]  # NEW optional field
}
```

**v2.0 (major, breaking change)**:
```python
# Breaking change: splits linguistic_register
{
    "schema_version": "2.0",
    # ... other fields ...
    "register": "formal",  # CHANGED from linguistic_register
    "formality_score": 0.9  # NEW required field
}
```

### Migration Scripts

When breaking changes occur (v2.0), migration scripts will convert old records:

```python
# Example migration: v1.0 → v2.0
def migrate_v1_to_v2(record_v1: dict) -> dict:
    """Migrate record from schema v1.0 to v2.0."""
    record_v2 = record_v1.copy()

    # Update schema version
    record_v2['schema_version'] = '2.0'

    # Split linguistic_register
    register = record_v1['linguistic_register']
    record_v2['register'] = register

    # Infer formality_score from register
    formality_map = {'formal': 0.9, 'informal': 0.5, 'colloquial': 0.2}
    record_v2['formality_score'] = formality_map[register]

    # Remove old field
    del record_v2['linguistic_register']

    return record_v2
```

---

## Validation Error Troubleshooting

### Common Errors and Solutions

#### Error: Missing required field

**Error Message**:
```
Field 'run_id' is missing (required)
```

**Cause**: Pipeline not setting required provenance field

**Solution**: Update pipeline to set `run_id`:

```python
from somali_dialect_classifier.infra.tracking import generate_run_id

run_id = generate_run_id("wikipedia")
record['run_id'] = run_id
```

#### Error: Invalid linguistic_register value

**Error Message**:
```
Field 'linguistic_register' has invalid value: 'neutral' (must be one of ['colloquial', 'formal', 'informal'])
```

**Cause**: Pipeline using invalid register value

**Solution**: Map to valid register:

```python
# Correct mapping
REGISTER_MAP = {
    'neutral': 'formal',
    'casual': 'informal',
    'slang': 'colloquial'
}

register = REGISTER_MAP.get(original_register, 'formal')  # Default to formal
record['linguistic_register'] = register
```

#### Error: Invalid schema_version

**Error Message**:
```
Field 'schema_version' has invalid value: '1.1' (expected exactly '1.0')
```

**Cause**: Pipeline using future schema version

**Solution**: Use current schema version:

```python
record['schema_version'] = "1.0"  # Must be exactly "1.0"
```

#### Error: Empty or whitespace text

**Error Message**:
```
Field 'text' is empty or whitespace (required, must be non-empty)
```

**Cause**: Text cleaning removed all content

**Solution**: Filter records with empty text before writing:

```python
cleaned_text = cleaner.clean(raw_text)

if not cleaned_text.strip():
    logger.warning(f"Skipping record with empty text after cleaning: {record_id}")
    continue  # Don't write to silver

record['text'] = cleaned_text
```

#### Error: Negative token count

**Error Message**:
```
Field 'tokens' has invalid value: -5 (must be >= 0)
```

**Cause**: Bug in token counting logic

**Solution**: Fix token counter:

```python
def count_tokens(text: str) -> int:
    """Count whitespace-separated tokens."""
    if not text or not text.strip():
        return 0

    tokens = text.split()
    return max(0, len(tokens))  # Ensure non-negative
```

---

## Best Practices

### 1. Validate Before Writing

Always validate records BEFORE writing to Parquet:

```python
from somali_dialect_classifier.contracts.ingestion_output import validate_ingestion_output

# Bad: Write then validate ❌
write_to_parquet(record)
is_valid, errors = validate_ingestion_output(record)  # Too late!

# Good: Validate then write ✅
is_valid, errors = validate_ingestion_output(record)
if not is_valid:
    logger.error(f"Invalid record: {errors}")
    raise ValidationError(f"Contract violation: {errors}")

write_to_parquet(record)
```

### 2. Run Validation in CI

Add validation to continuous integration:

```yaml
# .github/workflows/ci.yml
- name: Validate Silver Datasets
  run: |
    somali-validate-silver --input data/processed/silver/ --fail-fast
```

### 3. Monitor Validation Errors

Track validation error trends over time:

```bash
# Daily validation report
somali-validate-silver \
  --input data/processed/silver/ \
  --output "reports/validation_$(date +%Y%m%d).json"

# Analyze trends
python scripts/analyze_validation_trends.py
```

### 4. Graceful Degradation

For non-critical errors, log warnings instead of failing:

```python
is_valid, errors = validate_ingestion_output(record)

if not is_valid:
    # Separate critical vs. non-critical errors
    critical_errors = [e for e in errors if 'missing' in e.lower()]
    warnings = [e for e in errors if e not in critical_errors]

    if critical_errors:
        raise ValidationError(f"Critical errors: {critical_errors}")

    if warnings:
        logger.warning(f"Non-critical validation warnings: {warnings}")

write_to_parquet(record)
```

### 5. Schema Documentation

Document schema changes in CHANGELOG:

```markdown
# CHANGELOG.md

## [1.1.0] - 2025-XX-XX
### Added
- New optional field `quality_score` (float, 0.0-1.0)
- New optional field `dialect_hints` (list of strings)

### Migration
- No migration required (backward-compatible)
- Existing v1.0 records remain valid in v1.1
```

---

## Related Documentation

- **[Architecture Overview](../overview/architecture.md)** - Contract design rationale
- **[Silver Schema Reference](../reference/silver-schema.md)** - Complete schema specification
- **[Data Pipeline Guide](../guides/data-pipeline.md)** - Pipeline integration
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and fixes

---

**Maintainers**: Somali NLP Contributors
