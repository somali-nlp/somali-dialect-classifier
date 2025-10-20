# File Naming Convention Issues - Data Engineering & MLOps Analysis

## Executive Summary

**Status:** ⚠️ **INCONSISTENT** - File naming conventions violate data engineering and MLOps best practices

**Impact:**
- Difficult data lineage tracking
- Ambiguous file identification across sources
- Incompatible with automated data catalog tools
- Hard to implement incremental processing
- Poor observability in data lake/warehouse environments

---

## Current File Naming Conventions by Source

### 1. Wikipedia-Somali

#### Raw Layer
```
data/raw/source=Wikipedia-Somali/date_accessed=2025-10-20/
└── sowiki-latest-pages-articles.xml.bz2
```
**Issues:**
- ❌ No source identifier in filename
- ❌ Generic upstream naming (not project-specific)
- ⚠️ "latest" in filename becomes misleading after time passes
- ✅ Has date in partition path

#### Staging Layer
```
data/staging/source=Wikipedia-Somali/date_accessed=2025-10-20/
└── wikisom_raw.txt
```
**Issues:**
- ❌ Confusing name: "raw" in staging layer (should be "extracted" or "staged")
- ❌ No run_id for traceability
- ❌ No timestamp in filename
- ❌ Generic `.txt` extension (no format metadata)

#### Processed Layer
```
data/processed/source=Wikipedia-Somali/date_processed=2025-10-20/
└── wikisom.txt
```
**Issues:**
- ❌ No run_id
- ❌ No timestamp
- ❌ Generic `.txt` extension
- ❌ Partition key changed from `date_accessed` to `date_processed` (inconsistent)

---

### 2. BBC-Somali

#### Raw Layer
```
data/raw/source=BBC-Somali/date_accessed=2025-10-20/
├── article_links.json
└── article_0001.json
└── article_0002.json
...
```
**Issues:**
- ❌ `article_links.json` - no run_id, no timestamp
- ✅ Incremental files with counters (good for resume)
- ❌ No source identifier in filename
- ❌ Counter-based naming doesn't preserve URL identity

#### Staging Layer
```
data/staging/source=BBC-Somali/date_accessed=2025-10-20/
└── bbcsom_articles.json
```
**Issues:**
- ❌ No run_id
- ❌ No timestamp
- ❌ Monolithic file (not partitioned)

#### Processed Layer
```
data/processed/source=BBC-Somali/date_processed=2025-10-20/
└── bbcsom.txt
```
**Issues:**
- ❌ Same issues as Wikipedia processed layer
- ❌ Partition key inconsistency

---

### 3. HuggingFace-Somali

#### Raw Layer
```
data/raw/source=HuggingFace-Somali_mc4-so/date_accessed=2025-10-20/
└── mc4_manifest.json
```
**Issues:**
- ❌ No run_id
- ❌ No timestamp
- ⚠️ Manifest-only approach is good, but filename lacks metadata

#### Staging Layer
```
data/staging/source=HuggingFace-Somali_mc4-so/date_accessed=2025-10-20/
└── mc4_batch_00000.jsonl
└── mc4_batch_00001.jsonl
...
```
**Issues:**
- ❌ No run_id in filename
- ❌ No timestamp
- ✅ Batched JSONL (good for streaming)
- ⚠️ No checksum/hash for data integrity

#### Processed Layer
```
data/processed/source=HuggingFace-Somali_mc4-so/date_processed=2025-10-20/
└── mc4_processed.txt
```
**Issues:**
- ❌ Same generic naming issues

---

### 4. Sprakbanken-Somali

#### Raw Layer
```
data/raw/source=Sprakbanken-Somali-cilmi/date_accessed=2025-10-19/
├── sprakbankensom_manifest.json
└── somali-cilmi.xml.bz2
```
**Issues:**
- ❌ Inconsistent naming: `sprakbankensom_manifest.json` vs `somali-cilmi.xml.bz2`
- ❌ No run_id
- ❌ No source identifier consistency
- ⚠️ Actual file shows as `SprakbankenSom-cilmi` (truncated, inconsistent casing)

#### Staging Layer
```
data/staging/source=Sprakbanken-Somali-cilmi/date_accessed=2025-10-19/
└── sprakbankensom_extracted.jsonl
```
**Issues:**
- ❌ Generic name across all 23 corpora (collision risk)
- ❌ No corpus_id in filename
- ❌ No run_id

---

### 5. Silver Layer (All Sources)

```
data/silver/source={source}/date_accessed={date}/
└── part-0000.parquet
└── part-0001.parquet
```

**Issues:**
- ❌❌❌ **CRITICAL:** Generic `part-0000.parquet` name for ALL sources
- ❌ No run_id
- ❌ No timestamp
- ❌ No source identifier in filename
- ❌ No record count metadata
- ❌ No data version/schema version
- ❌ Impossible to distinguish files from different runs with same partition path
- ❌ Overwrites risk when same source runs twice in same day

**Example of the problem:**
```bash
# Two runs on same day produce identical filenames:
data/silver/source=BBC-Somali/date_accessed=2025-10-20/part-0000.parquet  # Run 1 (10:00 AM)
data/silver/source=BBC-Somali/date_accessed=2025-10-20/part-0000.parquet  # Run 2 (4:00 PM) - OVERWRITES!
```

---

## Data Engineering Best Practices Violations

### 1. **Missing Run IDs** (Critical)
**Problem:** Cannot trace lineage from raw → staging → processed → silver

**Best Practice:**
```
{source}_{run_id}_{layer}_{partition}.{ext}
```

**Example:**
```
bbc_20251020_143045_raw_article_links.json
bbc_20251020_143045_staging_articles.jsonl
bbc_20251020_143045_silver_part-0000.parquet
```

### 2. **Missing Timestamps** (High Priority)
**Problem:** Cannot determine file creation time from filename alone

**Best Practice:** Include ISO8601 timestamp
```
wikisom_20251020T143045Z_extracted.txt
```

### 3. **Generic Filenames Across Sources** (Critical)
**Problem:** `part-0000.parquet` is same for Wikipedia, BBC, HuggingFace, Språkbanken

**Best Practice:** Include source identifier
```
wikipedia-somali_20251020_143045_part-0000.parquet
bbc-somali_20251020_143045_part-0000.parquet
```

### 4. **Inconsistent Partition Keys** (High Priority)
**Problem:**
- Raw/Staging use: `date_accessed=2025-10-20`
- Processed uses: `date_processed=2025-10-20`
- Silver uses: `date_accessed=2025-10-20`

**Best Practice:** Consistent partitioning scheme across all layers
```
# Option 1: Always use date_accessed
date_accessed=2025-10-20/run_id=20251020_143045/

# Option 2: Add run_id as partition
date_accessed=2025-10-20/run_id=20251020_143045/layer=silver/
```

### 5. **No Data Versioning** (Medium Priority)
**Problem:** Schema changes or pipeline version changes not tracked in filenames

**Best Practice:**
```
{source}_{version}_{run_id}_part-0000.parquet

# Example:
bbc-somali_v2.1_20251020_143045_part-0000.parquet
```

### 6. **No Checksums/Hashes** (Medium Priority)
**Problem:** Data integrity cannot be verified from filename

**Best Practice:** Include content hash in metadata or filename
```
# Metadata file approach (preferred):
bbc-somali_20251020_143045_part-0000.parquet
bbc-somali_20251020_143045_part-0000.parquet.md5

# Or use data lakehouse format (Delta Lake, Iceberg)
```

### 7. **No Record Count Metadata** (Low Priority)
**Problem:** Cannot estimate file size/content without opening

**Best Practice:** Include in metadata file
```
bbc-somali_20251020_143045_part-0000_5000records.parquet
# Or use _metadata.json sidecar
```

---

## Recommended Naming Convention

### General Pattern
```
{source_slug}_{run_id}_{layer}_{descriptive_name}[_{partition_num}].{ext}
```

### Components:
1. **source_slug:** Lowercase, hyphenated source identifier
   - `wikipedia-somali`, `bbc-somali`, `hf-mc4-so`, `sprakbanken-cilmi`

2. **run_id:** Timestamp-based unique identifier
   - Format: `YYYYMMDD_HHMMSS` or `YYYYMMDD_HHMMSS_SSS` (with milliseconds)
   - Example: `20251020_143045`

3. **layer:** Data layer indicator
   - `raw`, `staging`, `processed`, `silver`

4. **descriptive_name:** Purpose-specific identifier
   - `manifest`, `extracted`, `articles`, `cleaned`, `part-0000`

5. **partition_num:** Zero-padded partition number (if applicable)
   - `part-0000`, `part-0001`, `batch-00000`

6. **ext:** File extension with format metadata
   - `.parquet`, `.jsonl`, `.json`, `.txt`, `.xml.bz2`

---

## Proposed File Structure (Examples)

### Wikipedia-Somali

#### Raw Layer
```
data/raw/source=wikipedia-somali/date_accessed=2025-10-20/run_id=20251020_143045/
└── wikipedia-somali_20251020_143045_raw_sowiki-latest-pages-articles.xml.bz2
└── wikipedia-somali_20251020_143045_raw_manifest.json
```

#### Staging Layer
```
data/staging/source=wikipedia-somali/date_accessed=2025-10-20/run_id=20251020_143045/
└── wikipedia-somali_20251020_143045_staging_extracted.txt
└── wikipedia-somali_20251020_143045_staging_metadata.json
```

#### Processed Layer
```
data/processed/source=wikipedia-somali/date_accessed=2025-10-20/run_id=20251020_143045/
└── wikipedia-somali_20251020_143045_processed_cleaned.txt
└── wikipedia-somali_20251020_143045_processed_stats.json
```

#### Silver Layer
```
data/silver/source=wikipedia-somali/date_accessed=2025-10-20/run_id=20251020_143045/pipeline_version=2.1/
├── wikipedia-somali_20251020_143045_silver_part-0000.parquet
├── wikipedia-somali_20251020_143045_silver_part-0001.parquet
└── wikipedia-somali_20251020_143045_silver_metadata.json
```

**Metadata JSON:**
```json
{
  "run_id": "20251020_143045",
  "source": "wikipedia-somali",
  "pipeline_version": "2.1.0",
  "date_accessed": "2025-10-20",
  "date_processed": "2025-10-20T14:45:30Z",
  "total_records": 15000,
  "total_partitions": 3,
  "schema_version": "2.1",
  "checksums": {
    "part-0000": "sha256:abc123...",
    "part-0001": "sha256:def456..."
  },
  "statistics": {
    "total_size_bytes": 45000000,
    "avg_record_size_bytes": 3000
  }
}
```

---

### BBC-Somali

#### Raw Layer
```
data/raw/source=bbc-somali/date_accessed=2025-10-20/run_id=20251020_150230/
├── bbc-somali_20251020_150230_raw_article-links.json
├── bbc-somali_20251020_150230_raw_article-0001.json
├── bbc-somali_20251020_150230_raw_article-0002.json
└── bbc-somali_20251020_150230_raw_manifest.json
```

#### Staging Layer
```
data/staging/source=bbc-somali/date_accessed=2025-10-20/run_id=20251020_150230/
└── bbc-somali_20251020_150230_staging_articles.jsonl
└── bbc-somali_20251020_150230_staging_metadata.json
```

#### Silver Layer
```
data/silver/source=bbc-somali/date_accessed=2025-10-20/run_id=20251020_150230/pipeline_version=2.1/
├── bbc-somali_20251020_150230_silver_part-0000.parquet
└── bbc-somali_20251020_150230_silver_metadata.json
```

---

### HuggingFace (MC4)

#### Raw Layer
```
data/raw/source=hf-mc4-so/date_accessed=2025-10-20/run_id=20251020_160145/
└── hf-mc4-so_20251020_160145_raw_manifest.json
```

#### Staging Layer
```
data/staging/source=hf-mc4-so/date_accessed=2025-10-20/run_id=20251020_160145/
├── hf-mc4-so_20251020_160145_staging_batch-00000.jsonl
├── hf-mc4-so_20251020_160145_staging_batch-00001.jsonl
└── hf-mc4-so_20251020_160145_staging_checkpoint.json
```

#### Silver Layer
```
data/silver/source=hf-mc4-so/date_accessed=2025-10-20/run_id=20251020_160145/pipeline_version=2.1/
├── hf-mc4-so_20251020_160145_silver_part-0000.parquet
├── hf-mc4-so_20251020_160145_silver_part-0001.parquet
└── hf-mc4-so_20251020_160145_silver_metadata.json
```

---

### Språkbanken (Cilmi Corpus)

#### Raw Layer
```
data/raw/source=sprakbanken-cilmi/date_accessed=2025-10-20/run_id=20251020_170330/
├── sprakbanken-cilmi_20251020_170330_raw_corpus.xml.bz2
└── sprakbanken-cilmi_20251020_170330_raw_manifest.json
```

#### Staging Layer
```
data/staging/source=sprakbanken-cilmi/date_accessed=2025-10-20/run_id=20251020_170330/
└── sprakbanken-cilmi_20251020_170330_staging_extracted.jsonl
└── sprakbanken-cilmi_20251020_170330_staging_metadata.json
```

#### Silver Layer
```
data/silver/source=sprakbanken-cilmi/date_accessed=2025-10-20/run_id=20251020_170330/pipeline_version=2.1/
├── sprakbanken-cilmi_20251020_170330_silver_part-0000.parquet
└── sprakbanken-cilmi_20251020_170330_silver_metadata.json
```

---

## MLOps Compatibility Benefits

### 1. **Data Lineage Tracking**
```python
# Can trace from silver back to raw using run_id
run_id = extract_run_id_from_filename("wikipedia-somali_20251020_143045_silver_part-0000.parquet")
# run_id = "20251020_143045"

# Find all related files
raw_files = glob(f"data/raw/**/*{run_id}*")
staging_files = glob(f"data/staging/**/*{run_id}*")
```

### 2. **Automated Data Catalogs** (AWS Glue, Databricks Unity Catalog)
```python
# Parse metadata from filenames
filename = "bbc-somali_20251020_150230_silver_part-0000.parquet"
metadata = parse_filename(filename)
# {
#   "source": "bbc-somali",
#   "run_id": "20251020_150230",
#   "layer": "silver",
#   "partition": "0000",
#   "format": "parquet"
# }
```

### 3. **Incremental Processing**
```python
# Find latest run for source
latest_run = get_latest_run("wikipedia-somali", layer="silver")
# "20251020_143045"

# Process only new runs
new_runs = get_runs_after(latest_run)
```

### 4. **Data Versioning & Time Travel**
```python
# Get data as of specific run
data = read_parquet(f"data/silver/**/wikipedia-somali_20251020_143045_silver_*.parquet")

# Compare two versions
v1 = read_run("20251020_143045")
v2 = read_run("20251021_090000")
diff = compare_runs(v1, v2)
```

### 5. **DVC/Git LFS Integration**
```yaml
# .dvc config
data/silver/source=bbc-somali/date_accessed=2025-10-20/run_id=20251020_150230/:
  desc: BBC Somali articles processed on 2025-10-20
  cmd: python -m somali_dialect_classifier.cli.download_bbcsom
  deps:
    - src/somali_dialect_classifier/preprocessing/bbc_somali_processor.py
  outs:
    - bbc-somali_20251020_150230_silver_part-0000.parquet
```

---

## Migration Strategy

### Phase 1: Add run_id to filenames (Non-breaking)
- Keep existing partition structure
- Add run_id to filename only
- Update SilverDatasetWriter, BasePipeline

### Phase 2: Add run_id partition (Breaking change)
- Add `run_id=` to partition path
- Migrate existing files (optional)

### Phase 3: Standardize all layer filenames
- Update all processors (Wikipedia, BBC, HuggingFace, Språkbanken)
- Add metadata JSON sidecars

### Phase 4: Add pipeline_version partition
- Enable schema evolution tracking

---

## Implementation Checklist

### Immediate (High Priority)
- [ ] Add run_id to silver layer filenames
- [ ] Add run_id to staging layer filenames
- [ ] Add run_id to processed layer filenames
- [ ] Fix `date_processed` vs `date_accessed` inconsistency
- [ ] Add metadata JSON sidecars for silver layer

### Short-term (Medium Priority)
- [ ] Standardize source slugs across all processors
- [ ] Add run_id partition to directory structure
- [ ] Add checksum verification
- [ ] Update file reading logic to handle new naming

### Long-term (Low Priority)
- [ ] Add pipeline_version partition
- [ ] Migrate to Delta Lake/Iceberg for built-in versioning
- [ ] Implement data catalog integration
- [ ] Add automated lineage tracking

---

## Conclusion

**Current state:** File naming conventions are inconsistent, make lineage tracking difficult, and violate data engineering best practices.

**Recommended action:** Implement Phase 1 changes immediately to add run_id to all filenames, then plan migration for partitioning structure changes.

**ROI:** Improved observability, easier debugging, automated data catalog integration, and MLOps compatibility.
