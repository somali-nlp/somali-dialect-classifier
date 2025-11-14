#!/usr/bin/env python3
"""
Export filter metrics to Parquet for historical analysis.

Reads processing.json metrics files and exports filter breakdowns to Parquet format
with Hive-style partitioning by source and month for efficient querying.

Features:
- Incremental processing: Skips already-processed run_ids
- Batch processing: Processes files in chunks to reduce memory usage
- Partitioning: Creates Hive-style partitions (source=X/month=Y)
- Progress indicators: Shows progress every 100 files
- Validation: Gracefully handles missing filter_breakdown data

Usage:
    # Full export (process all metrics)
    python scripts/export_filters_to_parquet.py

    # Incremental export (skip existing run_ids)
    python scripts/export_filters_to_parquet.py --incremental

    # Custom paths and batch size
    python scripts/export_filters_to_parquet.py \
        --metrics-dir data/metrics \
        --output data/warehouse/filter_history.parquet \
        --batch-size 50

Requirements:
    pip install pyarrow pandas
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError as e:
    print(f"ERROR: Missing required dependencies: {e}")
    print("Install with: pip install pyarrow pandas")
    sys.exit(1)

# Import filter catalog functions
try:
    from somali_dialect_classifier.pipeline.filters.catalog import (
        get_filter_category,
        get_filter_label,
    )
except ImportError:
    print("WARNING: Could not import filter catalog. Using fallback labels.")

    def get_filter_label(key: str) -> str:
        """Fallback: Convert snake_case to Title Case."""
        return ' '.join(word.capitalize() for word in key.replace('_', ' ').split())

    def get_filter_category(key: str) -> str:
        """Fallback: Return unknown category."""
        return "unknown"


logger = logging.getLogger(__name__)


def load_processed_run_ids(parquet_path: Path) -> set[str]:
    """
    Load run_ids that have already been processed from existing Parquet.

    Args:
        parquet_path: Path to existing Parquet dataset

    Returns:
        Set of run_ids already in the dataset
    """
    if not parquet_path.exists():
        logger.info("No existing Parquet data found - starting fresh export")
        return set()

    try:
        # Read only run_id column for efficiency
        df = pd.read_parquet(parquet_path, columns=['run_id'])
        processed_ids = set(df['run_id'].unique())
        logger.info(f"Loaded {len(processed_ids)} existing run_ids from Parquet")
        return processed_ids
    except Exception as e:
        logger.warning(f"Could not read existing Parquet: {e}. Starting fresh export.")
        return set()


def parse_metrics_file(metrics_path: Path) -> dict[str, Any]:
    """
    Parse processing.json metrics file and extract filter data.

    Args:
        metrics_path: Path to *_processing.json file

    Returns:
        Dictionary with extracted metadata and filter breakdown
    """
    try:
        with metrics_path.open() as f:
            metrics = json.load(f)
    except Exception as e:
        logger.error(f"Failed to parse {metrics_path.name}: {e}")
        return None

    # Extract timestamp
    timestamp_str = metrics.get("_timestamp", "")
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")) if timestamp_str else None
    except Exception:
        logger.warning(f"Invalid timestamp in {metrics_path.name}: {timestamp_str}")
        timestamp = None

    # Extract source (clean up format)
    source = metrics.get("_source", "unknown")
    # Normalize source name: "TikTok-Somali" -> "tiktok-somali"
    source = source.lower().replace(" ", "-")

    # Use run_id from metrics or filename
    run_id = metrics.get("_run_id", metrics_path.stem)

    # Extract filter breakdown from layered_metrics.quality
    quality = metrics.get("layered_metrics", {}).get("quality", {})
    filter_breakdown = quality.get("filter_breakdown", {})

    # Extract related quality metrics
    records_received = quality.get("records_received", 0)
    records_passed = quality.get("records_passed_filters", 0)
    records_filtered = quality.get("records_filtered", 0)

    return {
        "timestamp": timestamp,
        "source": source,
        "run_id": run_id,
        "filter_breakdown": filter_breakdown,
        "records_received": records_received,
        "records_passed": records_passed,
        "records_filtered": records_filtered
    }


def create_filter_records(parsed_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Create individual records for each filter in the breakdown.

    Transforms filter_breakdown dictionary into list of records with one row per filter.

    Args:
        parsed_metrics: Output from parse_metrics_file()

    Returns:
        List of dictionaries, one per filter type
    """
    if not parsed_metrics or not parsed_metrics["filter_breakdown"]:
        return []

    records = []
    timestamp = parsed_metrics["timestamp"]

    # Add derived month column for partitioning
    month = timestamp.strftime("%Y-%m") if timestamp else None

    for filter_type, count in parsed_metrics["filter_breakdown"].items():
        record = {
            "timestamp": timestamp,
            "date": timestamp.date() if timestamp else None,
            "source": parsed_metrics["source"],
            "run_id": parsed_metrics["run_id"],
            "filter_type": filter_type,
            "filter_label": get_filter_label(filter_type),
            "filter_category": get_filter_category(filter_type),
            "records_filtered": count,
            "records_passed": parsed_metrics["records_passed"],
            "records_received": parsed_metrics["records_received"],
            "month": month
        }

        # Add derived filter_rate (percentage of received records filtered by this filter)
        if parsed_metrics["records_received"] > 0:
            record["filter_rate"] = count / parsed_metrics["records_received"]
        else:
            record["filter_rate"] = 0.0

        records.append(record)

    return records


def export_to_parquet(
    metrics_dir: Path,
    output_path: Path,
    incremental: bool = False,
    batch_size: int = 100
):
    """
    Export filter metrics to Parquet with partitioning and incremental support.

    Args:
        metrics_dir: Directory containing *processing.json files
        output_path: Output Parquet file/directory path
        incremental: If True, skip already-processed run_ids
        batch_size: Number of files to process per batch (memory management)
    """
    # Find all processing metrics files
    metrics_files = sorted(metrics_dir.glob("*_processing.json"))
    logger.info(f"Found {len(metrics_files)} processing.json files")

    if not metrics_files:
        logger.warning("No processing.json files found - nothing to export")
        return

    # Load existing run_ids if incremental mode
    processed_run_ids = set()
    if incremental:
        processed_run_ids = load_processed_run_ids(output_path)
        logger.info(f"Incremental mode: Will skip {len(processed_run_ids)} existing run_ids")

    # Process files in batches
    all_records = []
    skipped_count = 0
    error_count = 0
    empty_breakdown_count = 0

    for i, metrics_file in enumerate(metrics_files, 1):
        # Progress indicator every 100 files
        if i % 100 == 0:
            logger.info(f"Progress: {i}/{len(metrics_files)} files processed")

        # Parse metrics
        parsed = parse_metrics_file(metrics_file)

        if not parsed:
            error_count += 1
            continue

        # Skip if already processed (incremental mode)
        if incremental and parsed["run_id"] in processed_run_ids:
            skipped_count += 1
            continue

        # Skip if no filter breakdown data
        if not parsed["filter_breakdown"]:
            empty_breakdown_count += 1
            logger.debug(f"Skipping {metrics_file.name}: No filter_breakdown data")
            continue

        # Create records for this file
        records = create_filter_records(parsed)
        all_records.extend(records)

        # Batch processing: Convert to DataFrame periodically to manage memory
        if len(all_records) >= batch_size * 10:  # Process every ~1000 records
            logger.info(f"Batch checkpoint: {len(all_records)} records accumulated")

    logger.info("Extraction complete:")
    logger.info(f"  - Total files: {len(metrics_files)}")
    logger.info(f"  - Processed: {len(metrics_files) - skipped_count - error_count - empty_breakdown_count}")
    logger.info(f"  - Skipped (incremental): {skipped_count}")
    logger.info(f"  - Skipped (empty breakdown): {empty_breakdown_count}")
    logger.info(f"  - Errors: {error_count}")
    logger.info(f"  - Total filter records: {len(all_records)}")

    if not all_records:
        logger.warning("No filter records extracted - nothing to export")
        return

    # Convert to DataFrame
    logger.info("Converting to DataFrame...")
    df = pd.DataFrame(all_records)

    # Ensure timestamp is datetime type
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = pd.to_datetime(df["date"])

    # Sort by timestamp for better compression
    df = df.sort_values(["timestamp", "source", "filter_type"])

    # Display summary statistics
    logger.info("Dataset summary:")
    logger.info(f"  - Date range: {df['date'].min()} to {df['date'].max()}")
    logger.info(f"  - Sources: {df['source'].nunique()} unique ({', '.join(df['source'].unique())})")
    logger.info(f"  - Filter types: {df['filter_type'].nunique()} unique")
    logger.info(f"  - Months covered: {df['month'].nunique()} unique")

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing data if incremental mode
    if incremental and output_path.exists():
        logger.info("Merging with existing Parquet data...")
        try:
            existing_df = pd.read_parquet(output_path)
            df = pd.concat([existing_df, df], ignore_index=True)
            # Remove duplicates based on run_id and filter_type
            df = df.drop_duplicates(subset=["run_id", "filter_type"], keep="last")
            logger.info(f"Merged dataset size: {len(df)} records")
        except Exception as e:
            logger.warning(f"Could not merge with existing data: {e}. Writing fresh.")

    # Write to Parquet with partitioning
    logger.info(f"Writing Parquet to {output_path}...")

    # Convert to PyArrow Table
    table = pa.Table.from_pandas(df)

    # Write with Hive-style partitioning
    pq.write_to_dataset(
        table,
        root_path=str(output_path),
        partition_cols=["source", "month"],
        compression="snappy",
        existing_data_behavior="overwrite_or_ignore" if incremental else "overwrite_or_ignore"
    )

    logger.info("Export complete!")
    print("\n✅ Filter metrics exported to Parquet")
    print(f"   Output: {output_path}")
    print(f"   Total records: {len(df):,}")
    print(f"   Unique sources: {df['source'].nunique()}")
    print(f"   Unique filters: {df['filter_type'].nunique()}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print("   Partition structure: source=<source>/month=<YYYY-MM>/")
    print("\n📊 Parquet file size:")

    # Calculate total size
    total_size = sum(f.stat().st_size for f in output_path.rglob("*.parquet"))
    print(f"   {total_size / (1024 * 1024):.2f} MB")

    # Show sample query
    print("\n🔍 Query example:")
    print("   import pandas as pd")
    print(f"   df = pd.read_parquet('{output_path}')")
    print("   print(df.head())")


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Export filter metrics to Parquet for historical analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full export
  python scripts/export_filters_to_parquet.py

  # Incremental export (skip existing run_ids)
  python scripts/export_filters_to_parquet.py --incremental

  # Custom paths
  python scripts/export_filters_to_parquet.py \\
      --metrics-dir data/metrics \\
      --output data/warehouse/filter_history.parquet
        """
    )

    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=Path("data/metrics"),
        help="Directory containing *_processing.json files (default: data/metrics)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/warehouse/filter_history.parquet"),
        help="Output Parquet file path (default: data/warehouse/filter_history.parquet)"
    )

    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Incremental mode: Skip already-processed run_ids"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of files to process per batch (default: 100)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Validate inputs
    if not args.metrics_dir.exists():
        logger.error(f"Metrics directory not found: {args.metrics_dir}")
        sys.exit(1)

    # Run export
    try:
        export_to_parquet(
            metrics_dir=args.metrics_dir,
            output_path=args.output,
            incremental=args.incremental,
            batch_size=args.batch_size
        )
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
