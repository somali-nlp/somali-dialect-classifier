# HuggingFace Datasets Integration Guide

**Status**: Using **MC4 only** for HuggingFace data sources
**Last Updated**: 2025-10-18

This guide explains how to use HuggingFace datasets as data sources for the Somali Dialect Classifier.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Supported Datasets](#supported-datasets)
3. [Pipeline Architecture](#pipeline-architecture)
4. [Configuration](#configuration)
5. [Usage Examples](#usage-examples)
6. [Data Flow and Directory Structure](#data-flow-and-directory-structure)
7. [Excluded Datasets](#excluded-datasets)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
# Install with HuggingFace support
pip install -e ".[ml]"

# Or install datasets separately
pip install datasets
```

### Basic Usage

```bash
# Process MC4 (limit to 10k records)
hfsom-download mc4 --max-records 10000

# Process full MC4 dataset (no limit)
hfsom-download mc4

# Force reprocessing
hfsom-download mc4 --force
```

### Programmatic Usage

```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_mc4_processor

# Create processor
processor = create_mc4_processor(max_records=10000)

# Run full pipeline
processor.run()  # download() -> extract() -> process()
```

---

## MLOps Infrastructure Integration

This processor is fully integrated with production MLOps infrastructure:

**Structured Logging:**
```python
# Logs include run_id, source, phase automatically
{
  "run_id": "hf_20250119_123456",
  "source": "HuggingFace-Somali",
  "phase": "fetch",
  "message": "...",
  ...
}
```

**Metrics Collected:**
- Discovery: `records_discovered`, `batches_created`
- Fetch: `records_fetched`, `fetch_duration_ms`
- Processing: `records_processed`, `filter_statistics`

**Quality Reports:**
Generated automatically at `data/reports/{run_id}_quality_report.md`

**Resume Capability:**
The crawl ledger tracks processing state, enabling resume after interruptions:
```bash
# First run - process 10k records
hfsom-download mc4 --max-records 10000

# Resume - continues from last offset if interrupted
hfsom-download mc4 --max-records 100000  # Starts from 10001, not 0
```

---

## Supported Datasets

### MC4 (Multilingual C4) - Primary Dataset ✅

**Dataset**: `allenai/c4`
**Config**: `so` (Somali, ISO 639-1)
**Split**: `train`
**Text Field**: `text`
**Metadata**: `url`, `timestamp`
**License**: ODC-BY-1.0
**Size**: ~100k-200k Somali records

**Description**: Web-scraped multilingual corpus from Common Crawl. This is our primary and **only** HuggingFace data source.

**Characteristics**:
- ✅ Large: ~100k-200k Somali records
- ✅ Streaming: Efficient memory usage for large datasets
- ✅ Compatible: Works with datasets>=3.0
- ✅ No Auth: Public access, no tokens required
- ✅ Maintained: Active development by allenai
- ✅ Metadata: Includes URLs and timestamps for provenance
- Web-scraped text (quality filters applied automatically)

---

## Pipeline Architecture

### Three-Stage Pipeline

The HuggingFace processor follows a three-phase pipeline:

```
┌─────────────────────────────────────────────────────────┐
│ Stage 1: DOWNLOAD (Manifest Creation)                  │
│ - Create manifest with dataset metadata                │
│ - Track revision, config, split, filters               │
│ - No data downloaded yet                               │
│ → Output: data/raw/source=HF-mc4-so/c4_manifest.json  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 2: EXTRACT (JSONL Batching)                      │
│ - Stream dataset from HuggingFace Hub                  │
│ - Write 5k-record batches to JSONL files              │
│ - Update manifest with last_offset for resume         │
│ → Output: data/staging/source=HF-mc4-so/batch_*.jsonl │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 3: PROCESS (Clean, Filter, Write)                │
│ - Replay JSONL batches                                 │
│ - Map fields to RawRecord                              │
│ - Apply text cleaning                                  │
│ - Apply quality filters (min_length, langid)          │
│ - Write to silver Parquet                              │
│ → Output: data/processed/silver/.../part-0000.parquet │
└─────────────────────────────────────────────────────────┘
```

### Why This Architecture?

1. **Resumable**: If extraction fails, restart from last completed batch
2. **Memory-efficient**: Process datasets larger than RAM via streaming
3. **Debuggable**: Inspect raw data in JSONL batches before filters
4. **Reproducible**: Manifest tracks exact dataset version and configuration

---

## Configuration

### Environment Variables

```bash
# Set in .env file or export
SDC_SCRAPING__HUGGINGFACE__STREAMING_BATCH_SIZE=5000
SDC_SCRAPING__HUGGINGFACE__MAX_RECORDS=100000
SDC_SCRAPING__HUGGINGFACE__MIN_LENGTH_THRESHOLD=100
SDC_SCRAPING__HUGGINGFACE__LANGID_CONFIDENCE_THRESHOLD=0.3
SDC_SCRAPING__HUGGINGFACE__RESUME_ENABLED=true
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAMING_BATCH_SIZE` | 5000 | Records per JSONL batch file |
| `MAX_RECORDS` | None | Maximum records to process (None = unlimited) |
| `MIN_LENGTH_THRESHOLD` | 100 | Minimum text length for quality filter (chars) |
| `LANGID_CONFIDENCE_THRESHOLD` | 0.3 | Language detection confidence (0-1) |
| `RESUME_ENABLED` | true | Enable resume from last offset on failure |

---

## Usage Examples

### Example 1: Small Test Run

```bash
# CLI
hfsom-download mc4 --max-records 10
```

```python
# Python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_mc4_processor

processor = create_mc4_processor(max_records=10)
processor.run()
```

**Expected output**:
```
data/raw/.../c4_manifest.json                    # 2KB (metadata)
data/staging/.../batch_000000.jsonl              # 5KB (10 raw records)
data/processed/silver/.../part-0000.parquet      # 36KB (9 cleaned records)
```

### Example 2: Production Run

```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_mc4_processor

# Process 100k records
processor = create_mc4_processor(max_records=100000)

# Step 1: Create manifest
manifest_path = processor.download()
print(f"Manifest: {manifest_path}")

# Step 2: Stream and batch
staging_dir = processor.extract()
print(f"Staging: {staging_dir}")

# Step 3: Process
silver_path = processor.process()
print(f"Silver: {silver_path}")
```

### Example 3: Custom Filters

```python
from somali_dialect_classifier.preprocessing.huggingface_somali_processor import create_mc4_processor
from somali_dialect_classifier.preprocessing.filters import custom_filter

# Create processor
processor = create_mc4_processor(max_records=5000)

# Add custom filter
def is_formal_somali(text: str) -> bool:
    """Check if text is formal Somali (not conversational)."""
    informal_markers = ["lol", "haha", "😂", "wlhi"]
    return not any(marker in text.lower() for marker in informal_markers)

processor.record_filters.append((custom_filter, {
    "predicate": is_formal_somali,
    "metadata_key": "is_formal"
}))

# Process
silver_path = processor.process()
```

---

## Data Flow and Directory Structure

### Directory Structure

```
data/
├── raw/                                    # Phase 1: Manifest Creation
│   └── source=HuggingFace-Somali_c4-so/
│       └── date_accessed=2025-10-18/
│           └── mc4_20251018_153000_raw_manifest.json  # Metadata with run_id
│
├── staging/                                # Phase 2: Raw Data Extraction
│   └── source=HuggingFace-Somali_c4-so/
│       └── date_accessed=2025-10-18/
│           ├── mc4_20251018_153000_staging_batch-000000.jsonl  # Raw extracted records (resumable)
│           ├── mc4_20251018_153000_staging_batch-000001.jsonl  # Additional batches
│           └── .extraction_complete                            # Marker: extraction finished
│
├── processed/
│   └── source=HuggingFace-Somali_c4-so/
│       └── date_accessed=2025-10-18/
│           └── mc4_20251018_153000_processed_cleaned.txt       # Cleaned text
│
└── processed/silver/                       # Phase 3: Processed Dataset (FINAL OUTPUT)
    └── source=HuggingFace-Somali_c4-so/
        └── date_accessed=2025-10-18/
            ├── hf-mc4-so_20251018_153000_silver_part-0000.parquet  # FINAL CLEANED DATA
            └── hf-mc4-so_20251018_153000_silver_metadata.json      # Metadata sidecar (NEW)
```

**File Naming Pattern**: Uses MC4 prefix in staging, hf-mc4-so in silver
- **run_id**: `20251018_153000` for complete lineage tracking
- **Batch Naming**: `batch-000000`, `batch-000001` (zero-padded, hyphenated)

### Manifest Format

```json
{
  "dataset_name": "allenai/c4",
  "dataset_config": "so",
  "split": "train",
  "revision": "main",
  "text_field": "text",
  "url_field": "url",
  "metadata_fields": ["timestamp"],
  "streaming_batch_size": 5000,
  "max_records": 10000,
  "created_at": "2025-10-18T10:30:00Z",
  "last_offset": 10000,
  "batches_completed": ["batch_000000.jsonl", "batch_000001.jsonl"],
  "total_records_extracted": 10000,
  "total_batches": 2,
  "manifest_version": "1.0"
}
```

### JSONL Batch Format

```jsonl
{"text": "Muqdisho waa magaalada...", "url": "https://...", "timestamp": "2023-01-01"}
{"text": "Soomaaliya waa waddan...", "url": "https://...", "timestamp": "2023-01-02"}
```

### Resume Capability

If extraction is interrupted:

```python
# First run (fails at record 7500)
processor.extract()  # Processes 0-7499, writes batch_000000 and batch_000001

# Resume (continues from 7500)
processor.extract()  # Skips 0-7499, continues from 7500
```

---

## Excluded Datasets

The following datasets were evaluated but **excluded** from the project:

### OSCAR-2301 - Excluded

**Reason**: Requires authentication, has less data than MC4

**Dataset**: `oscar-corpus/OSCAR-2301`
**Size**: ~50k-100k Somali records (LESS than MC4's ~100k-200k)
**Issue**: Gated dataset requiring HuggingFace authentication and terms acceptance

**Why Excluded**:
1. Less data than MC4: OSCAR has ~50% less Somali text
2. Authentication burden: Requires HuggingFace login, token management, terms acceptance
3. Redundant filtering: Our pipeline already has quality filters (min_length, langid)
4. Maintenance overhead: Tokens expire, access can be revoked
5. MC4 works perfectly: Already processing ~100k-200k records successfully

**Decision Document**: [docs/decisions/001-oscar-exclusion.md](../decisions/001-oscar-exclusion.md)

### MADLAD-400 - Excluded

**Reason**: Incompatible with datasets>=3.0, no fix timeline

**Dataset**: `allenai/MADLAD-400`
**Size**: 293k (clean) / 729k (noisy) Somali records
**Issue**: Uses Python dataset script, not supported by datasets>=3.0

**Why Excluded**:
1. Broken with datasets>=3.0: Raises `RuntimeError: Dataset scripts are no longer supported`
2. No Parquet conversion: Dataset has not been migrated to native format
3. No fix timeline: Could take 6-12 months or never be fixed
4. Workarounds unsustainable: Downgrading to datasets<3.0 blocks other features
5. MC4 is sufficient: ~100k-200k records is adequate for dialect classification

**Decision Document**: [docs/decisions/003-madlad-400-exclusion.md](../decisions/003-madlad-400-exclusion.md)

### Summary: Why MC4 Only

| Criterion | MC4 | OSCAR | MADLAD-400 |
|-----------|-----|-------|------------|
| **Size** | ~100k-200k | ~50k-100k ❌ | 293k-729k |
| **Compatibility** | datasets>=3.0 ✅ | datasets>=3.0 ✅ | datasets<3.0 only ❌ |
| **Authentication** | None ✅ | Required ❌ | None ✅ |
| **Status** | Working ✅ | Requires setup ❌ | Broken ❌ |
| **Maintenance** | Zero ✅ | Ongoing ❌ | High (workarounds) ❌ |
| **Decision** | ✅ **USE** | ❌ **SKIP** | ❌ **SKIP** |

**Recommendation**: Use MC4 for all HuggingFace data needs.

---

## Troubleshooting

### Issue: Import Error

**Error**:
```
ImportError: datasets library not available
```

**Solution**:
```bash
pip install datasets
# Or install with ML dependencies
pip install -e ".[ml]"
```

### Issue: Extraction Fails Partway

**Error**:
```
Extraction failed at offset 7500
```

**Solution**:
```python
# Resume from last offset
processor.extract()  # Automatically resumes from manifest.last_offset
```

### Issue: Memory Error

**Error**:
```
MemoryError: Unable to allocate array
```

**Solution**:
```bash
# Reduce batch size
export SDC_SCRAPING__HUGGINGFACE__STREAMING_BATCH_SIZE=1000
```

### Issue: Dataset Scripts No Longer Supported

**Error**:
```
RuntimeError: Dataset scripts are no longer supported
```

**Solution**: This project now uses **MC4 only**, which is natively compatible with datasets>=3.0.

---

## Best Practices

1. **Start Small**: Use `--max-records 1000` for testing
2. **Monitor Progress**: Check logs and manifest `last_offset`
3. **Use Resume**: Don't re-start from scratch on failures
4. **Filter Aggressively**: Web data is noisy, use high thresholds
5. **Check Schemas**: Inspect fields before processing
6. **Version Control**: Manifest tracks dataset revisions

---

## Performance Benchmarks

**Hardware**: M1 MacBook Pro, 16GB RAM

| Dataset | Records | Extraction Time | Processing Time | Total Time | Silver Size |
|---------|---------|-----------------|-----------------|------------|-------------|
| MC4 | 10,000 | 8 min | 2 min | 10 min | 12 MB |
| MC4 | 100,000 | ~80 min | ~20 min | ~100 min | ~120 MB |

**Throughput**:
- Extraction: ~20-30 records/sec (network-bound)
- Processing: ~100-200 records/sec (CPU-bound)

---

## See Also

- [Processing Pipelines Guide](processing-pipelines.md) - Step-by-step guides for all sources
- [Configuration Guide](configuration.md) - Environment setup and config management
- [ADR-001: OSCAR Exclusion](../decisions/001-oscar-exclusion.md) - Why we excluded OSCAR
- [ADR-003: MADLAD-400 Exclusion](../decisions/003-madlad-400-exclusion.md) - Why we excluded MADLAD-400
- [Architecture Overview](../overview/architecture.md) - System design
