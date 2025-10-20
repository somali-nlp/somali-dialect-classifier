# Data Pipeline Documentation

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
│       └── sowiki-latest-pages-articles.xml.bz2  # 500MB compressed
│
└── source=BBC-Somali/
    └── date_accessed=2025-01-15/
        ├── article_links.json                    # Discovered URLs
        └── article_*.json                        # Individual articles
```

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
│       └── wikisom_raw.txt                       # All pages concatenated
│
└── source=BBC-Somali/
    └── date_accessed=2025-01-15/
        └── bbcsom_articles.json                  # Array of articles
```

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

**Schema**:
```python
SILVER_SCHEMA = pa.schema([
    ('id', pa.string()),               # sha256(text)[:16] + source_prefix
    ('text', pa.string()),             # Cleaned Somali text
    ('source', pa.string()),           # "Wikipedia-Somali", "BBC-Somali"
    ('source_type', pa.string()),      # "encyclopedia", "news"
    ('date_accessed', pa.date32()),    # Collection timestamp
    ('language', pa.string()),         # "so" (ISO 639-1)
    ('license', pa.string()),          # "CC-BY-SA-3.0", "Fair Use"
    ('token_count', pa.int32()),       # Whitespace-based word count
    ('metadata', pa.string()),         # JSON: {"title", "url", "detected_lang", ...}
])
```

**Examples**:
```
data/processed/silver/
├── source=Wikipedia-Somali/
│   └── date_accessed=2025-01-15/
│       └── part-0000.parquet                     # 50,000 articles
│
└── source=BBC-Somali/
    └── date_accessed=2025-01-15/
        └── part-0000.parquet                     # 1,200 articles
```

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
   self.record_filters.append((dialect_heuristic_filter, {
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
       self.record_filters.append((dialect_heuristic_filter, {
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
- ✅ Add new topic lexicons (dialect_heuristic_filter)
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
