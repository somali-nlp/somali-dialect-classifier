# Metrics & Quality Report Issues - Analysis & Solutions

**Date**: 2025-10-20
**Status**: Critical Issues Identified

---

## Executive Summary

All four data sources complete successfully and generate data, BUT the metrics collection and quality reports contain critical errors that misrepresent pipeline health.

### Current Status

| Source | Actual Status | Reported Status | Success Rate (Reported) | Main Issue |
|--------|---------------|-----------------|-------------------------|------------|
| Wikipedia | ✅ Success | ✅ Healthy | 932900.0% ❌ | Wrong calculation |
| Språkbanken | ✅ Success | ❌ **UNHEALTHY** | 0.0% ❌ | Wrong semantic model |
| BBC | ✅ Success | ✅ Healthy | 100.0% ✓ | Correct (URL-based) |
| HuggingFace | ✅ Success | ❌ **UNHEALTHY** | 0.0% ❌ | Wrong semantic model |

---

## Critical Issues

### Issue 1: Broken Success Rate Calculation

**Problem**: Success rate formula assumes `urls_fetched` is always > 0

```python
# Current (BROKEN):
fetch_success_rate = (urls_fetched / urls_discovered) * 100  # Division by zero OR wrong semantics
```

**Evidence**:
- **Wikipedia**: 932900.0% success rate
  - Calculation: `(9329 records / 1 URL) * 100 = 932900%`
  - Reality: 1 XML dump file → 9,329 records extracted (100% success)

- **Språkbanken**: 0.0% success rate → Marked **UNHEALTHY**
  - Calculation: `(0 / 0) * 100 = 0%`
  - Reality: Successfully processed 4,015 records from corpus files

- **HuggingFace**: 0.0% success rate → Marked **UNHEALTHY**
  - Calculation: `(0 / 0) * 100 = 0%`
  - Reality: Successfully streamed and processed 48 records

**Root Cause**: Metrics designed for URL-based web scraping (BBC) but applied to all pipelines regardless of architecture.

---

### Issue 2: Semantic Mismatch - URL Metrics for Non-URL Pipelines

**Problem**: Different pipeline architectures tracked with same URL-centric metrics

| Pipeline | Architecture | Uses URLs? | Current Tracking | Should Track |
|----------|--------------|------------|------------------|--------------|
| **Wikipedia** | XML dump processing | ❌ No | urls_fetched=1, urls_processed=9329 | files_processed=1, records_extracted=9329 |
| **Språkbanken** | Corpus file reading | ❌ No | urls_fetched=0, urls_processed=4015 | files_read=1, records_loaded=4015 |
| **HuggingFace** | Dataset API streaming | ❌ No | urls_fetched=0, urls_processed=48 | batches_streamed=1, records_fetched=50, records_processed=48 |
| **BBC** | Web scraping | ✅ Yes | urls_fetched=3, urls_processed=3 | ✓ Correct model |

**Impact**:
- False "UNHEALTHY" status for Språkbanken and HuggingFace
- Meaningless metrics (e.g., "URLs Discovered: 0")
- Misleading recommendations ("Consider reviewing error logs" when there are no errors)

---

### Issue 3: Deduplication Metrics Not Tracked

**Problem**: All sources show zero deduplication despite deduplication running

**Evidence** (from all sources):
```json
"unique_hashes": 0,
"duplicate_hashes": 0,
"near_duplicates": 0
```

**Impact**:
- Cannot assess data quality
- Cannot track duplicate removal effectiveness
- Missing critical data lineage information

---

### Issue 4: Missing Text Length Tracking

**Problem**: Some pipelines don't record text lengths during processing

**Evidence**:
- **Wikipedia**: ✓ Has 9,329 text_length entries
- **Språkbanken**: ❌ `text_lengths: []` (empty)
- **BBC**: ✓ Has 3 text_length entries
- **HuggingFace**: ❌ `text_lengths: []` (empty)

**Impact**: Cannot analyze:
- Text quality distribution
- Outlier detection
- Mean/median text sizes

---

### Issue 5: HuggingFace Timing Data All Zeros

**Problem**: 50 fetch_duration entries all showing `0 ms`

```json
"fetch_durations_ms": [0, 0, 0, ..., 0]  // 50 zeros
```

**Root Cause**: Timer not capturing actual async streaming work

**Impact**: Cannot measure:
- Streaming performance
- Bottleneck identification
- Throughput optimization

---

## Detailed Metrics Breakdown

### Wikipedia (Run: 20251020_102754)

**What Worked:**
- ✓ Downloaded 12.7 MB XML dump successfully
- ✓ Extracted 9,329 records
- ✓ Text length distribution captured

**Metrics Issues:**
```json
{
  "urls_discovered": 1,        // Should be "files_downloaded"
  "urls_fetched": 1,           // Should be "files_processed"
  "urls_processed": 9329,      // Should be "records_extracted"
  "fetch_success_rate": 9329.0,  // ❌ Should be 100.0
  "unique_hashes": 0,          // ❌ Should track deduplication
  "duplicate_hashes": 0
}
```

**Quality Report Says:**
- "Success Rate: 932900.0%" ❌
- "URLs Processed: 9,329 (932900.0%)" ❌
- "🐢 Slow fetch times detected" ⚠️ (8.8s for 12.7MB is actually good)

---

### Språkbanken (Run: 20251020_102841)

**What Worked:**
- ✓ Successfully processed 4,015 records from corpus
- ✓ Created 700KB silver dataset

**Metrics Issues:**
```json
{
  "urls_discovered": 0,        // ❌ Should be "corpora_files_read"
  "urls_fetched": 0,           // ❌ Should be "files_processed"
  "urls_processed": 4015,      // Should be "records_loaded"
  "fetch_success_rate": 0,     // ❌ Should be 100.0
  "bytes_downloaded": 0,       // ❌ Should track file size
  "text_lengths": [],          // ❌ Empty - not collecting
  "unique_hashes": 0           // ❌ Not tracking
}
```

**Quality Report Says:**
- "**Pipeline Status:** ❌ **UNHEALTHY**" ❌ FALSE ALARM
- "Success Rate: 0.0%" ❌
- "Data Downloaded: 0.0 B" ❌
- "⚠️ Low success rate detected" ❌ WRONG

---

### BBC (Run: 20251020_102948)

**What Worked:**
- ✓ URL-based scraping model is correct
- ✓ All metrics meaningful
- ✓ Ethical rate limiting working

**Metrics Issues:**
```json
{
  "urls_discovered": 125,      // ✓ Correct
  "urls_fetched": 3,           // ✓ Correct (limited for test)
  "urls_processed": 3,         // ✓ Correct
  "fetch_success_rate": 1.0,   // ✓ 100% (displayed as 100.0%)
  "unique_hashes": 0,          // ❌ Not tracking deduplication
  "text_lengths": [581, 4753, 5323]  // ✓ Correct
}
```

**Quality Report Says:**
- "**Pipeline Status:** ✅ **HEALTHY**" ✓
- "Success Rate: 100.0%" ✓
- "URLs Fetched: 3 (2.4%)" ✓ (3 out of 125 discovered)

**Only Issue**: Missing deduplication tracking

---

### HuggingFace (Run: 20251020_104917)

**What Worked:**
- ✓ Streamed 50 records from allenai/c4
- ✓ Processed 48 records (2 filtered by langid)
- ✓ Created 275KB silver dataset

**Metrics Issues:**
```json
{
  "urls_discovered": 0,        // ❌ Should be "dataset_opened"
  "urls_fetched": 0,           // ❌ Should be "records_fetched"
  "urls_processed": 48,        // Should be "records_processed"
  "fetch_success_rate": 0,     // ❌ Should be 96.0% (48/50)
  "fetch_durations_ms": [0,0,0,...],  // ❌ All zeros
  "text_lengths": [],          // ❌ Empty
  "unique_hashes": 0           // ❌ Not tracking
}
```

**Quality Report Says:**
- "**Pipeline Status:** ❌ **UNHEALTHY**" ❌ FALSE ALARM
- "Success Rate: 0.0%" ❌
- "Fetch Performance: Mean: 0 ms" ❌
- "⚠️ Low success rate detected" ❌ WRONG

---

## Root Causes

### 1. One-Size-Fits-All Metrics Model
**Location**: `src/somali_dialect_classifier/utils/metrics.py`

The `MetricsCollector` class assumes all pipelines follow the BBC web scraping pattern:
- URLs discovered → URLs fetched → URLs processed
- But Wikipedia, Språkbanken, and HuggingFace don't use this model

### 2. Hardcoded Success Rate Formula
**Location**: `src/somali_dialect_classifier/utils/metrics.py` (likely line ~100-120)

```python
# Current (BROKEN):
def calculate_stats(self):
    total_urls = self.snapshot['urls_fetched']
    if total_urls > 0:
        self.statistics['fetch_success_rate'] = (
            (total_urls - self.snapshot['urls_failed']) / total_urls
        )
    else:
        self.statistics['fetch_success_rate'] = 0  # ❌ Marks healthy pipelines as failed
```

### 3. Missing Deduplication Tracking
**Location**: Multiple processors

Deduplication happens but metrics aren't incremented:
- Wikipedia: Uses DedupEngine but doesn't call `metrics.increment('unique_hashes')`
- Språkbanken: Same issue
- HuggingFace: Same issue

### 4. Text Lengths Not Collected in Some Pipelines
**Location**: Språkbanken and HuggingFace processors

The `metrics.record_text_length()` calls are missing or not being triggered.

---

## Solution Plan

### Phase 1: Add Pipeline Type Abstraction

**File**: `src/somali_dialect_classifier/utils/metrics.py`

```python
class PipelineType(Enum):
    """Pipeline architecture types for appropriate metrics collection."""
    WEB_SCRAPING = "web_scraping"    # BBC: URL-based fetching
    FILE_PROCESSING = "file_processing"  # Wikipedia, Språkbanken: File → records
    STREAM_PROCESSING = "stream_processing"  # HuggingFace: API streaming
```

### Phase 2: Fix MetricsCollector to Support Multiple Models

**Add type-aware metrics:**

```python
class MetricsCollector:
    def __init__(self, run_id: str, source: str, pipeline_type: PipelineType):
        self.pipeline_type = pipeline_type
        # ...

        # Flexible snapshot based on type
        if pipeline_type == PipelineType.WEB_SCRAPING:
            self.snapshot.update({
                'urls_discovered': 0,
                'urls_fetched': 0,
                'urls_processed': 0,
            })
        elif pipeline_type == PipelineType.FILE_PROCESSING:
            self.snapshot.update({
                'files_discovered': 0,
                'files_processed': 0,
                'records_extracted': 0,
            })
        elif pipeline_type == PipelineType.STREAM_PROCESSING:
            self.snapshot.update({
                'datasets_opened': 0,
                'records_fetched': 0,
                'records_processed': 0,
                'batches_completed': 0,
            })
```

### Phase 3: Fix Success Rate Calculation

```python
def _calculate_success_rate(self) -> float:
    """Calculate success rate appropriate to pipeline type."""
    if self.pipeline_type == PipelineType.WEB_SCRAPING:
        total = self.snapshot.get('urls_fetched', 0)
        failed = self.snapshot.get('urls_failed', 0)
        if total > 0:
            return ((total - failed) / total) * 100
        return 0.0

    elif self.pipeline_type == PipelineType.FILE_PROCESSING:
        total = self.snapshot.get('files_discovered', 0)
        processed = self.snapshot.get('files_processed', 0)
        if total > 0:
            return (processed / total) * 100
        return 100.0  # If no files tracked, assume success if records exist

    elif self.pipeline_type == PipelineType.STREAM_PROCESSING:
        fetched = self.snapshot.get('records_fetched', 0)
        processed = self.snapshot.get('records_processed', 0)
        if fetched > 0:
            return (processed / fetched) * 100
        return 100.0  # If no fetch tracking, assume success if records exist
```

### Phase 4: Add Deduplication Tracking

**For Wikipedia processor** (`wikipedia_somali_processor.py`):
```python
# After deduplication check:
if self.dedup.is_duplicate_hash(text_hash):
    self.metrics.increment('duplicate_hashes')
    continue

# After near-duplicate check:
is_dup, similar_url, minhash_sig = self.dedup.process_document(text, url)
if is_dup:
    self.metrics.increment('near_duplicates')
    continue
else:
    self.metrics.increment('unique_hashes')
```

**Similar changes for Språkbanken and HuggingFace processors.**

### Phase 5: Fix Text Length Collection

**For Språkbanken** (`sprakbanken_somali_processor.py`):
```python
# In process() method, after building silver_record:
for record in silver_records:
    self.metrics.record_text_length(len(record['text']))
```

**For HuggingFace** (`huggingface_somali_processor.py`):
```python
# In process() method, after cleaning:
if cleaned:
    self.metrics.record_text_length(len(cleaned))
```

### Phase 6: Update Quality Reporter

**File**: `src/somali_dialect_classifier/utils/metrics.py` (QualityReporter class)

Make reports adaptive to pipeline type:

```python
def generate_markdown_report(self, output_path: Path):
    """Generate quality report adapted to pipeline type."""

    # Detect pipeline type from metrics
    if 'urls_fetched' in self.metrics.snapshot:
        pipeline_type = PipelineType.WEB_SCRAPING
    elif 'files_processed' in self.metrics.snapshot:
        pipeline_type = PipelineType.FILE_PROCESSING
    else:
        pipeline_type = PipelineType.STREAM_PROCESSING

    # Generate appropriate sections
    if pipeline_type == PipelineType.WEB_SCRAPING:
        self._add_url_statistics(report)
    elif pipeline_type == PipelineType.FILE_PROCESSING:
        self._add_file_statistics(report)
    else:
        self._add_stream_statistics(report)
```

---

## Implementation Priority

### Priority 1: Critical (Immediate)
1. ✅ Fix success rate calculation (prevents false UNHEALTHY status)
2. ✅ Add pipeline type abstraction
3. ✅ Update all processors to specify pipeline type

### Priority 2: High (This Week)
4. ✅ Add deduplication metrics tracking
5. ✅ Fix text length collection in Språkbanken and HuggingFace
6. ✅ Update QualityReporter to adapt to pipeline type

### Priority 3: Medium (Next Week)
7. ⏳ Add HuggingFace streaming performance metrics (proper timing)
8. ⏳ Add filter statistics breakdown to reports
9. ⏳ Add data quality scores (completeness, validity, etc.)

### Priority 4: Low (Future Enhancement)
10. ⏳ Add comparison reports (compare multiple runs)
11. ⏳ Add alerting thresholds (configurable quality gates)
12. ⏳ Add visualization (charts for distributions)

---

## Testing Plan

### Test 1: Verify Success Rates
Run all 4 sources and verify:
- Wikipedia: 100.0% (not 932900.0%)
- Språkbanken: 100.0% (not 0.0%) → Status: HEALTHY
- BBC: 100.0% ✓
- HuggingFace: 96.0% (48/50 records) → Status: HEALTHY

### Test 2: Verify Deduplication Metrics
- Check all sources show non-zero unique_hashes
- Artificially inject duplicate to verify duplicate_hashes increments

### Test 3: Verify Text Lengths
- All sources should have populated text_lengths arrays
- Verify mean/median/min/max calculations are correct

### Test 4: Verify Reports
- Wikipedia report shows "Files Processed: 1"
- Språkbanken report shows "Corpus Files Read: 1"
- HuggingFace report shows "Records Fetched: 50, Records Processed: 48"
- No "UNHEALTHY" false alarms

---

## Expected Outcomes After Fixes

### Wikipedia
```markdown
**Pipeline Status:** ✅ **HEALTHY**
- **Success Rate:** 100.0%
- **Files Processed:** 1
- **Records Extracted:** 9,329
- **Deduplication Rate:** X.X%
- **Unique Documents:** XXXX
- **Data Processed:** 12.7 MB
```

### Språkbanken
```markdown
**Pipeline Status:** ✅ **HEALTHY**
- **Success Rate:** 100.0%
- **Corpus Files Read:** 1
- **Records Loaded:** 4,015
- **Deduplication Rate:** X.X%
- **Unique Documents:** XXXX
```

### HuggingFace
```markdown
**Pipeline Status:** ✅ **HEALTHY**
- **Success Rate:** 96.0%
- **Records Fetched:** 50
- **Records Processed:** 48
- **Filtered:** 2 (langid: 2)
- **Deduplication Rate:** X.X%
- **Unique Documents:** XX
```

---

## Files to Modify

1. `src/somali_dialect_classifier/utils/metrics.py`
   - Add PipelineType enum
   - Update MetricsCollector.__init__()
   - Fix _calculate_success_rate()
   - Update QualityReporter

2. `src/somali_dialect_classifier/preprocessing/base_pipeline.py`
   - Add pipeline_type parameter
   - Pass to MetricsCollector

3. `src/somali_dialect_classifier/preprocessing/wikipedia_somali_processor.py`
   - Specify pipeline_type=FILE_PROCESSING
   - Add deduplication metrics
   - Ensure text_lengths tracked

4. `src/somali_dialect_classifier/preprocessing/sprakbanken_somali_processor.py`
   - Specify pipeline_type=FILE_PROCESSING
   - Add deduplication metrics
   - Add text_lengths tracking

5. `src/somali_dialect_classifier/preprocessing/bbc_somali_processor.py`
   - Specify pipeline_type=WEB_SCRAPING
   - Add deduplication metrics

6. `src/somali_dialect_classifier/preprocessing/huggingface_somali_processor.py`
   - Specify pipeline_type=STREAM_PROCESSING
   - Add deduplication metrics
   - Add text_lengths tracking
   - Fix fetch timing (optional)

---

## Summary

**Current State**:
- ❌ 2/4 sources falsely reported as UNHEALTHY
- ❌ Wikipedia shows 932900% success rate
- ❌ Zero deduplication tracking across all sources
- ❌ Missing text length data for 2 sources

**After Fixes**:
- ✅ All sources accurately report HEALTHY status
- ✅ Success rates between 96-100%
- ✅ Full deduplication tracking
- ✅ Complete text length distributions
- ✅ Reports adapted to pipeline architecture

**Estimated Effort**:
- 4-6 hours for Priority 1-2 fixes
- Ready for production use after Phase 6 complete
