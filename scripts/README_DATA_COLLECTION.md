# Pipeline Run Data Collection Guide

## Overview

This guide explains how to collect and record pipeline run metrics using the semi-automated data collection system.

## Quick Start

### Interactive Mode (Recommended for Manual Collection)

```bash
python scripts/record_pipeline_run.py -o dashboard/data/pipeline_run_history.json
```

This will prompt you for all required metrics interactively.

### With JSON Input File

```bash
# Create run data in JSON format
cat > run_data.json <<EOF
{
  "run_id": "20251108_190000",
  "timestamp": "2025-11-08T19:00:00Z",
  "schema_version": "2.0",
  "sources_processed": 5,
  "total_duration_seconds": 3312,
  "total_records": 13198,
  "throughput_rpm": 11876,
  "quality_pass_rate": 0.661,
  "retries": 1,
  "errors": 0,
  "_synthetic": false
}
EOF

# Record the run
python scripts/record_pipeline_run.py -i run_data.json -o dashboard/data/pipeline_run_history.json
```

### Dry Run (Validation Only)

```bash
python scripts/record_pipeline_run.py -i run_data.json --dry-run
```

## Post-Pipeline Run Workflow

After each pipeline execution completes:

1. Run the data collection script (interactive or with JSON input)
2. Verify the entry was added: `git diff dashboard/data/pipeline_run_history.json`
3. Commit the changes: `git add dashboard/data/pipeline_run_history.json && git commit -m "data: add pipeline run [run_id]"`
4. Push to remote: `git push origin main`
5. Dashboard will automatically update within 5 minutes (cache refresh)

## Schema Versions

### Schema v1.0 (Basic Metrics)

Minimum required fields:
- `run_id` - Unique identifier (format: YYYYMMDD_HHMMSS)
- `timestamp` - ISO 8601 format (e.g., "2025-11-08T19:00:00Z")
- `sources_processed` - Number of data sources (1-10)
- `total_duration_seconds` - Total execution time (0-86400)
- `total_records` - Total records processed (0-1000000)
- `throughput_rpm` - Records per minute (0-100000)
- `quality_pass_rate` - Quality score (0-1)

Optional fields:
- `retries` - Number of retry attempts (default: 0)
- `errors` - Number of errors encountered (default: 0)

### Schema v2.0 (With Resource Metrics)

All v1.0 fields PLUS:

```json
{
  "schema_version": "2.0",
  "resource_metrics": {
    "cpu": {
      "peak_percent": 87.3,
      "avg_percent": 45.2
    },
    "memory": {
      "peak_mb": 2048,
      "avg_mb": 1536
    },
    "disk": {
      "read_mb": 145.3,
      "write_mb": 89.7
    }
  },
  "environment": {
    "python_version": "3.11.5",
    "hostname": "macbook-pro.local",
    "os": "darwin",
    "cpu_cores": 8,
    "total_memory_mb": 16384
  }
}
```

## Validation Rules

The script validates:

1. **Required Fields**: All mandatory fields must be present
2. **Schema Version**: Must be "1.0" or "2.0"
3. **Timestamp Format**: Must be valid ISO 8601
4. **Numeric Ranges**:
   - sources_processed: 1-10
   - total_duration_seconds: 0-86400
   - total_records: 0-1000000
   - throughput_rpm: 0-100000
   - quality_pass_rate: 0-1
5. **Duplicate Detection**: run_id must be unique
6. **Resource Metrics Sanity**:
   - CPU peak >= average
   - Memory peak >= average

## Resource Metrics Collection

When prompted "Collect resource metrics? (y/n)", enter `y` to enable:

- Real-time system monitoring using `psutil`
- 5-second sampling period
- Captures: CPU %, memory MB, disk I/O
- Automatically includes environment info

**Note**: Resource collection requires `psutil`:
```bash
pip install psutil
```

## Troubleshooting

### Error: Missing required fields

Check that all mandatory fields are present in your JSON input.

### Error: Duplicate run_id

The run_id already exists in history. Use a different identifier or check if this is a duplicate entry.

### Error: Timestamp must be ISO 8601 format

Use format: `YYYY-MM-DDTHH:MM:SSZ` (e.g., "2025-11-08T19:00:00Z")

### Error: Range error

One of your metrics is outside the acceptable range. Check the validation rules above.

## Data Quality Goals

- **Completeness**: 95%+ of runs have all expected fields
- **Accuracy**: No validation failures
- **Freshness**: <12 hours since last run
- **Consistency**: All timestamps in order, no duplicates

## Example: Complete v2.0 Run Object

```json
{
  "run_id": "20251108_190000",
  "timestamp": "2025-11-08T19:00:00Z",
  "schema_version": "2.0",
  "sources_processed": 5,
  "total_duration_seconds": 3312,
  "total_records": 13198,
  "throughput_rpm": 11876,
  "quality_pass_rate": 0.661,
  "retries": 1,
  "errors": 0,
  "resource_metrics": {
    "cpu": {
      "peak_percent": 87.3,
      "avg_percent": 45.2
    },
    "memory": {
      "peak_mb": 2048,
      "avg_mb": 1536
    },
    "disk": {
      "read_mb": 145.3,
      "write_mb": 89.7
    }
  },
  "environment": {
    "python_version": "3.11.5",
    "hostname": "macbook-pro.local",
    "os": "darwin",
    "os_version": "25.0.0",
    "cpu_cores": 8,
    "total_memory_mb": 16384
  },
  "_synthetic": false
}
```
