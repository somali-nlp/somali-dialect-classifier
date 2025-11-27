"""Tests for pipeline run tracking in crawl ledger."""
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from somali_dialect_classifier.ingestion.crawl_ledger import CrawlLedger, SQLiteLedger


@pytest.fixture
def temp_ledger():
    """Create temporary in-memory SQLite ledger for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        backend = SQLiteLedger(db_path)
        ledger = CrawlLedger(backend=backend)
        yield ledger
        ledger.close()


class TestPipelineRunRegistration:
    """Test registering and retrieving pipeline runs."""

    def test_register_pipeline_run(self, temp_ledger):
        """Test registering a new pipeline run."""
        run_id = "test_run_001"
        source = "wikipedia"
        pipeline_type = "web"
        config = {"quota": 1000, "max_pages": 500}
        git_commit = "abc123def456"

        temp_ledger.register_pipeline_run(
            run_id=run_id,
            source=source,
            pipeline_type=pipeline_type,
            config=config,
            git_commit=git_commit,
        )

        # Verify run was registered
        run = temp_ledger.get_pipeline_run(run_id)
        assert run is not None
        assert run["run_id"] == run_id
        assert run["source"] == source
        assert run["pipeline_type"] == pipeline_type
        assert run["status"] == "STARTED"
        assert run["git_commit"] == git_commit
        assert '"quota": 1000' in run["config_snapshot"]
        assert run["records_discovered"] == 0
        assert run["records_processed"] == 0
        assert run["records_failed"] == 0

    def test_register_pipeline_run_minimal(self, temp_ledger):
        """Test registering pipeline run with minimal information."""
        run_id = "test_run_minimal"
        source = "bbc"
        pipeline_type = "web"

        temp_ledger.register_pipeline_run(
            run_id=run_id, source=source, pipeline_type=pipeline_type
        )

        run = temp_ledger.get_pipeline_run(run_id)
        assert run is not None
        assert run["run_id"] == run_id
        assert run["source"] == source
        assert run["status"] == "STARTED"
        assert run["config_snapshot"] is None
        assert run["git_commit"] is None


class TestPipelineRunUpdates:
    """Test updating pipeline run status and metrics."""

    def test_update_pipeline_run_status(self, temp_ledger):
        """Test updating run status progression."""
        run_id = "test_run_status"
        temp_ledger.register_pipeline_run(
            run_id=run_id, source="wikipedia", pipeline_type="web"
        )

        # Update to RUNNING
        temp_ledger.update_pipeline_run(run_id=run_id, status="RUNNING")
        run = temp_ledger.get_pipeline_run(run_id)
        assert run["status"] == "RUNNING"

        # Update to COMPLETED
        temp_ledger.update_pipeline_run(run_id=run_id, status="COMPLETED")
        run = temp_ledger.get_pipeline_run(run_id)
        assert run["status"] == "COMPLETED"

    def test_update_pipeline_run_metrics(self, temp_ledger):
        """Test updating run metrics."""
        run_id = "test_run_metrics"
        temp_ledger.register_pipeline_run(
            run_id=run_id, source="wikipedia", pipeline_type="web"
        )

        # Update with discovery metrics
        temp_ledger.update_pipeline_run(
            run_id=run_id, status="RUNNING", records_discovered=100
        )
        run = temp_ledger.get_pipeline_run(run_id)
        assert run["records_discovered"] == 100

        # Update with processing metrics
        temp_ledger.update_pipeline_run(
            run_id=run_id,
            status="COMPLETED",
            records_processed=95,
            records_failed=5,
            end_time=datetime.now(timezone.utc),
        )
        run = temp_ledger.get_pipeline_run(run_id)
        assert run["status"] == "COMPLETED"
        assert run["records_processed"] == 95
        assert run["records_failed"] == 5
        assert run["end_time"] is not None

    def test_update_pipeline_run_with_error(self, temp_ledger):
        """Test updating run with error information."""
        run_id = "test_run_error"
        temp_ledger.register_pipeline_run(
            run_id=run_id, source="bbc", pipeline_type="web"
        )

        error_msg = "Connection timeout while fetching RSS feed"
        temp_ledger.update_pipeline_run(
            run_id=run_id,
            status="FAILED",
            errors=error_msg,
            end_time=datetime.now(timezone.utc),
        )

        run = temp_ledger.get_pipeline_run(run_id)
        assert run["status"] == "FAILED"
        assert run["errors"] == error_msg
        assert run["end_time"] is not None

    def test_update_pipeline_run_partial_fields(self, temp_ledger):
        """Test updating only specific fields without affecting others."""
        run_id = "test_run_partial"
        temp_ledger.register_pipeline_run(
            run_id=run_id, source="wikipedia", pipeline_type="web"
        )

        # Update only records_discovered
        temp_ledger.update_pipeline_run(run_id=run_id, records_discovered=50)
        run = temp_ledger.get_pipeline_run(run_id)
        assert run["records_discovered"] == 50
        assert run["status"] == "STARTED"  # Status unchanged
        assert run["records_processed"] == 0  # Other fields unchanged

        # Update only status
        temp_ledger.update_pipeline_run(run_id=run_id, status="RUNNING")
        run = temp_ledger.get_pipeline_run(run_id)
        assert run["status"] == "RUNNING"
        assert run["records_discovered"] == 50  # Previous value preserved


class TestLastSuccessfulRun:
    """Test getting last successful run for scheduling."""

    def test_get_last_successful_run(self, temp_ledger):
        """Test getting last successful run for a source."""
        source = "wikipedia"

        # Create multiple runs with different statuses and times
        now = datetime.now(timezone.utc)

        # Run 1: Completed 3 days ago
        temp_ledger.register_pipeline_run("run_1", source, "web")
        temp_ledger.update_pipeline_run(
            "run_1", status="COMPLETED", end_time=now - timedelta(days=3)
        )

        # Run 2: Failed 2 days ago (should be ignored)
        temp_ledger.register_pipeline_run("run_2", source, "web")
        temp_ledger.update_pipeline_run(
            "run_2", status="FAILED", end_time=now - timedelta(days=2)
        )

        # Run 3: Completed 1 day ago (most recent successful)
        temp_ledger.register_pipeline_run("run_3", source, "web")
        temp_ledger.update_pipeline_run(
            "run_3", status="COMPLETED", end_time=now - timedelta(days=1)
        )

        # Run 4: Currently running (should be ignored)
        temp_ledger.register_pipeline_run("run_4", source, "web")
        temp_ledger.update_pipeline_run("run_4", status="RUNNING")

        # Should return end_time of run_3
        last_run = temp_ledger.get_last_successful_run(source)
        assert last_run is not None

        # Verify it's approximately 1 day ago (with some tolerance for test execution time)
        days_ago = (now - last_run).total_seconds() / 86400
        assert 0.99 < days_ago < 1.01

    def test_get_last_successful_run_never_run(self, temp_ledger):
        """Test get_last_successful_run when source never run successfully."""
        # Source that never ran
        last_run = temp_ledger.get_last_successful_run("nonexistent")
        assert last_run is None

        # Source with only failed runs
        temp_ledger.register_pipeline_run("failed_run", "bbc", "web")
        temp_ledger.update_pipeline_run(
            "failed_run", status="FAILED", end_time=datetime.now(timezone.utc)
        )
        last_run = temp_ledger.get_last_successful_run("bbc")
        assert last_run is None

    def test_get_last_successful_run_different_sources(self, temp_ledger):
        """Test that last run is source-specific."""
        now = datetime.now(timezone.utc)

        # Wikipedia completed 2 days ago
        temp_ledger.register_pipeline_run("wiki_run", "wikipedia", "web")
        temp_ledger.update_pipeline_run(
            "wiki_run", status="COMPLETED", end_time=now - timedelta(days=2)
        )

        # BBC completed 1 day ago
        temp_ledger.register_pipeline_run("bbc_run", "bbc", "web")
        temp_ledger.update_pipeline_run(
            "bbc_run", status="COMPLETED", end_time=now - timedelta(days=1)
        )

        wiki_last = temp_ledger.get_last_successful_run("wikipedia")
        bbc_last = temp_ledger.get_last_successful_run("bbc")

        assert wiki_last is not None
        assert bbc_last is not None

        # Wikipedia should be ~2 days ago
        wiki_days = (now - wiki_last).total_seconds() / 86400
        assert 1.99 < wiki_days < 2.01

        # BBC should be ~1 day ago
        bbc_days = (now - bbc_last).total_seconds() / 86400
        assert 0.99 < bbc_days < 1.01


class TestFirstSuccessfulRun:
    """Test getting first successful run for initial collection detection."""

    def test_get_first_successful_run(self, temp_ledger):
        """Test getting first successful run for a source."""
        source = "wikipedia"
        now = datetime.now(timezone.utc)

        # Run 1: Completed 5 days ago (first successful)
        temp_ledger.register_pipeline_run("run_1", source, "web")
        temp_ledger.update_pipeline_run(
            "run_1", status="COMPLETED", end_time=now - timedelta(days=5)
        )

        # Run 2: Failed 4 days ago (should be ignored)
        temp_ledger.register_pipeline_run("run_2", source, "web")
        temp_ledger.update_pipeline_run(
            "run_2", status="FAILED", end_time=now - timedelta(days=4)
        )

        # Run 3: Completed 3 days ago (later success)
        temp_ledger.register_pipeline_run("run_3", source, "web")
        temp_ledger.update_pipeline_run(
            "run_3", status="COMPLETED", end_time=now - timedelta(days=3)
        )

        # Should return end_time of run_1
        first_run = temp_ledger.get_first_successful_run(source)
        assert first_run is not None

        days_ago = (now - first_run).total_seconds() / 86400
        assert 4.99 < days_ago < 5.01

    def test_get_first_successful_run_never_run(self, temp_ledger):
        """Test get_first_successful_run when source never run."""
        first_run = temp_ledger.get_first_successful_run("nonexistent")
        assert first_run is None


class TestPipelineRunsHistory:
    """Test retrieving pipeline run history."""

    def test_get_pipeline_runs_history(self, temp_ledger):
        """Test retrieving recent pipeline runs for a source."""
        source = "wikipedia"

        # Create 15 runs
        for i in range(15):
            run_id = f"run_{i:03d}"
            temp_ledger.register_pipeline_run(run_id, source, "web")
            time.sleep(0.01)  # Ensure different start times

        # Get last 10 runs
        history = temp_ledger.get_pipeline_runs_history(source, limit=10)

        assert len(history) == 10

        # Verify sorted by start_time DESC (most recent first)
        run_ids = [run["run_id"] for run in history]
        assert run_ids[0] == "run_014"  # Most recent
        assert run_ids[-1] == "run_005"  # 10th most recent

    def test_get_pipeline_runs_history_source_specific(self, temp_ledger):
        """Test that history is source-specific."""
        # Create runs for different sources
        for i in range(5):
            temp_ledger.register_pipeline_run(f"wiki_{i}", "wikipedia", "web")
            temp_ledger.register_pipeline_run(f"bbc_{i}", "bbc", "web")

        wiki_history = temp_ledger.get_pipeline_runs_history("wikipedia", limit=10)
        bbc_history = temp_ledger.get_pipeline_runs_history("bbc", limit=10)

        assert len(wiki_history) == 5
        assert len(bbc_history) == 5

        # Verify all wiki runs have source="wikipedia"
        assert all(run["source"] == "wikipedia" for run in wiki_history)

        # Verify all bbc runs have source="bbc"
        assert all(run["source"] == "bbc" for run in bbc_history)

    def test_get_pipeline_runs_history_empty(self, temp_ledger):
        """Test getting history for source with no runs."""
        history = temp_ledger.get_pipeline_runs_history("nonexistent", limit=10)
        assert len(history) == 0


class TestConcurrentRunUpdates:
    """Test thread-safe updates to pipeline runs."""

    def test_concurrent_run_updates(self, temp_ledger):
        """Test thread-safe updates to same run from multiple threads."""
        run_id = "concurrent_run"
        temp_ledger.register_pipeline_run(run_id, "wikipedia", "web")

        def update_discovered():
            for _ in range(10):
                run = temp_ledger.get_pipeline_run(run_id)
                current = run["records_discovered"] if run else 0
                temp_ledger.update_pipeline_run(
                    run_id, records_discovered=current + 1
                )
                time.sleep(0.001)

        def update_processed():
            for _ in range(10):
                run = temp_ledger.get_pipeline_run(run_id)
                current = run["records_processed"] if run else 0
                temp_ledger.update_pipeline_run(run_id, records_processed=current + 1)
                time.sleep(0.001)

        # Run updates concurrently
        thread1 = threading.Thread(target=update_discovered)
        thread2 = threading.Thread(target=update_processed)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Verify updates were applied (note: exact counts may vary due to race conditions)
        run = temp_ledger.get_pipeline_run(run_id)
        assert run["records_discovered"] > 0
        assert run["records_processed"] > 0


class TestPipelineRunRetrieval:
    """Test retrieving individual pipeline runs."""

    def test_get_pipeline_run_exists(self, temp_ledger):
        """Test retrieving an existing pipeline run."""
        run_id = "test_retrieve"
        temp_ledger.register_pipeline_run(
            run_id=run_id, source="wikipedia", pipeline_type="web", config={"test": True}
        )

        run = temp_ledger.get_pipeline_run(run_id)
        assert run is not None
        assert run["run_id"] == run_id
        assert run["source"] == "wikipedia"

    def test_get_pipeline_run_not_exists(self, temp_ledger):
        """Test retrieving non-existent pipeline run."""
        run = temp_ledger.get_pipeline_run("nonexistent_run")
        assert run is None


class TestSchedulingIntegration:
    """Test integration with scheduling logic."""

    def test_initial_collection_detection(self, temp_ledger):
        """Test that scheduler can detect if in initial collection phase."""
        sources = ["wikipedia", "bbc", "huggingface", "sprakbanken"]
        now = datetime.now(timezone.utc)

        # Scenario 1: No runs yet - should be in initial collection
        for source in sources:
            assert temp_ledger.get_first_successful_run(source) is None

        # Scenario 2: All sources have runs within 6 days - still initial collection
        for source in sources:
            temp_ledger.register_pipeline_run(f"{source}_run", source, "web")
            temp_ledger.update_pipeline_run(
                f"{source}_run", status="COMPLETED", end_time=now - timedelta(days=2)
            )

        # All should have first runs ~2 days ago
        first_runs = [temp_ledger.get_first_successful_run(s) for s in sources]
        assert all(run is not None for run in first_runs)

        # Scenario 3: Oldest run is 7+ days ago - moved to refresh phase
        temp_ledger.register_pipeline_run("old_run", "wikipedia", "web")
        temp_ledger.update_pipeline_run(
            "old_run", status="COMPLETED", end_time=now - timedelta(days=8)
        )

        # Wikipedia's first run should now be 8 days ago
        wiki_first = temp_ledger.get_first_successful_run("wikipedia")
        days_ago = (now - wiki_first).total_seconds() / 86400
        assert days_ago > 7

    def test_cadence_scheduling(self, temp_ledger):
        """Test that scheduler can determine if source should run based on cadence."""
        source = "wikipedia"
        now = datetime.now(timezone.utc)
        cadence_days = 7  # Wikipedia runs every 7 days

        # Last run was 8 days ago - should run
        temp_ledger.register_pipeline_run("run_1", source, "web")
        temp_ledger.update_pipeline_run(
            "run_1", status="COMPLETED", end_time=now - timedelta(days=8)
        )

        last_run = temp_ledger.get_last_successful_run(source)
        days_since = (now - last_run).total_seconds() / 86400
        should_run = days_since >= cadence_days
        assert should_run is True

        # Last run was 5 days ago - should NOT run
        temp_ledger.register_pipeline_run("run_2", source, "web")
        temp_ledger.update_pipeline_run(
            "run_2", status="COMPLETED", end_time=now - timedelta(days=5)
        )

        last_run = temp_ledger.get_last_successful_run(source)
        days_since = (now - last_run).total_seconds() / 86400
        should_run = days_since >= cadence_days
        assert should_run is False
