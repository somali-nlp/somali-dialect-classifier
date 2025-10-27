# Quick Start: Aggregation Functions

## Installation

The aggregation module is part of the `somali-dialect-classifier` package:

```bash
# Already installed if you have the project
cd somali-dialect-classifier
pip install -e .
```

## 5-Minute Quick Start

### 1. Basic Volume-Weighted Quality

```python
from somali_dialect_classifier.utils import calculate_volume_weighted_quality

sources = [
    {
        "name": "Source A",
        "records_written": 100,
        "layered_metrics": {"quality": {"quality_pass_rate": 0.8}}
    },
    {
        "name": "Source B",
        "records_written": 1000,
        "layered_metrics": {"quality": {"quality_pass_rate": 0.95}}
    }
]

result = calculate_volume_weighted_quality(sources)
print(f"Overall quality: {result['overall_quality_rate']:.1%}")
# Output: Overall quality: 93.6%
```

### 2. Validate Compatibility

```python
from somali_dialect_classifier.utils import validate_metric_compatibility

# Check if safe to aggregate
is_compat, reason = validate_metric_compatibility(sources, "quality_pass_rate")

if is_compat:
    # Safe to aggregate
    result = calculate_volume_weighted_quality(sources)
else:
    print(f"Cannot aggregate: {reason}")
```

### 3. Comprehensive Summary

```python
from somali_dialect_classifier.utils import calculate_aggregate_summary

# Works with processing.json format
summary = calculate_aggregate_summary(sources)

print(f"Total records: {summary['total_records']:,}")
print(f"Overall quality: {summary['quality_metrics']['overall_quality_rate']:.1%}")

# See each source's contribution
for source in summary['source_contributions']:
    print(f"{source['source']}: {source['contribution']:.1%}")
```

## Common Use Cases

### Use Case 1: Aggregate Metrics from Processing Files

```python
import json
from pathlib import Path
from somali_dialect_classifier.utils import calculate_aggregate_summary

# Load processing metrics
metrics_dir = Path("data/metrics")
sources = []

for file in metrics_dir.glob("*_processing.json"):
    with open(file) as f:
        sources.append(json.load(f))

# Calculate aggregate
summary = calculate_aggregate_summary(sources)
print(f"Total records: {summary['total_records']:,}")
print(f"Overall quality: {summary['quality_metrics']['overall_quality_rate']:.1%}")
```

### Use Case 2: Choose Aggregation Method

```python
from somali_dialect_classifier.utils import (
    aggregate_compatible_metrics,
    AggregationMethod
)

# Conservative estimate (minimum)
min_quality = aggregate_compatible_metrics(
    sources,
    "quality_pass_rate",
    method=AggregationMethod.MIN
)

# Optimistic estimate (maximum)
max_quality = aggregate_compatible_metrics(
    sources,
    "quality_pass_rate",
    method=AggregationMethod.MAX
)

# Penalize poor performers (harmonic mean)
harmonic_quality = aggregate_compatible_metrics(
    sources,
    "quality_pass_rate",
    method=AggregationMethod.HARMONIC_MEAN
)

print(f"Quality range: {min_quality:.1%} - {max_quality:.1%}")
print(f"Harmonic mean: {harmonic_quality:.1%}")
```

### Use Case 3: Workflow Integration

```bash
# Run the workflow script
python examples/aggregate_metrics_workflow.py data/metrics

# Generates:
# - data/reports/workflow_aggregate_report.md
# - data/metrics/workflow_aggregate_metrics.json
```

## Interactive Demo

Run the comprehensive demo to see all features:

```bash
python examples/aggregation_demo.py
```

This shows:
1. Simple average vs volume-weighted
2. Harmonic mean for penalizing outliers
3. Compatibility validation
4. Real data aggregation
5. All aggregation methods
6. Loading from files

## Testing

Run the test suite to verify everything works:

```bash
pytest tests/test_aggregation.py -v
```

Expected: 17 tests passing

## Key Principles

1. **Always validate compatibility first**
   ```python
   is_compat, reason = validate_metric_compatibility(sources, metric_name)
   if not is_compat:
       raise ValueError(f"Cannot aggregate: {reason}")
   ```

2. **Use volume-weighted mean by default**
   - Represents overall dataset accurately
   - Gives appropriate weight to each source

3. **Check the breakdown**
   ```python
   for source in result['source_breakdown']:
       print(f"{source['source']}: {source['contribution']:.1%} contribution")
   ```

4. **Choose the right method**
   - `VOLUME_WEIGHTED_MEAN`: Default, most representative
   - `HARMONIC_MEAN`: Penalize poor performers
   - `MIN`: Conservative estimate
   - `MAX`: Optimistic estimate
   - `SUM`: Total counts

## Compatible Metrics

### Always Compatible (across all pipeline types)
- `quality_pass_rate`
- `deduplication_rate`
- `records_written`
- `bytes_downloaded`

### Pipeline-Specific (only within same type)
- **Web Scraping**: `http_request_success_rate`, `content_extraction_success_rate`
- **File Processing**: `file_extraction_success_rate`, `record_parsing_success_rate`
- **Stream Processing**: `stream_connection_success_rate`, `record_retrieval_success_rate`

## Troubleshooting

### Error: "Cannot aggregate metric across different pipeline types"

**Problem:** Trying to aggregate pipeline-specific metrics across different types

**Solution:** Only aggregate compatible metrics, or filter to same pipeline type
```python
# Filter to same pipeline type
web_sources = [s for s in sources if s['snapshot']['pipeline_type'] == 'web_scraping']
result = aggregate_compatible_metrics(web_sources, "http_request_success_rate")
```

### Error: "No module named 'somali_dialect_classifier'"

**Problem:** Package not installed

**Solution:** Install in development mode
```bash
cd somali-dialect-classifier
pip install -e .
```

### Result is 0.0 when it shouldn't be

**Problem:** Source has zero records_written

**Solution:** Check that sources have non-zero volumes
```python
for source in sources:
    volume = source.get("records_written", 0)
    print(f"{source['name']}: {volume} records")
```

## Next Steps

1. Read the full documentation: `PHASE2_AGGREGATION_README.md`
2. Review the implementation: `src/somali_dialect_classifier/utils/aggregation.py`
3. Explore the examples: `examples/aggregation_demo.py`
4. Check the tests: `tests/test_aggregation.py`

## Support

For questions or issues:
1. Check the comprehensive README: `PHASE2_AGGREGATION_README.md`
2. Review test examples: `tests/test_aggregation.py`
3. Run the interactive demo: `examples/aggregation_demo.py`
