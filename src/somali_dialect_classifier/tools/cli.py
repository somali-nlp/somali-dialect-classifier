#!/usr/bin/env python3
"""
Somali Tools CLI - Unified command-line interface for operational tasks.

This module provides the main entry point and command group structure for the
somali-tools CLI. Individual command implementations will be added in Wave 3
of the Stage 1.2 restructuring.

Architecture:
    - Click-based CLI framework (consistent with existing lock_status.py)
    - Four main command groups: metrics, ledger, data, dashboard
    - Comprehensive help text for all commands
    - POSIX-style options (short/long forms)
    - Extensible structure for future commands

Entry Point:
    Configured in pyproject.toml as:
    [project.scripts]
    somali-tools = "somali_dialect_classifier.tools.cli:cli"

Usage:
    somali-tools --help
    somali-tools metrics consolidate
    somali-tools ledger status
    somali-tools data validate-silver
    somali-tools dashboard build
"""

import sys
from pathlib import Path

import click


@click.group()
@click.version_option(version="0.2.0", prog_name="somali-tools")
@click.pass_context
def cli(ctx):
    """
    Somali Dialect Classifier operational utilities.

    Unified CLI for metrics management, ledger operations, data validation,
    and dashboard deployment. Replaces scattered scripts with consistent,
    discoverable commands.

    \b
    Command Groups:
      metrics     Metrics consolidation and analysis
      ledger      Ledger database management
      data        Dataset validation and quality checks
      dashboard   Dashboard build and deployment

    \b
    Examples:
      # Consolidate metrics from multiple sources
      somali-tools metrics consolidate

      # Check ledger database status
      somali-tools ledger status

      # Validate silver dataset integrity
      somali-tools data validate-silver

      # Build dashboard site
      somali-tools dashboard build

    For detailed help on any command group:
      somali-tools <group> --help
    """
    # Ensure context object exists for subcommands
    ctx.ensure_object(dict)


# ============================================================================
# METRICS COMMAND GROUP
# ============================================================================


@cli.group()
def metrics():
    """
    Metrics management and analysis commands.

    This command group handles metrics consolidation from individual processing
    runs, enhanced metrics generation, schema validation, and anomaly detection.

    \b
    Commands:
      consolidate      Generate consolidated metrics from processing files
      enhance          Generate enhanced metrics with additional calculations
      validate         Validate metrics against Phase 3 schema
      check-anomalies  Check for metric anomalies and outliers
      export           Export metrics to various formats

    \b
    Examples:
      # Consolidate all metrics into all_metrics.json
      somali-tools metrics consolidate

      # Validate metrics schema compliance
      somali-tools metrics validate

      # Check for anomalies in metrics
      somali-tools metrics check-anomalies
    """
    pass


@metrics.command()
@click.option(
    "--metrics-dir",
    "-d",
    default="data/metrics",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing metrics JSON files (default: data/metrics)",
)
@click.option(
    "--output",
    "-o",
    default="_site/data/all_metrics.json",
    type=click.Path(path_type=Path),
    help="Output path for consolidated metrics (default: _site/data/all_metrics.json)",
)
@click.option(
    "--source",
    "-s",
    multiple=True,
    help="Filter by specific source(s) (can be specified multiple times)",
)
def consolidate(metrics_dir: Path, output: Path, source: tuple[str, ...]):
    """
    Generate consolidated metrics from processing files.

    Consolidates all metrics/*_processing.json files into a single file for
    improved dashboard performance. Properly handles Phase 3 schema by surfacing
    layered_metrics and computing derived statistics.

    \b
    Schema Contract:
      Input:  data/metrics/*_processing.json (Phase 3 schema)
      Output: _site/data/all_metrics.json (ConsolidatedMetricsOutput)
              _site/data/summary.json (DashboardSummary)

    \b
    Examples:
      # Consolidate all metrics
      somali-tools metrics consolidate

      # Consolidate only Wikipedia metrics
      somali-tools metrics consolidate --source wikipedia

      # Custom output path
      somali-tools metrics consolidate --output /tmp/metrics.json
    """
    from .metrics_commands import consolidate_metrics

    try:
        # Convert source tuple to list
        source_filter = list(source) if source else None

        # Run consolidation
        result_path = consolidate_metrics(
            metrics_dir=metrics_dir, output_path=output, source_filter=source_filter
        )

        click.echo(f"✓ Consolidated metrics written to: {result_path}")
        click.echo(f"✓ Summary written to: {result_path.parent / 'summary.json'}")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)


@metrics.command()
@click.option(
    "--metrics-dir",
    "-d",
    default="data/metrics",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing metrics JSON files",
)
@click.option(
    "--output",
    "-o",
    default="_site/data/enhanced_metrics.json",
    type=click.Path(path_type=Path),
    help="Output path for enhanced metrics",
)
def enhance(metrics_dir: Path, output: Path):
    """
    Generate enhanced metrics with additional calculations.

    Computes derived statistics, trend analysis, and comparative metrics
    across sources and time periods.

    \b
    Examples:
      # Generate enhanced metrics
      somali-tools metrics enhance

      # Custom paths
      somali-tools metrics enhance -d custom/metrics -o custom/output.json
    """
    click.echo(
        "Not yet implemented in Wave 1. Logic will be added in Wave 3.\n"
        "For now, use: python scripts/ops/generate_enhanced_metrics.py"
    )


@metrics.command()
@click.option(
    "--metrics-dir",
    "-d",
    default="data/metrics",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing metrics JSON files",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Fail on warnings (default: only fail on errors)",
)
def validate(metrics_dir: Path, strict: bool):
    """
    Validate metrics against Phase 3 schema.

    CI-ready validation that checks all metrics files against the Phase 3
    schema. Fails the build if validation errors are found.

    \b
    Exit Codes:
      0 - All validations passed
      1 - Validation errors found
      2 - No metrics files found (warning)

    \b
    Examples:
      # Validate all metrics
      somali-tools metrics validate

      # Strict mode (fail on warnings)
      somali-tools metrics validate --strict
    """
    from .metrics_commands import validate_metrics

    try:
        result = validate_metrics(metrics_dir=metrics_dir, strict=strict)

        click.echo("\nValidation Results:")
        click.echo(f"  Total Files: {result['total_files']}")
        click.echo(f"  Valid: {result['valid']}")
        click.echo(f"  Errors: {result['errors']}")
        click.echo(f"  Warnings: {result['warnings']}")

        # Show details if errors/warnings
        if result["errors"] > 0 or result["warnings"] > 0:
            click.echo("\nDetails:")
            for file_result in result["files"]:
                if file_result["status"] != "valid":
                    click.echo(f"  [{file_result['status'].upper()}] {file_result['file']}")
                    click.echo(f"    {file_result['message']}")

        # Exit with appropriate code
        if result["total_files"] == 0:
            click.echo("\n⚠ Warning: No metrics files found")
            sys.exit(2)
        elif result["errors"] > 0:
            click.echo(f"\n✗ Validation failed with {result['errors']} errors")
            sys.exit(1)
        elif result["warnings"] > 0 and strict:
            click.echo(f"\n✗ Validation failed with {result['warnings']} warnings (strict mode)")
            sys.exit(1)
        else:
            click.echo("\n✓ All validations passed")
            sys.exit(0)

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)


@metrics.command("check-anomalies")
@click.option(
    "--metrics-dir",
    "-d",
    default="data/metrics",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing metrics JSON files",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output path for anomaly report (JSON)",
)
@click.option(
    "--threshold",
    "-t",
    type=int,
    default=3,
    help="Warning threshold (number of anomalies before exit code 1)",
)
def check_anomalies(metrics_dir: Path, output: Path | None, threshold: int):
    """
    Check for metric anomalies and outliers.

    Scans all processing metrics files for validation warnings and anomalies
    (e.g., records_passed_filters > records_received, impossible percentages).

    \b
    Exit Codes:
      0 - No anomalies found
      1 - Warnings found (>= threshold warning-level anomalies)
      2 - Errors found (any error-level anomalies)

    \b
    Examples:
      # Check for anomalies
      somali-tools metrics check-anomalies

      # Save report to file
      somali-tools metrics check-anomalies --output anomalies.json

      # Custom warning threshold
      somali-tools metrics check-anomalies --threshold 5
    """
    import json

    from .metrics_commands import check_anomalies as check_anomalies_fn

    try:
        result = check_anomalies_fn(metrics_dir=metrics_dir, threshold=threshold)

        click.echo("\nAnomaly Check Results:")
        click.echo(f"  Files Checked: {result['total_files']}")
        click.echo(f"  Total Anomalies: {result['total_anomalies']}")
        click.echo(f"  Errors: {result['error_anomalies']}")
        click.echo(f"  Warnings: {result['warning_anomalies']}")

        # Show anomalies
        if result["total_anomalies"] > 0:
            click.echo("\nAnomalies Found:")
            for anomaly in result["anomalies"]:
                level_marker = "✗" if anomaly["level"] == "error" else "⚠"
                click.echo(f"  {level_marker} [{anomaly['level'].upper()}] {anomaly['file']}")
                click.echo(f"    {anomaly['message']}")

        # Write report if output specified
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            click.echo(f"\n✓ Anomaly report written to: {output}")

        # Exit with appropriate code
        if result["error_anomalies"] > 0:
            click.echo(f"\n✗ Found {result['error_anomalies']} error-level anomalies")
            sys.exit(2)
        elif result["warning_anomalies"] >= threshold:
            click.echo(f"\n⚠ Found {result['warning_anomalies']} warnings (threshold: {threshold})")
            sys.exit(1)
        else:
            click.echo("\n✓ No significant anomalies found")
            sys.exit(0)

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)


@metrics.command()
@click.option(
    "--metrics-dir",
    "-d",
    default="data/metrics",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing metrics JSON files",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "csv", "parquet"], case_sensitive=False),
    default="json",
    help="Export format (default: json)",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output file path",
)
def export(metrics_dir: Path, format: str, output: Path):
    """
    Export metrics to various formats.

    Converts metrics from internal JSON format to CSV, Parquet, or
    reformatted JSON for external analysis tools.

    \b
    Examples:
      # Export to CSV
      somali-tools metrics export --format csv --output metrics.csv

      # Export to Parquet
      somali-tools metrics export -f parquet -o metrics.parquet
    """
    from .metrics_commands import export_metrics

    try:
        result_path = export_metrics(metrics_dir=metrics_dir, output_path=output, format=format)

        click.echo(f"✓ Exported metrics to: {result_path} ({format.upper()})")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("  Hint: Install required dependency for this format", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)


# ============================================================================
# LEDGER COMMAND GROUP
# ============================================================================


@cli.group()
def ledger():
    """
    Ledger database management commands.

    This command group handles crawl ledger operations including migrations,
    lock management, status queries, and ad-hoc database queries.

    \b
    Commands:
      migrate      Run ledger database migrations
      clear-locks  Clear stale locks in ledger
      status       Show ledger info (table counts, database size)
      query        Execute ad-hoc ledger queries

    \b
    Examples:
      # Show ledger database status
      somali-tools ledger status

      # Clear stale locks
      somali-tools ledger clear-locks

      # Run migrations
      somali-tools ledger migrate
    """
    pass


@ledger.command()
@click.option(
    "--ledger-path",
    "-l",
    default="data/ledger/crawl_ledger.db",
    type=click.Path(path_type=Path),
    help="Path to SQLite ledger database",
)
@click.option(
    "--migration",
    "-m",
    type=str,
    help="Specific migration to run (default: all pending)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be migrated without executing",
)
def migrate(ledger_path: Path, migration: str | None, dry_run: bool):
    """
    Run ledger database migrations.

    Applies pending schema migrations to the crawl ledger database.
    Migrations are executed in order from migrations/ directory.

    \b
    Examples:
      # Run all pending migrations
      somali-tools ledger migrate

      # Dry run to see what would be applied
      somali-tools ledger migrate --dry-run

      # Run specific migration
      somali-tools ledger migrate --migration 002_pipeline_runs_table
    """

    from .ledger_commands import migrate_ledger_database

    try:
        result = migrate_ledger_database(
            ledger_path=ledger_path, migration_name=migration, dry_run=dry_run
        )

        click.echo("\nMigration Results:")
        click.echo(f"  Total Migrations: {result['total']}")
        click.echo(f"  Dry Run: {result['dry_run']}")

        if result["applied"]:
            click.echo("\nMigrations:")
            for mig in result["applied"]:
                status_marker = "→" if mig["status"] == "would_apply" else "✓"
                click.echo(f"  {status_marker} {mig['migration']}: {mig['status']}")

        if not dry_run and result["total"] > 0:
            click.echo("\n✓ Migrations applied successfully")
        elif dry_run and result["total"] > 0:
            click.echo("\n[DRY RUN] No changes made")
        else:
            click.echo("\n✓ No pending migrations")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)


@ledger.command("clear-locks")
@click.option(
    "--lock-dir",
    "-d",
    default=".locks",
    type=click.Path(path_type=Path),
    help="Lock directory path (default: .locks)",
)
@click.option(
    "--max-age-hours",
    "-a",
    type=int,
    default=24,
    help="Maximum lock age in hours (default: 24)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Clear all locks regardless of age",
)
def clear_locks(lock_dir: Path, max_age_hours: int, force: bool):
    """
    Clear stale locks in ledger.

    Removes lock files older than specified age. Use with caution as this
    can interrupt running pipelines if locks are cleared prematurely.

    \b
    Examples:
      # Clear locks older than 24 hours
      somali-tools ledger clear-locks

      # Clear locks older than 2 hours
      somali-tools ledger clear-locks --max-age-hours 2

      # Force clear all locks (dangerous!)
      somali-tools ledger clear-locks --force
    """
    click.echo(
        "Not yet implemented in Wave 1. Logic will be added in Wave 3.\n"
        "For now, use: somali-lock-status --cleanup"
    )


@ledger.command()
@click.option(
    "--ledger-path",
    "-l",
    default="data/ledger/crawl_ledger.db",
    type=click.Path(exists=True, path_type=Path),
    help="Path to SQLite ledger database",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed table information",
)
def status(ledger_path: Path, verbose: bool):
    """
    Show ledger database status.

    Displays summary information about the crawl ledger including table
    counts, database size, recent activity, and schema version.

    \b
    Examples:
      # Basic status
      somali-tools ledger status

      # Detailed status with table information
      somali-tools ledger status --verbose

      # Custom ledger path
      somali-tools ledger status --ledger-path /custom/path/ledger.db
    """

    from .ledger_commands import get_ledger_status

    try:
        result = get_ledger_status(ledger_path=ledger_path, verbose=verbose)

        click.echo("\nLedger Database Status:")
        click.echo(f"  Database: {result['database']}")
        click.echo(f"  Size: {result['size_mb']} MB")
        click.echo(f"  Schema Version: {result['schema_version']}")

        click.echo("\nTable Counts:")
        for table_name, table_info in result["tables"].items():
            click.echo(f"  {table_name}: {table_info['count']:,} records")
            if verbose and "columns" in table_info:
                click.echo(f"    Columns: {', '.join(table_info['columns'][:5])}")

        if result["recent_activity"]:
            click.echo("\nRecent Activity:")
            for key, value in result["recent_activity"].items():
                if isinstance(value, dict):
                    click.echo(f"  {key}: {value.get('source')} at {value.get('timestamp')}")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)


@ledger.command()
@click.option(
    "--ledger-path",
    "-l",
    default="data/ledger/crawl_ledger.db",
    type=click.Path(exists=True, path_type=Path),
    help="Path to SQLite ledger database",
)
@click.option(
    "--sql",
    "-q",
    required=True,
    type=str,
    help="SQL query to execute",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "csv"], case_sensitive=False),
    default="table",
    help="Output format (default: table)",
)
def query(ledger_path: Path, sql: str, format: str):
    """
    Execute ad-hoc ledger queries.

    Run custom SQL queries against the crawl ledger database. Useful for
    debugging, reporting, and one-off data extraction.

    \b
    Examples:
      # Count total URLs in ledger
      somali-tools ledger query --sql "SELECT COUNT(*) FROM url_queue"

      # Show recent pipeline runs
      somali-tools ledger query --sql "SELECT * FROM pipeline_runs LIMIT 5"

      # Export as JSON
      somali-tools ledger query --sql "SELECT * FROM sources" --format json
    """
    click.echo(
        "Not yet implemented in Wave 1. Logic will be added in Wave 3.\n"
        f"Would execute: {sql[:50]}..."
    )


# ============================================================================
# DATA COMMAND GROUP
# ============================================================================


@cli.group()
def data():
    """
    Dataset validation and quality check commands.

    This command group handles validation of silver datasets, sample exports,
    and quality checks across the data pipeline.

    \b
    Commands:
      validate-silver  Validate silver dataset integrity
      export-sample    Export sample records for inspection
      check-quality    Run quality checks on datasets

    \b
    Examples:
      # Validate silver dataset
      somali-tools data validate-silver

      # Export sample records
      somali-tools data export-sample --count 100

      # Run quality checks
      somali-tools data check-quality
    """
    pass


@data.command("validate-silver")
@click.option(
    "--silver-path",
    "-p",
    default="data/processed/silver",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to silver dataset directory",
)
@click.option(
    "--source",
    "-s",
    multiple=True,
    help="Validate specific source(s) only",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Fail on warnings (default: only fail on errors)",
)
def validate_silver(silver_path: Path, source: tuple[str, ...], strict: bool):
    """
    Validate silver dataset integrity.

    Checks silver Parquet files for schema compliance, data quality issues,
    and consistency with gold schema requirements.

    \b
    Validation Checks:
      - Schema compliance (required fields present)
      - Data type correctness
      - Foreign key constraints
      - Duplicate detection
      - Quality metric thresholds

    \b
    Examples:
      # Validate all silver datasets
      somali-tools data validate-silver

      # Validate specific source
      somali-tools data validate-silver --source wikipedia

      # Strict mode (fail on warnings)
      somali-tools data validate-silver --strict
    """
    click.echo(
        "Not yet implemented in Wave 1. Logic will be added in Wave 3.\n"
        "This will validate: schema, data types, quality metrics"
    )


@data.command("export-sample")
@click.option(
    "--silver-path",
    "-p",
    default="data/processed/silver",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to silver dataset directory",
)
@click.option(
    "--count",
    "-n",
    type=int,
    default=10,
    help="Number of sample records to export (default: 10)",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output file path (JSON or CSV)",
)
@click.option(
    "--source",
    "-s",
    help="Sample from specific source only",
)
def export_sample(silver_path: Path, count: int, output: Path, source: str | None):
    """
    Export sample records for inspection.

    Extracts a random sample of records from silver datasets for manual
    inspection, debugging, or example generation.

    \b
    Examples:
      # Export 10 random records
      somali-tools data export-sample --output sample.json

      # Export 100 records from Wikipedia
      somali-tools data export-sample -n 100 -s wikipedia -o wiki_sample.csv
    """
    click.echo(
        "Not yet implemented in Wave 1. Logic will be added in Wave 3.\n"
        f"Would export {count} records to: {output}"
    )


@data.command("check-quality")
@click.option(
    "--silver-path",
    "-p",
    default="data/processed/silver",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to silver dataset directory",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output path for quality report (JSON)",
)
def check_quality(silver_path: Path, output: Path | None):
    """
    Run quality checks on datasets.

    Performs comprehensive quality analysis including text statistics,
    language detection confidence, deduplication effectiveness, and
    filter pass rates.

    \b
    Quality Metrics:
      - Text length distribution
      - Character set analysis
      - Language detection confidence
      - Deduplication rate
      - Filter effectiveness

    \b
    Examples:
      # Run quality checks
      somali-tools data check-quality

      # Save report to file
      somali-tools data check-quality --output quality_report.json
    """
    click.echo(
        "Not yet implemented in Wave 1. Logic will be added in Wave 3.\n"
        "This will check: text quality, dedup effectiveness, filter rates"
    )


# ============================================================================
# DASHBOARD COMMAND GROUP
# ============================================================================


@cli.group()
def dashboard():
    """
    Dashboard build and deployment commands.

    This command group handles dashboard site generation, local development
    server, and deployment operations.

    \b
    Commands:
      build    Build dashboard site
      serve    Start local development server
      deploy   Deploy dashboard (if needed)

    \b
    Examples:
      # Build dashboard
      somali-tools dashboard build

      # Start local server
      somali-tools dashboard serve

      # Build and deploy
      somali-tools dashboard build --deploy
    """
    pass


@dashboard.command()
@click.option(
    "--clean",
    is_flag=True,
    help="Clean _site directory before building",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed build output",
)
def build(clean: bool, verbose: bool):
    """
    Build dashboard site.

    Wrapper around src/dashboard/build-site.sh that generates static dashboard
    files from metrics and data exports.

    \b
    Build Steps:
      1. Export metrics consolidation
      2. Export quota/manifest data
      3. Copy static assets
      4. Generate index.html

    \b
    Examples:
      # Standard build
      somali-tools dashboard build

      # Clean build
      somali-tools dashboard build --clean

      # Verbose output
      somali-tools dashboard build --verbose
    """
    from .dashboard_commands import build_dashboard

    try:
        result = build_dashboard(clean=clean, verbose=verbose)

        click.echo("\n✓ Dashboard built successfully")
        click.echo(f"  Site Directory: {result['site_dir']}")
        click.echo(f"  HTML Files: {result['files']['html']}")
        click.echo(f"  JS Files: {result['files']['js']}")
        click.echo(f"  JSON Files: {result['files']['json']}")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)


@dashboard.command()
@click.option(
    "--port",
    "-p",
    type=int,
    default=8000,
    help="Port for development server (default: 8000)",
)
@click.option(
    "--host",
    "-h",
    default="127.0.0.1",
    help="Host for development server (default: 127.0.0.1)",
)
def serve(port: int, host: str):
    """
    Start local development server.

    Runs a simple HTTP server for local dashboard development and testing.

    \b
    Examples:
      # Start server on default port (8000)
      somali-tools dashboard serve

      # Custom port
      somali-tools dashboard serve --port 3000

      # Allow external access
      somali-tools dashboard serve --host 0.0.0.0
    """
    click.echo(
        "Not yet implemented in Wave 1. Logic will be added in Wave 3.\n"
        f"Would start server at: http://{host}:{port}"
    )


@dashboard.command()
@click.option(
    "--target",
    "-t",
    type=click.Choice(["github-pages", "netlify", "s3"], case_sensitive=False),
    default="github-pages",
    help="Deployment target (default: github-pages)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deployed without executing",
)
def deploy(target: str, dry_run: bool):
    """
    Deploy dashboard.

    Deploys built dashboard to specified target (GitHub Pages, Netlify, or S3).

    \b
    Examples:
      # Deploy to GitHub Pages
      somali-tools dashboard deploy

      # Dry run to see what would happen
      somali-tools dashboard deploy --dry-run

      # Deploy to Netlify
      somali-tools dashboard deploy --target netlify
    """
    click.echo(
        f"Not yet implemented in Wave 1. Logic will be added in Wave 3.\nWould deploy to: {target}"
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main():
    """Main entry point for CLI (used by console_scripts)."""
    try:
        cli(obj={})
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
