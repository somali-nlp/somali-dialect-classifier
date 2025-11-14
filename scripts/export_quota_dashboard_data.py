#!/usr/bin/env python3
"""
Export quota and manifest data from crawl_ledger.db and manifest files to JSON
for dashboard visualization.

This script generates two JSON files:
1. quota_status.json - Daily quota usage from crawl ledger database
2. manifest_analytics.json - Aggregated manifest analytics from manifest files

Usage:
    python scripts/export_quota_dashboard_data.py
    python scripts/export_quota_dashboard_data.py --quota-days 60
    python scripts/export_quota_dashboard_data.py --ledger /custom/path/ledger.db
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def export_quota_status(
    ledger_path: Path,
    output_path: Path,
    days: int = 30
) -> Path:
    """
    Export quota status from crawl_ledger.db to JSON.

    Args:
        ledger_path: Path to SQLite ledger database
        output_path: Path to output JSON file
        days: Number of days of quota history to export (default: 30)

    Returns:
        Path to created JSON file

    Raises:
        FileNotFoundError: If ledger database doesn't exist
        sqlite3.Error: If database query fails
    """
    # Check if database exists
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger database not found: {ledger_path}")

    # Connect to database
    conn = sqlite3.connect(str(ledger_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Calculate date range (last N days)
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)

        # Query daily quota usage
        cursor.execute("""
            SELECT date, source, records_ingested, quota_limit,
                   items_remaining, quota_hit
            FROM daily_quotas
            WHERE date >= ? AND date <= ?
            ORDER BY date DESC, source
        """, (start_date.isoformat(), end_date.isoformat()))

        daily_usage = []
        quota_hits_by_source = {}
        sources_seen = set()

        for row in cursor.fetchall():
            # Calculate usage percentage (avoid division by zero)
            quota_limit = row['quota_limit'] or 0
            records_ingested = row['records_ingested'] or 0

            if quota_limit > 0:
                usage_percent = round((records_ingested / quota_limit) * 100, 1)
            else:
                usage_percent = 0.0

            # Build daily usage record
            daily_usage.append({
                "date": row['date'],
                "source": row['source'],
                "records_ingested": records_ingested,
                "quota_limit": quota_limit,
                "items_remaining": row['items_remaining'] or 0,
                "quota_hit": bool(row['quota_hit']),
                "usage_percent": usage_percent
            })

            # Track sources and quota hits
            sources_seen.add(row['source'])

            if row['quota_hit']:
                source = row['source']
                if source not in quota_hits_by_source:
                    quota_hits_by_source[source] = []
                quota_hits_by_source[source].append(row['date'])

        # Get total quota hit count
        total_quota_hits = sum(len(dates) for dates in quota_hits_by_source.values())

        # Build output structure
        output = {
            "export_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "summary": {
                "total_quota_hits": total_quota_hits,
                "sources_with_quotas": sorted(list(sources_seen)),
                "reporting_period_days": days
            },
            "daily_usage": daily_usage,
            "quota_hits_by_source": quota_hits_by_source
        }

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file with pretty formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, sort_keys=False)

        logger.info(f"Exported quota status: {len(daily_usage)} records, {total_quota_hits} quota hits")

        return output_path

    except sqlite3.Error as e:
        # Handle case where table doesn't exist (database not initialized)
        if "no such table" in str(e):
            logger.warning(f"daily_quotas table not found in {ledger_path}, creating empty export")

            # Create empty output
            output = {
                "export_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "summary": {
                    "total_quota_hits": 0,
                    "sources_with_quotas": [],
                    "reporting_period_days": days
                },
                "daily_usage": [],
                "quota_hits_by_source": {}
            }

            # Create output directory and write empty file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2, sort_keys=False)

            logger.info("Exported empty quota status (database not initialized)")
            return output_path
        else:
            raise

    finally:
        conn.close()


def export_manifest_analytics(
    manifests_dir: Path,
    output_path: Path,
    max_manifests: int = 50
) -> Path:
    """
    Export manifest analytics from manifest JSON files.

    Args:
        manifests_dir: Path to manifests directory
        output_path: Path to output JSON file
        max_manifests: Maximum number of manifests to process (default: 50)

    Returns:
        Path to created JSON file

    Raises:
        FileNotFoundError: If manifests directory doesn't exist
    """
    # Check if manifests directory exists
    if not manifests_dir.exists():
        logger.warning(f"Manifests directory not found: {manifests_dir}, creating empty export")

        # Create empty output
        output = {
            "export_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "manifest_count": 0,
            "summary": {
                "total_records_ingested": 0,
                "total_runs": 0,
                "quota_hit_runs": 0
            },
            "per_source_totals": {},
            "recent_manifests": []
        }

        # Create output directory and write empty file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, sort_keys=False)

        logger.info("Exported empty manifest analytics (directory not found)")
        return output_path

    # Find all manifest files, sorted by modification time (newest first)
    manifest_files = sorted(
        manifests_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:max_manifests]

    if not manifest_files:
        logger.warning(f"No manifest files found in {manifests_dir}, creating empty export")

        # Create empty output
        output = {
            "export_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "manifest_count": 0,
            "summary": {
                "total_records_ingested": 0,
                "total_runs": 0,
                "quota_hit_runs": 0
            },
            "per_source_totals": {},
            "recent_manifests": []
        }

        # Create output directory and write file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, sort_keys=False)

        logger.info("Exported empty manifest analytics (no manifests found)")
        return output_path

    # Process manifests
    per_source_totals = {}
    total_records = 0
    quota_hit_count = 0
    recent_manifests = []

    for manifest_file in manifest_files:
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Extract run metadata
            run_info = {
                "run_id": manifest.get("run_id", "unknown"),
                "timestamp": manifest.get("timestamp", ""),
                "total_records": manifest.get("totals", {}).get("total_records", 0),
                "sources_with_quota_hit": manifest.get("totals", {}).get("sources_with_quota_hit", [])
            }
            recent_manifests.append(run_info)

            # Aggregate per-source totals
            for source_name, source_data in manifest.get("sources", {}).items():
                if source_name not in per_source_totals:
                    per_source_totals[source_name] = {
                        "runs": 0,
                        "total_records": 0,
                        "quota_hits": 0
                    }

                per_source_totals[source_name]["runs"] += 1
                per_source_totals[source_name]["total_records"] += source_data.get("records_ingested", 0)

                if source_data.get("quota_hit", False):
                    per_source_totals[source_name]["quota_hits"] += 1

            # Track totals
            total_records += run_info["total_records"]
            if run_info["sources_with_quota_hit"]:
                quota_hit_count += 1

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse manifest {manifest_file.name}: {e}")
            continue

    # Build output structure
    output = {
        "export_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "manifest_count": len(manifest_files),
        "summary": {
            "total_records_ingested": total_records,
            "total_runs": len(manifest_files),
            "quota_hit_runs": quota_hit_count
        },
        "per_source_totals": per_source_totals,
        "recent_manifests": recent_manifests[:10]  # Only include 10 most recent
    }

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file with pretty formatting
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, sort_keys=False)

    logger.info(f"Exported manifest analytics: {len(manifest_files)} manifests, {total_records} total records")

    return output_path


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Export quota and manifest data for dashboard visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export with default settings
  python scripts/export_quota_dashboard_data.py

  # Export 60 days of quota history
  python scripts/export_quota_dashboard_data.py --quota-days 60

  # Use custom paths
  python scripts/export_quota_dashboard_data.py --ledger /custom/path/ledger.db --manifests /custom/manifests
        """
    )

    parser.add_argument(
        "--ledger",
        default="data/crawl_ledger.db",
        help="Path to SQLite ledger database (default: data/crawl_ledger.db)"
    )
    parser.add_argument(
        "--manifests",
        default="data/manifests",
        help="Path to manifests directory (default: data/manifests)"
    )
    parser.add_argument(
        "--output-dir",
        default="dashboard/data",
        help="Output directory for JSON files (default: dashboard/data)"
    )
    parser.add_argument(
        "--quota-days",
        type=int,
        default=30,
        help="Number of days of quota history to export (default: 30)"
    )
    parser.add_argument(
        "--max-manifests",
        type=int,
        default=50,
        help="Maximum number of manifests to process (default: 50)"
    )

    args = parser.parse_args()

    try:
        # Convert string paths to Path objects
        ledger_path = Path(args.ledger)
        manifests_dir = Path(args.manifests)
        output_dir = Path(args.output_dir)

        # Export quota status
        quota_output = output_dir / "quota_status.json"
        export_quota_status(ledger_path, quota_output, days=args.quota_days)
        print(f"✅ Exported quota status to {quota_output}")

        # Export manifest analytics
        manifest_output = output_dir / "manifest_analytics.json"
        export_manifest_analytics(manifests_dir, manifest_output, max_manifests=args.max_manifests)
        print(f"✅ Exported manifest analytics to {manifest_output}")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        logger.exception("Unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
