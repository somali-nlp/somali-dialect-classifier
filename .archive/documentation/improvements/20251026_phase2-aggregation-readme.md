# Phase 2: Volume-Weighted Aggregation

## Overview

Phase 2 implements safe, volume-weighted aggregation of compatible metrics across data sources for the Somali NLP metrics system. This addresses the fundamental issue from Phase 0 where incompatible metrics were being averaged together, producing meaningless results.

## The Problem (Phase 0)

Phase 0 had a critical bug where incompatible metrics were averaged:

```python
# WRONG - Phase 0 approach
overall_success_rate = (
    bbc_http_success_rate +      # 10.7% (web scraping)
    wiki_file_success_rate +     # 100% (file processing)
    hf_stream_success_rate       # 100% (streaming)
) / 3 = 70.2%  # Meaningless!
```

This is like averaging:
- Your car's fuel efficiency (30 MPG)
- Your Wi-Fi speed (100 Mbps)
- Your coffee temperature (180°F)

The result has no meaning because the metrics measure fundamentally different things.

## The Solution (Phase 2)

Phase 2 provides:

1. **Compatibility Validation**: Prevents aggregating incompatible metrics
2. **Volume-Weighted Aggregation**: Gives appropriate weight to each source based on data volume
3. **Multiple Aggregation Methods**: Choose the right method for your use case
4. **Comprehensive Breakdown**: Shows each source's contribution

### Example: Volume-Weighted Quality

```python
from somali_dialect_classifier.utils import calculate_volume_weighted_quality

sources = [
    {
        "name": "BBC",
        "records_written": 150,
        "layered_metrics": {"quality": {"quality_pass_rate": 0.847}}
    },
    {
        "name": "Wikipedia",
        "records_written": 10000,
        "layered_metrics": {"quality": {"quality_pass_rate": 1.0}}
    }
]

result = calculate_volume_weighted_quality(sources)
print(f"Overall quality: {result['overall_quality_rate']:.1%}")  # 99.8%
```

**Why volume-weighted?**
- Simple average: (84.7% + 100%) / 2 = 92.3%
- Volume-weighted: (150×84.7% + 10000×100%) / 10150 = 99.8%

The volume-weighted average correctly represents the actual dataset quality, giving more weight to Wikipedia which contributes 98.5% of the data.

## Compatible Metrics

### Always Compatible (across all pipeline types)
- `quality_pass_rate` - Records passing quality filters
- `deduplication_rate` - Records filtered as duplicates
- `records_written` - Total records written
- `bytes_downloaded` - Total bytes downloaded

### Pipeline-Specific (only compatible within same type)
- **Web Scraping**: `http_request_success_rate`, `content_extraction_success_rate`
- **File Processing**: `file_extraction_success_rate`, `record_parsing_success_rate`
- **Stream Processing**: `stream_connection_success_rate`, `record_retrieval_success_rate`

## Usage

### 1. Basic Volume-Weighted Quality

```python
from somali_dialect_classifier.utils import calculate_volume_weighted_quality

result = calculate_volume_weighted_quality(sources)

print(f"Overall quality: {result['overall_quality_rate']:.1%}")
print(f"Total records: {result['total_records']:,}")

# See breakdown by source
for source in result['source_breakdown']:
    print(f"{source['source']}: {source['contribution']:.1%} contribution")
```

### 2. Validate Compatibility Before Aggregating

```python
from somali_dialect_classifier.utils import validate_metric_compatibility

is_compat, reason = validate_metric_compatibility(sources, "http_request_success_rate")

if not is_compat:
    print(f"Cannot aggregate: {reason}")
else:
    # Safe to aggregate
    result = aggregate_compatible_metrics(sources, "http_request_success_rate")
```

### 3. Comprehensive Aggregate Summary

```python
from somali_dialect_classifier.utils import calculate_aggregate_summary

summary = calculate_aggregate_summary(sources)

print(f"Total records: {summary['total_records']:,}")
print(f"Total bytes: {summary['total_bytes']:,}")
print(f"Overall quality: {summary['quality_metrics']['overall_quality_rate']:.1%}")
```

### 4. Different Aggregation Methods

```python
from somali_dialect_classifier.utils import (
    aggregate_compatible_metrics,
    AggregationMethod
)

# Volume-weighted mean (default)
vw_mean = aggregate_compatible_metrics(
    sources, "quality_pass_rate",
    method=AggregationMethod.VOLUME_WEIGHTED_MEAN
)

# Harmonic mean (penalizes poor performers)
harmonic = aggregate_compatible_metrics(
    sources, "quality_pass_rate",
    method=AggregationMethod.HARMONIC_MEAN
)

# Min/Max for conservative/optimistic estimates
min_quality = aggregate_compatible_metrics(
    sources, "quality_pass_rate",
    method=AggregationMethod.MIN
)

# Sum for total counts
total_records = aggregate_compatible_metrics(
    sources, "records_written",
    method=AggregationMethod.SUM
)
```

## When to Use Each Aggregation Method

| Method | Use Case | Example |
|--------|----------|---------|
| `VOLUME_WEIGHTED_MEAN` | Default, most representative of overall dataset | Overall quality rate |
| `HARMONIC_MEAN` | When poor performers should heavily impact aggregate | Quality with critical thresholds |
| `WEIGHTED_HARMONIC_MEAN` | Harmonic mean weighted by volume | Balanced between penalties and volume |
| `MIN` | Worst-case scenario, conservative estimate | Minimum quality threshold |
| `MAX` | Best-case scenario, optimistic estimate | Maximum observed quality |
| `SUM` | Total counts | Total records, total bytes |

## Real Data Example

```python
# Load processing metrics from actual run
sources = [
    {
        "snapshot": {
            "source": "BBC-Somali",
            "pipeline_type": "web_scraping",
            "records_written": 20,
            "bytes_downloaded": 99176
        },
        "statistics": {
            "quality_pass_rate": 1.0,
            "deduplication_rate": 0.0
        }
    },
    {
        "snapshot": {
            "source": "Wikipedia-Somali",
            "pipeline_type": "file_processing",
            "records_written": 9623,
            "bytes_downloaded": 14280506
        },
        "statistics": {
            "quality_pass_rate": 0.7075735294117646,
            "deduplication_rate": 0.0
        }
    },
    {
        "snapshot": {
            "source": "HuggingFace-Somali_c4-so",
            "pipeline_type": "stream_processing",
            "records_written": 19,
            "bytes_downloaded": 0
        },
        "statistics": {
            "quality_pass_rate": 0.95,
            "deduplication_rate": 0.0
        }
    }
]

summary = calculate_aggregate_summary(sources)
# Total records: 9,662
# Overall quality: 70.9% (dominated by Wikipedia's 99.6% contribution)
```

## File Structure

```
src/somali_dialect_classifier/utils/
  aggregation.py                    # Phase 2 aggregation functions
  metrics.py                        # Phase 1 pipeline-specific metrics

tests/
  test_aggregation.py               # Comprehensive test suite (17 tests)

examples/
  aggregation_demo.py               # Interactive demo showing all features
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_aggregation.py -v
```

All 17 tests validate:
- Volume-weighted vs simple average shows difference
- Harmonic mean penalizes outliers
- Compatibility validation catches mistakes
- Handles zero records gracefully
- Breakdown shows source contributions
- Works with real processing.json format
- Phase 0 vs Phase 2 comparison

## Demo

Run the interactive demo to see all features:

```bash
python examples/aggregation_demo.py
```

The demo shows:
1. Simple average vs volume-weighted average
2. Harmonic mean for penalizing poor performers
3. Compatibility validation
4. Real data aggregation (BBC + Wikipedia + HuggingFace)
5. Comparison of all aggregation methods
6. Loading from processing.json files

## Key Principles

1. **Only aggregate COMPATIBLE metrics** - Use `validate_metric_compatibility()` first
2. **Weight by data volume** - Use `records_written` to weight contributions
3. **Provide breakdown** - Always show each source's contribution
4. **NEVER aggregate incompatible metrics** - Different pipeline types have different semantics
5. **Support multiple methods** - Choose the right aggregation for your use case

## Migration from Phase 0

Phase 0 code:
```python
# WRONG
overall_success = (source1_rate + source2_rate + source3_rate) / 3
```

Phase 2 code:
```python
# CORRECT
# 1. Validate compatibility
is_compat, reason = validate_metric_compatibility(sources, "quality_pass_rate")
if not is_compat:
    raise ValueError(f"Cannot aggregate: {reason}")

# 2. Calculate volume-weighted aggregate
result = calculate_volume_weighted_quality(sources)
overall_quality = result["overall_quality_rate"]

# 3. Review breakdown
for source in result["source_breakdown"]:
    print(f"{source['source']}: {source['contribution']:.1%}")
```

## Future Enhancements

Potential improvements for Phase 3:
- Time-weighted aggregation for temporal analysis
- Confidence intervals for aggregated metrics
- Automatic outlier detection and handling
- Integration with dashboard for visualization
- Historical aggregation tracking

## References

- Phase 1 Metrics Refactoring: Pipeline-specific metric names
- Processing.json format: Data structure for metrics storage
- MetricsCollector: Tracking metrics during pipeline execution
