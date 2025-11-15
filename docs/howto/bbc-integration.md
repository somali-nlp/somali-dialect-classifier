# BBC-Somali Integration Guide

**Status**: Production-ready
**Last Updated**: 2025-10-19

This guide explains how to integrate and process BBC Somali news articles into your Somali Dialect Classifier pipeline through ethical web scraping.

## Table of Contents

1. [Overview](#overview)
2. [What is BBC-Somali?](#what-is-bbc-somali)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Data Flow](#data-flow)
6. [Configuration](#configuration)
7. [Usage Examples](#usage-examples)
8. [Directory Structure](#directory-structure)
9. [Quality Filters](#quality-filters)
10. [Ethical Scraping Practices](#ethical-scraping-practices)
11. [Topic Enrichment](#topic-enrichment)
12. [Performance Considerations](#performance-considerations)
13. [Troubleshooting](#troubleshooting)
14. [Best Practices](#best-practices)

---

## Overview

The BBC-Somali processor scrapes, extracts, and processes news articles from BBC Somali to create high-quality training data for dialect classification. BBC Somali provides **contemporary journalistic content** representing modern written and spoken Somali.

### Key Features

- **Current events**: News articles covering recent developments
- **Journalistic language**: Professional news writing style
- **Diverse topics**: Politics, sports, business, culture, health
- **High quality**: Professional editing and fact-checking
- **Ethical scraping**: Respects robots.txt and rate limits
- **Topic enrichment**: Automatic categorization using keyword matching

### Use Cases

- Training modern Somali language models
- News article classification by topic
- Sentiment analysis on current events
- Comparative analysis with formal sources (Wikipedia)
- Named entity recognition (people, organizations, locations)
- Temporal language evolution studies

---

## What is BBC-Somali?

### About BBC Somali Service

[BBC Somali](https://www.bbc.com/somali) is the Somali-language service of the British Broadcasting Corporation (BBC). Established in 1957, it provides news and current affairs programming to Somali-speaking audiences worldwide.

### Content Characteristics

**Language style**: Professional journalistic Somali
- Modern vocabulary with occasional English loanwords
- Clear, accessible writing for broad audience
- Mix of formal and conversational tones
- Regional variations (Somalia, Somaliland, diaspora)

**Topic distribution**:
- Politics and government (40%)
- Business and economy (15%)
- Sports (20%)
- Culture and society (15%)
- Health and science (10%)

### Website Structure

**Article URLs**:
- Format: `https://www.bbc.com/somali/articles/{article-id}`
- Example: `https://www.bbc.com/somali/articles/c123xyz456`

**Discovery sources**:
1. **Homepage**: ~10-20 latest articles
2. **Topic sections**: Business, Sports, Video pages (~100 articles each)
3. **XML Sitemap**: ~500+ historical articles
4. **RSS Feeds**: Most recent updates

---

## Installation

No additional dependencies are required beyond the base project requirements. The BBC processor uses:

- `requests`: HTTP requests (automatically installed)
- `beautifulsoup4`: HTML parsing (automatically installed)
- `lxml`: HTML parser backend (automatically installed)

```bash
# Install project with all dependencies
pip install -e ".[config]"

# Verify dependencies
python -c "import requests, bs4; print('Dependencies OK')"
```

---

## Quick Start

### CLI Usage

```bash
# Scrape 100 articles (recommended for testing)
bbcsom-download --max-articles 100

# Scrape all discovered articles (no limit)
bbcsom-download

# Force reprocessing (re-scrape even if cached)
bbcsom-download --force
```

### Python API Usage

```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

# Scrape 100 articles
processor = BBCSomaliProcessor(max_articles=100)
processor.run()  # download() -> extract() -> process()
```

---

## MLOps Infrastructure Integration

This processor is fully integrated with production MLOps infrastructure:

**Structured Logging:**
```python
# Logs include run_id, source, phase automatically
{
  "run_id": "bbc_20250119_123456",
  "source": "BBC-Somali",
  "phase": "fetch",
  "message": "...",
  ...
}
```

**Metrics Collected:**
- Discovery: `urls_discovered`, `topic_urls_discovered`
- Fetch: `urls_fetched`, `fetch_duration_ms`, `http_status_codes`
- Processing: `records_processed`, `filter_statistics`

**Quality Reports:**
Generated automatically at `data/reports/{run_id}_quality_report.md`

**Resume Capability:**
The crawl ledger tracks URL state, enabling resume after interruptions:
```bash
# First run - scrape 100 articles
bbcsom-download --max-articles 100

# Resume - skips already fetched articles
bbcsom-download --max-articles 200  # Fetches 100 more, not 200 total
```

---

## Data Flow

The BBC processor follows a three-phase pipeline:

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: DOWNLOAD (Article Discovery)                  │
│ - Discover URLs from homepage, topics, sitemap         │
│ - Cache discovered links                               │
│ → Output: data/raw/.../article_links.json             │
│ ⏱️  Duration: ~1-2 minutes                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 2: EXTRACT (Article Scraping) - PRIMARY BOTTLENECK│
│ - Scrape each article (50-60s per article)             │
│   • BBC server response: ~45-55s                       │
│   • Network latency: ~2-5s                             │
│   • Rate limiting delay: ~1-3s                         │
│   • Processing overhead: ~5-10s                        │
│ - Extract title, text, metadata                        │
│ - Save to JSONL                                        │
│ → Output: data/staging/.../bbcsom_articles.jsonl      │
│ ⏱️  Duration: ~50-60s × article_count                   │
│    • 10 articles: ~10 minutes                          │
│    • 100 articles: ~85-100 minutes                     │
│    • 500 articles: ~7-8 hours                          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 3: PROCESS (Clean, Filter, Enrich)               │
│ - Apply text cleaning (HTML removal)                   │
│ - Execute quality filters                              │
│ - Enrich with topic classification                     │
│ → Output: data/processed/silver/.../part-0000.parquet │
│ ⏱️  Duration: ~2-5 minutes for 100 articles             │
└─────────────────────────────────────────────────────────┘
```

### Phase 1: Article Discovery

```python
def download(self) -> Path:
    """Discover article URLs from multiple sources."""

    article_urls = set()

    # Source 1: Homepage (latest articles)
    homepage_urls = self._discover_from_homepage()
    article_urls.update(homepage_urls)
    logger.info(f"Discovered {len(homepage_urls)} URLs from homepage")

    # Source 2: Topic sections (Business, Sports, etc.)
    for topic in ["business", "sports", "video"]:
        topic_urls = self._discover_from_topic(topic)
        article_urls.update(topic_urls)
        logger.info(f"Discovered {len(topic_urls)} URLs from {topic}")

    # Source 3: XML Sitemap (historical articles)
    sitemap_urls = self._discover_from_sitemap()
    article_urls.update(sitemap_urls)
    logger.info(f"Discovered {len(sitemap_urls)} URLs from sitemap")

    # Limit and save
    article_urls = list(article_urls)[:self.max_articles] if self.max_articles else list(article_urls)

    # Cache for resume capability
    with open(links_file, 'w') as f:
        json.dump({
            "max_articles_limit": self.max_articles,
            "discovered_at": datetime.now().isoformat(),
            "article_urls": article_urls
        }, f, indent=2)

    return links_file
```

**Output**: `data/raw/source=BBC-Somali/date_accessed=2025-10-19/article_links.json`

**Example content**:
```json
{
  "max_articles_limit": 100,
  "discovered_at": "2025-10-19T10:30:00",
  "article_urls": [
    "https://www.bbc.com/somali/articles/c123xyz456",
    "https://www.bbc.com/somali/articles/c789abc123",
    ...
  ]
}
```

### Phase 2: Article Scraping

```python
def extract(self) -> Path:
    """Scrape articles with ethical rate limiting."""

    # Load discovered URLs
    with open(links_file) as f:
        data = json.load(f)
        article_urls = data["article_urls"]

    articles = []

    for url in article_urls:
        # Rate limiting (3-6 second delay)
        time.sleep(random.uniform(3, 6))

        try:
            # Fetch article
            response = requests.get(url, headers={
                "User-Agent": "Somali-NLP-Research-Bot/1.0 (Educational Purpose)"
            })
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract content with fallback strategy
            article_body = (
                soup.find('main') or
                soup.find(attrs={'role': 'main'}) or
                soup.find('article') or
                soup.find(attrs={'data-component': 'text-block'})
            )

            if not article_body:
                logger.warning(f"Empty text extracted from {url}")
                continue

            # Extract metadata
            title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Untitled"
            text = article_body.get_text(separator='\n', strip=True)

            articles.append({
                "title": title,
                "text": text,
                "url": url,
                "scraped_at": datetime.now().isoformat()
            })

            logger.info(f"Scraped {len(articles)}/{len(article_urls)}: {title[:50]}...")

        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            continue

    # Save all articles
    with open(staging_file, 'w') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    return staging_file
```

**Output**: `data/staging/source=BBC-Somali/date_accessed=2025-10-19/bbcsom_articles.json`

**Example content**:
```json
[
  {
    "title": "Wararka Maanta: Soomaaliya iyo Itoobiya",
    "text": "Soomaaliya iyo Itoobiya ayaa maanta...",
    "url": "https://www.bbc.com/somali/articles/c123xyz456",
    "scraped_at": "2025-10-19T10:35:22"
  },
  ...
]
```

### Phase 3: Processing and Enrichment

```python
def process(self) -> Path:
    """Clean, filter, and enrich articles."""

    records = []

    for raw_record in self._extract_records():
        # 1. Clean HTML (remove tags, decode entities)
        cleaned_text = self.text_cleaner.clean(raw_record.text)

        # 2. Apply filters
        passes_filters, metadata = self._apply_filters(cleaned_text, raw_record)

        if not passes_filters:
            continue

        # 3. Enrich with topic classification
        topic_metadata = self._classify_topic(cleaned_text)
        metadata.update(topic_metadata)

        # 4. Build silver record
        record = build_silver_record(
            text=cleaned_text,
            title=raw_record.title,
            source="BBC-Somali",
            url=raw_record.url,
            date_accessed=self.date_accessed,
            source_type="news",
            language="so",
            license_str="BBC Terms of Use",
            source_metadata=metadata
        )
        records.append(record)

    # 5. Write to Parquet
    self.silver_writer.write(records, "BBC-Somali", self.date_accessed)
```

**Output**: `data/processed/silver/source=BBC-Somali/date_accessed=2025-10-19/part-0000.parquet`

---

## Configuration

### Environment Variables

```bash
# Set in .env file or export
SDC_SCRAPING__BBC__MAX_ARTICLES=100
SDC_SCRAPING__BBC__RATE_LIMIT_MIN_DELAY=3
SDC_SCRAPING__BBC__RATE_LIMIT_MAX_DELAY=6
SDC_SCRAPING__BBC__MIN_LENGTH_THRESHOLD=50
SDC_SCRAPING__BBC__LANGID_CONFIDENCE_THRESHOLD=0.3
SDC_SCRAPING__BBC__USER_AGENT="Somali-NLP-Research-Bot/1.0"
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_ARTICLES` | None (unlimited) | Maximum articles to scrape |
| `RATE_LIMIT_MIN_DELAY` | 3 | Minimum seconds between requests |
| `RATE_LIMIT_MAX_DELAY` | 6 | Maximum seconds between requests |
| `MIN_LENGTH_THRESHOLD` | 50 | Minimum characters for quality filter |
| `LANGID_CONFIDENCE_THRESHOLD` | 0.3 | Language detection confidence |
| `USER_AGENT` | Research bot identifier | HTTP User-Agent header |

### Programmatic Configuration

```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

# Custom configuration
processor = BBCSomaliProcessor(
    max_articles=200,
    delay_range=(5, 10),  # More conservative delays
    force=False
)
```

---

## Usage Examples

### Example 1: Small Test Run

```bash
# CLI
bbcsom-download --max-articles 10
```

```python
# Python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

processor = BBCSomaliProcessor(max_articles=10)
output_path = processor.run()
print(f"Processed data: {output_path}")
```

**Expected output** (10 articles):
```
data/raw/.../article_links.json         # 2 KB
data/staging/.../bbcsom_articles.json   # 50 KB
data/processed/silver/.../part-0000.parquet  # 15 KB
```

**Expected time**: ~10 minutes (50-60 seconds per article)

### Example 2: Production Run

```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

# Scrape 100 articles for production dataset
processor = BBCSomaliProcessor(
    max_articles=100,
    force=False  # Use crawl ledger to skip already-processed articles
)

# Phase 1: Discover (fast - ~1-2 minutes)
links_file = processor.download()
print(f"Discovered URLs: {links_file}")

# Phase 2: Scrape (takes ~85-100 minutes for 100 articles)
staging_file = processor.extract()
print(f"Scraped articles: {staging_file}")

# Phase 3: Process (fast - ~2-5 minutes)
silver_file = processor.process()
print(f"Silver dataset: {silver_file}")
```

**Expected time**: ~1.5 hours total for 100 articles

**For larger datasets (500+ articles)**, consider running overnight:
```python
# Large-scale collection (7-8 hours)
processor = BBCSomaliProcessor(max_articles=500)
processor.run()  # Run overnight or in background
```

### Example 3: Resume After Interruption

```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

# If scraping was interrupted, resume without re-discovery
processor = BBCSomaliProcessor(max_articles=100, force=False)

# This will skip discovery if cache is valid
processor.download()  # Uses cached links

# Continue scraping
processor.extract()
processor.process()
```

### Example 4: Custom Topic Filters

```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor
from somali_dialect_classifier.preprocessing.filters import custom_filter

processor = BBCSomaliProcessor(max_articles=100)

# Add custom filter: only sports articles
def is_sports(text: str) -> tuple:
    sports_keywords = ["kubadda", "ciyaaryahan", "kooxda", "tartanka", "garoonka"]
    count = sum(1 for keyword in sports_keywords if keyword in text.lower())
    is_sports_article = count >= 2
    return is_sports_article, {"sports_keyword_count": count}

processor.record_filters.append((custom_filter, {
    "predicate": is_sports,
    "metadata_key": "is_sports"
}))

processor.process()
```

---

## Directory Structure

After running the BBC processor:

```
data/
├── raw/
│   └── source=BBC-Somali/
│       └── date_accessed=2025-10-19/
│           ├── bbc-somali_20251019_150230_raw_article-links.json  # Discovered URLs with run_id
│           └── bbc-somali_20251019_150230_raw_article-0001.json   # Individual articles
│
├── staging/
│   └── source=BBC-Somali/
│       └── date_accessed=2025-10-19/
│           └── bbc-somali_20251019_150230_staging_articles.jsonl  # Scraped articles (JSONL format)
│
├── processed/
│   └── source=BBC-Somali/
│       └── date_accessed=2025-10-19/
│           └── bbc-somali_20251019_150230_processed_cleaned.txt   # Cleaned text with run_id
│
└── processed/silver/
    └── source=BBC-Somali/
        └── date_accessed=2025-10-19/
            ├── bbc-somali_20251019_150230_silver_part-0000.parquet  # Final dataset
            └── bbc-somali_20251019_150230_silver_metadata.json      # Metadata sidecar (NEW)
```

**File Naming Pattern**: `bbc-somali_{run_id}_{layer}_{descriptive-name}.{ext}`
- **run_id**: `20251019_150230` enables lineage tracking
- **Multiple Runs**: Different run_ids prevent file collisions on same day
- **Partition Consistency**: All layers use `date_accessed` (not `date_processed`)

### Silver Dataset Schema

Each record includes:

```python
{
    "id": "hash...",
    "text": "Cleaned article text",
    "title": "Article title",
    "source": "BBC-Somali",
    "source_type": "news",
    "url": "https://www.bbc.com/somali/articles/...",
    "date_accessed": "2025-10-19",
    "language": "so",
    "license": "BBC Terms of Use",
    "tokens": 456,
    "text_hash": "sha256...",
    "source_metadata": {
        "detected_lang": "so",
        "lang_confidence": 0.92,
        "primary_dialect": "politics",
        "dialect_markers": {
            "politics": 3,
            "sports": 0,
            "economy": 1
        },
        "total_dialect_markers": 4
    }
}
```

---

## Quality Filters

### 1. Minimum Length Filter

**Purpose**: Remove very short snippets or incomplete articles

```python
min_length_filter(cleaned_text, threshold=50)
```

- Rejects articles with < 50 characters
- ~3-5% rejection rate on BBC articles
- Ensures substantive content

### 2. Language Identification Filter

**Purpose**: Filter non-Somali content (e.g., English articles, ads)

```python
langid_filter(cleaned_text, allowed_langs={"so"}, confidence_threshold=0.3)
```

- Uses heuristic Somali word vocabulary
- Confidence threshold: 0.3 (relaxed for short articles)
- ~2-3% rejection rate on BBC Somali

### 3. Topic Lexicon Enrichment Filter (Enrichment Only)

**Purpose**: Classify articles by topic using keyword matching (NOT dialect classification)

```python
topic_lexicon_enrichment_filter(cleaned_text, ruleset=TOPIC_LEXICONS, enrich_only=True)
```

**Important**: This filter **does NOT reject** articles - it only enriches metadata with topic information.

See [Topic Enrichment](#topic-enrichment) section below for details.

---

## Ethical Scraping Practices

### Respect robots.txt

The processor automatically checks and respects `robots.txt`:

```python
import requests

robots_url = "https://www.bbc.com/robots.txt"
response = requests.get(robots_url)

# Check if /somali/ is allowed
if "Disallow: /somali" in response.text:
    raise ValueError("BBC Somali scraping not allowed by robots.txt")
```

### Rate Limiting

**Minimum delay**: 3 seconds between requests (default)
**Maximum delay**: 6 seconds between requests (default)

```python
import time
import random

for url in article_urls:
    # Random delay to avoid pattern detection
    delay = random.uniform(3, 6)
    time.sleep(delay)

    # Scrape article
    response = requests.get(url, headers=headers)
```

**Why rate limiting matters**:
- Prevents server overload
- Avoids IP bans (HTTP 429)
- Shows respect for BBC's resources
- Ensures ethical scraping compliance

### User-Agent Identification

Always identify your scraper:

```python
headers = {
    "User-Agent": "Somali-NLP-Research-Bot/1.0 (Educational Purpose; Contact: your-email@example.com)"
}
```

**Best practices**:
- Include bot name and version
- State purpose (research, educational)
- Provide contact information
- Never impersonate a browser

### Retry Logic with Exponential Backoff

Handle failures gracefully:

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure retry strategy
retry_strategy = Retry(
    total=3,
    backoff_factor=2,  # 1s, 2s, 4s delays
    status_forcelist=[429, 500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("https://", adapter)
```

### Cache Validation and Invalidation

The processor caches discovered URLs to avoid re-discovery:

```python
def _cache_is_valid(self, cached_links: dict) -> bool:
    """Check if cached links are still valid."""

    # Invalidate if max_articles changed
    if cached_links.get("max_articles_limit") != self.max_articles:
        return False

    # Invalidate if older than 7 days
    discovered_at = datetime.fromisoformat(cached_links["discovered_at"])
    if (datetime.now() - discovered_at).days > 7:
        return False

    return True
```

### Legal and Ethical Considerations

**Fair Use vs. Terms of Service**:
- BBC content may be subject to copyright
- Academic/research use typically covered by Fair Use (US) or Fair Dealing (UK)
- **Do NOT**: Republish scraped content commercially
- **Do NOT**: Scrape for competitive purposes
- **DO**: Use for research and education
- **DO**: Attribute BBC as source

**Recommended attribution**:
```
Data sourced from BBC Somali (https://www.bbc.com/somali)
© British Broadcasting Corporation
Used under Fair Use for academic research purposes
```

---

## Topic Enrichment

The BBC processor automatically enriches articles with topic classification using keyword matching.

### Topic Lexicons

```python
TOPIC_LEXICONS = {
    "politics": [
        "xukuumad",      # government
        "madaxweyne",    # president
        "baarlamaan",    # parliament
        "doorasho",      # election
        "siyaasad",      # politics
        "wasi ir",       # minister
    ],
    "sports": [
        "kubadda",       # football/ball
        "ciyaaryahan",   # player
        "kooxda",        # team
        "tartanka",      # competition
        "garoonka",      # stadium
        "guul",          # victory
    ],
    "economy": [
        "dhaqaale",      # economy
        "ganacsiga",     # commerce
        "suuq",          # market
        "lacagta",       # money
        "ganacsi",       # business
        "shirkad",       # company
    ],
    "health": [
        "caafimaad",     # health
        "cudur",         # disease
        "dhakhtar",      # doctor
        "isbitaal",      # hospital
        "dawo",          # medicine
    ],
    "education": [
        "waxbarasho",    # education
        "iskuul",        # school
        "arday",         # student
        "macallim",      # teacher
        "jaamacad",      # university
    ]
}
```

### Classification Logic

```python
def _classify_topic(self, text: str) -> dict:
    """Classify article by topic using keyword matching."""

    topic_counts = {}
    text_lower = text.lower()

    # Count keywords per topic
    for topic, keywords in TOPIC_LEXICONS.items():
        count = sum(1 for keyword in keywords if keyword in text_lower)
        topic_counts[topic] = count

    # Determine primary topic (most keyword matches)
    primary_topic = max(topic_counts, key=topic_counts.get) if max(topic_counts.values()) > 0 else "general"

    return {
        "primary_dialect": primary_topic,
        "dialect_markers": topic_counts,
        "total_dialect_markers": sum(topic_counts.values())
    }
```

### Example Classification

**Article text**:
```
"Madaxweynaha Soomaaliya ayaa maanta booqday baarlamaanka si uu ula hadlo
xildhibaannada doorashada soo socota. Siyaasadda cusub ee xukuumadda..."
```

**Enrichment result**:
```python
{
    "primary_dialect": "politics",
    "dialect_markers": {
        "politics": 5,  # madaxweyne, baarlamaan, xukuumad, doorasho, siyaasad
        "sports": 0,
        "economy": 0,
        "health": 0,
        "education": 0
    },
    "total_dialect_markers": 5
}
```

### Using Topic Metadata

```python
import pandas as pd

# Load silver dataset
df = pd.read_parquet("data/processed/silver/source=BBC-Somali/")

# Parse source_metadata JSON
import json
df['metadata'] = df['source_metadata'].apply(json.loads)
df['primary_topic'] = df['metadata'].apply(lambda x: x.get('primary_dialect'))

# Filter by topic
sports_articles = df[df['primary_topic'] == 'sports']
politics_articles = df[df['primary_topic'] == 'politics']

print(f"Sports articles: {len(sports_articles)}")
print(f"Politics articles: {len(politics_articles)}")
```

---

## Performance Characteristics

### Expected Timing

The BBC scraping process has well-established performance characteristics based on extensive testing:

**Per-Article Processing Time:**
- **Average**: 50-60 seconds per article
- **Range**: 45-70 seconds (depending on network conditions)

**Batch Processing Estimates:**
- **10 articles**: ~10 minutes
- **50 articles**: 45-50 minutes
- **100 articles**: 85-100 minutes (1.5 hours)
- **200 articles**: 170-200 minutes (3-3.5 hours)

### Performance Factors

The scraping timing is determined by several factors, ranked by impact:

**1. BBC Server Response Time (Primary Bottleneck - ~45-55 seconds per article)**

The dominant factor in scraping performance is BBC's server processing time. Each request requires BBC's infrastructure to:
- Process the incoming request through their CDN
- Generate dynamic HTML content
- Retrieve article data from their database
- Render the complete page with all components

This server-side processing is an external dependency that cannot be optimized from the client side.

**2. Network Latency (~2-5 seconds per article)**

International requests to BBC servers introduce additional overhead:
- DNS resolution
- SSL/TLS handshake
- Geographic routing (especially for non-UK requests)
- Data transfer time for HTML payloads

**3. Ethical Rate Limiting (~1-3 seconds per article)**

Industry-standard delays between requests:
- Current delay range: 1-3 seconds (optimized from previous 3-6 seconds)
- Random jitter prevents pattern detection
- Respects server resources and prevents IP bans
- Complies with ethical web scraping standards

**4. Processing Overhead (~5-10 seconds per article)**

Client-side operations add minimal time:
- HTML parsing with BeautifulSoup
- Text extraction and cleaning
- Quality validation
- Deduplication checks
- JSON serialization

### Optimization Status

**Completed Optimizations:**
- ✅ **Delay reduction**: Reduced from 3-6s to 1-3s (saves ~2.5s per article)
- ✅ **Adaptive rate limiting**: Implemented exponential backoff with jitter
- ✅ **Conditional requests**: Uses If-None-Match/If-Modified-Since headers
- ✅ **Resume capability**: Crawl ledger prevents re-fetching processed articles

**Cannot Be Optimized:**
- ⚠️ **BBC server response time**: External dependency (~45-55s per article)
- ⚠️ **Network latency**: Geographic and infrastructure constraints (~2-5s per article)

**Why 50-60 seconds is normal:**

The ~50-60 second average per article is **expected and persistent** for ethical web scraping. This timing is industry-standard for scraping major news organizations and reflects:
- Proper respect for server resources
- Compliance with terms of service
- Network realities for international requests
- Professional-grade scraping practices

Similar processing times are observed when scraping other major news sites (CNN, The Guardian, Reuters, etc.) through ethical means.

### Recommendations by Use Case

Choose your batch size based on your timeline and use case:

**Testing and Development:**
- Use `--max-articles 10` (~10 minutes)
- Validates pipeline functionality quickly
- Sufficient for code testing and development

**Small Datasets:**
- Use `--max-articles 50` (~45 minutes)
- Good for initial data exploration
- Suitable for topic analysis experiments

**Production Datasets:**
- Use `--max-articles 100-200` (1.5-3.5 hours)
- Recommended for model training datasets
- Balances data volume with processing time

**Large-Scale Collection:**
- Use `--max-articles 500+` (7+ hours)
- Consider running overnight or in background
- Use for comprehensive corpus building

**Incremental Updates:**
- Run daily with `--max-articles 20-30` (~30 minutes)
- Leverages crawl ledger to skip processed articles
- Maintains fresh dataset with minimal time investment

### Memory and Disk Usage

**Memory Usage:**
- **Peak memory**: ~50 MB (HTML parsing + JSON caching)
- **Scales linearly**: Safe for thousands of articles
- **Memory-efficient**: Streaming processing prevents memory bloat

**Disk Usage:**

| Layer | Format | Size (100 articles) | Compression Ratio |
|-------|--------|---------------------|-------------------|
| Raw | JSON | 2 KB | - (links only) |
| Staging | JSON | 500 KB | 1x (baseline) |
| Processed | TXT | 450 KB | 1.1x |
| Silver | Parquet (snappy) | 150 KB | 3.3x (compressed) |

**Storage efficiency**: Parquet compression reduces final storage by ~70% compared to raw text.

---

## Troubleshooting

### Issue: HTTP 429 (Too Many Requests)

**Symptoms**:
```
requests.exceptions.HTTPError: 429 Client Error: Too Many Requests
```

**Solutions**:
1. Increase rate limit delays:
   ```python
   processor = BBCSomaliProcessor(delay_range=(10, 15))  # More conservative
   ```
2. Reduce batch size:
   ```python
   processor = BBCSomaliProcessor(max_articles=50)
   ```
3. Wait 30-60 minutes before retrying

### Issue: Empty Article Bodies

**Symptoms**:
```
WARNING - Empty text extracted from https://www.bbc.com/somali/articles/...
```

**Cause**: BBC changed HTML structure (CSS classes, element IDs)

**Solution**: Check the fallback selector strategy in code:
```python
# Fallback strategy (in order of preference)
article_body = (
    soup.find('main') or                              # Semantic HTML5
    soup.find(attrs={'role': 'main'}) or              # ARIA role
    soup.find('article') or                           # Article tag
    soup.find(attrs={'data-component': 'text-block'}) # BBC component
)
```

If all fail, BBC has significantly changed their HTML - file an issue.

### Issue: Cache Invalidation Not Working

**Symptoms**: Changing `max_articles` doesn't trigger re-discovery

**Solution**: Force re-discovery:
```bash
# Delete cache file
rm data/raw/source=BBC-Somali/*/article_links.json

# Or use force flag
bbcsom-download --max-articles 200 --force
```

### Issue: Duplicate Articles

**Symptoms**: Same article appears multiple times in silver dataset

**Cause**: Article discovered from multiple sources (homepage + topic + sitemap)

**Solution**: Discovery-stage deduplication now prevents this automatically!

The pipeline now checks the crawl ledger BEFORE scraping (Phase 1 dedup), so duplicate articles are skipped automatically. This issue should only occur with legacy data processed before Phase 1 was implemented.

**For legacy data cleanup only**:
```bash
# Only needed for retroactive deduplication of old silver datasets
# Discovery-stage dedup prevents new duplicates automatically
python scripts/deduplicate_silver_dataset.py --source BBC-Somali
```

**See**: [Deduplication Strategy Guide](deduplication.md) for comprehensive explanation

### Issue: Language Filter Rejecting Somali Articles

**Symptoms**:
```
INFO - filtered_by_langid_filter: 50 records (50%)  # Abnormally high
```

**Solution**: Lower confidence threshold:
```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor
from somali_dialect_classifier.preprocessing.filters import langid_filter

processor = BBCSomaliProcessor(max_articles=100)

# Override default filter with lower threshold
processor.record_filters = [
    (min_length_filter, {"threshold": 50}),
    (langid_filter, {"confidence_threshold": 0.1})  # Very relaxed
]

processor.process()
```

---

## Best Practices

### 1. Start Small, Scale Gradually

```python
# Test with 10 articles first
processor = BBCSomaliProcessor(max_articles=10)
processor.run()

# Validate output
import pandas as pd
df = pd.read_parquet("data/processed/silver/source=BBC-Somali/")
assert len(df) > 0, "No articles processed!"

# Then scale to 100, 500, etc.
processor = BBCSomaliProcessor(max_articles=100)
processor.run()
```

### 2. Monitor Logs

```bash
# Watch logs in real-time
tail -f logs/download_bbcsom.log

# Check for errors
grep ERROR logs/download_bbcsom.log
grep WARNING logs/download_bbcsom.log
```

### 3. Validate Topic Classification

```python
import pandas as pd
import json

df = pd.read_parquet("data/processed/silver/source=BBC-Somali/")
df['metadata'] = df['source_metadata'].apply(json.loads)
df['topic'] = df['metadata'].apply(lambda x: x.get('primary_dialect'))

# Check topic distribution
print(df['topic'].value_counts())

# Expected distribution:
# politics    40%
# sports      20%
# economy     15%
# general     15%
# health      10%
```

### 4. Schedule Regular Updates

```bash
# Weekly cron job (Sundays at 2 AM)
0 2 * * 0 /path/to/bbcsom-download --max-articles 100

# Daily updates (smaller batches)
0 2 * * * /path/to/bbcsom-download --max-articles 20
```

### 5. Backup Scraped Data

```bash
# Compress and backup
tar -czf bbc-articles-$(date +%Y%m%d).tar.gz data/staging/source=BBC-Somali/

# Upload to cloud storage
aws s3 cp bbc-articles-*.tar.gz s3://somali-nlp-backups/
```

---

## Advanced Usage

### Custom Discovery Strategy

```python
from somali_dialect_classifier.preprocessing import BBCSomaliProcessor

class CustomBBCProcessor(BBCSomaliProcessor):
    def _discover_from_rss(self):
        """Custom: Discover from RSS feed."""
        import feedparser

        feed_url = "https://www.bbc.com/somali/index.xml"
        feed = feedparser.parse(feed_url)

        urls = []
        for entry in feed.entries:
            urls.append(entry.link)

        return urls

    def download(self):
        # Add RSS to discovery
        article_urls = set()
        article_urls.update(self._discover_from_homepage())
        article_urls.update(self._discover_from_rss())  # Custom
        # ... rest of logic
```

### Parallel Scraping (Advanced)

**Warning**: Only use if you have explicit permission from BBC.

```python
from concurrent.futures import ThreadPoolExecutor
import requests
import time
import random

def scrape_article(url):
    time.sleep(random.uniform(3, 6))  # Still rate limit per thread
    response = requests.get(url, headers=headers)
    # ... parse and return
    return article_data

with ThreadPoolExecutor(max_workers=2) as executor:  # Very conservative
    futures = [executor.submit(scrape_article, url) for url in article_urls]
    articles = [f.result() for f in futures]
```

---

## Integration with Other Sources

BBC data integrates seamlessly with other sources:

```python
from somali_dialect_classifier.preprocessing import (
    WikipediaSomaliProcessor,
    BBCSomaliProcessor,
    HuggingFaceSomaliProcessor,
    SprakbankenSomaliProcessor
)

# Process all sources
WikipediaSomaliProcessor().run()                    # Formal, encyclopedic
BBCSomaliProcessor(max_articles=500).run()          # Journalistic, current
HuggingFaceSomaliProcessor(max_records=10000).run() # Web-scraped, informal
SprakbankenSomaliProcessor(corpus_id="all").run()   # Academic, diverse domains

# Compare by source type
import pandas as pd
df = pd.read_parquet("data/processed/silver/")
print(df.groupby('source')['tokens'].describe())
```

---

## References

- **BBC Somali**: https://www.bbc.com/somali
- **robots.txt**: https://www.bbc.com/robots.txt
- **BeautifulSoup Documentation**: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- **Requests Documentation**: https://requests.readthedocs.io/
- **Ethical Scraping Guide**: https://www.scrapehero.com/how-to-prevent-getting-blacklisted-while-scraping/

---

## Next Steps

After processing BBC data:

1. **Verify Deduplication**: Discovery-stage deduplication now prevents duplicates automatically
   ```bash
   # Check ledger statistics
   sqlite3 data/ledger/crawl_ledger.db \
     "SELECT state, COUNT(*) FROM crawl_ledger WHERE source='bbc' GROUP BY state;"

   # See deduplication guide for comprehensive testing
   # docs/howto/deduplication.md
   ```

2. **Analyze Topics**: Examine topic distribution
   ```python
   import pandas as pd
   df = pd.read_parquet("data/processed/silver/source=BBC-Somali/")
   # Analyze by topic...
   ```

3. **Combine Sources**: Merge with Wikipedia, HuggingFace, Språkbanken
4. **Temporal Analysis**: Track language evolution over time using `scraped_at` field

---

## See Also

- [Data Pipeline Overview](../overview/data-pipeline-architecture.md) - ETL architecture
- [Processing Pipelines Guide](processing-pipelines.md) - Walkthroughs for all sources
- [API Reference](../reference/api.md) - BBCSomaliProcessor API
- [Custom Filters Guide](custom-filters.md) - Creating custom quality filters
- [Wikipedia Integration Guide](wikipedia-integration.md) - Encyclopedia processing
- [HuggingFace Integration Guide](huggingface-integration.md) - Large-scale web corpora
- [Språkbanken Integration Guide](sprakbanken-integration.md) - Academic corpora

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
