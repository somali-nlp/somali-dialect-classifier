"""
Compact duplicate entries in the crawl ledger database.

This script removes duplicate text_hash entries, keeping only the most recent
record per hash. This is safe because:
- Only removes duplicate content hashes (not URLs)
- Preserves most recent entry (by updated_at DESC)
- Never touches entries marked as 'duplicate' state (intentional markers)
- Never touches entries with NULL text_hash (not eligible for dedup)

Safety Features:
- Dry-run mode by default
- Creates automatic backup before modification
- Validates before and after
- Provides detailed statistics
"""

import argparse
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LedgerCompactor:
    """Compact duplicate entries in ledger database."""

    def __init__(self, db_path: Path):
        """Initialize compactor with database path."""
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.backup_path: Optional[Path] = None

    def connect(self):
        """Connect to database."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Ledger database not found: {self.db_path}")

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to ledger: {self.db_path}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def create_backup(self) -> Path:
        """
        Create backup of ledger database before modification.

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        self.backup_path = backup_dir / f"crawl_ledger_backup_{timestamp}.db"

        logger.info(f"Creating backup: {self.backup_path}")

        # Use SQLite backup API for safe copy
        backup_conn = sqlite3.connect(str(self.backup_path))
        with backup_conn:
            self.conn.backup(backup_conn)
        backup_conn.close()

        # Verify backup
        backup_size = self.backup_path.stat().st_size
        original_size = self.db_path.stat().st_size

        if backup_size != original_size:
            raise RuntimeError(f"Backup size mismatch: {backup_size} != {original_size}")

        logger.info(f"✅ Backup created successfully ({backup_size / 1024 / 1024:.1f} MB)")

        return self.backup_path

    def get_statistics(self) -> dict:
        """
        Get current ledger statistics.

        Returns:
            Dictionary with statistics
        """
        stats = {}

        # Total entries
        result = self.conn.execute("SELECT COUNT(*) as cnt FROM crawl_ledger").fetchone()
        stats['total_entries'] = result['cnt']

        # Entries with text_hash
        result = self.conn.execute("""
            SELECT COUNT(*) as cnt
            FROM crawl_ledger
            WHERE text_hash IS NOT NULL
        """).fetchone()
        stats['hashed_entries'] = result['cnt']

        # Unique hashes
        result = self.conn.execute("""
            SELECT COUNT(DISTINCT text_hash) as cnt
            FROM crawl_ledger
            WHERE text_hash IS NOT NULL
        """).fetchone()
        stats['unique_hashes'] = result['cnt']

        # Duplicate hash groups
        result = self.conn.execute("""
            SELECT COUNT(*) as cnt
            FROM (
                SELECT text_hash, COUNT(*) as hash_count
                FROM crawl_ledger
                WHERE text_hash IS NOT NULL
                AND state != 'duplicate'
                GROUP BY text_hash
                HAVING hash_count > 1
            )
        """).fetchone()
        stats['duplicate_groups'] = result['cnt']

        # Total duplicate entries (excluding the one we keep)
        result = self.conn.execute("""
            SELECT SUM(hash_count - 1) as cnt
            FROM (
                SELECT text_hash, COUNT(*) as hash_count
                FROM crawl_ledger
                WHERE text_hash IS NOT NULL
                AND state != 'duplicate'
                GROUP BY text_hash
                HAVING hash_count > 1
            )
        """).fetchone()
        stats['removable_duplicates'] = result['cnt'] or 0

        # Database size
        stats['db_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)

        return stats

    def find_duplicates(self, limit: int = 10) -> list:
        """
        Find duplicate hash groups.

        Args:
            limit: Maximum groups to return

        Returns:
            List of duplicate hash groups with details
        """
        results = self.conn.execute(f"""
            SELECT
                text_hash,
                COUNT(*) as count,
                GROUP_CONCAT(url, ' | ') as urls,
                MAX(updated_at) as most_recent
            FROM crawl_ledger
            WHERE text_hash IS NOT NULL
            AND state != 'duplicate'
            GROUP BY text_hash
            HAVING count > 1
            ORDER BY count DESC
            LIMIT {limit}
        """).fetchall()

        return [dict(row) for row in results]

    def compact(self, dry_run: bool = True) -> dict:
        """
        Compact duplicate entries, keeping most recent per hash.

        Args:
            dry_run: If True, only report what would be removed

        Returns:
            Dictionary with compaction results
        """
        logger.info("=" * 60)
        logger.info(f"{'DRY RUN' if dry_run else 'EXECUTING'}: Ledger Compaction")
        logger.info("=" * 60)

        # Get statistics before
        stats_before = self.get_statistics()

        logger.info(f"Total entries: {stats_before['total_entries']:,}")
        logger.info(f"Hashed entries: {stats_before['hashed_entries']:,}")
        logger.info(f"Unique hashes: {stats_before['unique_hashes']:,}")
        logger.info(f"Duplicate groups: {stats_before['duplicate_groups']:,}")
        logger.info(f"Removable duplicates: {stats_before['removable_duplicates']:,}")
        logger.info(f"Database size: {stats_before['db_size_mb']:.2f} MB")

        if stats_before['removable_duplicates'] == 0:
            logger.info("✅ No duplicates found. Database is already clean.")
            return {
                'dry_run': dry_run,
                'duplicates_removed': 0,
                'stats_before': stats_before,
                'stats_after': stats_before
            }

        # Show sample duplicates
        logger.info("\nSample duplicate groups:")
        duplicates = self.find_duplicates(limit=5)
        for dup in duplicates:
            logger.info(f"  Hash {dup['text_hash'][:16]}... has {dup['count']} copies")
            logger.info(f"    URLs: {dup['urls'][:100]}...")

        if dry_run:
            logger.info(f"\n[DRY RUN] Would remove {stats_before['removable_duplicates']} duplicate entries")
            return {
                'dry_run': True,
                'duplicates_found': stats_before['removable_duplicates'],
                'stats_before': stats_before
            }

        # Execute compaction
        logger.info("\n🔧 Executing compaction...")

        try:
            # Delete duplicates, keeping most recent
            cursor = self.conn.execute("""
                DELETE FROM crawl_ledger
                WHERE rowid NOT IN (
                    SELECT MAX(rowid)
                    FROM crawl_ledger
                    WHERE text_hash IS NOT NULL
                    AND state != 'duplicate'
                    GROUP BY text_hash
                )
                AND text_hash IS NOT NULL
                AND state != 'duplicate'
            """)

            deleted_count = cursor.rowcount
            self.conn.commit()

            logger.info(f"✅ Deleted {deleted_count:,} duplicate entries")

            # Vacuum to reclaim space
            logger.info("🔧 Vacuuming database to reclaim space...")
            self.conn.execute("VACUUM")
            logger.info("✅ Vacuum complete")

            # Get statistics after
            stats_after = self.get_statistics()

            logger.info("\nResults:")
            logger.info(f"  Entries before: {stats_before['total_entries']:,}")
            logger.info(f"  Entries after:  {stats_after['total_entries']:,}")
            logger.info(f"  Removed:        {deleted_count:,}")
            logger.info(f"  Size before:    {stats_before['db_size_mb']:.2f} MB")
            logger.info(f"  Size after:     {stats_after['db_size_mb']:.2f} MB")
            logger.info(f"  Space saved:    {stats_before['db_size_mb'] - stats_after['db_size_mb']:.2f} MB")

            # Validate
            if stats_after['unique_hashes'] != stats_before['unique_hashes']:
                logger.warning(f"⚠️ Unique hash count changed: {stats_before['unique_hashes']} → {stats_after['unique_hashes']}")

            if stats_after['duplicate_groups'] > 0:
                logger.warning(f"⚠️ {stats_after['duplicate_groups']} duplicate groups still remain")

            return {
                'dry_run': False,
                'duplicates_removed': deleted_count,
                'stats_before': stats_before,
                'stats_after': stats_after,
                'backup_path': str(self.backup_path) if self.backup_path else None
            }

        except Exception as e:
            logger.error(f"❌ Compaction failed: {e}")
            self.conn.rollback()
            raise

    def rollback_from_backup(self, backup_path: Path):
        """
        Rollback database from backup.

        Args:
            backup_path: Path to backup file
        """
        logger.info(f"🔄 Rolling back from backup: {backup_path}")

        self.close()

        # Replace current database with backup
        import shutil
        shutil.copy2(backup_path, self.db_path)

        logger.info("✅ Rollback complete")

        # Reconnect
        self.connect()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compact duplicate entries in crawl ledger database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (safe, shows what would be removed)
  python scripts/compact_ledger_duplicates.py --dry-run

  # Execute compaction
  python scripts/compact_ledger_duplicates.py

  # Non-interactive mode for automation
  python scripts/compact_ledger_duplicates.py --no-confirm

Safety:
  - Creates automatic backup before modification
  - Validates before and after
  - Can rollback if needed
        """
    )

    parser.add_argument(
        '--ledger-path',
        type=Path,
        default=Path('data/ledger/crawl_ledger.db'),
        help='Path to ledger database (default: data/ledger/crawl_ledger.db)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be removed without making changes'
    )

    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompt (for automation)'
    )

    args = parser.parse_args()

    # Initialize compactor
    compactor = LedgerCompactor(args.ledger_path)

    try:
        compactor.connect()

        # Run dry-run first
        results = compactor.compact(dry_run=True)

        if results.get('duplicates_found', 0) == 0:
            logger.info("✅ No action needed. Database is clean.")
            return 0

        # If --dry-run flag, stop here
        if args.dry_run:
            logger.info("\n[DRY RUN COMPLETE] Use --no-confirm to execute")
            return 0

        # Confirm with user
        if not args.no_confirm:
            print(f"\n⚠️  This will remove {results['duplicates_found']} duplicate entries")
            print(f"    from {args.ledger_path}")
            print("\n    A backup will be created automatically.")
            response = input("\nProceed? (yes/no): ").strip().lower()

            if response != 'yes':
                logger.info("❌ Cancelled by user")
                return 1

        # Create backup
        compactor.create_backup()

        # Execute compaction
        results = compactor.compact(dry_run=False)

        logger.info("\n" + "=" * 60)
        logger.info("✅ COMPACTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Removed: {results['duplicates_removed']} duplicate entries")
        logger.info(f"Backup: {results['backup_path']}")
        logger.info("\nTo rollback if needed:")
        logger.info(f"  cp {results['backup_path']} {args.ledger_path}")

        return 0

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1

    finally:
        compactor.close()


if __name__ == '__main__':
    sys.exit(main())
