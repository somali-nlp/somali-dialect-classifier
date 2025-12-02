# CLI Reference: somali-tools

**Complete reference for the somali-tools unified command-line interface.**

**Last Updated:** 2025-11-29

Complete reference for the `somali-tools` unified command-line interface.

## Installation

The `somali-tools` CLI is installed automatically when you install the package:

```bash
pip install -e .
```

Verify installation:

```bash
somali-tools --version
somali-tools --help
```

## Command Structure

```bash
somali-tools <group> <command> [OPTIONS]
```

## Command Groups

- `metrics` - Metrics management and analysis
- `ledger` - Ledger database management
- `data` - Dataset validation and quality checks
- `dashboard` - Dashboard build and deployment

## Global Options

```bash
somali-tools --version    # Show version and exit
somali-tools --help       # Show help message and exit
```

---

---

## Table of Contents

- [Installation](#installation)
- [Command Structure](#command-structure)
- [Command Groups](#command-groups)
- [Global Options](#global-options)
- [metrics - Metrics Management](#metrics-metrics-management)
  - [metrics consolidate](#metrics-consolidate)
  - [metrics enhance](#metrics-enhance)
  - [metrics validate](#metrics-validate)
  - [metrics check-anomalies](#metrics-check-anomalies)
  - [metrics export](#metrics-export)
- [ledger - Ledger Database Management](#ledger-ledger-database-management)
  - [ledger migrate](#ledger-migrate)
  - [ledger clear-locks](#ledger-clear-locks)
  - [ledger status](#ledger-status)
  - [ledger query](#ledger-query)
- [data - Dataset Validation](#data-dataset-validation)
  - [data validate-silver](#data-validate-silver)
  - [data export-sample](#data-export-sample)
  - [data check-quality](#data-check-quality)
- [dashboard - Dashboard Management](#dashboard-dashboard-management)
  - [dashboard build](#dashboard-build)
  - [dashboard serve](#dashboard-serve)
  - [dashboard deploy](#dashboard-deploy)
- [Backward Compatibility](#backward-compatibility)
  - [Script Stubs](#script-stubs)
  - [Migration Guide](#migration-guide)
- [Exit Codes](#exit-codes)
- [Configuration](#configuration)
- [Getting Help](#getting-help)
- [Common Workflows](#common-workflows)
  - [Complete Pipeline Workflow](#complete-pipeline-workflow)
  - [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
  - [Command Not Found](#command-not-found)
  - [Permission Errors](#permission-errors)
  - [Validation Failures](#validation-failures)
- [Additional Resources](#additional-resources)

---

## metrics - Metrics Management

Metrics consolidation, validation, and analysis commands.

### metrics consolidate

Generate consolidated metrics from processing files.

**Usage:**
```bash
somali-tools metrics consolidate [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--metrics-dir` | `-d` | Path | `data/metrics` | Directory containing metrics JSON files |
| `--output` | `-o` | Path | `_site/data/all_metrics.json` | Output path for consolidated metrics |
| `--source` | `-s` | String | (none) | Filter by specific source(s) (repeatable) |

**Examples:**
```bash
# Consolidate all metrics
somali-tools metrics consolidate

# Consolidate only Wikipedia metrics
somali-tools metrics consolidate --source wikipedia-somali

# Multiple sources
somali-tools metrics consolidate -s wikipedia-somali -s bbc-somali

# Custom output path
somali-tools metrics consolidate --output /tmp/metrics.json
```

**Replaces:** `python scripts/ops/generate_consolidated_metrics.py`

---

### metrics enhance

Generate enhanced metrics with additional calculations.

**Usage:**
```bash
somali-tools metrics enhance [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--metrics-dir` | `-d` | Path | `data/metrics` | Directory containing metrics JSON files |
| `--output` | `-o` | Path | `_site/data/enhanced_metrics.json` | Output path for enhanced metrics |

**Examples:**
```bash
# Generate enhanced metrics
somali-tools metrics enhance

# Custom paths
somali-tools metrics enhance -d custom/metrics -o custom/output.json
```

**Replaces:** `python scripts/ops/generate_enhanced_metrics.py`

---

### metrics validate

Validate metrics against Phase 3 schema.

**Usage:**
```bash
somali-tools metrics validate [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--metrics-dir` | `-d` | Path | `data/metrics` | Directory containing metrics JSON files |
| `--strict` | (flag) | Boolean | False | Fail on warnings (default: only fail on errors) |

**Exit Codes:**
- `0` - All validations passed
- `1` - Validation errors found
- `2` - No metrics files found (warning)

**Examples:**
```bash
# Validate all metrics
somali-tools metrics validate

# Strict mode (fail on warnings)
somali-tools metrics validate --strict
```

**Replaces:** `python scripts/validate_metrics_schema.py`

---

### metrics check-anomalies

Check for metric anomalies and outliers.

**Usage:**
```bash
somali-tools metrics check-anomalies [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--metrics-dir` | `-d` | Path | `data/metrics` | Directory containing metrics JSON files |
| `--output` | `-o` | Path | (none) | Output path for anomaly report (JSON) |
| `--threshold` | `-t` | Integer | 3 | Warning threshold (number of anomalies before exit code 1) |

**Exit Codes:**
- `0` - No anomalies found
- `1` - Warnings found (>= threshold warning-level anomalies)
- `2` - Errors found (any error-level anomalies)

**Anomaly Checks:**
- `records_passed_filters > records_received` (ERROR)
- `quality_pass_rate > 1.0` (ERROR)
- `records_written < 0` (ERROR)
- Unusual metric distributions (WARNING)

**Examples:**
```bash
# Check for anomalies
somali-tools metrics check-anomalies

# Save report to file
somali-tools metrics check-anomalies --output anomalies.json

# Custom warning threshold
somali-tools metrics check-anomalies --threshold 5
```

**Replaces:** `python scripts/check_metrics_anomalies.py`

---

### metrics export

Export metrics to various formats.

**Usage:**
```bash
somali-tools metrics export [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--metrics-dir` | `-d` | Path | `data/metrics` | Directory containing metrics JSON files |
| `--format` | `-f` | Choice | `json` | Export format (json, csv, parquet) |
| `--output` | `-o` | Path | (required) | Output file path |

**Examples:**
```bash
# Export to CSV
somali-tools metrics export --format csv --output metrics.csv

# Export to Parquet
somali-tools metrics export -f parquet -o metrics.parquet
```

**New functionality** (not replacing existing script)

---

## ledger - Ledger Database Management

Ledger database operations and state tracking.

### ledger migrate

Run SQLite ledger state migrations (data migrations, not PostgreSQL schema).

**Usage:**
```bash
somali-tools ledger migrate [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--ledger-path` | `-l` | Path | `data/ledger/crawl_ledger.db` | Path to SQLite ledger database |
| `--migration` | `-m` | String | (none) | Specific migration to run (default: all pending) |
| `--dry-run` | (flag) | Boolean | False | Show what would be migrated without executing |

**Examples:**
```bash
# Run all pending migrations
somali-tools ledger migrate

# Dry run to see what would be applied
somali-tools ledger migrate --dry-run

# Run specific migration
somali-tools ledger migrate --migration 002_pipeline_runs_table
```

**Note:** This migrates SQLite ledger data (e.g., state transitions). For **PostgreSQL database schema migrations**, use Alembic:
```bash
cd migrations/database
alembic upgrade head
```

See [`migrations/database/README.md`](../../migrations/database/README.md) for PostgreSQL schema migration documentation.

**Replaces:** `python scripts/migrate_ledger_states.py`

---

### ledger clear-locks

Clear stale locks in ledger.

**Usage:**
```bash
somali-tools ledger clear-locks [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--lock-dir` | `-d` | Path | `.locks` | Lock directory path |
| `--max-age-hours` | `-a` | Integer | 24 | Maximum lock age in hours |
| `--force` | `-f` | Boolean | False | Clear all locks regardless of age |

**Warning:** Clearing locks can interrupt running pipelines. Use with caution.

**Examples:**
```bash
# Clear locks older than 24 hours
somali-tools ledger clear-locks

# Clear locks older than 2 hours
somali-tools ledger clear-locks --max-age-hours 2

# Force clear all locks (dangerous!)
somali-tools ledger clear-locks --force
```

**Replaces:** `somali-lock-status --cleanup` (partial)

---

### ledger status

Show ledger database status.

**Usage:**
```bash
somali-tools ledger status [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--ledger-path` | `-l` | Path | `data/ledger/crawl_ledger.db` | Path to SQLite ledger database |
| `--verbose` | `-v` | Boolean | False | Show detailed table information |

**Examples:**
```bash
# Basic status
somali-tools ledger status

# Detailed status with table information
somali-tools ledger status --verbose

# Custom ledger path
somali-tools ledger status --ledger-path /custom/path/ledger.db
```

**Output Example:**
```
Ledger Database Status
======================
Database: data/ledger/crawl_ledger.db
Size: 24.5 MB
Schema Version: 002

Table Counts:
  url_queue:         45,234 records
  pipeline_runs:        127 records
  daily_quotas:          89 records

Recent Activity:
  Last pipeline run: 2025-11-15 13:10:55 (wikipedia)
  Last quota update: 2025-11-15 00:00:00
```

**New functionality** (partial from export_quota_dashboard_data.py)

---

### ledger query

Execute ad-hoc ledger queries.

**Usage:**
```bash
somali-tools ledger query [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--ledger-path` | `-l` | Path | `data/ledger/crawl_ledger.db` | Path to SQLite ledger database |
| `--sql` | `-q` | String | (required) | SQL query to execute |
| `--format` | `-f` | Choice | `table` | Output format (table, json, csv) |

**Security Note:** SQL injection risk - validate queries or use read-only connection.

**Examples:**
```bash
# Count total URLs in ledger
somali-tools ledger query --sql "SELECT COUNT(*) FROM url_queue"

# Show recent pipeline runs
somali-tools ledger query --sql "SELECT * FROM pipeline_runs LIMIT 5"

# Export as JSON
somali-tools ledger query --sql "SELECT * FROM sources" --format json
```

**New functionality**

---

## data - Dataset Validation

Dataset validation and quality check commands.

### data validate-silver

Validate silver dataset integrity.

**Usage:**
```bash
somali-tools data validate-silver [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--silver-path` | `-p` | Path | `data/processed/silver` | Path to silver dataset directory |
| `--source` | `-s` | String | (none) | Validate specific source(s) only (repeatable) |
| `--strict` | (flag) | Boolean | False | Fail on warnings (default: only fail on errors) |

**Validation Checks:**
- Schema compliance (required fields present)
- Data type correctness
- Foreign key constraints
- Duplicate detection
- Quality metric thresholds

**Examples:**
```bash
# Validate all silver datasets
somali-tools data validate-silver

# Validate specific source
somali-tools data validate-silver --source wikipedia-somali

# Strict mode (fail on warnings)
somali-tools data validate-silver --strict
```

**Replaces:** `python scripts/validate_deduplication.py` (partial)

---

### data export-sample

Export sample records for inspection.

**Usage:**
```bash
somali-tools data export-sample [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--silver-path` | `-p` | Path | `data/processed/silver` | Path to silver dataset directory |
| `--count` | `-n` | Integer | 10 | Number of sample records to export |
| `--output` | `-o` | Path | (required) | Output file path (JSON or CSV) |
| `--source` | `-s` | String | (none) | Sample from specific source only |

**Examples:**
```bash
# Export 10 random records
somali-tools data export-sample --output sample.json

# Export 100 records from Wikipedia
somali-tools data export-sample -n 100 -s wikipedia-somali -o wiki_sample.csv
```

**New functionality**

---

### data check-quality

Run quality checks on datasets.

**Usage:**
```bash
somali-tools data check-quality [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--silver-path` | `-p` | Path | `data/processed/silver` | Path to silver dataset directory |
| `--output` | `-o` | Path | (none) | Output path for quality report (JSON) |

**Quality Metrics:**
- Text length distribution
- Character set analysis
- Language detection confidence
- Deduplication rate
- Filter effectiveness

**Examples:**
```bash
# Run quality checks
somali-tools data check-quality

# Save report to file
somali-tools data check-quality --output quality_report.json
```

**New functionality**

---

## dashboard - Dashboard Management

Dashboard build and deployment commands.

### dashboard build

Build dashboard site.

**Usage:**
```bash
somali-tools dashboard build [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--clean` | (flag) | Boolean | False | Clean _site directory before building |
| `--verbose` | `-v` | Boolean | False | Show detailed build output |

**Build Steps:**
1. Export metrics consolidation
2. Export quota/manifest data
3. Copy static assets
4. Generate index.html

**Examples:**
```bash
# Standard build
somali-tools dashboard build

# Clean build
somali-tools dashboard build --clean

# Verbose output
somali-tools dashboard build --verbose
```

**Replaces:** `src/dashboard/build-site.sh`

---

### dashboard serve

Start local development server.

**Usage:**
```bash
somali-tools dashboard serve [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--port` | `-p` | Integer | 8000 | Port for development server |
| `--host` | `-h` | String | `127.0.0.1` | Host for development server |

**Examples:**
```bash
# Start server on default port (8000)
somali-tools dashboard serve

# Custom port
somali-tools dashboard serve --port 3000

# Allow external access
somali-tools dashboard serve --host 0.0.0.0
```

**New functionality**

---

### dashboard deploy

Deploy dashboard.

**Usage:**
```bash
somali-tools dashboard deploy [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--target` | `-t` | Choice | `github-pages` | Deployment target (github-pages, netlify, s3) |
| `--dry-run` | (flag) | Boolean | False | Show what would be deployed without executing |

**Examples:**
```bash
# Deploy to GitHub Pages
somali-tools dashboard deploy

# Dry run to see what would happen
somali-tools dashboard deploy --dry-run

# Deploy to Netlify
somali-tools dashboard deploy --target netlify
```

**Replaces:** `somali-deploy-dashboard` (partial)

---

## Backward Compatibility

### Script Stubs

Old scripts remain as compatibility stubs during transition:

```bash
# OLD (deprecated, but still works with warning)
python scripts/ops/generate_consolidated_metrics.py

# NEW (preferred)
somali-tools metrics consolidate
```

**Deprecation Timeline:**
- **Stage 1 (current):** Scripts work with deprecation warnings
- **Stage 2 (future):** Scripts removed, CLI is primary interface

### Migration Guide

See `docs/guides/module-restructuring.md` for complete migration guide.

---

## Exit Codes

Standard exit codes across all commands:

- `0` - Success
- `1` - User error (invalid arguments, validation failure)
- `2` - System error (file not found, permission denied)

---

## Configuration

CLI commands respect configuration from:

1. Environment variables (highest priority)
2. `.env` file
3. Default values (lowest priority)

Example:
```bash
# Set custom metrics directory
export SDC_DATA__METRICS_DIR=/custom/metrics
somali-tools metrics consolidate  # Uses /custom/metrics
```

See `docs/howto/configuration.md` for complete configuration reference.

---

## Getting Help

```bash
# Main help
somali-tools --help

# Group help
somali-tools metrics --help
somali-tools ledger --help
somali-tools data --help
somali-tools dashboard --help

# Command help
somali-tools metrics consolidate --help
somali-tools ledger status --help
```

---

## Common Workflows

### Complete Pipeline Workflow

```bash
# 1. Run data ingestion
wikisom-download
bbcsom-download --max-articles 500

# 2. Validate metrics
somali-tools metrics validate

# 3. Check for anomalies
somali-tools metrics check-anomalies

# 4. Consolidate metrics
somali-tools metrics consolidate

# 5. Validate silver datasets
somali-tools data validate-silver

# 6. Build dashboard
somali-tools dashboard build

# 7. Preview dashboard
somali-tools dashboard serve
```

### Development Workflow

```bash
# Check ledger status
somali-tools ledger status --verbose

# Export sample data for inspection
somali-tools data export-sample -n 100 -o samples.json

# Run quality checks
somali-tools data check-quality --output report.json

# Query ledger for debugging
somali-tools ledger query --sql "SELECT * FROM pipeline_runs WHERE status='failed'"
```

---

## Troubleshooting

### Command Not Found

**Problem:** `somali-tools: command not found`

**Solution:**
```bash
# Reinstall package
pip install -e .

# Verify installation
which somali-tools
somali-tools --version
```

### Permission Errors

**Problem:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
```bash
# Check file permissions
ls -la data/

# Fix permissions
chmod -R u+w data/
```

### Validation Failures

**Problem:** `Validation errors found: Schema mismatch`

**Solution:**
```bash
# Check metrics schema
somali-tools metrics validate --strict

# Review error details in output
# Fix data or schema as needed
```

---

## Additional Resources

- **Architecture:** `docs/overview/architecture.md` - System design
- **Module Restructuring:** `docs/guides/module-restructuring.md` - Migration guide
- **Configuration:** `docs/howto/configuration.md` - Configuration reference
- **API Reference:** `docs/reference/api.md` - Python API documentation

---

**CLI Version:** 0.2.0

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index

**Maintainers**: Somali NLP Contributors
