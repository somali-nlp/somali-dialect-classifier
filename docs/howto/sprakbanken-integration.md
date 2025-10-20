# Språkbanken Somali Corpora Integration Guide

## Overview

This guide explains how to integrate and process the 23 Somali language corpora from University of Gothenburg's Språkbanken repository into your Somali Dialect Classifier pipeline.

## What is Språkbanken?

Språkbanken (The Swedish Language Bank) is a research infrastructure at the University of Gothenburg that provides access to linguistic resources, including 23 Somali language corpora spanning different domains, time periods, and genres.

### Key Features

- **23 Diverse Corpora**: News, literature, science, health, radio transcripts, and more
- **Rich Metadata**: Dates, authors, publishers, regions, and genres
- **Open License**: All corpora use CC BY 4.0 license
- **Standardized Format**: XML format (bz2 compressed)
- **Domain Coverage**: Excellent coverage across multiple content types

### Available Corpora

The 23 corpora are organized by domain:

| Domain | Corpora | Description |
|--------|---------|-------------|
| **News** | as-2001, as-2016, ah-2010-19, cb, cb-2001-03, cb-2016 | News articles from various Somali sources |
| **News (Regional)** | ogaden | News from Ogaden region |
| **Literature** | sheekooyin, sheekooying, suugaan | Stories, poetry, and literature |
| **Literature (Translation)** | suugaan-turjuman | Translated literature |
| **Science** | cilmi, saynis-1980-89 | Scientific texts |
| **Health** | caafimaad-1972-79 | Health-related content |
| **Children** | sheekooyin-carruureed | Children's stories |
| **Radio** | radioden2014, radioswe2014 | Radio broadcast transcriptions |
| **Translation** | tid-turjuman | Translated content |
| **QA** | kqa | Question-answer format |
| **Historical** | 1971-79, 1993-94, 2001, mk-1972-79 | Historical documents |

## Installation

No additional dependencies are required beyond the base project requirements. The Språkbanken processor uses:
- `requests`: For downloading corpora
- `xml.etree.ElementTree`: For XML parsing
- `bz2`: For decompression

## Quick Start

### List Available Corpora

```bash
python -m somali_dialect_classifier.cli.download_sprakbankensom --list
```

This displays all 23 corpora organized by domain with metadata.

### View Corpus Information

```bash
python -m somali_dialect_classifier.cli.download_sprakbankensom --info cilmi
```

### Download and Process Single Corpus

```bash
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus ogaden
```

This will:
1. Download the compressed XML file
2. Extract texts and sentences
3. Clean and process the text
4. Apply quality filters
5. Write to silver dataset with domain metadata

### Download and Process All Corpora

```bash
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all
```

**Note**: Processing all 23 corpora may take several hours depending on your internet connection and processing speed.

### Force Reprocessing

If you need to reprocess data:

```bash
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all --force
```

## Python API Usage

### Basic Usage

```python
from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import (
    SprakbankenSomaliProcessor
)

# Process single corpus
processor = SprakbankenSomaliProcessor(corpus_id="cilmi")
result = processor.run()  # Downloads, extracts, and processes

print(f"Processed file: {result}")
```

### Process All Corpora

```python
processor = SprakbankenSomaliProcessor(corpus_id="all", batch_size=10000)
result = processor.run()
```

### Custom Processing

```python
# Just download
processor = SprakbankenSomaliProcessor(corpus_id="ogaden")
manifest = processor.download()

# Just extract
staging_file = processor.extract()

# Just process (requires download and extract first)
processed_file = processor.process()
```

## MLOps Infrastructure Integration

This processor is fully integrated with production MLOps infrastructure:

**Structured Logging:**
```python
# Logs include run_id, source, phase automatically
# Source is always "Sprakbanken-Somali" regardless of corpus_id
{
  "run_id": "sprak_20250119_123456",
  "source": "Sprakbanken-Somali",  # Consistent across all corpora
  "phase": "fetch",
  "message": "...",
  ...
}
```

**Metrics Collected:**
- Discovery: `corpora_discovered`, `texts_discovered`
- Fetch: `download_duration_ms`, `xml_parse_duration_ms`
- Processing: `records_processed`, `filter_statistics`, `domain_distribution`

**Quality Reports:**
Generated automatically at `data/reports/{run_id}_quality_report.md`

**Resume Capability:**
The crawl ledger tracks processing state, enabling resume after interruptions:
```bash
# First run - process cilmi corpus
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus cilmi

# Resume - skips already processed corpora when using --corpus all
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all  # Skips cilmi
```

### Query Corpus Metadata

```python
from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import (
    list_available_corpora,
    get_corpus_info,
)

# List all corpus IDs
corpora = list_available_corpora()
print(f"Total corpora: {len(corpora)}")

# Get specific corpus info
info = get_corpus_info("ogaden")
print(f"Domain: {info['domain']}")
print(f"Region: {info['region']}")
```

## Data Flow

### 1. Download Phase

```
URL → Compressed XML (.bz2) → data/raw/source=Sprakbanken-Somali-*/
```

- Downloads from: `https://spraakbanken.gu.se/lb/resurser/meningsmangder/`
- Creates manifest file tracking all downloaded corpora
- Handles download failures gracefully

### 2. Extract Phase

```
Compressed XML → Decompressed XML → JSONL Records → data/staging/
```

- Parses XML structure:
  - `<corpus>` → Root container
  - `<text>` → Individual document with metadata
  - `<page>` → Page divisions
  - `<sentence>` → Sentence elements
  - `<token word="...">` → Individual tokens

- Extracts metadata:
  - Title, author, date, publisher
  - Edition, place, sponsor
  - Custom attributes

- Combines sentences into complete texts
- Writes JSONL staging file for processing

### 3. Process Phase

```
JSONL Records → Text Cleaning → Quality Filters → Silver Dataset
```

- Applies text cleaning pipeline
- Executes quality filters:
  - Minimum length (20 tokens)
  - Language identification (Somali)
- Enriches with domain metadata
- Writes to partitioned Parquet format

## Output Structure

### Silver Dataset Schema

Each record includes:

```python
{
    "id": "hash...",
    "text": "Cleaned text content",
    "title": "Document title",
    "source": "Sprakbanken-Somali",  # Consistent source name
    "source_id": "cilmi",              # Corpus ID for easy querying
    "source_type": "corpus",
    "url": "https://spraakbanken.gu.se/korp/...",
    "date_accessed": "2025-01-01",
    "language": "so",
    "license": "CC BY 4.0",
    "tokens": 1234,
    "domain": "science",  # Content domain
    "register": "formal", # Linguistic register
    "embedding": None,    # Placeholder for future embeddings
    "source_metadata": {
        "repository": "Språkbanken",
        "institution": "University of Gothenburg",
        "corpus_id": "cilmi",
        "domain": "science",
        "author": "...",
        "date": "...",
        "publisher": "..."
    }
}
```

**Key Fields for Querying:**

- `source`: Always "Sprakbanken-Somali" (consistent across all corpora)
- `source_id`: Corpus identifier (e.g., "cilmi", "ogaden", "as-2016")
- `domain`: Content domain (news, science, literature, etc.)

This design makes querying simple and data-engineering friendly:

```python
import pyarrow.parquet as pq

# Read all Språkbanken records
table = pq.read_table("data/processed/silver/source=Sprakbanken-Somali/")

# Filter by specific corpus
cilmi_records = table.filter(
    (table.column("source") == "Sprakbanken-Somali") &
    (table.column("source_id") == "cilmi")
)

# Filter by domain
news_records = table.filter(table.column("domain") == "news")

# Combine filters
science_corpus = table.filter(
    (table.column("source_id") == "cilmi") &
    (table.column("tokens") > 500)
)

# Get all news corpora
news_corpora = table.filter(
    (table.column("source") == "Sprakbanken-Somali") &
    (table.column("domain") == "news")
)
```

### Directory Structure

```
data/
├── raw/
│   └── source=Sprakbanken-Somali/
│       └── date_accessed=2025-10-19/
│           ├── sprakbanken-cilmi_20251019_160000_raw_manifest.json  # Metadata with run_id
│           └── somali-cilmi.xml.bz2                                  # Original corpus (external)
│
├── staging/
│   └── source=Sprakbanken-Somali/
│       └── date_accessed=2025-10-19/
│           └── sprakbanken-cilmi_20251019_160000_staging_extracted.jsonl  # Extracted texts
│
├── processed/
│   └── source=Sprakbanken-Somali/
│       └── date_accessed=2025-10-19/
│           └── sprakbanken-cilmi_20251019_160000_processed_cleaned.txt    # Cleaned text
│
└── processed/silver/
    └── source=Sprakbanken-Somali/
        └── date_accessed=2025-10-19/
            ├── sprakbanken-cilmi_20251019_160000_silver_part-0000.parquet  # Final dataset
            └── sprakbanken-cilmi_20251019_160000_silver_metadata.json      # Metadata sidecar
```

**File Naming Pattern**: `sprakbanken-{corpus_id}_{run_id}_{layer}_{descriptive-name}.{ext}`
- **source**: Always "Sprakbanken-Somali" (consistent across all corpora)
- **corpus_id**: Specific corpus (e.g., `cilmi`, `ogaden`, `as-2016`) - stored in filename and `source_id` field
- **run_id**: Timestamp `YYYYMMDD_HHMMSS` for lineage tracking
- **Partition Consistency**: All layers use `date_accessed`

## Domain Mapping

The processor automatically maps each corpus to the appropriate domain:

| Corpus Pattern | Domain |
|----------------|--------|
| as-*, ah-*, cb* | news |
| ogaden | news_regional |
| sheekooyin-carruureed | children |
| sheekooyin*, suugaan | literature |
| *-turjuman (with suugaan) | literature_translation |
| *-turjuman (other) | translation |
| cilmi, saynis-* | science |
| caafimaad-* | health |
| radio* | radio |
| kqa | qa |
| Historical dates | historical |
| Others | general |

## Quality Filters

### Minimum Length Filter

- **Threshold**: 20 tokens
- **Purpose**: Remove very short or incomplete sentences
- **Applied to**: All corpora

### Language Identification Filter

- **Method**: Heuristic-based Somali detection
- **Confidence**: 0.3 (relaxed threshold)
- **Purpose**: Filter out non-Somali content
- **Applied to**: All corpora

## Performance Considerations

### Download Speed

- Total size of all 23 corpora: ~5-10 MB compressed
- Download time: 5-10 minutes (depending on connection)
- Bandwidth-friendly: Incremental downloads

### Processing Speed

- Extraction: ~100-500 texts/second
- Processing: ~50-200 records/second
- Total time (all corpora): 30-60 minutes

### Memory Usage

- Peak memory: ~500 MB - 1 GB
- Batch processing prevents OOM errors
- Streaming XML parsing for large corpora

## Troubleshooting

### Download Failures

**Issue**: HTTP errors or timeouts

**Solution**:
```bash
# Retry with force flag
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus <id> --force
```

The processor uses retry logic with exponential backoff for network issues.

### XML Parsing Errors

**Issue**: Malformed XML or encoding issues

**Solution**:
- Check the downloaded XML file is not corrupted
- Re-download with `--force`
- Report issue to Språkbanken if persistent

### Empty Output

**Issue**: No records in silver dataset

**Solution**:
- Check filter statistics in logs
- Adjust filter thresholds if too strict
- Verify corpus contains Somali text

### Metadata Extraction

**Issue**: Missing metadata fields

**Solution**:
- Not all corpora have all metadata fields
- The processor handles missing fields gracefully
- Check `source_metadata` for available fields

## Best Practices

### 1. Start with Single Corpus

Test with one corpus before processing all:

```bash
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus cilmi
```

### 2. Monitor Logs

Use verbose logging to track progress:

```bash
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all -v
```

### 3. Incremental Processing

Process corpora incrementally by domain:

```bash
# News corpora first
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus as-2016
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus ogaden

# Then literature
python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus sheekooyin

# etc.
```

### 4. Validate Output

After processing, check the silver dataset:

```python
import pyarrow.parquet as pq
from somali_dialect_classifier.preprocessing.silver_writer import SilverDatasetWriter

# Read all Språkbanken records
table = pq.read_table("data/processed/silver/source=Sprakbanken-Somali/")
print(f"Total records: {len(table)}")

# Check unique corpora
unique_corpora = table.column("source_id").unique().to_pylist()
print(f"Corpora processed: {unique_corpora}")

# Check domain distribution
writer = SilverDatasetWriter()
stats = writer.get_domain_statistics(source="Sprakbanken-Somali")
print(f"Domain statistics: {stats}")

# Filter by specific corpus
cilmi_records = table.filter(table.column("source_id") == "cilmi")
print(f"Cilmi corpus records: {len(cilmi_records)}")
```

### 5. Backup Downloaded Files

Keep downloaded XML files for reproducibility:

```bash
# Backup raw directory
tar -czf sprakbanken_raw_backup.tar.gz data/raw/source=Sprakbanken-Somali-*
```

## Integration with Other Processors

Språkbanken data integrates seamlessly with other sources:

```python
from somali_dialect_classifier.preprocessing import (
    WikipediaSomaliProcessor,
    BBCSomaliProcessor,
    SprakbankenSomaliProcessor,
)

# Process all sources
wiki = WikipediaSomaliProcessor()
wiki.run()

bbc = BBCSomaliProcessor(max_articles=1000)
bbc.run()

sprakbanken = SprakbankenSomaliProcessor(corpus_id="all")
sprakbanken.run()

# All write to same silver dataset with consistent schema
# Domain field allows filtering by content type
```

## Advanced Usage

### Custom Filters

Add custom filters for specific corpora:

```python
from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import SprakbankenSomaliProcessor
from somali_dialect_classifier.preprocessing.filters import create_custom_filter

processor = SprakbankenSomaliProcessor(corpus_id="ogaden")

# Add custom filter for regional dialect features
def regional_filter(text, **kwargs):
    # Custom logic here
    return True, {}

processor.record_filters.append((regional_filter, {}))
processor.run()
```

### Domain-Specific Processing

Process only specific domains:

```python
from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import (
    CORPUS_INFO,
    SprakbankenSomaliProcessor
)

# Get all news corpora
news_corpora = [
    cid for cid, info in CORPUS_INFO.items()
    if info.get("domain") == "news"
]

for corpus_id in news_corpora:
    processor = SprakbankenSomaliProcessor(corpus_id=corpus_id)
    processor.run()
```

## References

- **Språkbanken Website**: https://spraakbanken.gu.se/
- **Somali Corpora Collection**: https://spraakbanken.gu.se/en/resources?search=somali
- **Korp Interface**: https://spraakbanken.gu.se/korp/?mode=somali
- **License**: CC BY 4.0 - https://creativecommons.org/licenses/by/4.0/
- **Institution**: University of Gothenburg, Sweden

## Next Steps

After processing Språkbanken corpora:

1. **Deduplicate**: Run deduplication across all silver datasets
2. **Analyze**: Use domain field to analyze dataset composition
3. **Filter**: Select specific domains for downstream tasks
4. **Train**: Use domain-diverse data for robust model training

See also:
- [Data Pipeline Overview](../overview/data-pipeline-architecture.md)
- [Silver Schema Reference](../reference/silver-schema.md)
- [Quality Filters Guide](../howto/quality-filters.md)

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors