# Backup and Restore Procedures

**Procedures for backing up and restoring project data, databases, and configurations.**

**Last Updated:** 2025-11-21

## Table of Contents

- [Overview](#overview)
- [Backup System](#backup-system)
- [Restore System](#restore-system)
- [Automated Backups](#automated-backups)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The Somali NLP pipeline includes a robust backup and restore system for protecting critical data:

### What Gets Backed Up

1. **Ledger Database** (`data/ledger/crawl_ledger.db`)
   - URL deduplication records
   - Pipeline run history
   - Source statistics

2. **Silver Data** (`data/processed/*.parquet`)
   - Processed Parquet files
   - Cleaned and structured datasets

3. **Metrics** (`data/metrics/*.json`)
   - Pipeline performance metrics
   - Quality statistics
   - Filter analysis results

4. **Reports** (`data/reports/*.md`)
   - Processing reports
   - Quality assessments
   - Data summaries

### Backup Features

- Timestamped backup folders (YYYY-MM-DD_HH-MM-SS)
- SHA256 checksums for integrity verification
- Metadata manifest (JSON) with file information
- Automatic retention policy (default: 30 days)
- Automatic cleanup of old backups
- Progress reporting and logging

## Backup System

### Quick Start

```bash
# Create a backup
python scripts/backup_system.py

# List existing backups
python scripts/backup_system.py --list

# Cleanup old backups only
python scripts/backup_system.py --cleanup-only
```

### Command-Line Options

```bash
# Full syntax
python scripts/backup_system.py \
  --source-dir data \
  --backup-dir backups \
  --retention-days 30

# Custom source directory
python scripts/backup_system.py --source-dir /mnt/data

# Custom backup destination
python scripts/backup_system.py --backup-dir /backup/somali-nlp

# Custom retention period (keep 60 days)
python scripts/backup_system.py --retention-days 60
```

### Backup Process

When you run a backup, the system:

1. Creates timestamped folder: `backups/2025-11-11_14-30-00/`
2. Copies ledger database with checksum
3. Copies all silver Parquet files with checksums
4. Copies all metrics JSON files with checksums
5. Copies all report markdown files with checksums
6. Generates metadata manifest: `metadata.json`
7. Logs total size and file count
8. Removes backups older than retention period

### Backup Structure

```
backups/
├── 2025-11-11_14-30-00/
│   ├── crawl_ledger.db
│   ├── processed/
│   │   ├── bbc-somali_20251110.parquet
│   │   ├── wikipedia-somali_20251110.parquet
│   │   └── tiktok-somali_20251110.parquet
│   ├── metrics/
│   │   ├── bbc_metrics.json
│   │   └── wikipedia_metrics.json
│   ├── reports/
│   │   └── pipeline_report.md
│   └── metadata.json
├── 2025-11-10_02-00-00/
│   └── ...
└── safety/
    └── 2025-11-11_15-00-00/
        └── ... (safety backups created before restore)
```

### Metadata Manifest

Each backup includes a `metadata.json` file:

```json
{
  "timestamp": "2025-11-11_14-30-00",
  "created_at": "2025-11-11T14:30:00.123456",
  "source_dir": "data",
  "total_size_bytes": 123456789,
  "files": [
    {
      "name": "crawl_ledger.db",
      "path": "crawl_ledger.db",
      "source_path": "data/ledger/crawl_ledger.db",
      "size_bytes": 12345,
      "modified_time": "2025-11-11T10:00:00",
      "sha256": "abc123def456..."
    },
    {
      "name": "bbc-somali_20251110.parquet",
      "path": "processed/bbc-somali_20251110.parquet",
      "source_path": "data/processed/bbc-somali_20251110.parquet",
      "size_bytes": 67890,
      "modified_time": "2025-11-10T18:00:00",
      "sha256": "123abc456def..."
    }
  ]
}
```

### Listing Backups

```bash
# List all available backups
python scripts/backup_system.py --list
```

Output:
```
================================================================================
AVAILABLE BACKUPS (3 total)
================================================================================

Backup: 2025-11-11_14-30-00
  Path: backups/2025-11-11_14-30-00
  Age: 0 days
  Size: 1234.56 MB
  Files: 15

Backup: 2025-11-10_02-00-00
  Path: backups/2025-11-10_02-00-00
  Age: 1 days
  Size: 1200.00 MB
  Files: 12

Backup: 2025-11-09_02-00-00
  Path: backups/2025-11-09_02-00-00
  Age: 2 days
  Size: 1100.00 MB
  Files: 10

================================================================================
```

## Restore System

### Quick Start

```bash
# List available backups
python scripts/restore_system.py --list

# Restore from specific backup
python scripts/restore_system.py --backup 2025-11-11_14-30-00

# Dry run (test without making changes)
python scripts/restore_system.py --backup 2025-11-11_14-30-00 --dry-run
```

### Command-Line Options

```bash
# Full syntax
python scripts/restore_system.py \
  --backup 2025-11-11_14-30-00 \
  --backup-dir backups \
  --target-dir data

# Dry run (simulation)
python scripts/restore_system.py \
  --backup 2025-11-11_14-30-00 \
  --dry-run

# Skip safety backup (not recommended)
python scripts/restore_system.py \
  --backup 2025-11-11_14-30-00 \
  --skip-safety-backup
```

### Restore Process

When you run a restore, the system:

1. Validates backup exists and has manifest
2. Verifies all files exist with correct checksums
3. Creates safety backup of current state (unless skipped)
4. Restores files to correct locations:
   - `crawl_ledger.db` → `data/ledger/crawl_ledger.db`
   - Parquet files → `data/processed/`
   - Metrics → `data/metrics/`
   - Reports → `data/reports/`
5. Validates restored data (database integrity, file counts)
6. Logs restoration summary

### Safety Backups

Before restoring, the system automatically creates a safety backup of your current state:

```bash
# Safety backups stored in backups/safety/
backups/
├── safety/
│   └── 2025-11-11_15-00-00/
│       └── ... (backup of state before restore)
```

This allows you to rollback if the restore causes issues.

### Dry Run Mode

Test a restore without making changes:

```bash
python scripts/restore_system.py --backup 2025-11-11_14-30-00 --dry-run
```

Output:
```
================================================================================
STARTING RESTORE PROCESS
================================================================================
DRY RUN MODE - No changes will be made
Backup: 2025-11-11_14-30-00
Created: 2025-11-11T14:30:00.123456
Files: 15
Size: 1234.56 MB

Verifying backup integrity...
✓ Backup integrity verified

[DRY RUN] Would restore: crawl_ledger.db -> data/ledger/crawl_ledger.db
[DRY RUN] Would restore: bbc-somali_20251110.parquet -> data/processed/bbc-somali_20251110.parquet
...

Restored 15 files
================================================================================
RESTORE COMPLETED SUCCESSFULLY
================================================================================
```

### Validation

After restore, the system validates:

1. **Ledger Database**: Checks SQLite integrity, table count
2. **Parquet Files**: Counts files in `data/processed/`
3. **Metrics**: Counts JSON files in `data/metrics/`
4. **Reports**: Verifies markdown files exist

If validation fails, check logs and safety backup.

## Automated Backups

### GitHub Actions (Scheduled)

Automatic daily backups via GitHub Actions:

```yaml
# .github/workflows/scheduled-backup.yml
# Runs daily at 2 AM UTC
# Stores backups as GitHub Actions artifacts (30-day retention)
```

**Trigger manually:**
```bash
# Go to: Repository > Actions > Scheduled Backup > Run workflow
```

**Download backup artifact:**
```bash
# Go to: Actions > Workflow run > Artifacts
# Download: backup-<run-number>-<attempt>.zip
```

### Local Scheduled Backups (Cron)

For local/server deployments, use cron:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/somali-dialect-classifier && python scripts/backup_system.py >> logs/backup.log 2>&1

# Add weekly cleanup
0 3 * * 0 cd /path/to/somali-dialect-classifier && python scripts/backup_system.py --cleanup-only >> logs/backup-cleanup.log 2>&1
```

### Docker Backup Service

Run backup as Docker service:

```bash
# Using docker-compose backup profile
docker-compose --profile backup run --rm somali-nlp-backup

# Schedule with cron
0 2 * * * docker-compose -f /path/to/docker-compose.yml --profile backup run --rm somali-nlp-backup
```

### Systemd Timer (Linux)

Create systemd service and timer:

**Service** (`/etc/systemd/system/somali-nlp-backup.service`):
```ini
[Unit]
Description=Somali NLP Backup Service

[Service]
Type=oneshot
WorkingDirectory=/opt/somali-nlp
ExecStart=/usr/bin/python3 scripts/backup_system.py
StandardOutput=journal
StandardError=journal
```

**Timer** (`/etc/systemd/system/somali-nlp-backup.timer`):
```ini
[Unit]
Description=Daily Somali NLP Backup Timer

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable somali-nlp-backup.timer
sudo systemctl start somali-nlp-backup.timer

# Check status
sudo systemctl list-timers | grep somali-nlp
```

## Best Practices

### Backup Frequency

Recommended backup schedule:

- **Development**: Manual backups before major changes
- **Staging**: Daily automated backups
- **Production**: Daily automated backups + manual before deploys

### Retention Policies

Recommended retention:

- **Local backups**: 30 days (default)
- **Remote backups**: 90 days
- **Critical milestones**: Keep indefinitely

### Storage Locations

**3-2-1 Backup Rule:**
- **3** copies of data
- **2** different storage types
- **1** off-site backup

Implementation:
```bash
# Local backup (primary)
python scripts/backup_system.py --backup-dir backups

# Remote backup (off-site)
python scripts/backup_system.py --backup-dir /mnt/remote-backup

# Cloud backup (optional)
rsync -av backups/ user@remote:/backup/somali-nlp/
# Or: aws s3 sync backups/ s3://somali-nlp-backups/
```

### Pre-Deployment Backups

**Always backup before:**
- Major code deployments
- Database migrations
- Configuration changes
- System updates

```bash
# Pre-deployment backup
python scripts/backup_system.py

# Make changes...

# If issues, restore
python scripts/restore_system.py --backup <latest-backup>
```

### Verification

Regularly verify backups:

```bash
# Verify latest backup integrity
python scripts/restore_system.py --backup <latest-backup> --dry-run

# Monthly: test full restore in isolated environment
# Quarterly: test disaster recovery procedure
```

## Troubleshooting

### Backup Issues

#### 1. Backup Fails with Permission Error

```bash
# Error: Permission denied writing to backups/

# Solution: Check permissions
ls -la backups/
sudo chown -R $USER:$USER backups/

# Or run with appropriate user
sudo -u somali-nlp python scripts/backup_system.py
```

#### 2. Backup Takes Too Long

```bash
# Symptoms: Backup hangs or takes hours

# Check disk I/O
iostat -x 1

# Check backup size
du -sh data/

# Solution: Exclude temporary files or use compression
# (Note: Current implementation doesn't compress; feature for future)
```

#### 3. Disk Space Full

```bash
# Error: No space left on device

# Check disk usage
df -h
du -sh backups/

# Solution: Clean old backups
python scripts/backup_system.py --cleanup-only --retention-days 7

# Or manually remove old backups
rm -rf backups/2025-10-*
```

### Restore Issues

#### 1. Checksum Verification Fails

```bash
# Error: Backup verification failed - checksums don't match

# This means backup is corrupted

# Solution: Use different backup
python scripts/restore_system.py --list
python scripts/restore_system.py --backup <older-backup>
```

#### 2. Database Corruption After Restore

```bash
# Symptoms: SQLite errors, ledger queries fail

# Check database integrity
sqlite3 data/ledger/crawl_ledger.db "PRAGMA integrity_check;"

# Solution: Restore from safety backup
python scripts/restore_system.py --backup backups/safety/<timestamp>
```

#### 3. Partial Restore

```bash
# Symptoms: Some files missing after restore

# Check logs
tail -n 100 logs/restore_system.log

# Solution: Re-run restore
python scripts/restore_system.py --backup <backup-name>
```

### Debugging

Enable detailed logging:

```bash
# Check backup logs
tail -f logs/backup_system.log

# Check restore logs
tail -f logs/restore_system.log

# Run with Python debug mode
python -u scripts/backup_system.py 2>&1 | tee backup-debug.log
```

## Advanced Usage

### Programmatic Backup

Use backup system in Python code:

```python
from pathlib import Path
from scripts.backup_system import BackupSystem

# Create backup
backup_system = BackupSystem(
    source_dir=Path("data"),
    backup_dir=Path("backups"),
    retention_days=30
)

backup_path = backup_system.create_backup()
print(f"Backup created: {backup_path}")

# List backups
backups = backup_system.list_backups()
for backup in backups:
    print(f"{backup['name']}: {backup['size_mb']:.2f} MB, {backup['age_days']} days old")

# Cleanup old backups
backup_system.cleanup_old_backups()
```

### Programmatic Restore

Use restore system in Python code:

```python
from pathlib import Path
from scripts.restore_system import RestoreSystem

# Create restore system
restore_system = RestoreSystem(
    backup_dir=Path("backups"),
    target_dir=Path("data")
)

# List available backups
backups = restore_system.list_backups()
latest = backups[0]

# Restore from latest
success = restore_system.restore(
    backup_name=latest['name'],
    dry_run=False,
    skip_safety_backup=False
)

if success:
    print("Restore completed successfully")
else:
    print("Restore failed")
```

### Selective Restore

To restore only specific files, manually extract from backup:

```bash
# Extract only ledger database
BACKUP=backups/2025-11-11_14-30-00
cp $BACKUP/crawl_ledger.db data/ledger/

# Extract only specific parquet file
cp $BACKUP/processed/bbc-somali_20251110.parquet data/processed/

# Verify checksum manually
sha256sum data/ledger/crawl_ledger.db
# Compare with metadata.json
```

## Next Steps

- [Docker Deployment Guide](./docker-deployment.md)
- [General Deployment Guide](./deployment.md)
- [CI/CD Dashboard Guide](./cicd-dashboard.md)

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index

**Maintainers**: Somali NLP Contributors
