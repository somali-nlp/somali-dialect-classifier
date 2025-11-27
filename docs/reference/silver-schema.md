# Silver Dataset Schema Reference

**Complete schema reference for silver-layer processed datasets.**

**Last Updated:** 2025-11-21

---

## Table of Contents

- [Overview](#overview)
- [Schema Versioning System](#schema-versioning-system)
- [Schema Version Fields Clarification](#schema-version-fields-clarification)
- [Current Schema Version: 1.0](#current-schema-version-10)
- [Full Schema](#full-schema)
- [Field Descriptions](#field-descriptions)
- [Metadata JSON Sidecars](#metadata-json-sidecars)
- [Domain Taxonomy](#domain-taxonomy)
- [Backward Compatibility](#backward-compatibility)
- [Complete Record Examples by Source](#complete-record-examples-by-source)
- [Partitioning](#partitioning)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Future Enhancements](#future-enhancements)
- [Schema Version History](#schema-version-history)
- [Related Documentation](#related-documentation)

---

## Overview

The silver dataset uses a standardized Parquet schema for all data sources with formal schema versioning starting at v1.0. Every record includes `schema_version` and `run_id` fields for tracking provenance and enabling schema evolution.

## Schema Versioning System

**Status**: Production (v1.0)
**Implementation**: Pydantic-based validation with migration framework
**Introduced**: 2025-11-11

### Key Features

- **Versioned schemas** with Pydantic validation models
- **Automatic validation** during pipeline processing
- **Migration framework** for future schema evolution
- **Provenance tracking** via `run_id` field linking to logs and metrics

### Version History

| Version | Date | Status | Changes | Breaking |
|---------|------|--------|---------|----------|
| 1.0 | 2025-11-11 | Production | Initial versioned schema with `schema_version` and `run_id` fields | N/A (initial) |

**Note**: Prior to v1.0, the pipeline used unversioned schemas (referred to as pipeline v2.0 and v2.1). Starting with schema v1.0, all records explicitly track their schema version.

### Future Planned Versions

| Version | Planned Date | Proposed Changes | Breaking |
|---------|--------------|------------------|----------|
| 1.1 | Q1 2026 | Add `confidence_scores` field (optional quality metrics) | No |
| 2.0 | Q2 2026 | Add `dialect_label` and `dialect_confidence` fields (required) | Yes |

##  Schema Version Fields Clarification

**IMPORTANT**: The schema uses two distinct version fields that serve different purposes:

### Record `schema_version` Field

- **Location**: `schema_version` column in Parquet records
- **Purpose**: Tracks the schema version of the **data record itself**
- **Current Value**: `"1.0"`
- **Scope**: Record-level field
- **Example**:
  ```python
  {
    "id": "abc123...",
    "text": "Sample text",
    "schema_version": "1.0",  # <-- Record schema version
    "run_id": "20251113_143045"
  }
  ```

### Sidecar `sidecar_format_version` Field

- **Location**: `sidecar_format_version` field in metadata JSON sidecar files
- **Purpose**: Tracks the schema version of the **sidecar file format**
- **Current Value**: `"1.0"`
- **Scope**: Sidecar file-level field
- **Example**:
  ```json
  {
    "run_id": "20251113_143045",
    "source": "Wikipedia-Somali",
    "sidecar_format_version": "1.0",  // <-- Sidecar schema version
    "total_records": 50000,
    "checksums": {...}
  }
  ```

**Why Two Version Fields?**
- **Separation of concerns**: Record schema evolution is independent of sidecar format evolution
- **Prevents collision**: Both can evolve independently without version conflicts
- **Clarity**: Makes it explicit which schema (data vs. metadata) is being referenced

**Migration Note**: These fields were disambiguated in Phase B (2025-11-13) to prevent schema version collisions.

## Current Schema Version: 1.0

**Format**: Apache Parquet
**Validation**: Pydantic v2
**Pipeline Version**: 2.1.0

## Full Schema

```python
pa.schema([
    # Core identification
    ("id", pa.string()),                    # Unique record identifier (SHA256 hash)
    ("text", pa.string()),                  # Cleaned text content
    ("title", pa.string()),                 # Document title

    # Source information
    ("source", pa.string()),                # Source name (e.g., "BBC-Somali")
    ("source_type", pa.string()),           # Source type (wiki, news, corpus, web)
    ("url", pa.string()),                   # Source URL
    ("source_id", pa.string()),             # External source ID (optional)

    # Temporal metadata
    ("date_published", pa.string()),        # Publication date (ISO 8601)
    ("date_accessed", pa.string()),         # Access date (ISO 8601)

    # Content metadata
    ("language", pa.string()),              # ISO 639-1 language code (always "so")
    ("license", pa.string()),               # License identifier
    ("topic", pa.string()),                 # Content topic/category (optional)
    ("tokens", pa.int64()),                 # Token count

    # Processing metadata
    ("text_hash", pa.string()),             # SHA256 hash of text (for deduplication)
    ("pipeline_version", pa.string()),      # Processing pipeline version
    ("source_metadata", pa.string()),       # Source-specific metadata (JSON string)

    # New in v2.0
    ("domain", pa.string()),                # Content domain (news, literature, etc.)
    ("embedding", pa.string()),             # Embedding representation (JSON string, optional)

    # New in v2.1
    ("register", pa.string()),              # Linguistic register (formal, informal, colloquial)

    # New in schema v1.0 (provenance fields)
    ("schema_version", pa.string()),        # Schema version (e.g., "1.0")
    ("run_id", pa.string()),                # Run identifier for provenance tracking
])
```

## Field Descriptions

### Core Identification

#### `id` (string, required)
- **Description**: Unique identifier for the record
- **Generation**: SHA256 hash of title + URL
- **Example**: `"a1b2c3d4e5f6..."`
- **Purpose**: Deduplication and record tracking

#### `text` (string, required)
- **Description**: Cleaned text content
- **Processing**:
  - HTML/XML tags removed
  - Wikipedia markup cleaned
  - Normalized whitespace
  - Special characters handled
- **Example**: `"Waxaan baran doonaa luqadda Soomaaliga..."`
- **Minimum length**: Varies by source (typically 20-50 tokens after filtering)

#### `title` (string, required)
- **Description**: Document title or heading
- **Example**: `"Barashada Luqadda Soomaaliga"`
- **Auto-generated**: For sources without explicit titles (first 50 chars)

### Source Information

#### `source` (string, required)
- **Description**: Human-readable source identifier
- **Format**: `Source-Language[_variant]`
- **Examples**:
  - `"Wikipedia-Somali"` - Wikipedia encyclopedia
  - `"BBC-Somali"` - BBC Somali news service
  - `"Sprakbanken-Somali"` - Språkbanken corpora (consistent across all 23 corpora)
  - `"HuggingFace-Somali_c4-so"` - HuggingFace MC4 dataset
  - `"TikTok-Somali"` - TikTok comments (social media)
- **Purpose**: Distinguishes data origin, enables source-level filtering
- **Note**: For Språkbanken, the corpus ID is stored in `source_id` field for easy querying

### Source Naming Policy

**All sources must follow these standardized naming conventions** (enforced in Phase A, 2025-11-13):

| Source | `source` Field Value | `source_type` Value | Notes |
|--------|---------------------|---------------------|-------|
| **Wikipedia** | `"Wikipedia-Somali"` | `"wiki"` | No prefix, consistent case |
| **BBC Somali** | `"BBC-Somali"` | `"news"` | Uppercase "BBC", hyphen separator |
| **Språkbanken** | `"Sprakbanken-Somali"` | `"corpus"` | Use "Sprakbanken", not "sprakbanken" |
| **HuggingFace** | `"HuggingFace-Somali_*"` | `"web"` | **MUST use prefix** `"HuggingFace-Somali"` |
| **TikTok** | `"TikTok-Somali"` | `"social"` | **NOT** `"social_media"` |

**HuggingFace Prefix Requirement**:
- **MANDATORY**: All HuggingFace datasets must use the prefix `"HuggingFace-Somali"`
- **Examples**:
  - ✅ `"HuggingFace-Somali_mc4-so"` - Correct
  - ✅ `"HuggingFace-Somali_opus"` - Correct
  - ❌ `"HuggingFace_mc4-so"` - WRONG (missing "Somali")
  - ❌ `"mc4-so"` - WRONG (missing prefix)
  - ❌ `"hf-mc4-so"` - WRONG (use full "HuggingFace-Somali")

**TikTok `source_type` Clarification**:
- **MUST use**: `"social"` (not `"social_media"`)
- **Rationale**: Consistent with existing source type taxonomy
- **Example**: `{"source": "TikTok-Somali", "source_type": "social"}`

**Validation**:
- Source names are validated during silver dataset writing
- Incorrect names will raise `ValueError` with helpful error message
- Fixed in Phase A (2025-11-13) to ensure consistency

**Why This Matters**:
- Enables reliable filtering and aggregation
- Prevents duplicate entries with variant names
- Ensures dashboard and analytics work correctly
- Maintains data lineage clarity

#### `source_type` (string, required)
- **Description**: Category of source
- **Valid values**:
  - `"wiki"` - Wikipedia and encyclopedia sources
  - `"news"` - News articles and journalism
  - `"corpus"` - Linguistic corpora (Språkbanken)
  - `"web"` - Web-scraped content (MC4, OSCAR)
  - `"social"` - Social media posts
- **Purpose**: Broad categorization for filtering

#### `url` (string, required)
- **Description**: Source URL or identifier
- **Examples**:
  - `"https://so.wikipedia.org/wiki/Soomaaliya"`
  - `"https://www.bbc.com/somali/articles/c123xyz"`
  - `"https://spraakbanken.gu.se/korp/?corpus=somali-cilmi"`
  - `"hf://allenai/c4/so"` (for HuggingFace datasets)
- **Purpose**: Traceability, citation, verification

#### `source_id` (string, optional)
- **Description**: Source-specific identifier for queryable sub-collections
- **Purpose**: Enables easy filtering within a source
- **Examples**:
  - Språkbanken: Corpus ID (e.g., `"cilmi"`, `"ogaden"`, `"as-2016"`)
  - BBC: Article ID from CMS (future)
  - Wikipedia: Page ID (future)
  - HuggingFace: Dataset subset identifier (future)
- **Usage**:
  ```python
  # Query specific Språkbanken corpus
  cilmi_records = table.filter(
      (table.column("source") == "Sprakbanken-Somali") &
      (table.column("source_id") == "cilmi")
  )

  # Get all news corpora from Språkbanken
  news_corpora_ids = ["as-2016", "as-2001", "ah-2010-19", "cb-2016", "ogaden"]
  sprak_news = table.filter(
      (table.column("source") == "Sprakbanken-Somali") &
      (table.column("source_id").isin(news_corpora_ids))
  )
  ```

### Temporal Metadata

#### `date_published` (string, optional)
- **Description**: When content was originally published
- **Format**: ISO 8601 (`YYYY-MM-DD` or full datetime)
- **Example**: `"2024-05-15"` or `"2024-05-15T10:30:00Z"`
- **Source availability**:
  - Wikipedia: Not available (use dump date)
  - BBC: Extracted from article metadata
  - Språkbanken: Varies by corpus
  - HuggingFace: May be in metadata

#### `date_accessed` (string, required)
- **Description**: When data was downloaded/accessed
- **Format**: ISO 8601 date (`YYYY-MM-DD`)
- **Example**: `"2025-01-15"`
- **Purpose**: Versioning, reproducibility, partitioning

### Content Metadata

#### `language` (string, required)
- **Description**: Content language
- **Value**: Always `"so"` (Somali, ISO 639-1)
- **Validation**: Language identification filter ensures content is Somali
- **Note**: Future versions may include language confidence scores

#### `license` (string, required)
- **Description**: License under which content is distributed
- **Examples**:
  - `"CC-BY-SA-3.0"` (Wikipedia)
  - `"BBC Terms of Use"` (BBC Somali)
  - `"CC BY 4.0"` (Språkbanken)
  - `"ODC-BY-1.0"` (MC4)
  - `"CC0-1.0"` (OSCAR)
- **Purpose**: Legal compliance, usage restrictions

#### `topic` (string, optional)
- **Description**: Content topic or category
- **Examples**: `"sports"`, `"politics"`, `"technology"`
- **Source**: May be extracted from article metadata or inferred
- **Usage**: Topic-based filtering, analysis

#### `tokens` (int64, required)
- **Description**: Number of tokens in text
- **Method**: Simple whitespace-based tokenization
- **Purpose**: Length filtering, statistics, batching
- **Example**: `1234`

### Processing Metadata

#### `text_hash` (string, required)
- **Description**: SHA256 hash of cleaned text
- **Purpose**: Exact duplicate detection across sources
- **Example**: `"abc123def456..."`
- **Usage**: Deduplication pipeline uses this field

#### `pipeline_version` (string, required)
- **Description**: Version of processing pipeline
- **Values**:
  - `"1.0.0"` - Original schema (no domain/embedding)
  - `"2.0.0"` - Enhanced schema (with domain/embedding)
- **Purpose**: Track processing provenance, schema evolution

#### `source_metadata` (string, required)
- **Description**: Source-specific metadata as JSON string
- **Format**: JSON-encoded dictionary
- **Examples**:
  ```json
  {
    "wiki_code": "sowiki",
    "dump_url": "https://dumps.wikimedia.org/..."
  }
  ```
  ```json
  {
    "base_url": "https://www.bbc.com/somali",
    "category": "news",
    "scraped_at": "2025-01-15T10:30:00Z"
  }
  ```
  ```json
  {
    "repository": "Språkbanken",
    "corpus_id": "cilmi",
    "domain": "science",
    "author": "...",
    "publisher": "..."
  }
  ```
- **Purpose**: Preserve source-specific information, enable rich queries

### Domain Classification (New in v2.0)

#### `domain` (string, required)
- **Description**: Content domain/genre classification
- **Standard taxonomy**:
  - `"news"` - News articles
  - `"encyclopedia"` - Encyclopedia/reference (Wikipedia)
  - `"literature"` - Fiction, poetry, stories
  - `"science"` - Scientific texts
  - `"health"` - Health-related content
  - `"children"` - Children's content
  - `"radio"` - Radio transcripts
  - `"social_media"` - Social media posts
  - `"web"` - General web content
  - `"academic"` - Academic papers
  - `"translation"` - Translated content
  - `"qa"` - Question-answer format
  - `"historical"` - Historical documents
  - `"general"` - Unclassified/mixed
  - `"news_regional"` - Regional news (e.g., Ogaden)
  - `"literature_translation"` - Translated literature

- **Purpose**:
  - Domain-specific filtering
  - Dataset composition analysis
  - Domain adaptation in models
  - Quality assessment by domain

- **Assignment**:
  - Explicit: Set by processor based on source knowledge
  - Inferred: Derived from source name/type if not explicit
  - Default: `"general"` if cannot be determined

- **Examples by source**:
  ```python
  "Wikipedia-Somali" → "encyclopedia"
  "BBC-Somali" → "news"
  "Sprakbanken-Somali" (source_id="cilmi") → "science"
  "Sprakbanken-Somali" (source_id="ogaden") → "news_regional"
  "HuggingFace-Somali_c4" → "web"
  ```

### Embeddings (New in v2.0)

#### `embedding` (string, optional)
- **Description**: Text embedding representation
- **Format**: JSON string encoding embedding vector
- **Current status**: Placeholder (always `null` in v2.0)
- **Future use**:
  - Sentence embeddings (mBERT, LaBSE)
  - Document embeddings (FastText, USE)
  - Semantic search
  - Clustering and similarity

- **Example (future)**:
  ```json
  "[0.123, -0.456, 0.789, ...]"  // 768-dimensional mBERT embedding
  ```

- **Storage considerations**:
  - JSON string allows flexible dimensionality
  - Consider separate embedding storage for large-scale use
  - May add embedding_model field in future versions

### Register Classification (New in v2.1)

#### `register` (string, required)
- **Description**: Linguistic register indicating formality level of text
- **Valid values**:
  - `"formal"` - Standard, academic, or professional language
  - `"informal"` - Casual but structured language
  - `"colloquial"` - Conversational, dialectal variations

- **Purpose**:
  - Linguistic analysis by formality level
  - Training register-aware language models
  - Filtering for specific use cases (formal vs. informal datasets)
  - Understanding stylistic variation across sources

- **Assignment**:
  - Source-based: Assigned by processor based on source characteristics
  - Deterministic: Same source type always gets same register value
  - Required: All records must have a register value (no null)

- **Current Mapping by Source**:
  ```python
  "Wikipedia-Somali" → "formal"           # Encyclopedic, standard orthography
  "BBC-Somali" → "formal"                 # Professional journalism
  "HuggingFace-Somali_c4" → "formal"      # Web corpus (mixed but generally formal)
  "Sprakbanken-Somali-*" → "formal"       # Academic corpora

  # Future sources (planned):
  "TikTok-Somali" → "informal"            # Social media content
  "Conversational-Somali" → "colloquial"  # Dialogue/speech transcripts
  ```

- **Design Rationale**:
  - Current data sources are predominantly formal in nature
  - All 4 existing sources (Wikipedia, BBC, HuggingFace MC4, Språkbanken) produce formal written text
  - Future expansion will include informal sources (social media) and colloquial sources (speech)
  - Register field enables filtering and analysis by linguistic formality

- **Usage Example**:
  ```python
  import pandas as pd
  import pyarrow.parquet as pq

  # Read silver dataset
  table = pq.read_table("data/processed/silver/")
  df = table.to_pandas()

  # Filter by register
  formal_only = df[df['register'] == 'formal']
  informal_only = df[df['register'] == 'informal']

  # Register distribution
  print(df['register'].value_counts())
  # Output:
  # formal        245000
  # informal           0  (no informal sources yet)
  # colloquial         0  (no colloquial sources yet)
  ```

- **Validation**:
  - Enforced via `VALID_REGISTERS` constant in `SilverDatasetWriter`
  - Invalid values raise `ValueError` during record creation
  - Schema validation ensures string type

## Metadata JSON Sidecars

### Overview

Starting with pipeline version 2.1, every silver dataset partition is accompanied by a **metadata JSON sidecar file** that contains checksums, statistics, and lineage information.

### File Naming

Metadata files follow the same naming pattern as their associated Parquet files:

```
{source_slug}_{run_id}_silver_metadata.json
```

**Examples**:
- `wikipedia-somali_20251020_143045_silver_metadata.json`
- `bbc-somali_20251020_150230_silver_metadata.json`
- `hf-mc4-so_20251020_153000_silver_metadata.json`
- `sprakbanken-cilmi_20251020_160000_silver_metadata.json`

### Schema

```json
{
  "run_id": "20251020_143045",
  "source": "Wikipedia-Somali",
  "pipeline_version": "2.1.0",
  "date_accessed": "2025-10-20",
  "date_processed": "2025-10-20T14:45:30Z",
  "total_records": 50000,
  "total_partitions": 3,
  "schema_version": "2.1",
  "checksums": {
    "part-0000": {
      "sha256": "abc123def456789...",
      "size_bytes": 15000000,
      "record_count": 17000
    },
    "part-0001": {
      "sha256": "def456abc123789...",
      "size_bytes": 15000000,
      "record_count": 17000
    },
    "part-0002": {
      "sha256": "789abc123def456...",
      "size_bytes": 15000000,
      "record_count": 16000
    }
  },
  "statistics": {
    "total_size_bytes": 45000000,
    "avg_record_size_bytes": 900,
    "min_tokens": 50,
    "max_tokens": 15000,
    "avg_tokens": 342,
    "total_tokens": 17100000
  },
  "filters_applied": {
    "min_length_filter": {
      "threshold": 50,
      "rejected_count": 2300
    },
    "langid_filter": {
      "confidence_threshold": 0.3,
      "rejected_count": 5700
    }
  }
}
```

### Field Descriptions

#### Core Metadata

**run_id** (string, required)
- Timestamp-based unique identifier for this pipeline run
- Format: `YYYYMMDD_HHMMSS`
- Links to structured logs and quality reports
- Example: `"20251020_143045"`

**source** (string, required)
- Human-readable source identifier
- Matches the `source` field in Parquet records
- Example: `"Wikipedia-Somali"`, `"BBC-Somali"`

**pipeline_version** (string, required)
- Semantic version of the processing pipeline
- Tracks code version that generated this data
- Example: `"2.1.0"`

**date_accessed** (string, required)
- Date when source data was downloaded/accessed
- Format: ISO 8601 date (`YYYY-MM-DD`)
- Matches partition key in directory structure
- Example: `"2025-10-20"`

**date_processed** (string, required)
- Timestamp when silver dataset was created
- Format: ISO 8601 datetime with timezone (`YYYY-MM-DDTHH:MM:SSZ`)
- Example: `"2025-10-20T14:45:30Z"`

**total_records** (integer, required)
- Total number of records across all partitions
- Useful for validation and statistics
- Example: `50000`

**total_partitions** (integer, required)
- Number of Parquet partition files
- Typically 1, may be higher for large datasets
- Example: `3`

**schema_version** (string, required)
- Version of the Parquet schema
- Current version: `"2.1"`
- Enables schema evolution tracking
- Example: `"2.1"`

#### Checksums

**checksums** (object, required)
- Per-partition integrity checksums
- Keys: partition filenames (e.g., `"part-0000"`, `"part-0001"`)
- Values: checksum objects with the following fields:

**sha256** (string, required)
- SHA256 hash of the Parquet file
- Used for corruption detection and verification
- Example: `"abc123def456789..."`

**size_bytes** (integer, required)
- File size in bytes
- Used for capacity planning and monitoring
- Example: `15000000` (15 MB)

**record_count** (integer, required)
- Number of records in this partition
- Sum of all partitions should equal `total_records`
- Example: `17000`

#### Statistics

**statistics** (object, required)
- Aggregate statistics across all partitions

**total_size_bytes** (integer, required)
- Total size of all Parquet files combined
- Example: `45000000` (45 MB)

**avg_record_size_bytes** (number, required)
- Average record size in bytes
- Calculated as: `total_size_bytes / total_records`
- Example: `900`

**min_tokens** (integer, required)
- Minimum token count across all records
- Example: `50`

**max_tokens** (integer, required)
- Maximum token count across all records
- Example: `15000`

**avg_tokens** (number, required)
- Average token count per record
- Example: `342.5`

**total_tokens** (integer, required)
- Total token count across all records
- Example: `17100000`

#### Filters Applied

**filters_applied** (object, optional)
- Filter statistics from quality filtering
- Keys: filter names
- Values: filter configuration and rejection counts

**Example**:
```json
{
  "min_length_filter": {
    "threshold": 50,
    "rejected_count": 2300
  },
  "langid_filter": {
    "confidence_threshold": 0.3,
    "rejected_count": 5700
  }
}
```

### Use Cases

#### 1. Data Integrity Verification

```python
import json
import hashlib

# Load metadata
with open("wikipedia-somali_20251020_143045_silver_metadata.json") as f:
    metadata = json.load(f)

# Verify partition integrity
partition_file = "wikipedia-somali_20251020_143045_silver_part-0000.parquet"
expected_checksum = metadata["checksums"]["part-0000"]["sha256"]

# Calculate actual checksum
with open(partition_file, "rb") as f:
    actual_checksum = hashlib.sha256(f.read()).hexdigest()

if actual_checksum != expected_checksum:
    print("ERROR: Checksum mismatch! File may be corrupted.")
else:
    print("OK: File integrity verified.")
```

#### 2. Lineage Tracking

```python
import json

# Load metadata
with open("wikipedia-somali_20251020_143045_silver_metadata.json") as f:
    metadata = json.load(f)

run_id = metadata["run_id"]

# Find related artifacts
log_file = f"logs/wikipedia_somali_{run_id}.log"
metrics_file = f"data/metrics/{run_id}_extraction.json"
quality_report = f"data/reports/{run_id}_quality_report.md"

print(f"Run ID: {run_id}")
print(f"Logs: {log_file}")
print(f"Metrics: {metrics_file}")
print(f"Quality Report: {quality_report}")
```

#### 3. Statistics Collection

```python
import json
import glob

# Collect statistics across all sources
all_metadata = glob.glob("data/processed/silver/**/*/metadata.json", recursive=True)

total_records = 0
total_size = 0

for metadata_file in all_metadata:
    with open(metadata_file) as f:
        meta = json.load(f)
        total_records += meta["total_records"]
        total_size += meta["statistics"]["total_size_bytes"]

print(f"Total Records: {total_records:,}")
print(f"Total Size: {total_size / 1e9:.2f} GB")
```

#### 4. Quality Monitoring

```python
import json

with open("bbc-somali_20251020_150230_silver_metadata.json") as f:
    metadata = json.load(f)

filters = metadata.get("filters_applied", {})

for filter_name, filter_stats in filters.items():
    rejected = filter_stats.get("rejected_count", 0)
    total = metadata["total_records"] + rejected
    rejection_rate = (rejected / total) * 100

    print(f"{filter_name}:")
    print(f"  Rejected: {rejected:,} ({rejection_rate:.2f}%)")
    print(f"  Config: {filter_stats}")
```

### Best Practices

1. **Always Verify Checksums**: Check SHA256 hashes after copying or transferring data
2. **Track run_id**: Use run_id to correlate data with logs and metrics
3. **Monitor Statistics**: Alert on unusual changes in avg_tokens or rejection rates
4. **Version Control**: Track pipeline_version for reproducibility
5. **Archive Metadata**: Keep metadata files alongside Parquet files in backups

### Future Enhancements

Planned additions to metadata schema:

- **v2.2**: Source-specific metrics (e.g., HTTP status codes for web scraping)
- **v2.3**: Lineage graph (upstream/downstream dataset references)
- **v2.4**: Data quality scores (completeness, validity, consistency)
- **v3.0**: Provenance tracking (transformations applied, parent datasets)

## Domain Taxonomy

### Domain Assignment by Source

| Source | source_id | Domain | Rationale |
|--------|-----------|--------|-----------|
| Wikipedia-Somali | null | encyclopedia | Encyclopedia content |
| BBC-Somali | null | news | News articles |
| Sprakbanken-Somali | as-*, ah-*, cb* | news | News sources (Arlaadi Soomaaliyeed, Afhayeenka, CB News) |
| Sprakbanken-Somali | ogaden | news_regional | Regional Ogaden news |
| Sprakbanken-Somali | sheekooyin-carruureed | children | Children's stories |
| Sprakbanken-Somali | sheekooyin*, sheekooying | literature | Stories and narratives |
| Sprakbanken-Somali | suugaan | literature | Literature and poetry |
| Sprakbanken-Somali | suugaan-turjuman | literature_translation | Translated literature |
| Sprakbanken-Somali | tid-turjuman | translation | Translations |
| Sprakbanken-Somali | cilmi | science | Science content |
| Sprakbanken-Somali | saynis-* | science | Science content |
| Sprakbanken-Somali | caafimaad-* | health | Health content |
| Sprakbanken-Somali | radio* | radio | Radio transcripts |
| Sprakbanken-Somali | kqa | qa | Question-answer |
| Sprakbanken-Somali | 197*, 2001, 1993-94, mk-* | historical | Historical documents |
| HuggingFace-Somali_* | null | web | Web-scraped content |

### Domain Use Cases

#### Training Data Composition
```python
from somali_dialect_classifier.preprocessing.silver_writer import SilverDatasetWriter

writer = SilverDatasetWriter()
stats = writer.get_domain_statistics()

print("Dataset composition:")
for domain, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
    print(f"  {domain}: {count:,} records")
```

#### Domain-Specific Filtering
```python
import pyarrow.parquet as pq

# Read silver dataset
table = pq.read_table("data/silver/")

# Filter to specific domains
news_table = table.filter(pc.field("domain") == "news")
lit_table = table.filter(pc.field("domain").isin(["literature", "literature_translation"]))
```

#### Domain Adaptation
```python
# Separate training sets by domain
domains = ["news", "encyclopedia", "literature", "web"]

for domain in domains:
    domain_table = table.filter(pc.field("domain") == domain)
    # Train domain-specific model or adapter
```

## Backward Compatibility

### Reading Legacy Data (v1.0 and v2.0)

The v2.1 writer automatically handles legacy data:

```python
from somali_dialect_classifier.preprocessing.silver_writer import SilverDatasetWriter

writer = SilverDatasetWriter()

# Reading v1.0 data automatically adds default values
table = writer.read("BBC-Somali", "2024-12-01")  # v1.0 data
# Domain field added with inferred value
# Embedding field added as null
# Register field added with inferred value (based on source)

# Reading v2.0 data automatically adds register field
table = writer.read("Wikipedia-Somali", "2025-01-01")  # v2.0 data
# Register field added with inferred value: "formal" for Wikipedia
```

### Migration Strategy

For existing v1.0 and v2.0 silver datasets:

1. **Automatic migration on read**: Default domains and registers inferred from source
2. **Explicit migration** (recommended):
   ```python
   writer = SilverDatasetWriter()
   writer.migrate_legacy_data("BBC-Somali", "2024-12-01")
   # Migrates v1.0 → v2.1 or v2.0 → v2.1
   ```

3. **Batch migration script** (coming soon):
   ```bash
   python scripts/migrate_silver_schema.py
   # Automatically detects schema version and migrates to v2.1
   ```

**Register Inference Logic**:
- Wikipedia sources → `"formal"`
- BBC sources → `"formal"`
- HuggingFace sources → `"formal"` (for web/corpus), `"informal"` (for social media)
- Språkbanken sources → `"formal"`

## Complete Record Examples by Source

Below are complete silver record examples for all 5 data sources, highlighting the correct `source` and `source_type` field values:

### Example 1: Wikipedia

```python
{
    "id": "a1b2c3d4e5f6...",
    "text": "Soomaaliya waa waddan ku yaal Geeska Afrika...",
    "title": "Soomaaliya",
    "source": "Wikipedia-Somali",  # Correct naming
    "source_type": "wiki",
    "url": "https://so.wikipedia.org/wiki/Soomaaliya",
    "source_id": None,
    "date_published": None,
    "date_accessed": "2025-11-13",
    "language": "so",
    "license": "CC-BY-SA-3.0",
    "topic": None,
    "tokens": 850,
    "text_hash": "abc123...",
    "pipeline_version": "2.1.0",
    "source_metadata": '{"wiki_code": "sowiki", "dump_url": "..."}',
    "domain": "encyclopedia",
    "embedding": None,
    "register": "formal",
    "schema_version": "1.0",
    "run_id": "20251113_143045"
}
```

### Example 2: BBC Somali

```python
{
    "id": "def456789...",
    "text": "Madaxweynaha Soomaaliya ayaa maanta...",
    "title": "Madaxweynaha oo magaalada booqday",
    "source": "BBC-Somali",  # Correct naming
    "source_type": "news",
    "url": "https://www.bbc.com/somali/articles/c123xyz",
    "source_id": None,
    "date_published": "2025-11-12",
    "date_accessed": "2025-11-13",
    "language": "so",
    "license": "BBC Terms of Use",
    "topic": "politics",
    "tokens": 450,
    "text_hash": "def456...",
    "pipeline_version": "2.1.0",
    "source_metadata": '{"category": "news", "scraped_at": "2025-11-13T10:30:00Z"}',
    "domain": "news",
    "embedding": None,
    "register": "formal",
    "schema_version": "1.0",
    "run_id": "20251113_150230"
}
```

### Example 3: Språkbanken

```python
{
    "id": "ghi789abc...",
    "text": "Cilmiga taarikhda ayaa ah...",
    "title": "Cilmi: Historical science",
    "source": "Sprakbanken-Somali",  # Correct naming (note: "Sprakbanken", not "sprakbanken")
    "source_type": "corpus",
    "url": "https://spraakbanken.gu.se/korp/?corpus=somali-cilmi",
    "source_id": "cilmi",  # Corpus ID for filtering
    "date_published": None,
    "date_accessed": "2025-11-13",
    "language": "so",
    "license": "CC BY 4.0",
    "topic": "science",
    "tokens": 1200,
    "text_hash": "ghi789...",
    "pipeline_version": "2.1.0",
    "source_metadata": '{"repository": "Språkbanken", "corpus_id": "cilmi", "domain": "science"}',
    "domain": "science",
    "embedding": None,
    "register": "formal",
    "schema_version": "1.0",
    "run_id": "20251113_160000"
}
```

### Example 4: HuggingFace (MC4)

```python
{
    "id": "jkl012def...",
    "text": "Wadanka Soomaaliya wuxuu ku yaalaa bariga Afrika...",
    "title": "Web document about Somalia",
    "source": "HuggingFace-Somali_mc4-so",  # MUST use prefix "HuggingFace-Somali"
    "source_type": "web",
    "url": "hf://allenai/c4/so",
    "source_id": None,
    "date_published": None,
    "date_accessed": "2025-11-13",
    "language": "so",
    "license": "ODC-BY-1.0",
    "topic": None,
    "tokens": 680,
    "text_hash": "jkl012...",
    "pipeline_version": "2.1.0",
    "source_metadata": '{"dataset": "allenai/c4", "config": "so", "split": "train"}',
    "domain": "web",
    "embedding": None,
    "register": "formal",
    "schema_version": "1.0",
    "run_id": "20251113_153000"
}
```

### Example 5: TikTok

```python
{
    "id": "mno345ghi...",
    "text": "Waan ku faraxsanahay in aan arko dadka wanaagsan...",
    "title": "Comment on TikTok video",
    "source": "TikTok-Somali",  # Correct naming
    "source_type": "social",  # MUST be "social", NOT "social_media"
    "url": "https://www.tiktok.com/@user/video/123456789",
    "source_id": None,
    "date_published": "2025-11-12T15:30:00Z",
    "date_accessed": "2025-11-13",
    "language": "so",
    "license": "TikTok Terms of Service",
    "topic": None,
    "tokens": 85,
    "text_hash": "mno345...",
    "pipeline_version": "2.1.0",
    "source_metadata": '{"comment_id": "987654321", "video_url": "..."}',
    "domain": "social_media",
    "embedding": None,
    "register": "informal",
    "schema_version": "1.0",
    "run_id": "20251113_170000"
}
```

**Key Observations**:
- **Wikipedia**: `source_type="wiki"`, no `source_id`
- **BBC**: `source_type="news"`, includes `date_published` and `topic`
- **Språkbanken**: `source_type="corpus"`, uses `source_id` for corpus filtering
- **HuggingFace**: **MUST use prefix** `"HuggingFace-Somali_*"`, `source_type="web"`
- **TikTok**: `source_type="social"` (**NOT** `"social_media"`), shorter text, `register="informal"`

## Partitioning

Silver datasets are partitioned by:
- `source=<source_name>/` - Source-level partitioning
- `date_accessed=<YYYY-MM-DD>/` - Temporal partitioning
- `part-NNNN.parquet` - File-level partitioning for large sources

Example structure:
```
data/silver/
├── source=BBC-Somali/
│   ├── date_accessed=2025-01-01/
│   │   ├── part-0000.parquet
│   │   └── part-0001.parquet
│   └── date_accessed=2025-01-15/
│       └── part-0000.parquet
├── source=Wikipedia-Somali/
│   └── date_accessed=2025-01-10/
│       ├── part-0000.parquet
│       ├── part-0001.parquet
│       └── part-0002.parquet
└── source=Sprakbanken-Somali/
    └── date_accessed=2025-01-15/
        ├── sprakbanken-cilmi_20251015_120000_silver_part-0000.parquet
        ├── sprakbanken-ogaden_20251015_130000_silver_part-0000.parquet
        └── sprakbanken-as-2016_20251015_140000_silver_part-0000.parquet
```

**Note**: All Språkbanken corpora share the same source partition (`source=Sprakbanken-Somali`). Individual corpora are distinguished by `source_id` field within the records and by filename prefixes.

Benefits:
- Fast source-level filtering
- Temporal versioning
- Incremental updates
- Parallel processing

## Usage Examples

### Basic Reading

```python
import pyarrow.parquet as pq

# Read all silver data
table = pq.read_table("data/silver/")

# Read specific source
table = pq.read_table("data/silver/source=BBC-Somali/")

# Read specific date
table = pq.read_table("data/silver/source=BBC-Somali/date_accessed=2025-01-01/")
```

### Filtering

```python
import pyarrow.compute as pc

# Filter by domain
news_only = table.filter(pc.field("domain") == "news")

# Filter by register (NEW in v2.1)
formal_only = table.filter(pc.field("register") == "formal")
informal_only = table.filter(pc.field("register") == "informal")

# Filter by multiple domains
content_domains = ["literature", "children", "encyclopedia"]
filtered = table.filter(pc.field("domain").isin(content_domains))

# Filter by source type and domain
news_articles = table.filter(
    (pc.field("source_type") == "news") &
    (pc.field("domain") == "news")
)

# Filter by register and domain (combined)
formal_news = table.filter(
    (pc.field("register") == "formal") &
    (pc.field("domain") == "news")
)

# Filter by token count
long_docs = table.filter(pc.field("tokens") >= 500)
```

### Statistics

```python
# Domain distribution
domains = table.column("domain").to_pylist()
from collections import Counter
print(Counter(domains))

# Register distribution (NEW in v2.1)
registers = table.column("register").to_pylist()
print(Counter(registers))
# Expected output (current sources):
# Counter({'formal': 245000})

# Average tokens by domain
import pandas as pd
df = table.to_pandas()
print(df.groupby("domain")["tokens"].agg(["mean", "median", "count"]))

# Average tokens by register (NEW in v2.1)
print(df.groupby("register")["tokens"].agg(["mean", "median", "count"]))

# Cross-tabulation: domain vs register
print(pd.crosstab(df["domain"], df["register"]))
```

### Deduplication

```python
# Find duplicates by text_hash
df = table.to_pandas()
duplicates = df[df.duplicated("text_hash", keep=False)]

# Deduplicate keeping first occurrence
unique_df = df.drop_duplicates("text_hash", keep="first")
```

## Best Practices

1. **Always specify domain**: Set explicit domain when known
2. **Use source_metadata**: Preserve source-specific information
3. **Validate before writing**: Check required fields are present
4. **Partition appropriately**: Use source and date for natural partitioning
5. **Monitor domain distribution**: Track dataset composition
6. **Plan for embeddings**: Reserve embedding field for future use
7. **Document custom fields**: Add to source_metadata as JSON

## Future Enhancements

Planned for future schema versions:

- **v2.2**: Confidence scores for language identification
- **v2.3**: Dialect labels and scores (Northern, Southern, etc.)
- **v3.0**: Separate embedding table with multiple embedding types
- **v3.1**: Sentence-level annotations

## Schema Version History

### Version 2.1 (Current)
- **Added**: `register` field for linguistic formality classification
- **Values**: "formal", "informal", "colloquial"
- **Implementation**: Source-based inference via `_get_register()` method in all processors

### Version 2.0
- **Added**: `domain` field for content classification
- **Added**: `embedding` field (placeholder for future use)
- **Purpose**: Enable domain-specific filtering and analysis

### Version 1.0 (Original)
- **Core fields**: id, text, title, source, source_type, url, license, etc.
- **Purpose**: Basic data collection and standardization

## Related Documentation

- [Data Pipeline Overview](../overview/data-pipeline-architecture.md)
- [Språkbanken Integration](../howto/sprakbanken-integration.md)
- [Quality Filters](../howto/quality-filters.md)
- [Deduplication Guide](../howto/deduplication.md)

---

**Maintainers**: Somali NLP Contributors