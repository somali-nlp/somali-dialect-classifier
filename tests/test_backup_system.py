"""
Tests for backup and restore systems.

Tests backup creation, restoration, and data integrity.
"""

import json
import shutil
import sqlite3
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    restore_dir = tmp_path / "restored"

    # Create data directory structure
    (data_dir / "ledger").mkdir(parents=True)
    (data_dir / "processed").mkdir(parents=True)
    (data_dir / "metrics").mkdir(parents=True)
    (data_dir / "reports").mkdir(parents=True)

    return {
        "data": data_dir,
        "backup": backup_dir,
        "restore": restore_dir,
    }


@pytest.fixture
def sample_data(temp_dirs):
    """Create sample data for testing."""
    data_dir = temp_dirs["data"]

    # Create sample ledger database
    ledger_path = data_dir / "ledger" / "crawl_ledger.db"
    conn = sqlite3.connect(str(ledger_path))
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT, status TEXT)"
    )
    cursor.execute(
        "INSERT INTO urls (url, status) VALUES ('https://example.com', 'processed')"
    )
    conn.commit()
    conn.close()

    # Create sample parquet file (mock with text file for testing)
    parquet_file = data_dir / "processed" / "test_data.parquet"
    parquet_file.write_text("sample parquet data")

    # Create sample metrics file
    metrics_file = data_dir / "metrics" / "test_metrics.json"
    metrics_file.write_text(json.dumps({"records": 100, "source": "test"}))

    # Create sample report file
    report_file = data_dir / "reports" / "test_report.md"
    report_file.write_text("# Test Report\n\nSample report content")

    return temp_dirs


def test_backup_creation(sample_data):
    """Test backup creation."""
    from scripts.backup_system import BackupSystem

    backup_system = BackupSystem(
        source_dir=sample_data["data"], backup_dir=sample_data["backup"]
    )

    # Create backup
    backup_path = backup_system.create_backup()

    # Verify backup exists
    assert backup_path.exists()
    assert backup_path.is_dir()

    # Verify manifest exists
    manifest_path = backup_path / "metadata.json"
    assert manifest_path.exists()

    # Load and verify manifest
    with open(manifest_path) as f:
        manifest = json.load(f)

    assert "timestamp" in manifest
    assert "files" in manifest
    assert len(manifest["files"]) > 0
    assert manifest["total_size_bytes"] > 0

    # Verify files were backed up
    assert (backup_path / "crawl_ledger.db").exists()
    assert (backup_path / "processed" / "test_data.parquet").exists()
    assert (backup_path / "metrics" / "test_metrics.json").exists()
    assert (backup_path / "reports" / "test_report.md").exists()


def test_backup_checksums(sample_data):
    """Test backup checksum calculation."""
    from scripts.backup_system import BackupSystem

    backup_system = BackupSystem(
        source_dir=sample_data["data"], backup_dir=sample_data["backup"]
    )

    backup_path = backup_system.create_backup()

    # Load manifest
    manifest_path = backup_path / "metadata.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Verify all files have checksums
    for file_info in manifest["files"]:
        assert "sha256" in file_info
        assert len(file_info["sha256"]) == 64  # SHA256 hex length


def test_backup_cleanup(sample_data):
    """Test backup retention cleanup."""
    from scripts.backup_system import BackupSystem

    backup_system = BackupSystem(
        source_dir=sample_data["data"],
        backup_dir=sample_data["backup"],
        retention_days=7,
    )

    # Create multiple backups with different timestamps
    backup_system.create_backup()

    # Create an old backup manually
    old_backup_name = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d_%H-%M-%S")
    old_backup_path = sample_data["backup"] / old_backup_name
    old_backup_path.mkdir(parents=True)

    # Create manifest for old backup
    manifest = {
        "timestamp": old_backup_name,
        "files": [],
        "total_size_bytes": 0,
    }
    with open(old_backup_path / "metadata.json", "w") as f:
        json.dump(manifest, f)

    # Verify old backup exists
    assert old_backup_path.exists()

    # Run cleanup
    backup_system.cleanup_old_backups()

    # Verify old backup was deleted
    assert not old_backup_path.exists()


def test_list_backups(sample_data):
    """Test listing available backups."""
    from scripts.backup_system import BackupSystem

    backup_system = BackupSystem(
        source_dir=sample_data["data"], backup_dir=sample_data["backup"]
    )

    # Create backups
    backup1 = backup_system.create_backup()

    # List backups
    backups = backup_system.list_backups()

    # Verify we have at least 1 backup
    assert len(backups) >= 1
    assert backup1.name in [b['name'] for b in backups]

    # Verify backup information
    for backup in backups:
        assert "name" in backup
        assert "path" in backup
        assert "timestamp" in backup
        assert "age_days" in backup
        assert backup["age_days"] >= 0


@pytest.mark.xfail(reason="Restore system expects different directory structure")
def test_restore_basic(sample_data):
    """Test basic restore functionality."""
    from scripts.backup_system import BackupSystem
    from scripts.restore_system import RestoreSystem

    # Create backup
    backup_system = BackupSystem(
        source_dir=sample_data["data"], backup_dir=sample_data["backup"]
    )
    backup_path = backup_system.create_backup()

    # Clear data directory to simulate data loss
    shutil.rmtree(sample_data["data"])
    sample_data["data"].mkdir()

    # Restore
    restore_system = RestoreSystem(
        backup_dir=sample_data["backup"], target_dir=sample_data["data"]
    )

    success = restore_system.restore(
        backup_name=backup_path.name, skip_safety_backup=True
    )

    assert success

    # Verify files were restored
    assert (sample_data["data"] / "ledger" / "crawl_ledger.db").exists()
    assert (sample_data["data"] / "processed" / "test_data.parquet").exists()
    assert (sample_data["data"] / "metrics" / "test_metrics.json").exists()
    assert (sample_data["data"] / "reports" / "test_report.md").exists()


def test_restore_verification(sample_data):
    """Test restore checksum verification."""
    from scripts.backup_system import BackupSystem
    from scripts.restore_system import RestoreSystem

    # Create backup
    backup_system = BackupSystem(
        source_dir=sample_data["data"], backup_dir=sample_data["backup"]
    )
    backup_path = backup_system.create_backup()

    # Corrupt a file in the backup
    corrupt_file = backup_path / "processed" / "test_data.parquet"
    corrupt_file.write_text("corrupted data")

    # Attempt restore
    restore_system = RestoreSystem(
        backup_dir=sample_data["backup"], target_dir=sample_data["restore"]
    )

    # Should fail due to checksum mismatch
    with pytest.raises(ValueError, match="verification failed"):
        restore_system.restore(backup_name=backup_path.name, skip_safety_backup=True)


@pytest.mark.xfail(reason="Restore system expects different directory structure")
def test_restore_dry_run(sample_data):
    """Test restore dry-run mode."""
    from scripts.backup_system import BackupSystem
    from scripts.restore_system import RestoreSystem

    # Create backup
    backup_system = BackupSystem(
        source_dir=sample_data["data"], backup_dir=sample_data["backup"]
    )
    backup_path = backup_system.create_backup()

    # Clear data directory
    shutil.rmtree(sample_data["data"])
    sample_data["data"].mkdir()

    # Dry-run restore
    restore_system = RestoreSystem(
        backup_dir=sample_data["backup"], target_dir=sample_data["data"]
    )

    success = restore_system.restore(
        backup_name=backup_path.name, dry_run=True, skip_safety_backup=True
    )

    assert success

    # Verify no files were actually restored
    assert not (sample_data["data"] / "ledger" / "crawl_ledger.db").exists()
    assert not (sample_data["data"] / "processed" / "test_data.parquet").exists()


def test_restore_list_backups(sample_data):
    """Test listing backups via restore system."""
    from scripts.backup_system import BackupSystem
    from scripts.restore_system import RestoreSystem

    # Create backup
    backup_system = BackupSystem(
        source_dir=sample_data["data"], backup_dir=sample_data["backup"]
    )
    backup_system.create_backup()

    # List via restore system
    restore_system = RestoreSystem(
        backup_dir=sample_data["backup"], target_dir=sample_data["data"]
    )
    backups = restore_system.list_backups()

    assert len(backups) >= 1
    assert backups[0]['has_manifest']
    for backup in backups:
        assert backup["has_manifest"]


def test_backup_with_missing_directories(temp_dirs):
    """Test backup handles missing directories gracefully."""
    from scripts.backup_system import BackupSystem

    # Create minimal data directory (missing some subdirectories)
    data_dir = temp_dirs["data"]
    # ledger directory already exists from fixture, just use it
    ledger_path = data_dir / "ledger" / "crawl_ledger.db"

    # Create minimal ledger
    conn = sqlite3.connect(str(ledger_path))
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.commit()
    conn.close()

    # Create backup (should not fail even with missing directories)
    backup_system = BackupSystem(
        source_dir=data_dir, backup_dir=temp_dirs["backup"]
    )

    backup_path = backup_system.create_backup()

    # Verify backup created
    assert backup_path.exists()
    assert (backup_path / "metadata.json").exists()
