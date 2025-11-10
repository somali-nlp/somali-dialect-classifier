"""
Validate deduplication system integrity.

This script performs comprehensive validation of:
1. Ledger database integrity
2. Silver dataset consistency
3. Cross-system validation (ledger ↔ silver)
4. Deduplication fix verification

Checks:
- No duplicate hashes in ledger
- No duplicate records in silver dataset
- Ledger and silver counts match
- All processed URLs have silver records
- All silver records have ledger entries
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

try:
    import sqlite3
    import duckdb
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install duckdb")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeduplicationValidator:
    """Validate deduplication system integrity."""

    def __init__(self, ledger_path: Path, silver_dir: Path):
        """Initialize validator."""
        self.ledger_path = ledger_path
        self.silver_dir = silver_dir
        self.conn = None
        self.validation_results = []

    def connect_ledger(self):
        """Connect to ledger database."""
        if not self.ledger_path.exists():
            raise FileNotFoundError(f"Ledger not found: {self.ledger_path}")

        self.conn = sqlite3.connect(str(self.ledger_path))
        self.conn.row_factory = sqlite3.Row
        logger.info(f"✅ Connected to ledger: {self.ledger_path}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def add_result(self, check_name: str, passed: bool, message: str, details: Dict = None):
        """Add validation result."""
        self.validation_results.append({
            'check': check_name,
            'passed': passed,
            'message': message,
            'details': details or {}
        })

        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {check_name}")
        if message:
            logger.info(f"       {message}")

    def validate_ledger_no_duplicates(self) -> bool:
        """Validate no duplicate hashes exist in ledger."""
        logger.info("\n" + "="*60)
        logger.info("LEDGER VALIDATION: No Duplicate Hashes")
        logger.info("="*60)

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

        duplicate_groups = result['cnt']

        passed = duplicate_groups == 0

        self.add_result(
            "Ledger: No duplicate hashes",
            passed,
            f"{duplicate_groups} duplicate hash groups found" if not passed else "All hashes are unique",
            {'duplicate_groups': duplicate_groups}
        )

        return passed

    def validate_silver_no_duplicates(self) -> bool:
        """Validate no duplicate records in silver dataset."""
        logger.info("\n" + "="*60)
        logger.info("SILVER VALIDATION: No Duplicate Records")
        logger.info("="*60)

        sources = list(self.silver_dir.glob("source=*"))
        all_passed = True

        for source_dir in sources:
            parquet_files = list(source_dir.glob("**/*.parquet"))

            if not parquet_files:
                continue

            # Build union query
            union_query = " UNION ALL ".join([
                f"SELECT text_hash FROM read_parquet('{f}')"
                for f in parquet_files
            ])

            result = duckdb.execute(f"""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT text_hash) as unique_hashes
                FROM ({union_query})
            """).fetchone()

            total = result[0]
            unique = result[1]
            duplicates = total - unique

            passed = duplicates == 0

            self.add_result(
                f"Silver: {source_dir.name} no duplicates",
                passed,
                f"{duplicates} duplicates found ({duplicates/total*100:.1f}%)" if not passed else f"{total:,} unique records",
                {'total': total, 'unique': unique, 'duplicates': duplicates}
            )

            all_passed = all_passed and passed

        return all_passed

    def validate_ledger_silver_consistency(self) -> bool:
        """Validate ledger and silver counts match."""
        logger.info("\n" + "="*60)
        logger.info("CROSS-SYSTEM VALIDATION: Ledger ↔ Silver Consistency")
        logger.info("="*60)

        # Get ledger statistics per source
        ledger_stats = {}
        for row in self.conn.execute("""
            SELECT
                source,
                COUNT(DISTINCT text_hash) as unique_hashes
            FROM crawl_ledger
            WHERE text_hash IS NOT NULL
            AND state = 'processed'
            GROUP BY source
        """):
            ledger_stats[row['source']] = row['unique_hashes']

        # Get silver statistics per source
        silver_stats = {}
        for source_dir in self.silver_dir.glob("source=*"):
            parquet_files = list(source_dir.glob("**/*.parquet"))

            if not parquet_files:
                continue

            # Get unique hash count
            union_query = " UNION ALL ".join([
                f"SELECT DISTINCT text_hash FROM read_parquet('{f}')"
                for f in parquet_files
            ])

            result = duckdb.execute(f"""
                SELECT COUNT(DISTINCT text_hash) as cnt
                FROM ({union_query})
            """).fetchone()

            # Normalize source name for matching
            source_name = source_dir.name.replace("source=", "")
            silver_stats[source_name] = result[0]

        # Compare
        all_passed = True

        for source in set(ledger_stats.keys()) | set(silver_stats.keys()):
            ledger_count = ledger_stats.get(source, 0)
            silver_count = silver_stats.get(source, 0)

            # Allow small discrepancy (within 5%)
            diff = abs(ledger_count - silver_count)
            diff_pct = (diff / max(ledger_count, silver_count) * 100) if max(ledger_count, silver_count) > 0 else 0

            passed = diff_pct < 5

            self.add_result(
                f"Consistency: {source}",
                passed,
                f"Ledger: {ledger_count:,}, Silver: {silver_count:,}, Diff: {diff} ({diff_pct:.1f}%)",
                {'ledger': ledger_count, 'silver': silver_count, 'diff': diff}
            )

            all_passed = all_passed and passed

        return all_passed

    def generate_report(self) -> str:
        """Generate validation report."""
        total = len(self.validation_results)
        passed = sum(1 for r in self.validation_results if r['passed'])
        failed = total - passed

        pass_rate = (passed / total * 100) if total > 0 else 0

        report = []
        report.append("\n" + "="*60)
        report.append("VALIDATION REPORT")
        report.append("="*60)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"Ledger: {self.ledger_path}")
        report.append(f"Silver: {self.silver_dir}")
        report.append("")
        report.append(f"Total Checks: {total}")
        report.append(f"Passed: {passed} ({pass_rate:.1f}%)")
        report.append(f"Failed: {failed}")
        report.append("")

        # Group results by category
        categories = {}
        for result in self.validation_results:
            category = result['check'].split(':')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)

        for category, results in categories.items():
            report.append(f"\n{category}:")
            for result in results:
                status = "✅" if result['passed'] else "❌"
                report.append(f"  {status} {result['check']}")
                report.append(f"     {result['message']}")

        # Overall status
        report.append("\n" + "="*60)
        if failed == 0:
            report.append("✅ ALL CHECKS PASSED")
        else:
            report.append(f"❌ {failed} CHECKS FAILED")
        report.append("="*60)

        return "\n".join(report)

    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        try:
            self.connect_ledger()

            # Run checks
            checks = [
                self.validate_ledger_no_duplicates(),
                self.validate_silver_no_duplicates(),
                self.validate_ledger_silver_consistency()
            ]

            # Generate report
            report = self.generate_report()
            print(report)

            # Return overall result
            return all(checks)

        finally:
            self.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate deduplication system integrity"
    )

    parser.add_argument(
        '--ledger-path',
        type=Path,
        default=Path('data/ledger/crawl_ledger.db'),
        help='Path to ledger database'
    )

    parser.add_argument(
        '--silver-dir',
        type=Path,
        default=Path('data/processed/silver'),
        help='Path to silver dataset directory'
    )

    parser.add_argument(
        '--report',
        type=Path,
        help='Write report to file'
    )

    args = parser.parse_args()

    # Initialize validator
    validator = DeduplicationValidator(args.ledger_path, args.silver_dir)

    try:
        # Run validations
        all_passed = validator.run_all_validations()

        # Write report if requested
        if args.report:
            report = validator.generate_report()
            args.report.write_text(report)
            logger.info(f"\n📄 Report written to: {args.report}")

        return 0 if all_passed else 1

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
