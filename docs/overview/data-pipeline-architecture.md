# Data Pipeline Documentation
# Data Pipeline Architecture

**Detailed architecture of the data collection and processing pipeline including medallion architecture, deduplication, and state management.**

**Last Updated:** 2025-11-21

Comprehensive guide to the ETL (Extract, Transform, Load) pipeline architecture, data flows, and processing stages.

## Table of Contents

1. [Pipeline Overview](#pipeline-overview)
2. [Data Layers](#data-layers)
3. [Processing Stages](#processing-stages)
4. [Source-Specific Pipelines](#source-specific-pipelines)
5. [Data Quality](#data-quality)
6. [Performance Optimization](#performance-optimization)
7. [Monitoring and Observability](#monitoring-and-observability)

## Pipeline Overview

The Somali Dialect Classifier implements a **medallion architecture** with three data layers:

```
┌──────────────┐
│   SOURCES    │  Wikipedia dumps, BBC articles, HuggingFace datasets
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ BRONZE (Raw) │  Immutable raw data (XML, JSON, HTML)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ STAGING      │  Intermediate extracts (TXT, JSON)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│SILVER (Clean)│  Validated, schema-enforced Parquet
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ GOLD (Future)│  Dialect-labeled, model-ready datasets
└──────────────┘
```

### Pipeline Execution Flow

```python
# CLI entry point
bbcsom-download --max-articles 100

# Internally calls
processor = BBCSomaliProcessor(max_articles=100)
processor.process()

# Which executes:
# 1. Download/discover raw data → Bronze layer
# 2. Extract text from raw formats → Staging layer
# 3. Clean and filter text → Silver layer
# 4. Log statistics and metadata
```

## Production Infrastructure

All processors are integrated with production-ready MLOps infrastructure:

### Observability

**Structured Logging:**
```python
# Automatic context injection
from somali_dialect_classifier.utils.logging_utils import set_context, generate_run_id

run_id = generate_run_id("bbc")  # "20250119_103045_bbc_a1b2c3d4"
set_context(run_id=run_id, source="BBC-Somali", phase="fetch")

# All subsequent logs include run_id, source, phase
logger.info("Article fetched", url="...", http_status=200)
# → {"timestamp": "...", "run_id": "20250119_103045_bbc_a1b2c3d4", "source": "BBC-Somali", ...}
```

**Metrics Collection:**
```python
from somali_dialect_classifier.utils.metrics import MetricsCollector, QualityReporter

metrics = MetricsCollector(run_id, "BBC-Somali")
metrics.increment('urls_discovered', 100)
metrics.record_fetch_duration(234.5)  # milliseconds
metrics.record_http_status(200)

# Export metrics
metrics.export_json(Path("data/metrics/20250119_103045_bbc_discovery.json"))

# Generate quality report
QualityReporter(metrics).generate_markdown_report(Path("data/reports/quality.md"))
```

**Quality Reports:**

Automated reports include:
- Executive summary (✅ Healthy, ⚠️ Warning, ❌ Critical)
- Processing statistics (success/failure rates)
- Performance metrics (mean, median, p95, p99)
- HTTP status distribution
- Automated recommendations

### State Management

**Crawl Ledger:**
```python
from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger

ledger = get_ledger()

# Discovery phase
ledger.discover_url("https://example.com/article", "bbc", metadata={})

# Fetch phase
if ledger.should_fetch_url(url, force=False):
    # Fetch article
    ledger.mark_fetched(url, http_status=200, content_length=5000)

# Processing phase
ledger.mark_processed(url, text_hash="sha256...", silver_id="uuid...")
```

**URL States:**
- `discovered` → `fetched` → `processed` ✅
- `discovered` → `fetched` → `failed` ❌
- `discovered` → `skipped` (already processed)
- `discovered` → `duplicate` (dedup detected)

### Deduplication

**Three-Phase Strategy** to eliminate duplicates across pipeline runs:

**Phase 1: Discovery-Stage Deduplication** ⭐ NEW
- Check crawl ledger BEFORE fetching/streaming to skip already-processed URLs
- Prevents re-downloading identical data on subsequent runs
- Saves bandwidth and enables cross-run idempotency

```python
from somali_dialect_classifier.preprocessing.crawl_ledger import get_ledger

ledger = get_ledger()

# Phase 1: Skip already-processed URLs
if ledger.should_fetch_url(url, force=False):
    fetch_and_process(url)
else:
    logger.info(f"Skipping already-processed URL: {url}")
    metrics.increment("records_skipped_discovery_dedup")
```

**Phase 2: Extraction-Stage Deduplication**
1. **Exact Deduplication** (SHA256 hash):
```python
from somali_dialect_classifier.preprocessing.dedup import DedupEngine, DedupConfig

config = DedupConfig(hash_fields=["text", "url"], enable_minhash=True)
dedup = DedupEngine(config)

text_hash, minhash_sig = dedup.get_content_hash(record)
if dedup.is_exact_duplicate(text_hash):
    logger.info("Exact duplicate detected")
```

2. **Near-Duplicate Detection** (MinHash LSH):
   - Jaccard similarity threshold: 0.85
   - Detects paraphrased or lightly edited content
   - In-memory LSH index for current batch

**Phase 3: Processing-Stage Cross-Dataset Deduplication**
- Persistent LSH index saved to disk for cross-run near-duplicate detection
- Enables detecting duplicates ACROSS different sources and runs

```python
# Enable LSH persistence for Phase 3
config = DedupConfig(
    hash_fields=["text", "url"],
    enable_minhash=True,
    similarity_threshold=0.85,
    storage_path=Path("data/ledger/lsh_index_{source}.pkl")
)
```

**For comprehensive guide**, see [Deduplication Strategy](../howto/deduplication.md)

### Configuration

**YAML-Based Settings:**

```yaml
# config/production.yaml
sources:
  bbc:
    rate_limiting:
      max_requests_per_hour: 60
      min_delay_seconds: 5
      max_delay_seconds: 10
    quality:
      min_length_threshold: 50
      langid_confidence_threshold: 0.3
```

**Environment Overrides:**
```bash
export SDC_SCRAPING__BBC__MAX_REQUESTS_PER_HOUR=100
```

### Data Lineage

**Run ID Continuity:**

All phases share the same run_id for tracking:

```
download() → run_id: wiki_20250119_123456
  ├─ data/raw/source=Wikipedia-Somali/date_accessed=2025-01-19/
  ├─ data/metrics/wiki_20250119_123456_discovery.json
  └─ manifest stores run_id

extract() → same run_id: wiki_20250119_123456
  ├─ data/staging/source=Wikipedia-Somali/date_accessed=2025-01-19/
  ├─ data/metrics/wiki_20250119_123456_extraction.json
  └─ data/reports/wiki_20250119_123456_quality_report.md

process() → same run_id
  └─ data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-01-19/
```

This enables:
- Tracing data from raw to silver
- Correlating logs, metrics, and outputs
- Reproducing specific runs
- Debugging issues across pipeline stages

## File Naming Conventions

All processed files follow a consistent naming pattern for traceability and lineage tracking.

### Naming Pattern

```
{source_slug}_{run_id}_{layer}_{descriptive_name}[_{partition_num}].{ext}
```

**Components**:
- **source_slug**: Lowercase hyphenated source identifier
  - `wikipedia-somali`: Wikipedia articles
  - `bbc-somali`: BBC news articles
  - `hf-mc4-so`: HuggingFace MC4 Somali subset
  - `sprakbanken-cilmi`: Språkbanken Cilmi corpus
  - `sprakbanken-ogaden`: Språkbanken Ogaden corpus

- **run_id**: Timestamp in format `YYYYMMDD_HHMMSS`
  - Example: `20251020_143045`
  - Unique per pipeline execution
  - Enables lineage tracking across all pipeline stages
  - Links files to logs, metrics, and quality reports

- **layer**: Data processing layer
  - `raw`: Immutable source data
  - `staging`: Intermediate extracts
  - `processed`: Cleaned text
  - `silver`: Production-ready Parquet

- **descriptive_name**: Purpose-specific identifier
  - `manifest`: Dataset metadata
  - `extracted`: Extracted raw text
  - `articles`: Article collection
  - `cleaned`: Cleaned/processed text
  - `part-0000`, `part-0001`: Partitioned files
  - `metadata`: Metadata sidecar

- **partition_num**: Optional zero-padded partition number
  - Format: `0000`, `0001`, `0002`, etc.
  - Used for files split across multiple partitions

### Examples by Source

**Wikipedia-Somali**:
```
# Staging
wikipedia-somali_20251020_143045_staging_extracted.txt

# Processed
wikipedia-somali_20251020_143045_processed_cleaned.txt

# Silver
wikipedia-somali_20251020_143045_silver_part-0000.parquet
wikipedia-somali_20251020_143045_silver_metadata.json
```

**BBC-Somali**:
```
# Raw
bbc-somali_20251020_150230_raw_article-links.json
bbc-somali_20251020_150230_raw_article-0001.json
bbc-somali_20251020_150230_raw_article-0002.json

# Staging
bbc-somali_20251020_150230_staging_articles.jsonl

# Processed
bbc-somali_20251020_150230_processed_cleaned.txt

# Silver
bbc-somali_20251020_150230_silver_part-0000.parquet
bbc-somali_20251020_150230_silver_metadata.json
```

**HuggingFace MC4**:
```
# Raw
mc4_20251020_153000_raw_manifest.json

# Staging
mc4_20251020_153000_staging_batch-000000.jsonl
mc4_20251020_153000_staging_batch-000001.jsonl

# Processed
mc4_20251020_153000_processed_cleaned.txt

# Silver
hf-mc4-so_20251020_153000_silver_part-0000.parquet
hf-mc4-so_20251020_153000_silver_metadata.json
```

**Språkbanken**:
```
# Raw
sprakbanken-cilmi_20251020_160000_raw_manifest.json

# Staging
sprakbanken-cilmi_20251020_160000_staging_extracted.jsonl

# Processed
sprakbanken-cilmi_20251020_160000_processed_cleaned.txt

# Silver
sprakbanken-cilmi_20251020_160000_silver_part-0000.parquet
sprakbanken-cilmi_20251020_160000_silver_metadata.json
```

### Key Benefits

1. **Traceability**: Every file includes run_id for complete lineage tracking
2. **No Overwrites**: Multiple runs on same day never collide
3. **Debuggability**: Can trace from silver → processed → staging → raw using run_id
4. **Log Correlation**: run_id matches structured logs and metrics files
5. **Reproducibility**: Exact run can be identified and reproduced
6. **Automation**: Predictable patterns enable automated data catalog integration

### Partition Key Consistency

**Old Behavior** (INCONSISTENT):
- Raw/Staging: `date_accessed=YYYY-MM-DD`
- Processed: `date_processed=YYYY-MM-DD` ⚠️ DIFFERENT KEY

**New Behavior** (CONSISTENT):
- All layers: `date_accessed=YYYY-MM-DD` ✅ SAME KEY

This consistency enables:
- Simpler queries (same partition key across layers)
- Correct temporal alignment (all layers track access date)
- Better data catalog integration

## Data Layers

### Bronze Layer (Raw)

**Purpose**: Immutable storage of original data in native formats

**Location**: `data/raw/source={SOURCE}/date_accessed={DATE}/`

**Characteristics**:
- ✅ **Immutable**: Never modified after download
- ✅ **Format-preserving**: XML, JSON, HTML as-is
- ✅ **Partitioned by source and date**: Enable time-travel queries
- ❌ **Not queryable**: Require parsing for analysis

**Examples**:
```
data/raw/
├── source=Wikipedia-Somali/
│   └── date_accessed=2025-01-15/
│       └── sowiki-latest-pages-articles.xml.bz2  # 500MB compressed (no run_id - external source)
│
└── source=BBC-Somali/
    └── date_accessed=2025-01-15/
        ├── bbc-somali_20250115_143000_raw_article-links.json     # Discovered URLs
        └── bbc-somali_20250115_143000_raw_article-0001.json      # Individual articles
```

**File Naming Pattern**: `{source-slug}_{run_id}_{layer}_{descriptive-name}.{ext}`
- Wikipedia dumps don't include run_id (external source)
- All processed files include run_id for traceability

**Code**:
```python
# BasePipeline._get_raw_dir()
raw_dir = config.data.raw_dir / f"source={self.source}" / f"date_accessed={date}"
raw_dir.mkdir(parents=True, exist_ok=True)
```

### Staging Layer (Intermediate)

**Purpose**: Extracted text before cleaning, useful for debugging

**Location**: `data/staging/source={SOURCE}/date_accessed={DATE}/`

**Characteristics**:
- ⚠️ **Semi-structured**: Extracted but not cleaned
- ✅ **Text format**: TXT or JSON for easy inspection
- ⚠️ **Contains markup**: May have residual HTML/Wiki syntax

**Examples**:
```
data/staging/
├── source=Wikipedia-Somali/
│   └── date_accessed=2025-01-15/
│       └── wikipedia-somali_20250115_143000_staging_extracted.txt     # All pages concatenated
│
└── source=BBC-Somali/
    └── date_accessed=2025-01-15/
        └── bbc-somali_20250115_143000_staging_articles.jsonl          # JSONL format (one article per line)
```

**File Naming**: Includes run_id for lineage tracking across pipeline stages

**When to Use**:
- Debugging extraction logic
- Inspecting raw content before cleaning
- Verifying markup removal completeness

### Silver Layer (Cleaned)

**Purpose**: Production-ready, schema-enforced, validated datasets

**Location**: `data/processed/silver/source={SOURCE}/date_accessed={DATE}/`

**Characteristics**:
- ✅ **Schema-enforced**: PyArrow schema prevents drift
- ✅ **Validated**: Quality filters applied
- ✅ **Deduplicated**: Hash-based ID prevents duplicates
- ✅ **Queryable**: Parquet columnar format

**Schema (v2.1)**:
```python
SILVER_SCHEMA = pa.schema([
    ('id', pa.string()),               # sha256(text)[:16] + source_prefix
    ('text', pa.string()),             # Cleaned Somali text
    ('source', pa.string()),           # "Wikipedia-Somali", "BBC-Somali"
    ('source_type', pa.string()),      # "encyclopedia", "news", "web", "corpus"
    ('date_accessed', pa.date32()),    # Collection timestamp
    ('language', pa.string()),         # "so" (ISO 639-1)
    ('license', pa.string()),          # "CC-BY-SA-3.0", "BBC Terms", "ODC-BY-1.0", "CC BY 4.0"
    ('token_count', pa.int32()),       # Whitespace-based word count
    ('metadata', pa.string()),         # JSON: {"title", "url", "detected_lang", ...}
    ('domain', pa.string()),           # v2.0: Content domain (news, encyclopedia, web, etc.)
    ('embedding', pa.string()),        # v2.0: Embedding vector (JSON, currently null)
    ('register', pa.string()),         # v2.1: Linguistic register (formal/informal/colloquial)
])
```

**Register field** (NEW in v2.1):
- All current sources return `"formal"` (Wikipedia, BBC, HuggingFace MC4, Språkbanken)
- Future social media sources will use `"informal"`
- Future conversational sources will use `"colloquial"`

**Examples**:
```
data/processed/silver/
├── source=Wikipedia-Somali/
│   └── date_accessed=2025-01-15/
│       ├── wikipedia-somali_20250115_143000_silver_part-0000.parquet     # 50,000 articles
│       └── wikipedia-somali_20250115_143000_silver_metadata.json         # Metadata sidecar
│
└── source=BBC-Somali/
    └── date_accessed=2025-01-15/
        ├── bbc-somali_20250115_150230_silver_part-0000.parquet           # 1,200 articles
        └── bbc-somali_20250115_150230_silver_metadata.json               # Metadata sidecar
```

**Metadata JSON Sidecar** (NEW):
```json
{
  "run_id": "20250115_143000",
  "source": "Wikipedia-Somali",
  "pipeline_version": "2.1.0",
  "date_accessed": "2025-01-15",
  "date_processed": "2025-01-15T14:45:30Z",
  "total_records": 50000,
  "total_partitions": 1,
  "schema_version": "2.1",
  "checksums": {
    "part-0000": {
      "sha256": "abc123def456...",
      "size_bytes": 45000000,
      "record_count": 50000
    }
  },
  "statistics": {
    "total_size_bytes": 45000000,
    "avg_record_size_bytes": 900,
    "min_tokens": 50,
    "max_tokens": 15000,
    "avg_tokens": 342
  }
}
```

**Benefits of Metadata Sidecars**:
- ✅ **Data Integrity**: SHA256 checksums for corruption detection
- ✅ **Lineage Tracking**: run_id links to logs and metrics
- ✅ **Statistics**: Record counts, sizes, token statistics
- ✅ **Version Control**: Pipeline and schema versions tracked
- ✅ **Automation Ready**: Machine-readable metadata for data catalogs

**Querying**:
```python
import pandas as pd

# Load entire partition
df = pd.read_parquet("data/processed/silver/source=BBC-Somali/")

# Filter by metadata
df[df['token_count'] > 100]

# Aggregate by source
df.groupby('source')['token_count'].describe()
```

## Processing Stages

### Stage 1: Extraction

**Purpose**: Discover and download raw data from sources

**Wikipedia Flow**:
```python
def download(self) -> Path:
    # 1. Construct download URL
    url = "https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2"

    # 2. Check if already downloaded (skip if not forced)
    if raw_file.exists() and not self.force:
        return raw_file

    # 3. Stream download with progress bar
    response = requests.get(url, stream=True)
    with open(raw_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024*1024):
            f.write(chunk)

    return raw_file
```

**BBC Flow**:
```python
def download(self) -> Path:
    # 1. Check cache and validate parameters
    cached_links = self._load_cached_links()
    if cached_links and self._cache_is_valid(cached_links):
        return cached_links

    # 2. Discover article URLs
    article_urls = []
    article_urls.extend(self._discover_from_homepage())
    article_urls.extend(self._discover_from_sitemap())
    article_urls.extend(self._discover_from_topics(["business", "sports"]))

    # 3. Scrape individual articles with rate limiting
    for url in article_urls[:self.max_articles]:
        time.sleep(random.uniform(3, 6))  # Rate limit
        article = self._scrape_article(url)
        self._save_article(article)
```

**Key Considerations**:
- **Idempotency**: Re-running download doesn't duplicate data
- **Resume capability**: Wikipedia downloads can be resumed
- **Rate limiting**: BBC scraper respects robots.txt
- **Error handling**: Network failures logged, retried with backoff

### Stage 2: Text Cleaning

**Purpose**: Remove markup, normalize whitespace, prepare for analysis

**Pipeline**:
```python
# Create cleaning pipeline (composition pattern)
cleaner = TextCleaningPipeline([
    WikiMarkupCleaner(),      # Remove [[links]], {{templates}}
    WhitespaceCleaner(),      # Collapse newlines, trim spaces
])

# Apply to each record
cleaned_text = cleaner.clean(raw_record.text)
```

**Cleaning Operations**:

1. **Wiki Markup Removal** (`WikiMarkupCleaner`):
   ```python
   # Before
   "[[Soomaaliya|Somalia]] waa waddan ku yaal [[Geeska Afrika]]."

   # After
   "Somalia waa waddan ku yaal Geeska Afrika."
   ```

2. **HTML Stripping** (`HTMLCleaner`):
   ```python
   # Before
   "<p>Muqdisho &mdash; magaalada caasimadda ah.</p>"

   # After
   "Muqdisho — magaalada caasimadda ah."
   ```

3. **Whitespace Normalization** (`WhitespaceCleaner`):
   ```python
   # Before
   "Soomaaliya\n\n\nwaa    waddan."

   # After
   "Soomaaliya waa waddan."
   ```

**Configuration**:
```python
# Wikipedia articles
create_wikipedia_cleaner(min_length=50)

# News articles
create_html_cleaner(min_length=50)
```

### Stage 3: Quality Filtering

**Purpose**: Validate text quality, enrich metadata, reject low-quality records

**Filter Execution**:
```python
filter_stats = Counter()

for raw_record in self._extract_records():
    cleaned_text = self.text_cleaner.clean(raw_record.text)

    # Execute filter chain
    filter_metadata = {}
    passed_all_filters = True

    for filter_func, filter_kwargs in self.record_filters:
        passes, metadata_updates = filter_func(cleaned_text, **filter_kwargs)

        if not passes:
            filter_stats[f"filtered_by_{filter_func.__name__}"] += 1
            passed_all_filters = False
            break  # Short-circuit on first failure

        filter_metadata.update(metadata_updates)

    if passed_all_filters:
        # Build and write record
        record = build_silver_record(cleaned_text, source, metadata=filter_metadata)
        records.append(record)
```

**Filter Examples**:

1. **Minimum Length** (Reject short snippets):
   ```python
   self.record_filters.append((min_length_filter, {"threshold": 50}))
   # Rejects: "Soomaaliya." (10 chars)
   # Accepts: "Soomaaliya waa waddan ku yaal Geeska Afrika..." (50+ chars)
   ```

2. **Language Detection** (Reject non-Somali):
   ```python
   self.record_filters.append((langid_filter, {
       "allowed_langs": {"so"},
       "confidence_threshold": 0.3
   }))
   # Rejects: "This is an English article..."
   # Accepts: "Muqdisho waa magaalada ugu weyn..."
   ```

3. **Topic Enrichment** (Add metadata without rejecting):
   ```python
   topic_lexicons = {
       "sports": ["kubadda", "ciyaaryahan", "kooxda"],
       "politics": ["xukuumad", "madaxweyne", "doorasho"]
   }
   self.record_filters.append((topic_lexicon_enrichment_filter, {
       "ruleset": topic_lexicons,
       "enrich_only": True  # Don't reject, just enrich
   }))
   # Adds: {"primary_dialect": "sports", "dialect_markers": {"sports": 3}}
   ```

**Filter Statistics Logging**:
```
INFO - Processing 10,000 records from Wikipedia-Somali
INFO - Filter statistics:
INFO -   filtered_by_min_length_filter: 234 records (2.3%)
INFO -   filtered_by_langid_filter: 567 records (5.7%)
INFO - Successfully processed 9,199 records (91.99%)
```

### Stage 4: Record Building

**Purpose**: Construct schema-compliant records with metadata

**Record Builder**:
```python
def build_silver_record(
    cleaned_text: str,
    source: str,
    source_type: str,
    date_accessed: datetime,
    language: str,
    license: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build schema-compliant silver record."""

    # Generate deterministic ID
    text_hash_value = text_hash(cleaned_text)
    record_id = generate_record_id(cleaned_text, source)

    # Count tokens
    token_count = count_tokens(cleaned_text)

    # Serialize metadata
    metadata_json = json.dumps(metadata or {}, ensure_ascii=False)

    return {
        'id': record_id,
        'text': cleaned_text,
        'source': source,
        'source_type': source_type,
        'date_accessed': date_accessed.date(),
        'language': language,
        'license': license,
        'token_count': token_count,
        'metadata': metadata_json,
    }
```

**Metadata Examples**:
```json
// Wikipedia
{
  "title": "Muqdisho",
  "url": "https://so.wikipedia.org/wiki/Muqdisho",
  "namespace": 0,
  "revision_id": 12345
}

// BBC
{
  "title": "Wararka Maanta",
  "url": "https://www.bbc.com/somali/articles/...",
  "published_date": "2025-01-15",
  "primary_dialect": "news",
  "detected_lang": "so",
  "lang_confidence": 0.92
}
```

### Stage 5: Batch Writing

**Purpose**: Atomically write validated records to Parquet

**Writer Logic**:
```python
def write(
    self,
    records: List[Dict[str, Any]],
    source: str,
    date_accessed: datetime
) -> Optional[Path]:
    """Write records to partitioned Parquet file."""

    if not records:
        return None

    # 1. Create DataFrame
    df = pd.DataFrame(records)

    # 2. Convert to PyArrow Table with explicit schema
    table = pa.Table.from_pandas(df, schema=SILVER_SCHEMA)

    # 3. Determine partition path
    partition_dir = self.base_dir / f"source={source}" / f"date_accessed={date_str}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    # 4. Write atomically (tmp file + rename)
    tmp_path = partition_dir / f".tmp-part-{uuid.uuid4().hex[:8]}.parquet"
    final_path = partition_dir / "part-0000.parquet"

    pq.write_table(table, tmp_path, compression='snappy')
    tmp_path.rename(final_path)

    return final_path
```

**Atomic Write Benefits**:
- **Crash safety**: Partial writes don't corrupt data
- **Concurrency**: Readers never see incomplete files
- **Idempotency**: Re-running overwrites cleanly

## Source-Specific Pipelines

### Wikipedia Pipeline

**Data Source**: MediaWiki XML dumps from dumps.wikimedia.org

**Pipeline Steps**:

1. **Download**:
   ```bash
   wget https://dumps.wikimedia.org/sowiki/latest/sowiki-latest-pages-articles.xml.bz2
   # → data/raw/source=Wikipedia-Somali/date_accessed=2025-01-15/
   ```

2. **Extract**:
   ```python
   import mwxml
   dump = mwxml.Dump.from_file(bz2.BZ2File(xml_path))

   for page in dump:
       if page.namespace == 0:  # Main namespace only
           for revision in page:
               yield RawRecord(
                   text=revision.text,
                   metadata={"title": page.title, "namespace": page.namespace}
               )
   ```

3. **Clean**:
   ```python
   cleaner = create_wikipedia_cleaner()
   cleaned = cleaner.clean(raw_text)
   # Removes: [[links]], {{templates}}, ===headers===, <ref>citations</ref>
   ```

4. **Filter**:
   ```python
   def _register_filters(self):
       self.record_filters.append((min_length_filter, {"threshold": 50}))
       self.record_filters.append((langid_filter, {"confidence_threshold": 0.3}))
   ```

5. **Write**: Parquet with schema enforcement

**Memory Optimization**:
```python
# Stream processing with buffer limit
buffer = []
for page in dump:
    buffer.append(page)
    if len(buffer) >= self.batch_size or sys.getsizeof(buffer) > 10_000_000:
        self.silver_writer.write(buffer, ...)
        buffer.clear()
```

**Expected Output**:
- **Input**: 50,000 Wikipedia articles (500MB XML)
- **After cleaning**: 45,000 articles (10% removed for length/quality)
- **Silver output**: 40MB Parquet (10x compression)

### BBC Pipeline

**Data Source**: BBC Somali news website (bbc.com/somali)

**Pipeline Steps**:

1. **Discover**:
   ```python
   def _discover_articles(self) -> List[str]:
       urls = set()
       urls.update(self._discover_from_homepage())        # 10-20 articles
       urls.update(self._discover_from_sitemap())         # 500+ articles
       urls.update(self._discover_from_topics(["business", "sports"]))  # 100+ each
       return list(urls)[:self.max_articles]
   ```

2. **Scrape**:
   ```python
   def _scrape_article(self, url: str) -> Dict:
       time.sleep(random.uniform(3, 6))  # Rate limit

       response = requests.get(url, headers={"User-Agent": "Research Bot"})
       soup = BeautifulSoup(response.content, 'html.parser')

       return {
           "title": soup.find('h1').get_text(),
           "text": soup.find('article').get_text(),
           "url": url,
           "scraped_at": datetime.now().isoformat()
       }
   ```

3. **Clean**:
   ```python
   cleaner = create_html_cleaner()
   cleaned = cleaner.clean(raw_html)
   # Removes: <tags>, decodes &entities;
   ```

4. **Filter + Enrich**:
   ```python
   def _register_filters(self):
       self.record_filters.append((min_length_filter, {"threshold": 50}))
       self.record_filters.append((langid_filter, {"confidence_threshold": 0.3}))

       # Topic enrichment for downstream analysis
       topic_lexicons = {
           "sports": ["kubadda", "ciyaaryahan", "kooxda"],
           "politics": ["xukuumad", "madaxweyne", "baarlamaan"],
           "economy": ["dhaqaale", "ganacsiga", "suuq"]
       }
       self.record_filters.append((topic_lexicon_enrichment_filter, {
           "ruleset": topic_lexicons,
           "enrich_only": True
       }))
   ```

5. **Cache Management**:
   ```python
   # Save discovered links with parameters
   {
       "max_articles_limit": 100,
       "discovered_at": "2025-01-15T10:30:00",
       "article_urls": ["https://...", ...]
   }

   # Invalidate cache if max_articles changes
   if cached["max_articles_limit"] != self.max_articles:
       self.logger.info("Cache invalidated: max_articles changed")
       return None  # Re-discover
   ```

**Expected Output**:
- **Input**: 100 news articles (HTML pages)
- **After cleaning**: 95 articles (5% removed for length/language)
- **Silver output**: 2MB Parquet

## Data Quality

### Quality Metrics

**Per-Source Statistics**:
```
Source: Wikipedia-Somali
  Total extracted: 50,000 articles
  Filtered by length: 2,300 (4.6%)
  Filtered by language: 5,700 (11.4%)
  Final count: 42,000 (84.0%)
  Avg token count: 342
  Total tokens: 14,364,000

Source: BBC-Somali
  Total extracted: 100 articles
  Filtered by length: 3 (3.0%)
  Filtered by language: 2 (2.0%)
  Final count: 95 (95.0%)
  Avg token count: 456
  Total tokens: 43,320
```

### Deduplication

**Hash-Based ID Generation**:
```python
def generate_record_id(text: str, source: str) -> str:
    """Generate unique ID: {source_prefix}_{text_hash}."""
    text_hash_value = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    source_prefix = source.replace('-', '').replace('_', '')[:4].upper()
    return f"{source_prefix}_{text_hash_value}"

# Example IDs
"WIKI_a3f5b2c1d4e6f7a8"  # Wikipedia article
"BBCS_1b2c3d4e5f6a7b8c"  # BBC article
```

**Duplicate Detection**:
```bash
# Count duplicates across all sources
python scripts/deduplicate_silver.py --dry-run

# Output
Found 234 duplicate records (0.5% of total)
  Wikipedia-Somali: 200 duplicates
  BBC-Somali: 34 duplicates
```

### Schema Validation

**Enforcement via PyArrow**:
```python
# Schema mismatch raises exception
try:
    table = pa.Table.from_pandas(df, schema=SILVER_SCHEMA)
except pa.ArrowInvalid as e:
    logger.error(f"Schema validation failed: {e}")
    # Example: "Field 'token_count' expected int32, got int64"
```

**Validation Checks**:
- ✅ All required fields present
- ✅ Correct data types (string, int32, date32)
- ✅ Non-null constraints (id, text, source)
- ✅ JSON-serializable metadata

## Performance Optimization

### Throughput

**Current Performance** (M1 MacBook Pro, 16GB RAM):

| Pipeline | Records/sec | Bottleneck | Optimization |
|----------|------------|------------|--------------|
| Wikipedia | 500-800 | XML parsing | Stream with mwxml |
| BBC | 0.2-0.3 | Network I/O | Rate limiting (required) |

### Memory Usage

**Wikipedia Pipeline**:
- **Peak memory**: ~200MB (10MB buffer + XML parser overhead)
- **Optimization**: Stream processing, batch writes

**BBC Pipeline**:
- **Peak memory**: ~50MB (HTML parsing + in-memory cache)
- **Optimization**: Process articles sequentially

### Disk Usage

**Compression Ratios**:

| Layer | Format | Size (10K records) | Compression |
|-------|--------|-------------------|-------------|
| Raw | XML/JSON | 500 MB | 1x (baseline) |
| Staging | TXT | 450 MB | 1.1x |
| Silver | Parquet (snappy) | 40 MB | 12.5x |

**Partitioning Benefits**:
- **Query pruning**: Read only relevant partitions
- **Incremental updates**: Add new dates without reprocessing
- **Parallel I/O**: Multiple workers read different partitions

## Monitoring and Observability

### Logging

**Log Levels**:
```python
# config.py
logging.level = "INFO"  # DEBUG, INFO, WARNING, ERROR

# Output
INFO - [Wikipedia-Somali] Starting extraction from sowiki-latest-pages-articles.xml.bz2
INFO - [Wikipedia-Somali] Extracted 10,000 pages (elapsed: 12.3s)
INFO - [Wikipedia-Somali] Filter statistics:
INFO -   filtered_by_min_length_filter: 234 records
INFO -   filtered_by_langid_filter: 567 records
INFO - [Wikipedia-Somali] Wrote 9,199 records to silver layer
```

**Log Files**:
```
logs/
├── download_wikisom.log         # Wikipedia pipeline logs
├── download_wikisom.log.1       # Rotated backup (5MB max)
└── download_bbcsom.log          # BBC pipeline logs
```

**Rotation Policy**:
- **Max size**: 5MB per log file
- **Backup count**: 3 rotated files
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Metrics

**Filter Statistics** (logged at end of each run):
```python
filter_stats = Counter()
# ...
logger.info("Filter statistics:")
for filter_reason, count in filter_stats.most_common():
    logger.info(f"  {filter_reason}: {count} records")
```

**Processing Metrics**:
- **Total records extracted**: Count from source
- **Records per filter**: Rejection counts
- **Final record count**: Silver layer output
- **Processing time**: Elapsed seconds
- **Throughput**: Records/second

### Future: MLflow Integration

**Planned Metrics Tracking**:
```python
import mlflow

with mlflow.start_run(run_name=f"process_{source}_{date}"):
    mlflow.log_param("source", source)
    mlflow.log_param("date_accessed", date)

    # Log filter statistics
    mlflow.log_metric("total_extracted", total_count)
    mlflow.log_metric("filtered_by_length", length_filter_count)
    mlflow.log_metric("filtered_by_language", language_filter_count)
    mlflow.log_metric("final_count", final_count)
    mlflow.log_metric("processing_time_sec", elapsed_time)
```

**Benefits**:
- **Historical tracking**: Compare runs over time
- **Drift detection**: Monitor filter rejection rates
- **Performance analysis**: Identify slowdowns

## Troubleshooting

### Common Issues

**Issue: Wikipedia download fails**
```
ERROR - Failed to download Wikipedia dump: ConnectionError
```
**Solution**: Check network, verify URL, retry with exponential backoff

**Issue: BBC scraping blocked**
```
ERROR - HTTP 429 Too Many Requests
```
**Solution**: Increase rate limit delay, verify User-Agent compliance

**Issue: Memory error during processing**
```
MemoryError: Unable to allocate array
```
**Solution**: Reduce `batch_size` in config, increase system RAM

**Issue: Schema validation error**
```
pa.ArrowInvalid: Field 'token_count' expected int32, got int64
```
**Solution**: Ensure `count_tokens()` returns `int` not `np.int64`

### Debug Mode

**Enable verbose logging**:
```bash
# Set environment variable
export SDC_LOGGING__LEVEL=DEBUG

# Or in .env file
SDC_LOGGING__LEVEL=DEBUG
```

**Debug output**:
```
DEBUG - [Wikipedia-Somali] Parsing page: "Muqdisho"
DEBUG - [Wikipedia-Somali] Raw text length: 5432 chars
DEBUG - [Wikipedia-Somali] Cleaned text length: 4821 chars
DEBUG - [Wikipedia-Somali] Filter min_length_filter: PASS
DEBUG - [Wikipedia-Somali] Filter langid_filter: PASS (confidence=0.87)
DEBUG - [Wikipedia-Somali] Built record: id=WIKI_a3f5b2c1d4e6f7a8
```

## Pipeline Maintenance

### Regular Tasks

**Weekly**:
- ✅ Run `wikisom-download --force` to refresh Wikipedia data
- ✅ Run `bbcsom-download` to collect new articles
- ✅ Review logs for errors or anomalies

**Monthly**:
- ✅ Run deduplication: `python scripts/deduplicate_silver.py`
- ✅ Analyze filter statistics for drift
- ✅ Archive old raw data (Bronze layer)

**Quarterly**:
- ✅ Review and update Somali word list (langid_filter)
- ✅ Add new topic lexicons (topic_lexicon_enrichment_filter)
- ✅ Benchmark performance and optimize

### Data Retention Policy

**Recommended**:
- **Bronze (Raw)**: Keep 30 days, then archive to cold storage
- **Staging**: Delete after successful Silver creation
- **Silver**: Keep indefinitely (compressed, queryable)
- **Logs**: Keep 90 days, then delete

**Archival**:
```bash
# Archive old raw data to S3
aws s3 sync data/raw/source=Wikipedia-Somali/date_accessed=2024-12-15/ \
    s3://somali-nlp-archive/raw/Wikipedia-Somali/2024-12-15/ \
    --storage-class GLACIER

# Delete local copy
rm -rf data/raw/source=Wikipedia-Somali/date_accessed=2024-12-15/
```

---

**Maintainers**: Somali NLP Contributors
