"""
Unit tests for ManifestWriter class.

Tests the ingestion manifest generation system including:
- CRUD operations (create, write, read, list)
- Validation (schema compliance, error handling)
- Cleanup (retention policy)
- Analytics (quota hit tracking, aggregation)
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from somali_dialect_classifier.utils.manifest_writer import ManifestWriter


@pytest.fixture
def temp_manifest_dir():
    """Create temporary directory for manifest testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_dir = Path(tmpdir) / "manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        yield manifest_dir


@pytest.fixture
def writer(temp_manifest_dir):
    """Create ManifestWriter instance with temp directory."""
    return ManifestWriter(manifest_dir=temp_manifest_dir)


@pytest.fixture
def sample_sources():
    """Sample source data for manifest creation."""
    return {
        "wikipedia": {
            "status": "completed",
            "records_ingested": 1234,
            "records_skipped": 8726,
            "partitions": ["2025-11-13"],
            "quota_hit": False,
            "processing_time_seconds": 45.2
        },
        "bbc": {
            "status": "quota_reached",
            "records_ingested": 350,
            "records_skipped": 0,
            "partitions": ["2025-11-13"],
            "quota_hit": True,
            "quota_limit": 350,
            "items_remaining": 127,
            "processing_time_seconds": 180.5
        }
    }


# =============================================================================
# CRUD Operations Tests (4 tests)
# =============================================================================

def test_create_manifest_valid_structure(writer, sample_sources):
    """Verify create_manifest generates valid JSON schema."""
    run_id = "run_20251113_143022_abc123"
    timestamp = datetime.now(timezone.utc)

    manifest = writer.create_manifest(run_id, sample_sources, timestamp)

    # Check required top-level fields
    assert "manifest_version" in manifest
    assert "run_id" in manifest
    assert "timestamp" in manifest
    assert "orchestrator_version" in manifest
    assert "sources" in manifest
    assert "totals" in manifest

    # Verify values
    assert manifest["run_id"] == run_id
    assert manifest["manifest_version"] == "1.0"
    assert manifest["orchestrator_version"] == "1.1.0"
    assert manifest["sources"] == sample_sources

    # Check totals calculation
    assert manifest["totals"]["total_records"] == 1584  # 1234 + 350
    assert manifest["totals"]["total_partitions"] == 1
    assert manifest["totals"]["sources_with_quota_hit"] == ["bbc"]


def test_write_manifest_creates_file(writer, sample_sources):
    """Verify write_manifest creates file in correct location."""
    run_id = "run_20251113_143022"
    manifest = writer.create_manifest(run_id, sample_sources)

    manifest_path = writer.write_manifest(manifest)

    # Verify file was created
    assert manifest_path.exists()
    assert manifest_path.parent == writer.manifest_dir
    assert manifest_path.name == f"{run_id}.json"

    # Verify content is valid JSON
    with open(manifest_path) as f:
        loaded_manifest = json.load(f)
        assert loaded_manifest["run_id"] == run_id


def test_read_manifest_loads_correctly(writer, sample_sources):
    """Verify read_manifest deserializes correctly."""
    run_id = "run_20251113_143022"
    manifest = writer.create_manifest(run_id, sample_sources)
    manifest_path = writer.write_manifest(manifest)

    # Read manifest back
    loaded_manifest = writer.read_manifest(manifest_path.name)

    # Verify loaded content matches original
    assert loaded_manifest["run_id"] == run_id
    assert loaded_manifest["sources"] == sample_sources
    assert loaded_manifest["manifest_version"] == manifest["manifest_version"]


def test_list_manifests_returns_sorted(writer, sample_sources):
    """Verify list_manifests returns chronologically sorted list."""
    # Create multiple manifests with different timestamps
    manifests_created = []
    for i in range(5):
        run_id = f"run_2025111{i}_143022"
        manifest = writer.create_manifest(run_id, sample_sources)
        path = writer.write_manifest(manifest)
        manifests_created.append(path)

    # List all manifests
    listed_manifests = writer.list_manifests()

    # Verify all manifests are listed
    assert len(listed_manifests) == 5

    # Verify sorted by modification time (newest first)
    # Last created should be first in list
    assert listed_manifests[0].name == manifests_created[-1].name


# =============================================================================
# Validation Tests (3 tests)
# =============================================================================

def test_manifest_schema_validation(writer, sample_sources):
    """Verify manifest schema validation enforces required fields."""
    manifest = writer.create_manifest("run_123", sample_sources)

    # Should not raise - valid manifest
    writer._validate_manifest(manifest)

    # Verify all required fields are present
    required_fields = ["manifest_version", "run_id", "timestamp", "sources", "totals"]
    for field in required_fields:
        assert field in manifest


def test_invalid_manifest_rejected(writer):
    """Verify malformed manifests are rejected."""
    # Missing required fields
    invalid_manifest = {
        "run_id": "test_123",
        # Missing: manifest_version, timestamp, sources, totals
    }

    with pytest.raises(ValueError, match="Missing required field"):
        writer._validate_manifest(invalid_manifest)


def test_manifest_version_compatibility(writer, sample_sources):
    """Verify manifest version field is correct."""
    manifest = writer.create_manifest("run_123", sample_sources)

    assert manifest["manifest_version"] == "1.0"
    assert "orchestrator_version" in manifest


# =============================================================================
# Cleanup Tests (2 tests)
# =============================================================================

def test_cleanup_old_manifests_90_days(writer, sample_sources):
    """Verify manifests older than 90 days are deleted."""
    # Create old manifest (100 days ago)
    old_run_id = "run_old"
    old_timestamp = datetime.now(timezone.utc) - timedelta(days=100)
    old_manifest = writer.create_manifest(old_run_id, sample_sources, timestamp=old_timestamp)
    old_path = writer.write_manifest(old_manifest)

    # Create recent manifest (30 days ago)
    recent_run_id = "run_recent"
    recent_timestamp = datetime.now(timezone.utc) - timedelta(days=30)
    recent_manifest = writer.create_manifest(recent_run_id, sample_sources, timestamp=recent_timestamp)
    recent_path = writer.write_manifest(recent_manifest)

    # Run cleanup with 90-day retention
    deleted_count = writer.cleanup_old_manifests(keep_days=90)

    # Verify old manifest was deleted
    assert deleted_count == 1
    assert not old_path.exists()
    assert recent_path.exists()


def test_cleanup_preserves_recent(writer, sample_sources):
    """Verify recent manifests are preserved during cleanup."""
    # Create 3 recent manifests (within last 90 days)
    recent_paths = []
    for i in range(3):
        run_id = f"run_recent_{i}"
        timestamp = datetime.now(timezone.utc) - timedelta(days=10 + i)
        manifest = writer.create_manifest(run_id, sample_sources, timestamp=timestamp)
        path = writer.write_manifest(manifest)
        recent_paths.append(path)

    # Run cleanup
    deleted_count = writer.cleanup_old_manifests(keep_days=90)

    # Verify nothing was deleted
    assert deleted_count == 0
    for path in recent_paths:
        assert path.exists()


# =============================================================================
# Analytics Tests (3 tests)
# =============================================================================

def test_get_quota_hit_sources(writer):
    """Verify get_sources_with_quota_hits tracks quota hits correctly."""
    # Create manifests with quota hits
    sources_with_hit = {
        "bbc": {
            "status": "quota_reached",
            "records_ingested": 350,
            "records_skipped": 0,
            "partitions": ["2025-11-13"],
            "quota_hit": True,
            "quota_limit": 350,
            "items_remaining": 100,
            "processing_time_seconds": 180.0
        },
        "wikipedia": {
            "status": "completed",
            "records_ingested": 1000,
            "records_skipped": 0,
            "partitions": ["2025-11-13"],
            "quota_hit": False,
            "processing_time_seconds": 50.0
        }
    }

    # Create 3 manifests with BBC quota hits
    for i in range(3):
        run_id = f"run_quota_hit_{i}"
        timestamp = datetime.now(timezone.utc) - timedelta(hours=i)
        manifest = writer.create_manifest(run_id, sources_with_hit, timestamp=timestamp)
        writer.write_manifest(manifest)

    # Get quota hit summary
    quota_hits = writer.get_sources_with_quota_hits(days=7)

    # Verify BBC hit 3 times, Wikipedia 0 times
    assert quota_hits["bbc"] == 3
    assert "wikipedia" not in quota_hits


def test_aggregate_manifests(writer, sample_sources):
    """Verify can aggregate stats across multiple manifests."""
    # Create multiple manifests
    for i in range(5):
        run_id = f"run_aggregate_{i}"
        manifest = writer.create_manifest(run_id, sample_sources)
        writer.write_manifest(manifest)

    # List all manifests
    manifests = writer.list_manifests()

    # Aggregate total records
    total_records = 0
    for manifest_path in manifests:
        manifest = writer.read_manifest(manifest_path.name)
        total_records += manifest["totals"]["total_records"]

    # Each manifest has 1584 records (1234 + 350)
    expected_total = 1584 * 5
    assert total_records == expected_total


def test_filter_manifests_by_date_range(writer, sample_sources):
    """Verify date range filtering works correctly."""
    # Create manifests at different times
    timestamps = [
        datetime.now(timezone.utc) - timedelta(days=10),
        datetime.now(timezone.utc) - timedelta(days=5),
        datetime.now(timezone.utc) - timedelta(days=1),
    ]

    for i, timestamp in enumerate(timestamps):
        run_id = f"run_filter_{i}"
        manifest = writer.create_manifest(run_id, sample_sources, timestamp=timestamp)
        writer.write_manifest(manifest)

    # Filter manifests from last 7 days
    start_date = datetime.now(timezone.utc) - timedelta(days=7)
    filtered_manifests = writer.list_manifests(start_date=start_date)

    # Should return only the last 2 manifests (within 7 days)
    assert len(filtered_manifests) == 2


# =============================================================================
# Additional Helper Tests
# =============================================================================

def test_get_manifest_for_run(writer, sample_sources):
    """Verify get_manifest_for_run retrieves specific manifest."""
    run_id = "run_specific_123"
    manifest = writer.create_manifest(run_id, sample_sources)
    writer.write_manifest(manifest)

    # Retrieve by run_id
    retrieved = writer.get_manifest_for_run(run_id)

    assert retrieved is not None
    assert retrieved["run_id"] == run_id

    # Try non-existent run_id
    non_existent = writer.get_manifest_for_run("run_does_not_exist")
    assert non_existent is None
