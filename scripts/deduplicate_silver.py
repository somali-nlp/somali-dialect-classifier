#!/usr/bin/env python3
"""
Deduplication script for silver dataset.

Scans all parquet partitions, identifies duplicate records by text_hash,
keeps the earliest record, and records provenance of duplicates.

Usage:
    python scripts/deduplicate_silver.py
    python scripts/deduplicate_silver.py --dry-run
    python scripts/deduplicate_silver.py --output-dir data/silver_deduped
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_silver_partitions(silver_dir: Path) -> List[Path]:
    """Find all parquet partition files in silver directory."""
    partitions = sorted(silver_dir.glob("part-*.parquet"))
    logger.info(f"Found {len(partitions)} partition files")
    return partitions


def load_all_partitions(partitions: List[Path]) -> pd.DataFrame:
    """Load all partitions into a single DataFrame."""
    logger.info("Loading all partitions...")
    dfs = []

    for partition in partitions:
        df = pd.read_parquet(partition)
        df['_source_partition'] = partition.name
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(combined):,} total records")
    return combined


def find_duplicates(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identify duplicates by text_hash and return deduplicated DataFrame.

    Returns:
        deduplicated_df: DataFrame with duplicates removed (keeps earliest)
        duplicates_df: DataFrame containing duplicate records with provenance
    """
    logger.info("Identifying duplicates by text_hash...")

    # Add row index for tracking
    df['_original_index'] = df.index

    # Sort by date_accessed to keep earliest record
    df_sorted = df.sort_values('date_accessed')

    # Mark duplicates (keep='first' keeps the earliest)
    df_sorted['_is_duplicate'] = df_sorted.duplicated(subset=['text_hash'], keep='first')

    # Split into deduplicated and duplicates
    deduplicated_df = df_sorted[~df_sorted['_is_duplicate']].copy()
    duplicates_df = df_sorted[df_sorted['_is_duplicate']].copy()

    # Drop helper columns from deduplicated
    deduplicated_df = deduplicated_df.drop(columns=['_is_duplicate', '_original_index', '_source_partition'])

    # Keep provenance info in duplicates
    duplicates_df['_dedup_timestamp'] = datetime.now().isoformat()

    logger.info(f"Found {len(duplicates_df):,} duplicate records")
    logger.info(f"Retained {len(deduplicated_df):,} unique records")

    return deduplicated_df, duplicates_df


def analyze_duplicates(duplicates_df: pd.DataFrame) -> Dict:
    """Generate statistics about duplicates."""
    if len(duplicates_df) == 0:
        return {
            'total_duplicates': 0,
            'by_source': {},
            'by_source_type': {},
            'by_topic': {}
        }

    stats = {
        'total_duplicates': len(duplicates_df),
        'by_source': duplicates_df['source'].value_counts().to_dict(),
        'by_source_type': duplicates_df['source_type'].value_counts().to_dict(),
    }

    # Topic stats (only if topic column exists)
    if 'topic' in duplicates_df.columns:
        topic_counts = duplicates_df['topic'].value_counts().to_dict()
        stats['by_topic'] = topic_counts

    return stats


def write_deduplicated_dataset(
    df: pd.DataFrame,
    output_dir: Path,
    duplicates_df: pd.DataFrame
) -> Tuple[Path, Path]:
    """
    Write deduplicated dataset to parquet files.

    Args:
        df: Deduplicated DataFrame
        output_dir: Output directory for deduplicated data
        duplicates_df: DataFrame containing duplicate records

    Returns:
        Tuple of (deduplicated_path, duplicates_path)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write deduplicated data as single partition
    dedup_path = output_dir / "part-0000.parquet"
    logger.info(f"Writing {len(df):,} deduplicated records to {dedup_path}")
    df.to_parquet(dedup_path, index=False)

    # Write duplicates log
    duplicates_path = output_dir / "duplicates_removed.parquet"
    if len(duplicates_df) > 0:
        logger.info(f"Writing {len(duplicates_df):,} duplicate records to {duplicates_path}")
        duplicates_df.to_parquet(duplicates_path, index=False)
    else:
        logger.info("No duplicates found - skipping duplicates log")
        duplicates_path = None

    return dedup_path, duplicates_path


def print_statistics(stats: Dict, original_count: int, dedup_count: int):
    """Print deduplication statistics."""
    print("\n" + "=" * 60)
    print("DEDUPLICATION SUMMARY")
    print("=" * 60)
    print(f"Original records:    {original_count:,}")
    print(f"Deduplicated records: {dedup_count:,}")
    print(f"Duplicates removed:   {stats['total_duplicates']:,}")
    print(f"Reduction:            {stats['total_duplicates']/original_count*100:.2f}%")

    if stats['total_duplicates'] > 0:
        print("\nDuplicates by source:")
        for source, count in sorted(stats['by_source'].items(), key=lambda x: -x[1]):
            print(f"  {source}: {count:,}")

        print("\nDuplicates by source type:")
        for source_type, count in sorted(stats['by_source_type'].items(), key=lambda x: -x[1]):
            print(f"  {source_type}: {count:,}")

        if stats.get('by_topic'):
            print("\nTop 10 duplicate topics:")
            top_topics = sorted(stats['by_topic'].items(), key=lambda x: -x[1])[:10]
            for topic, count in top_topics:
                print(f"  {topic}: {count:,}")

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Deduplicate silver dataset by text_hash"
    )
    parser.add_argument(
        '--silver-dir',
        type=Path,
        default=Path('data/silver'),
        help='Path to silver dataset directory (default: data/silver)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/silver_deduped'),
        help='Output directory for deduplicated data (default: data/silver_deduped)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Analyze duplicates without writing output'
    )

    args = parser.parse_args()

    # Validate silver directory exists
    if not args.silver_dir.exists():
        logger.error(f"Silver directory not found: {args.silver_dir}")
        return 1

    # Find and load partitions
    partitions = find_silver_partitions(args.silver_dir)
    if not partitions:
        logger.error(f"No partition files found in {args.silver_dir}")
        return 1

    df = load_all_partitions(partitions)
    original_count = len(df)

    # Find duplicates
    deduplicated_df, duplicates_df = find_duplicates(df)
    dedup_count = len(deduplicated_df)

    # Analyze duplicates
    stats = analyze_duplicates(duplicates_df)
    print_statistics(stats, original_count, dedup_count)

    # Write output (unless dry-run)
    if args.dry_run:
        logger.info("Dry-run mode: skipping write to disk")
    else:
        write_deduplicated_dataset(
            deduplicated_df,
            args.output_dir,
            duplicates_df
        )
        logger.info(f"Deduplication complete! Output written to {args.output_dir}")

    return 0


if __name__ == '__main__':
    exit(main())
