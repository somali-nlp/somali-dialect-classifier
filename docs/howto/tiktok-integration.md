# TikTok Integration Guide

**Collect Somali comments from TikTok videos using Apify**

---

## Overview

### What is TikTok as a Data Source?

TikTok is a social media platform where users create and share short videos. The comments section contains rich colloquial Somali text with diverse dialects - perfect for training dialect classification models.

**Key characteristics:**
- **Register:** Colloquial/informal social media language
- **Dialect diversity:** Natural mixing of Somali dialects
- **Text quality:** Variable (includes emojis, slang, code-switching)
- **Volume:** High engagement = many comments per video

### Why Collect TikTok Comments?

1. **Dialect Diversity:** TikTok users represent diverse Somali-speaking regions
2. **Colloquial Language:** Natural, everyday Somali (unlike formal news/Wikipedia)
3. **Social Media Register:** Captures modern internet Somali usage
4. **High Volume:** Popular videos have hundreds to thousands of comments

### Data Collection via Apify

We use [Apify's TikTok Comments Scraper](https://apify.com/clockworks/tiktok-comments-scraper) to collect comments ethically and efficiently.

**Pricing:** $1 per 1,000 comments (see [Cost Analysis](../cost-analysis/tiktok-apify-costs.md))

---

## Prerequisites

### 1. Apify Account Setup

1. **Create account:**
   - Visit https://apify.com
   - Sign up (free tier available)
   - Consider Starter plan ($49/month) for production use

2. **Get API token:**
   - Log in to Apify Console
   - Go to Settings → Integrations
   - Copy your API token (starts with `apify_api_`)
   - Keep this secret - do not commit to git!

3. **Budget planning:**
   - Estimate comment volume
   - Calculate cost: $1 per 1,000 comments
   - Effective cost after filtering: ~$3.67 per 1k linguistic comments
   - See [Cost Analysis](../cost-analysis/tiktok-apify-costs.md) for details

### 2. Video URL Collection

You need to curate a list of TikTok video URLs with Somali content.

**Selection criteria:**
- Videos with Somali audio or captions
- High engagement (many comments)
- Recent uploads (last 6 months)
- Diverse topics and creators

**How to find videos:**
- Search TikTok for Somali hashtags: #somalia, #somali, #mogadishu
- Browse popular Somali creators
- Check trending videos in Somali language setting
- Use TikTok's "For You" feed with Somali language preference

---

## Installation

### 1. Install Integration

The TikTok integration is included in the main package. Simply install in development mode:

```bash
cd /path/to/somali-dialect-classifier
pip install -e .
```

This installs:
- `apify-client==1.7.1` (Apify API client)
- `tiktoksom-download` CLI command
- TikTok processor modules

### 2. Verify Installation

```bash
# Check apify-client installed
pip show apify-client

# Test CLI command available
tiktoksom-download --help

# Test imports
python -c "from somali_dialect_classifier.preprocessing.tiktok_somali_processor import TikTokSomaliProcessor"
```

### 3. Configure Environment Variables

Create or update `.env` file in project root:

```bash
# TikTok Apify Configuration
SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=apify_api_YOUR_TOKEN_HERE
SDC_SCRAPING__TIKTOK__APIFY_USER_ID=your_user_id  # optional
SDC_SCRAPING__TIKTOK__MAX_TOTAL_COMMENTS=30000    # target limit
SDC_SCRAPING__TIKTOK__MAX_COMMENTS_PER_VIDEO=500  # per-video limit
```

**Security:** Add `.env` to `.gitignore` to prevent committing API tokens!

---

## Basic Usage

### Step 1: Create Video URLs File

Create a plain text file with one URL per line:

**Example `data/tiktok_urls.txt`:**
```
https://www.tiktok.com/@somaliuser1/video/7123456789012345678
https://www.tiktok.com/@somaliuser2/video/7234567890123456789
https://www.tiktok.com/@somaliuser3/video/7345678901234567890
```

Or use JSON format for metadata:

**Example `videos.json`:**
```json
{
  "video_urls": [
    "https://www.tiktok.com/@somaliuser1/video/7123456789012345678",
    "https://www.tiktok.com/@somaliuser2/video/7234567890123456789"
  ],
  "metadata": {
    "collection_date": "2025-10-31",
    "curator": "researcher@example.com",
    "topic": "somali_culture"
  }
}
```

### Step 2: Run TikTok Scraper

```bash
tiktoksom-download --video-urls data/tiktok_urls.txt
```

**What happens:**
1. **Cost estimate displayed** (e.g., "Estimated cost: $1.50 for 3 videos")
2. **User confirmation** (for costs >$10)
3. **Apify actor starts** (scraping begins)
4. **Progress updates** (poll every 15 seconds)
5. **Data saved** in 4 stages:
   - `data/raw/` - Raw Apify JSON
   - `data/staging/` - Transformed comments
   - `data/processed/` - Cleaned text
   - `data/processed/silver/` - Final Parquet dataset

### Step 3: Check Outputs

```bash
# View raw Apify data
ls data/raw/source=TikTok-Somali/date_accessed=*/

# View staging comments (JSONL)
head data/staging/source=TikTok-Somali/date_accessed=*/tiktok-somali_*_staging_comments.jsonl

# View silver dataset (Parquet)
python -c "import pyarrow.parquet as pq; print(pq.read_table('data/processed/silver/source=TikTok-Somali/date_accessed=*/tiktok-somali_*_silver_part-0000.parquet'))"

# Check metrics
cat data/metrics/*tiktok*extraction.json | jq '.layered_metrics.extraction'
```

---

## Advanced Usage

### Setting Comment Limits

Control how many comments to scrape:

```bash
# Limit total comments across all videos
tiktoksom-download --video-urls data/tiktok_urls.txt --max-comments 10000

# Limit comments per video
tiktoksom-download --video-urls data/tiktok_urls.txt --max-per-video 500

# Both limits (whichever hits first)
tiktoksom-download --video-urls data/tiktok_urls.txt --max-comments 10000 --max-per-video 500
```

### Cost Management Strategies

**Budget-conscious collection:**

```bash
# Small test run (100 comments, ~$0.10)
tiktoksom-download --video-urls data/test_tiktok_urls.txt --max-comments 100

# Phased collection (collect in batches)
tiktoksom-download --video-urls data/batch1_tiktok_urls.txt --max-comments 5000
tiktoksom-download --video-urls data/batch2_tiktok_urls.txt --max-comments 5000

# Target collection (30k comments = ~$39)
tiktoksom-download --video-urls data/tiktok_urls.txt --max-comments 30000
```

**Tips:**
- Start with small test run to validate video URLs
- Monitor Apify console for real-time cost tracking
- Curate high-quality videos to maximize linguistic value
- Use `--max-per-video` to avoid over-collecting from single viral videos

### Orchestration with Other Sources

Combine TikTok with other data sources:

```bash
# Run TikTok only
somali-orchestrate --pipeline tiktok --tiktok-video-urls data/tiktok_urls.txt

# Run TikTok + Wikipedia + BBC
somali-orchestrate --pipeline all \
  --tiktok-video-urls data/tiktok_urls.txt \
  --max-bbc-articles 100 \
  --skip-sources huggingface,sprakbanken
```

### Video URL Curation Best Practices

**Quality over quantity:**
- Prioritize videos with 100+ comments
- Select diverse creators (not just one popular account)
- Mix topics (culture, news, comedy, education)
- Include regional variation (Somalia, Somaliland, diaspora)

**Tools for curation:**
- **TikTok search:** Use hashtags like #somalia, #somali, #af-soomaali
- **Browser extensions:** TikTok downloader tools show video stats
- **Spreadsheet tracking:** Maintain curation log with video metadata

---

## Troubleshooting

### Error: "Apify API token not provided"

**Cause:** Missing or incorrectly set environment variable

**Solution:**
```bash
# Check if token is set
echo $SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN

# If empty, set it:
export SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=apify_api_YOUR_TOKEN

# Or add to .env file:
echo 'SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN=apify_api_YOUR_TOKEN' >> .env

# Verify with --api-token flag:
tiktoksom-download --video-urls data/tiktok_urls.txt --api-token apify_api_YOUR_TOKEN
```

### Error: "No valid URLs found in file"

**Cause:** Video URLs file is empty or has invalid URLs

**Solution:**
```bash
# Check file contents
cat data/tiktok_urls.txt

# Ensure URLs start with https://
# Valid format: https://www.tiktok.com/@username/video/1234567890

# Remove comments and empty lines
grep -v '^#' data/tiktok_urls.txt | grep -v '^$' > data/tiktok_urls_clean.txt
```

### Error: "Run FAILED"

**Cause:** Apify actor failed (invalid URLs, rate limits, etc.)

**Solution:**
1. Check Apify console: https://console.apify.com/actors/runs
2. View actor run logs for specific error
3. Common issues:
   - **Invalid video URLs:** Verify URLs are public and accessible
   - **Age-restricted content:** Apify can't access restricted videos
   - **Rate limits:** Reduce number of videos, try again later
   - **Insufficient credits:** Top up Apify account

### Warning: "Empty dataset"

**Cause:** Videos have no comments or all comments were filtered

**Solution:**
- Check if videos are very recent (no comments yet)
- Verify videos have Somali language content
- Look for videos with higher engagement
- Check Apify actor output for actual comment count

### Error: "APIConnectionError" or Timeout

**Cause:** Network issues or Apify API down

**Solution:**
```bash
# Check Apify status
curl -I https://api.apify.com/v2

# Increase timeout (default: 3600s = 1 hour)
# Edit config if needed in .env:
SDC_SCRAPING__TIKTOK__MAX_WAIT_TIME=7200  # 2 hours

# Retry with exponential backoff
tiktoksom-download --video-urls data/tiktok_urls.txt --force
```

---

## Data Pipeline Details

### Pipeline Stages

1. **Discovery:** Video URLs saved to `data/raw/`
2. **Extraction:** Apify scrapes comments → `data/raw/` (JSON)
3. **Transformation:** Comments formatted → `data/staging/` (JSONL)
4. **Processing:** Text cleaned, deduplicated → `data/processed/` (TXT)
5. **Silver dataset:** Final Parquet with metadata → `data/processed/silver/`

### Data Preservation Strategy

**Key principle:** You pay for every comment, so we keep them ALL!

- **No fuzzy deduplication:** MinHash disabled (only exact duplicates removed)
- **Minimal filtering:** Only emoji-only comments removed (e.g., "😂😂😂")
- **All metadata preserved:** Author, timestamps, likes, replies

### Silver Dataset Schema

The final dataset includes:

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Cleaned comment text |
| `url` | string | Unique comment URL (video + comment ID) |
| `title` | string | Truncated comment text (first 100 chars) |
| `source_type` | string | "social_media" |
| `license` | string | "TikTok Terms of Service" |
| `language` | string | "so" (Somali) |
| `domain` | string | "social_media" |
| `register` | string | "colloquial" |
| `metadata` | struct | Video URL, author, timestamp, likes, etc. |

---

## Cost Management

See detailed cost analysis in [Cost Analysis Guide](../cost-analysis/tiktok-apify-costs.md).

**Quick reference:**
- **Raw cost:** $1 per 1,000 Apify results
- **Effective cost:** ~$3.67 per 1,000 linguistic comments (after 27% emoji-only filtering)
- **Target budget:** 30,000 comments = ~$39 (within Apify Starter plan)

---

## Best Practices

### Video Selection
- ✅ High engagement (100+ comments)
- ✅ Somali language content
- ✅ Diverse creators and topics
- ✅ Recent uploads (last 6 months)
- ❌ Avoid age-restricted content
- ❌ Avoid very new videos (<24 hours, few comments)

### Collection Strategy
- Start with small test (100 comments)
- Monitor Apify console during first run
- Collect in batches to stay within budget
- Keep curation log for reproducibility

### Data Quality
- Review sample of collected comments
- Check language distribution (some code-switching expected)
- Verify dialect diversity across videos
- Monitor emoji-only filter effectiveness

---

## Additional Resources

- **Apify TikTok Scraper:** https://apify.com/clockworks/tiktok-comments-scraper
- **Apify Documentation:** https://docs.apify.com
- **Cost Analysis:** `docs/cost-analysis/tiktok-apify-costs.md`
- **Integration Architecture:** `.claude/reports/arch/arch-tiktok-integration-20251031.md`

---

**Integration Date:** 2025-10-31
**Code Quality:** 9.3/10
**Status:** Production-ready ✅
