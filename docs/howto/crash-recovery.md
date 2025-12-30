# Crash Recovery Guide

**Comprehensive guide to checkpoint-based crash recovery and automatic resume behavior.**

**Last Updated:** 2025-12-29

---

## Table of Contents

- [Overview](#overview)
- [How Crash Recovery Works](#how-crash-recovery-works)
- [Automatic Resume Behavior](#automatic-resume-behavior)
- [Checkpoint File Format](#checkpoint-file-format)
- [Force Restart Options](#force-restart-options)
- [Troubleshooting Corrupted Checkpoints](#troubleshooting-corrupted-checkpoints)
- [Best Practices](#best-practices)
- [Related Documentation](#related-documentation)

---

## Overview

The Somali Dialect Classifier implements **checkpoint-based crash recovery** to automatically resume processing from the last saved state after crashes, interruptions, or system failures.

### Key Features

- **Automatic checkpointing**: Saves progress every 1000 records
- **Transparent resume**: Automatically detects and loads checkpoints
- **Crash-safe storage**: Atomic writes prevent checkpoint corruption
- **Minimal overhead**: Checkpoint writes take <10ms
- **Cross-run persistence**: Checkpoints survive process restarts

### Supported Pipelines

All data ingestion pipelines support crash recovery:

- **Wikipedia**: Saves after each XML batch
- **BBC**: Saves after each article fetch
- **HuggingFace**: Saves every 1000 streamed records
- **Språkbanken**: Saves after each corpus file
- **TikTok**: Saves after each video comment batch

---

## How Crash Recovery Works

### Processing Flow with Checkpoints

```
┌────────────────────────────────────────────────────────────┐
│ 1. STARTUP: Check for existing checkpoint                 │
│    - Look for .checkpoint.json in staging directory        │
│    - Load last_index, processed_count, timestamp           │
└──────────────────┬─────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────┐
│ 2. RESUME: Skip already-processed records                 │
│    - Start from checkpoint.last_index                      │
│    - Log: "Resuming from checkpoint: offset=1000"         │
└──────────────────┬─────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────┐
│ 3. PROCESS: Save checkpoint every 1000 records            │
│    - Atomic write: .checkpoint.tmp → .checkpoint.json     │
│    - Update: last_index, processed_count, timestamp       │
└──────────────────┬─────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────┐
│ 4. COMPLETION: Delete checkpoint on success               │
│    - Pipeline finished: rm .checkpoint.json                │
│    - Next run starts fresh from offset 0                   │
└────────────────────────────────────────────────────────────┘
```

### Example: HuggingFace Streaming Recovery

```python
from somali_dialect_classifier.ingestion.processors import create_mc4_processor

# Run 1: Process 5000 records, crash at record 3200
processor = create_mc4_processor(max_records=5000)
processor.process()
# Output:
# INFO: Checkpoint saved: offset=1000, processed=1000
# INFO: Checkpoint saved: offset=2000, processed=2000
# INFO: Checkpoint saved: offset=3000, processed=3000
# ERROR: Process crashed (e.g., out of memory)

# Run 2: Automatic resume from last checkpoint
processor = create_mc4_processor(max_records=5000)
processor.process()
# Output:
# INFO: Found checkpoint: .checkpoint.json
# INFO: Resuming from checkpoint: offset=3000, processed=3000
# INFO: Checkpoint saved: offset=4000, processed=4000
# INFO: Checkpoint saved: offset=5000, processed=5000
# INFO: Processing complete, removing checkpoint
```

---

## Automatic Resume Behavior

### When Checkpoints Are Created

Checkpoints are created in the following scenarios:

1. **Regular intervals** (every 1000 records):
   ```
   Record 1000 → Save checkpoint
   Record 2000 → Save checkpoint
   Record 3000 → Save checkpoint
   ...
   ```

2. **Before risky operations**:
   - HTTP downloads (in case of network failure)
   - Large file parsing (in case of memory errors)

3. **User interruption** (Ctrl+C):
   ```python
   try:
       process_records()
   except KeyboardInterrupt:
       logger.info("Interrupted by user, saving checkpoint")
       save_checkpoint()
       raise
   ```

### When Checkpoints Are Deleted

Checkpoints are automatically deleted on successful completion:

```
Pipeline finished successfully
  → Remove .checkpoint.json
  → Next run starts fresh from beginning
```

Checkpoints are **NOT** deleted on failure, allowing automatic resume.

### Resume Detection Logic

```python
# Pseudocode for checkpoint detection
def start_processing():
    checkpoint_path = staging_dir / ".checkpoint.json"

    if checkpoint_path.exists():
        checkpoint = load_checkpoint(checkpoint_path)
        logger.info(f"Resuming from checkpoint: offset={checkpoint['last_index']}")
        start_offset = checkpoint['last_index']
    else:
        logger.info("No checkpoint found, starting from beginning")
        start_offset = 0

    return start_offset
```

---

## Checkpoint File Format

Checkpoints are stored as JSON files in the staging directory.

### File Location

```
data/staging/source=<SOURCE_NAME>/.checkpoint.json
```

Examples:
- `data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.json`
- `data/staging/source=Wikipedia-Somali/.checkpoint.json`
- `data/staging/source=BBC-Somali/.checkpoint.json`

### File Structure

```json
{
  "last_index": 3000,
  "processed_count": 3000,
  "timestamp": "2025-12-29T10:15:30.123456Z",
  "run_id": "20251229_101500_huggingface_abc123",
  "source": "HuggingFace-Somali_c4-so",
  "schema_version": "1.0"
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `last_index` | int | Offset to resume from (e.g., record 3000) |
| `processed_count` | int | Total records successfully processed |
| `timestamp` | str | ISO 8601 timestamp when checkpoint was saved |
| `run_id` | str | Pipeline run identifier for tracking |
| `source` | str | Data source identifier |
| `schema_version` | str | Checkpoint schema version (for future compatibility) |

### Atomic Writes

Checkpoints use atomic writes to prevent corruption:

```python
# Write to temporary file first
checkpoint_tmp = Path(f"{checkpoint_path}.tmp")
with open(checkpoint_tmp, 'w') as f:
    json.dump(checkpoint_data, f, indent=2)

# Atomic rename (POSIX guarantees atomicity)
checkpoint_tmp.rename(checkpoint_path)
```

This ensures checkpoints are never partially written, even during crashes.

---

## Force Restart Options

### Skip Checkpoint and Start Fresh

Use `--force` flag to ignore checkpoints:

```bash
# Start from beginning, ignoring any existing checkpoint
hfsom-download mc4 --max-records 10000 --force
```

This will:
1. Delete existing checkpoint file
2. Start processing from offset 0
3. Create new checkpoints as usual

### Delete Checkpoint Manually

```bash
# Remove checkpoint for specific source
rm data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.json

# Remove all checkpoints
find data/staging -name ".checkpoint.json" -delete
```

### Resume from Specific Offset

Not currently supported via CLI, but can be done programmatically:

```python
# Create custom checkpoint
checkpoint_data = {
    "last_index": 5000,  # Resume from record 5000
    "processed_count": 5000,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "run_id": generate_run_id("huggingface"),
    "source": "HuggingFace-Somali_c4-so",
    "schema_version": "1.0"
}

checkpoint_path = Path("data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.json")
with open(checkpoint_path, 'w') as f:
    json.dump(checkpoint_data, f, indent=2)

# Run pipeline - will resume from offset 5000
processor.process()
```

---

## Troubleshooting Corrupted Checkpoints

### Symptom: Invalid JSON

**Error Message**:
```
ERROR: Failed to load checkpoint: JSONDecodeError
```

**Cause**: Checkpoint file corrupted (partial write before atomic rename)

**Solution**: Delete corrupted checkpoint and restart

```bash
rm data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.json
hfsom-download mc4 --max-records 10000
```

### Symptom: Offset Too Large

**Error Message**:
```
ERROR: Checkpoint offset 50000 exceeds dataset size 10000
```

**Cause**: Checkpoint from different dataset version or configuration

**Solution**: Delete stale checkpoint

```bash
rm data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.json
hfsom-download mc4 --max-records 10000
```

### Symptom: Checkpoint Not Loading

**Error Message**:
```
INFO: No checkpoint found, starting from beginning
```

**Cause**: Checkpoint file not in expected location

**Solution**: Verify checkpoint path

```bash
# Expected location
ls data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.json

# If missing, check for similar files
find data/staging -name ".checkpoint.json"
```

### Symptom: Resume Loops Infinitely

**Error Message**:
```
INFO: Resuming from checkpoint: offset=1000
INFO: Resuming from checkpoint: offset=1000
INFO: Resuming from checkpoint: offset=1000
...
```

**Cause**: Pipeline not updating checkpoint or failing immediately after resume

**Solution**: Enable debug logging to identify failure point

```bash
export SDC_LOGGING__LEVEL=DEBUG
hfsom-download mc4 --max-records 10000
```

---

## Best Practices

### 1. Regular Checkpoint Monitoring

Check checkpoint status periodically:

```bash
# List all active checkpoints
find data/staging -name ".checkpoint.json" -exec cat {} \;

# Show checkpoint ages
find data/staging -name ".checkpoint.json" -ls
```

### 2. Checkpoint Cleanup

Remove old checkpoints from completed runs:

```bash
# Clean checkpoints older than 7 days
find data/staging -name ".checkpoint.json" -mtime +7 -delete
```

### 3. Backup Before Force Restart

```bash
# Backup checkpoint before deleting
cp data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.json \
   data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.backup.json

# Force restart
hfsom-download mc4 --max-records 10000 --force

# Restore if needed
mv data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.backup.json \
   data/staging/source=HuggingFace-Somali_c4-so/.checkpoint.json
```

### 4. Monitor Checkpoint Frequency

Too frequent checkpoints can slow processing:

```bash
# Check checkpoint file modification times
watch -n 1 'ls -lh data/staging/source=*/checkpoint.json'
```

Expected: 1 checkpoint per 1000 records (~30-60 seconds for HuggingFace)

### 5. Disk Space for Checkpoints

Checkpoints are small (<1 KB each), but ensure sufficient disk space:

```bash
# Check disk space
df -h data/staging

# Estimate checkpoint count
find data/staging -name ".checkpoint.json" | wc -l
```

---

## Related Documentation

- **[Data Pipeline Guide](../guides/data-pipeline.md)** - Complete pipeline overview
- **[HuggingFace Integration](huggingface-integration.md)** - Streaming datasets with checkpoints
- **[Troubleshooting Guide](troubleshooting.md)** - General troubleshooting
- **[Configuration Guide](configuration.md)** - Pipeline configuration options

---

**Maintainers**: Somali NLP Contributors
