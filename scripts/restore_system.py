#!/usr/bin/env python3
"""
Restore system for Somali NLP data pipeline.

Restores data from timestamped backups created by backup_system.py.

Features:
- Restore from specific backup folder
- Checksum verification before restore
- Create safety backup of current state before restore
- Restore validation (verify data integrity)
- Dry-run mode for testing
"""

import argparse
import hashlib
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/restore_system.log"),
    ],
)
logger = logging.getLogger(__name__)


class RestoreSystem:
    """
    Automated restore system for Somali NLP pipeline data.

    Handles data restoration from backups with verification and safety features.
    """

    def __init__(
        self,
        backup_dir: Path = Path("backups"),
        target_dir: Path = Path("data"),
    ):
        """
        Initialize restore system.

        Args:
            backup_dir: Directory containing backups
            target_dir: Directory to restore data to
        """
        self.backup_dir = Path(backup_dir)
        self.target_dir = Path(target_dir)

        # Ensure logs directory exists
        Path("logs").mkdir(exist_ok=True)

    def list_backups(self) -> list[dict[str, Any]]:
        """
        List all available backups.

        Returns:
            List of backup information dictionaries
        """
        backups = []

        for backup_folder in sorted(self.backup_dir.glob("*"), reverse=True):
            if not backup_folder.is_dir():
                continue

            try:
                # Parse timestamp from folder name
                backup_time = datetime.strptime(backup_folder.name, "%Y-%m-%d_%H-%M-%S")

                # Load manifest if available
                manifest_path = backup_folder / "metadata.json"
                manifest = None
                if manifest_path.exists():
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)

                backups.append(
                    {
                        "name": backup_folder.name,
                        "path": str(backup_folder),
                        "timestamp": backup_time.isoformat(),
                        "age_days": (datetime.now() - backup_time).days,
                        "size_mb": (
                            manifest["total_size_bytes"] / (1024**2)
                            if manifest
                            else None
                        ),
                        "num_files": len(manifest["files"]) if manifest else None,
                        "has_manifest": manifest is not None,
                    }
                )
            except ValueError:
                continue

        return backups

    def restore(
        self, backup_name: str, dry_run: bool = False, skip_safety_backup: bool = False
    ) -> bool:
        """
        Restore data from specified backup.

        Args:
            backup_name: Name of backup folder to restore from
            dry_run: If True, only simulate restore without making changes
            skip_safety_backup: If True, skip creating safety backup of current state

        Returns:
            True if restore successful, False otherwise

        Raises:
            FileNotFoundError: If backup doesn't exist
            ValueError: If backup is invalid or corrupt
        """
        logger.info("=" * 80)
        logger.info("STARTING RESTORE PROCESS")
        logger.info("=" * 80)

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")

        # Validate backup exists
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        # Load and validate manifest
        manifest_path = backup_path / "metadata.json"
        if not manifest_path.exists():
            raise ValueError(f"Backup manifest not found: {manifest_path}")

        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        logger.info(f"Backup: {backup_name}")
        logger.info(f"Created: {manifest.get('created_at', 'Unknown')}")
        logger.info(f"Files: {len(manifest['files'])}")
        logger.info(
            f"Size: {manifest['total_size_bytes'] / (1024**2):.2f} MB"
        )

        # Verify checksums
        logger.info("\nVerifying backup integrity...")
        if not self._verify_backup(backup_path, manifest):
            raise ValueError("Backup verification failed - checksums don't match")
        logger.info("✓ Backup integrity verified")

        # Create safety backup of current state (unless skipped)
        if not skip_safety_backup and not dry_run:
            logger.info("\nCreating safety backup of current state...")
            safety_backup_path = self._create_safety_backup()
            logger.info(f"✓ Safety backup created: {safety_backup_path}")

        # Restore files
        logger.info("\nRestoring files...")
        restored_count = 0

        for file_info in manifest["files"]:
            source_file = backup_path / Path(file_info["path"]).name
            if "/" in file_info["path"]:
                # Handle subdirectories (processed/, metrics/, reports/)
                source_file = backup_path / file_info["path"]

            # Determine target location
            target_file = self._get_target_path(file_info)

            if dry_run:
                logger.info(f"[DRY RUN] Would restore: {file_info['name']} -> {target_file}")
            else:
                # Create parent directory if needed
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(source_file, target_file)
                logger.info(f"✓ Restored: {file_info['name']} -> {target_file}")

            restored_count += 1

        logger.info(f"\nRestored {restored_count} files")

        # Validate restoration
        if not dry_run:
            logger.info("\nValidating restored data...")
            if self._validate_restoration(manifest):
                logger.info("✓ Restoration validated successfully")
            else:
                logger.warning("⚠ Restoration validation warnings detected")

        logger.info("=" * 80)
        logger.info("RESTORE COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

        return True

    def _verify_backup(self, backup_path: Path, manifest: dict[str, Any]) -> bool:
        """
        Verify backup integrity by checking file checksums.

        Args:
            backup_path: Path to backup folder
            manifest: Backup manifest with checksums

        Returns:
            True if all checksums match, False otherwise
        """
        for file_info in manifest["files"]:
            source_file = backup_path / Path(file_info["path"]).name
            if "/" in file_info["path"]:
                source_file = backup_path / file_info["path"]

            if not source_file.exists():
                logger.error(f"✗ Missing file in backup: {file_info['name']}")
                return False

            # Calculate checksum
            actual_checksum = self._calculate_checksum(source_file)
            expected_checksum = file_info["sha256"]

            if actual_checksum != expected_checksum:
                logger.error(
                    f"✗ Checksum mismatch for {file_info['name']}: "
                    f"expected {expected_checksum}, got {actual_checksum}"
                )
                return False

        return True

    def _create_safety_backup(self) -> Path:
        """
        Create safety backup of current state before restore.

        Returns:
            Path to safety backup folder
        """
        # Import backup system to create safety backup
        from backup_system import BackupSystem

        backup_system = BackupSystem(
            source_dir=self.target_dir, backup_dir=self.backup_dir / "safety"
        )

        return backup_system.create_backup()

    def _get_target_path(self, file_info: dict[str, Any]) -> Path:
        """
        Determine target path for file restoration.

        Args:
            file_info: File information from manifest

        Returns:
            Target path for file
        """
        # Handle ledger
        if file_info["name"] == "crawl_ledger.db":
            return self.target_dir / "ledger" / "crawl_ledger.db"

        # Handle parquet files (silver data)
        if file_info["name"].endswith(".parquet"):
            return self.target_dir / "processed" / file_info["name"]

        # Handle JSON files (metrics)
        if file_info["name"].endswith(".json"):
            return self.target_dir / "metrics" / file_info["name"]

        # Handle markdown files (reports)
        if file_info["name"].endswith(".md"):
            return self.target_dir / "reports" / file_info["name"]

        # Default: use path from manifest
        return self.target_dir / file_info["path"]

    def _validate_restoration(self, manifest: dict[str, Any]) -> bool:
        """
        Validate restored data.

        Args:
            manifest: Backup manifest

        Returns:
            True if validation passes, False otherwise
        """
        all_valid = True

        # Check ledger exists and is valid SQLite database
        ledger_path = self.target_dir / "ledger" / "crawl_ledger.db"
        if ledger_path.exists():
            try:
                import sqlite3

                conn = sqlite3.connect(str(ledger_path))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()

                if tables:
                    logger.info(f"✓ Ledger database validated ({len(tables)} tables)")
                else:
                    logger.warning("⚠ Ledger database has no tables")
                    all_valid = False
            except Exception as e:
                logger.error(f"✗ Ledger database validation failed: {e}")
                all_valid = False
        else:
            logger.warning("⚠ Ledger database not found after restoration")

        # Check parquet files
        processed_dir = self.target_dir / "processed"
        if processed_dir.exists():
            parquet_files = list(processed_dir.glob("*.parquet"))
            logger.info(f"✓ Found {len(parquet_files)} parquet files in processed/")
        else:
            logger.warning("⚠ Processed directory not found after restoration")

        # Check metrics files
        metrics_dir = self.target_dir / "metrics"
        if metrics_dir.exists():
            json_files = list(metrics_dir.glob("*.json"))
            logger.info(f"✓ Found {len(json_files)} JSON files in metrics/")
        else:
            logger.warning("⚠ Metrics directory not found after restoration")

        return all_valid

    def _calculate_checksum(self, filepath: Path) -> str:
        """
        Calculate SHA256 checksum of file.

        Args:
            filepath: Path to file

        Returns:
            Hex-encoded SHA256 checksum
        """
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def main():
    """CLI entry point for restore system."""
    parser = argparse.ArgumentParser(
        description="Restore system for Somali NLP data pipeline"
    )
    parser.add_argument(
        "--backup",
        type=str,
        help="Name of backup to restore from (e.g., 2025-11-11_14-30-00)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("backups"),
        help="Backup directory (default: backups)",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path("data"),
        help="Target directory to restore to (default: data)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available backups",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate restore without making changes",
    )
    parser.add_argument(
        "--skip-safety-backup",
        action="store_true",
        help="Skip creating safety backup of current state",
    )

    args = parser.parse_args()

    # Initialize restore system
    restore_system = RestoreSystem(
        backup_dir=args.backup_dir, target_dir=args.target_dir
    )

    try:
        # List backups mode
        if args.list:
            backups = restore_system.list_backups()
            if backups:
                print(f"\n{'=' * 80}")
                print(f"AVAILABLE BACKUPS ({len(backups)} total)")
                print(f"{'=' * 80}")
                for backup in backups:
                    print(f"\nBackup: {backup['name']}")
                    print(f"  Path: {backup['path']}")
                    print(f"  Age: {backup['age_days']} days")
                    if backup["size_mb"] is not None:
                        print(f"  Size: {backup['size_mb']:.2f} MB")
                    if backup["num_files"] is not None:
                        print(f"  Files: {backup['num_files']}")
                    print(
                        f"  Valid: {'✓' if backup['has_manifest'] else '✗ (missing manifest)'}"
                    )
                print(f"\n{'=' * 80}")
                print("\nTo restore a backup, use:")
                print(f"  python scripts/restore_system.py --backup BACKUP_NAME")
            else:
                print("No backups found")
            return

        # Restore mode
        if not args.backup:
            print("Error: --backup argument required for restore")
            print("Use --list to see available backups")
            sys.exit(1)

        # Perform restore
        success = restore_system.restore(
            backup_name=args.backup,
            dry_run=args.dry_run,
            skip_safety_backup=args.skip_safety_backup,
        )

        if success:
            print(f"\nRestore completed successfully from backup: {args.backup}")
            if not args.dry_run:
                print(f"Data restored to: {args.target_dir}")
        else:
            print(f"\nRestore failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Restore system failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
