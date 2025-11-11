#!/usr/bin/env python3
"""
Backup system for Somali NLP data pipeline.

Creates timestamped backups of critical data including:
- Ledger database (crawl_ledger.db)
- Silver data (parquet files)
- Metrics (JSON files)
- Reports (markdown files)

Features:
- Timestamped backup folders
- Backup manifest with checksums
- Retention policy (default: 30 days)
- Automatic cleanup of old backups
- Progress reporting
- Error handling and logging
"""

import argparse
import hashlib
import json
import logging
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/backup_system.log"),
    ],
)
logger = logging.getLogger(__name__)


class BackupSystem:
    """
    Automated backup system for Somali NLP pipeline data.

    Handles backup creation, retention management, and manifest generation.
    """

    def __init__(
        self,
        source_dir: Path = Path("data"),
        backup_dir: Path = Path("backups"),
        retention_days: int = 30,
    ):
        """
        Initialize backup system.

        Args:
            source_dir: Directory containing data to backup
            backup_dir: Directory to store backups
            retention_days: Number of days to keep backups
        """
        self.source_dir = Path(source_dir)
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Ensure logs directory exists
        Path("logs").mkdir(exist_ok=True)

    def create_backup(self) -> Path:
        """
        Create timestamped backup of critical data.

        Returns:
            Path to created backup folder

        Raises:
            FileNotFoundError: If source directory doesn't exist
            IOError: If backup creation fails
        """
        logger.info("=" * 80)
        logger.info("STARTING BACKUP PROCESS")
        logger.info("=" * 80)

        # Create timestamped backup folder
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = self.backup_dir / timestamp
        backup_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Backup location: {backup_path}")

        # Initialize manifest
        manifest = {
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "source_dir": str(self.source_dir),
            "files": [],
            "total_size_bytes": 0,
        }

        try:
            # Backup ledger database
            self._backup_ledger(backup_path, manifest)

            # Backup silver data (parquet files)
            self._backup_silver_data(backup_path, manifest)

            # Backup metrics (JSON files)
            self._backup_metrics(backup_path, manifest)

            # Backup reports (markdown files)
            self._backup_reports(backup_path, manifest)

            # Write manifest
            manifest_path = backup_path / "metadata.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"Backup manifest: {manifest_path}")
            logger.info(f"Total files backed up: {len(manifest['files'])}")
            logger.info(
                f"Total backup size: {manifest['total_size_bytes'] / (1024**2):.2f} MB"
            )
            logger.info("=" * 80)
            logger.info("BACKUP COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)

            return backup_path

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Clean up partial backup
            if backup_path.exists():
                shutil.rmtree(backup_path)
            raise

    def _backup_ledger(self, backup_path: Path, manifest: dict[str, Any]) -> None:
        """Backup ledger database."""
        ledger_source = self.source_dir / "ledger" / "crawl_ledger.db"

        if ledger_source.exists():
            ledger_dest = backup_path / "crawl_ledger.db"
            shutil.copy2(ledger_source, ledger_dest)
            logger.info(f"✓ Backed up ledger: {ledger_source.name}")

            file_info = self._file_info(ledger_dest, ledger_source)
            manifest["files"].append(file_info)
            manifest["total_size_bytes"] += file_info["size_bytes"]
        else:
            logger.warning(f"⚠ Ledger not found: {ledger_source}")

    def _backup_silver_data(self, backup_path: Path, manifest: dict[str, Any]) -> None:
        """Backup silver data (parquet files)."""
        silver_source = self.source_dir / "processed"
        silver_dest = backup_path / "processed"

        if silver_source.exists():
            silver_dest.mkdir(parents=True, exist_ok=True)

            # Find all parquet files
            parquet_files = list(silver_source.glob("*.parquet"))

            if parquet_files:
                logger.info(f"Backing up {len(parquet_files)} silver parquet files...")
                for parquet_file in parquet_files:
                    dest_file = silver_dest / parquet_file.name
                    shutil.copy2(parquet_file, dest_file)
                    logger.info(f"✓ Backed up: {parquet_file.name}")

                    file_info = self._file_info(dest_file, parquet_file)
                    manifest["files"].append(file_info)
                    manifest["total_size_bytes"] += file_info["size_bytes"]
            else:
                logger.warning("⚠ No parquet files found in processed directory")
        else:
            logger.warning(f"⚠ Silver data directory not found: {silver_source}")

    def _backup_metrics(self, backup_path: Path, manifest: dict[str, Any]) -> None:
        """Backup metrics (JSON files)."""
        metrics_source = self.source_dir / "metrics"
        metrics_dest = backup_path / "metrics"

        if metrics_source.exists():
            metrics_dest.mkdir(parents=True, exist_ok=True)

            # Find all JSON files
            json_files = list(metrics_source.glob("*.json"))

            if json_files:
                logger.info(f"Backing up {len(json_files)} metrics files...")
                for json_file in json_files:
                    dest_file = metrics_dest / json_file.name
                    shutil.copy2(json_file, dest_file)
                    logger.info(f"✓ Backed up: {json_file.name}")

                    file_info = self._file_info(dest_file, json_file)
                    manifest["files"].append(file_info)
                    manifest["total_size_bytes"] += file_info["size_bytes"]
            else:
                logger.warning("⚠ No JSON files found in metrics directory")
        else:
            logger.warning(f"⚠ Metrics directory not found: {metrics_source}")

    def _backup_reports(self, backup_path: Path, manifest: dict[str, Any]) -> None:
        """Backup reports (markdown files)."""
        reports_source = self.source_dir / "reports"
        reports_dest = backup_path / "reports"

        if reports_source.exists():
            reports_dest.mkdir(parents=True, exist_ok=True)

            # Find all markdown files
            md_files = list(reports_source.glob("*.md"))

            if md_files:
                logger.info(f"Backing up {len(md_files)} report files...")
                for md_file in md_files:
                    dest_file = reports_dest / md_file.name
                    shutil.copy2(md_file, dest_file)
                    logger.info(f"✓ Backed up: {md_file.name}")

                    file_info = self._file_info(dest_file, md_file)
                    manifest["files"].append(file_info)
                    manifest["total_size_bytes"] += file_info["size_bytes"]
            else:
                logger.warning("⚠ No markdown files found in reports directory")
        else:
            logger.warning(f"⚠ Reports directory not found: {reports_source}")

    def cleanup_old_backups(self) -> None:
        """Remove backups older than retention period."""
        logger.info(f"Cleaning up backups older than {self.retention_days} days...")

        cutoff = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0

        for backup_folder in self.backup_dir.glob("*"):
            # Skip non-directories
            if not backup_folder.is_dir():
                continue

            try:
                # Parse timestamp from folder name
                backup_time = datetime.strptime(backup_folder.name, "%Y-%m-%d_%H-%M-%S")

                if backup_time < cutoff:
                    shutil.rmtree(backup_folder)
                    deleted_count += 1
                    logger.info(f"✓ Deleted old backup: {backup_folder.name}")
            except ValueError:
                # Skip folders that don't match timestamp format
                logger.debug(f"Skipping non-timestamp folder: {backup_folder.name}")
                continue

        if deleted_count > 0:
            logger.info(f"Cleanup complete: {deleted_count} old backups deleted")
        else:
            logger.info("No old backups to clean up")

    def list_backups(self) -> list[dict[str, Any]]:
        """
        List all available backups with metadata.

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
                    }
                )
            except ValueError:
                continue

        return backups

    def _file_info(self, filepath: Path, source_path: Optional[Path] = None) -> dict:
        """
        Get file metadata and checksum.

        Args:
            filepath: Path to file to analyze
            source_path: Original source path (for reference)

        Returns:
            Dictionary with file information
        """
        stat = filepath.stat()
        checksum = self._calculate_checksum(filepath)

        return {
            "name": filepath.name,
            "path": str(filepath.relative_to(self.backup_dir)),
            "source_path": str(source_path) if source_path else None,
            "size_bytes": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "sha256": checksum,
        }

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
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def main():
    """CLI entry point for backup system."""
    parser = argparse.ArgumentParser(
        description="Backup system for Somali NLP data pipeline"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("data"),
        help="Source directory to backup (default: data)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("backups"),
        help="Backup destination directory (default: backups)",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Number of days to keep backups (default: 30)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available backups",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only run cleanup without creating new backup",
    )

    args = parser.parse_args()

    # Initialize backup system
    backup_system = BackupSystem(
        source_dir=args.source_dir,
        backup_dir=args.backup_dir,
        retention_days=args.retention_days,
    )

    try:
        # List backups mode
        if args.list:
            backups = backup_system.list_backups()
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
                print(f"\n{'=' * 80}")
            else:
                print("No backups found")
            return

        # Cleanup only mode
        if args.cleanup_only:
            backup_system.cleanup_old_backups()
            return

        # Normal mode: create backup and cleanup
        backup_path = backup_system.create_backup()
        print(f"\nBackup created successfully: {backup_path}")

        # Run cleanup
        backup_system.cleanup_old_backups()

    except Exception as e:
        logger.error(f"Backup system failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
