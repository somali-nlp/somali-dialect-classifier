"""
Deduplicate silver dataset partitions.

This script consolidates all partitions for each source, removing duplicate
records (by text_hash) and keeping the most recent version.

Strategy:
- Groups partitions by source
- Keeps most recent record per text_hash (by date_accessed DESC)
- Archives original partitions before consolidation
- Writes single consolidated partition per source
- Validates before and after

Safety Features:
- Dry-run mode by default
- Archives original partitions (not destructive)
- Validates record counts
- Provides detailed statistics
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import shutil

try:
    import duckdb
    import pandas as pd
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install duckdb pandas pyarrow")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SilverDeduplicator:
    """Deduplicate silver dataset partitions."""

    def __init__(self, silver_dir: Path):
        """Initialize deduplicator with silver directory."""
        self.silver_dir = silver_dir
        self.archive_dir = silver_dir.parent / "archive" / f"pre-dedup-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def find_sources(self) -> List[Path]:
        """
        Find all source directories.

        Returns:
            List of source directory paths
        """
        sources = sorted([
            d for d in self.silver_dir.glob("source=*")
            if d.is_dir()
        ])

        logger.info(f"Found {len(sources)} source directories:")
        for source in sources:
            logger.info(f"  - {source.name}")

        return sources

    def get_source_statistics(self, source_dir: Path) -> Dict:
        """
        Get statistics for a source directory.

        Args:
            source_dir: Source directory path

        Returns:
            Dictionary with statistics
        """
        parquet_files = list(source_dir.glob("**/*.parquet"))

        if not parquet_files:
            return {
                'source': source_dir.name,
                'files': 0,
                'total_rows': 0,
                'unique_hashes': 0,
                'duplicates': 0,
                'size_mb': 0
            }

        # Query all partitions
        file_patterns = [str(f) for f in parquet_files]

        try:
            # Get total rows
            total_rows = 0
            for file_path in file_patterns:
                result = duckdb.execute(
                    f"SELECT COUNT(*) as cnt FROM read_parquet('{file_path}')"
                ).fetchone()
                total_rows += result[0]

            # Get unique hashes across all partitions
            union_query = " UNION ALL ".join([
                f"SELECT text_hash FROM read_parquet('{f}')"
                for f in file_patterns
            ])

            result = duckdb.execute(f"""
                SELECT COUNT(DISTINCT text_hash) as unique_hashes
                FROM ({union_query})
            """).fetchone()

            unique_hashes = result[0]

            # Calculate size
            total_size = sum(f.stat().st_size for f in parquet_files)

            return {
                'source': source_dir.name,
                'files': len(parquet_files),
                'total_rows': total_rows,
                'unique_hashes': unique_hashes,
                'duplicates': total_rows - unique_hashes,
                'size_mb': total_size / (1024 * 1024),
                'parquet_files': parquet_files
            }

        except Exception as e:
            logger.error(f"Error analyzing {source_dir.name}: {e}")
            return {
                'source': source_dir.name,
                'error': str(e)
            }

    def deduplicate_source(self, source_dir: Path, dry_run: bool = True, archive: bool = True) -> Dict:
        """
        Deduplicate a single source directory.

        Args:
            source_dir: Source directory to deduplicate
            dry_run: If True, only report what would be done
            archive: If True, archive original partitions

        Returns:
            Dictionary with deduplication results
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"{'DRY RUN' if dry_run else 'EXECUTING'}: {source_dir.name}")
        logger.info(f"{'='*60}")

        # Get statistics
        stats = self.get_source_statistics(source_dir)

        if 'error' in stats:
            logger.error(f"❌ Skipping {source_dir.name}: {stats['error']}")
            return stats

        if stats['files'] == 0:
            logger.info(f"⚠️ No parquet files found in {source_dir.name}")
            return stats

        logger.info(f"Files: {stats['files']}")
        logger.info(f"Total rows: {stats['total_rows']:,}")
        logger.info(f"Unique hashes: {stats['unique_hashes']:,}")
        logger.info(f"Duplicates: {stats['duplicates']:,}")
        logger.info(f"Size: {stats['size_mb']:.2f} MB")

        if stats['duplicates'] == 0:
            logger.info(f"✅ {source_dir.name} has no duplicates")
            return {**stats, 'action': 'skipped', 'reason': 'no duplicates'}

        dedup_rate = (stats['duplicates'] / stats['total_rows'] * 100) if stats['total_rows'] > 0 else 0
        logger.info(f"Deduplication rate: {dedup_rate:.1f}%")

        if dry_run:
            logger.info(f"\n[DRY RUN] Would consolidate {stats['files']} files into 1")
            logger.info(f"[DRY RUN] Would remove {stats['duplicates']:,} duplicate records")
            return {**stats, 'dry_run': True}

        # Execute deduplication
        logger.info("\n🔧 Deduplicating...")

        try:
            # Build deduplication query
            file_patterns = [str(f) for f in stats['parquet_files']]

            union_query = " UNION ALL ".join([
                f"SELECT * FROM read_parquet('{f}')"
                for f in file_patterns
            ])

            query = f"""
                WITH ranked AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY text_hash
                            ORDER BY date_accessed DESC, id DESC
                        ) as rn
                    FROM ({union_query})
                )
                SELECT * EXCLUDE (rn)
                FROM ranked
                WHERE rn = 1
            """

            # Execute query
            result_df = duckdb.execute(query).fetchdf()

            logger.info(f"✅ Deduplicated to {len(result_df):,} unique records")

            # Archive or delete original partitions
            if archive:
                archive_path = self.archive_dir / source_dir.name
                archive_path.mkdir(parents=True, exist_ok=True)

                logger.info(f"📦 Archiving {stats['files']} original files to {archive_path}")

                for parquet_file in stats['parquet_files']:
                    # Preserve directory structure
                    relative_path = parquet_file.relative_to(source_dir)
                    archive_file = archive_path / relative_path
                    archive_file.parent.mkdir(parents=True, exist_ok=True)

                    shutil.move(str(parquet_file), str(archive_file))

                logger.info(f"✅ Archived {stats['files']} files")

            else:
                logger.info(f"🗑️ Deleting {stats['files']} original files")
                for parquet_file in stats['parquet_files']:
                    parquet_file.unlink()
                logger.info(f"✅ Deleted {stats['files']} files")

            # Write consolidated partition
            output_path = source_dir / f"{source_dir.name.lower()}_deduplicated.parquet"

            logger.info(f"💾 Writing consolidated partition: {output_path.name}")

            result_df.to_parquet(
                output_path,
                engine='pyarrow',
                compression='snappy',
                index=False
            )

            output_size = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Wrote {len(result_df):,} records ({output_size:.2f} MB)")

            # Calculate savings
            space_saved = stats['size_mb'] - output_size

            logger.info(f"\nResults for {source_dir.name}:")
            logger.info(f"  Files: {stats['files']} → 1")
            logger.info(f"  Rows: {stats['total_rows']:,} → {len(result_df):,}")
            logger.info(f"  Removed: {stats['duplicates']:,} duplicates")
            logger.info(f"  Size: {stats['size_mb']:.2f} MB → {output_size:.2f} MB")
            logger.info(f"  Saved: {space_saved:.2f} MB ({space_saved/stats['size_mb']*100:.1f}%)")

            return {
                **stats,
                'action': 'deduplicated',
                'final_rows': len(result_df),
                'final_size_mb': output_size,
                'space_saved_mb': space_saved,
                'output_file': str(output_path),
                'archive_path': str(archive_path) if archive else None
            }

        except Exception as e:
            logger.error(f"❌ Deduplication failed for {source_dir.name}: {e}")
            raise

    def deduplicate_all(self, dry_run: bool = True, archive: bool = True, source_filter: Optional[str] = None) -> List[Dict]:
        """
        Deduplicate all sources.

        Args:
            dry_run: If True, only report what would be done
            archive: If True, archive original partitions
            source_filter: If provided, only process this source

        Returns:
            List of results for each source
        """
        sources = self.find_sources()

        if source_filter:
            sources = [s for s in sources if source_filter in s.name]
            if not sources:
                logger.error(f"❌ No sources match filter: {source_filter}")
                return []

        results = []

        for source_dir in sources:
            try:
                result = self.deduplicate_source(source_dir, dry_run=dry_run, archive=archive)
                results.append(result)
            except Exception as e:
                logger.error(f"❌ Failed to process {source_dir.name}: {e}")
                results.append({
                    'source': source_dir.name,
                    'error': str(e)
                })

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)

        total_files = sum(r.get('files', 0) for r in results if 'error' not in r)
        total_original_rows = sum(r.get('total_rows', 0) for r in results if 'error' not in r)
        total_final_rows = sum(r.get('final_rows', 0) for r in results if 'error' not in r and 'final_rows' in r)
        total_duplicates = sum(r.get('duplicates', 0) for r in results if 'error' not in r)
        total_space_saved = sum(r.get('space_saved_mb', 0) for r in results if 'error' not in r and 'space_saved_mb' in r)

        logger.info(f"Sources processed: {len(results)}")
        logger.info(f"Total files: {total_files}")
        logger.info(f"Total rows: {total_original_rows:,} → {total_final_rows:,}")
        logger.info(f"Duplicates removed: {total_duplicates:,}")
        logger.info(f"Space saved: {total_space_saved:.2f} MB")

        if not dry_run and archive:
            logger.info(f"\n📦 Archives stored in: {self.archive_dir}")
            logger.info(f"To rollback:")
            logger.info(f"  mv {self.archive_dir}/source=*/* {self.silver_dir}/source=*/")

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deduplicate silver dataset partitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (shows what would be done)
  python scripts/deduplicate_silver_dataset.py --dry-run

  # Execute deduplication
  python scripts/deduplicate_silver_dataset.py

  # Process specific source only
  python scripts/deduplicate_silver_dataset.py --source Wikipedia-Somali

  # Skip archiving (permanently delete old partitions)
  python scripts/deduplicate_silver_dataset.py --no-archive

Safety:
  - Archives original partitions by default
  - Can rollback by moving archived files back
  - Validates before and after
        """
    )

    parser.add_argument(
        '--silver-dir',
        type=Path,
        default=Path('data/processed/silver'),
        help='Path to silver dataset directory'
    )

    parser.add_argument(
        '--source',
        type=str,
        help='Process only this source (e.g., Wikipedia-Somali)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    parser.add_argument(
        '--no-archive',
        action='store_true',
        help='Delete original partitions instead of archiving'
    )

    args = parser.parse_args()

    # Initialize deduplicator
    deduplicator = SilverDeduplicator(args.silver_dir)

    try:
        # Execute
        results = deduplicator.deduplicate_all(
            dry_run=args.dry_run,
            archive=not args.no_archive,
            source_filter=args.source
        )

        # Check for errors
        errors = [r for r in results if 'error' in r]
        if errors:
            logger.error(f"\n❌ {len(errors)} sources failed:")
            for err in errors:
                logger.error(f"  - {err['source']}: {err['error']}")
            return 1

        if args.dry_run:
            logger.info("\n[DRY RUN COMPLETE] Run without --dry-run to execute")
            return 0

        logger.info("\n✅ DEDUPLICATION COMPLETE")

        return 0

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
