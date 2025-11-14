"""
Unit tests for quota enforcement system.

Tests the daily quota tracking functionality including:
- Ledger quota methods (check, increment, mark hit)
- Config quota retrieval
- Processor integration
- Edge cases (resets, concurrency, partial processing)
"""

import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from somali_dialect_classifier.config import get_config, reset_config
from somali_dialect_classifier.preprocessing.crawl_ledger import (
    CrawlLedger,
    SQLiteLedger,
    reset_ledger,
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        yield db_path


@pytest.fixture
def ledger(temp_db):
    """Create test ledger instance."""
    backend = SQLiteLedger(temp_db)
    backend.initialize_schema()
    ledger = CrawlLedger(backend=backend)
    yield ledger
    ledger.close()
    reset_ledger()


@pytest.fixture
def config():
    """Get config instance for testing."""
    reset_config()
    config = get_config()
    yield config
    reset_config()


# =============================================================================
# Ledger Methods Tests (4 tests)
# =============================================================================

def test_check_quota_available_under_limit(ledger):
    """Verify check_quota_available returns True with correct remaining count."""
    # No quota used yet
    has_quota, remaining = ledger.check_quota_available("bbc", quota_limit=350)
    assert has_quota is True
    assert remaining == 350

    # Use 100 quota
    ledger.increment_daily_quota("bbc", count=100, quota_limit=350)
    has_quota, remaining = ledger.check_quota_available("bbc", quota_limit=350)
    assert has_quota is True
    assert remaining == 250


def test_check_quota_available_at_limit(ledger):
    """Verify check_quota_available returns False when quota reached."""
    # Use all quota
    ledger.increment_daily_quota("bbc", count=350, quota_limit=350)

    has_quota, remaining = ledger.check_quota_available("bbc", quota_limit=350)
    assert has_quota is False
    assert remaining == 0


def test_increment_daily_quota_atomic(ledger):
    """Verify atomic increments work correctly."""
    # First increment
    result = ledger.increment_daily_quota("bbc", count=10, quota_limit=350)
    assert result["records_ingested"] == 10
    assert result["quota_limit"] == 350

    # Second increment (should add to existing)
    result = ledger.increment_daily_quota("bbc", count=5, quota_limit=350)
    assert result["records_ingested"] == 15
    assert result["quota_limit"] == 350

    # Verify total
    usage = ledger.get_daily_quota_usage("bbc")
    assert usage["records_ingested"] == 15


def test_mark_quota_hit_records_remaining(ledger):
    """Verify items_remaining tracked correctly when quota hit."""
    # Mark quota hit with 127 items remaining
    ledger.mark_quota_hit("bbc", items_remaining=127, quota_limit=350)

    usage = ledger.get_daily_quota_usage("bbc")
    assert usage["quota_hit"] is True
    assert usage["items_remaining"] == 127
    assert usage["quota_limit"] == 350


# =============================================================================
# Config Methods Tests (2 tests)
# =============================================================================

def test_get_quota_returns_correct_limits(config):
    """Verify get_quota returns correct limits for each source."""
    assert config.orchestration.get_quota("bbc") == 350
    assert config.orchestration.get_quota("huggingface") == 10000
    assert config.orchestration.get_quota("sprakbanken") == 10


def test_get_quota_returns_none_for_unlimited(config):
    """Verify get_quota returns None for unlimited sources."""
    assert config.orchestration.get_quota("wikipedia") is None
    assert config.orchestration.get_quota("tiktok") is None


# =============================================================================
# Processor Integration Tests (4 tests)
# =============================================================================

def test_bbc_enforces_quota_350(ledger):
    """Verify BBC processor respects quota of 350 articles."""
    quota_limit = 350

    # Simulate processing 350 articles
    for _i in range(350):
        ledger.increment_daily_quota("bbc", count=1, quota_limit=quota_limit)

    # Check quota is exhausted
    has_quota, remaining = ledger.check_quota_available("bbc", quota_limit)
    assert has_quota is False
    assert remaining == 0

    # Verify usage
    usage = ledger.get_daily_quota_usage("bbc")
    assert usage["records_ingested"] == 350


def test_huggingface_enforces_quota_10000(ledger):
    """Verify HuggingFace processor respects quota of 10,000 records."""
    quota_limit = 10000

    # Simulate processing 10,000 records
    ledger.increment_daily_quota("huggingface", count=10000, quota_limit=quota_limit)

    # Check quota is exhausted
    has_quota, remaining = ledger.check_quota_available("huggingface", quota_limit)
    assert has_quota is False
    assert remaining == 0


def test_sprakbanken_enforces_quota_10(ledger):
    """Verify Språkbanken processor respects quota of 10 corpora."""
    quota_limit = 10

    # Simulate processing 10 corpora
    for _i in range(10):
        ledger.increment_daily_quota("sprakbanken", count=1, quota_limit=quota_limit)

    # Check quota is exhausted
    has_quota, remaining = ledger.check_quota_available("sprakbanken", quota_limit)
    assert has_quota is False
    assert remaining == 0


def test_wikipedia_unlimited_no_quota(ledger):
    """Verify Wikipedia processes without quota limits."""
    # Wikipedia should return unlimited (True, -1)
    has_quota, remaining = ledger.check_quota_available("wikipedia", quota_limit=None)
    assert has_quota is True
    assert remaining == -1  # -1 indicates unlimited


# =============================================================================
# Edge Cases Tests (5 tests)
# =============================================================================

def test_quota_resets_daily(ledger):
    """Verify quota resets on new day."""
    quota_limit = 350
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")

    # Use quota today
    ledger.increment_daily_quota("bbc", count=350, quota_limit=quota_limit, date=today)
    has_quota_today, remaining_today = ledger.check_quota_available("bbc", quota_limit, date=today)
    assert has_quota_today is False

    # Check tomorrow's quota (should be fresh)
    has_quota_tomorrow, remaining_tomorrow = ledger.check_quota_available("bbc", quota_limit, date=tomorrow)
    assert has_quota_tomorrow is True
    assert remaining_tomorrow == quota_limit


def test_quota_tracking_across_runs(ledger):
    """Verify quota persists across runs same day."""
    quota_limit = 350

    # First run: process 100
    ledger.increment_daily_quota("bbc", count=100, quota_limit=quota_limit)

    # Second run: process 100 more
    ledger.increment_daily_quota("bbc", count=100, quota_limit=quota_limit)

    # Verify total is 200
    usage = ledger.get_daily_quota_usage("bbc")
    assert usage["records_ingested"] == 200

    # Third run: try to process 200 more (should hit quota at 350)
    has_quota, remaining = ledger.check_quota_available("bbc", quota_limit)
    assert has_quota is True
    assert remaining == 150  # Only 150 left, not 200


def test_concurrent_quota_increments(ledger):
    """Verify thread safety of quota operations."""
    quota_limit = 1000
    num_threads = 10
    increments_per_thread = 10

    def increment_quota():
        for _ in range(increments_per_thread):
            ledger.increment_daily_quota("bbc", count=1, quota_limit=quota_limit)

    # Run concurrent increments
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=increment_quota)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    # Verify total is correct (no race conditions)
    usage = ledger.get_daily_quota_usage("bbc")
    expected_total = num_threads * increments_per_thread
    assert usage["records_ingested"] == expected_total


def test_quota_hit_multiple_times_same_day(ledger):
    """Verify subsequent runs on same day respect quota hit."""
    quota_limit = 350

    # First run: hit quota
    ledger.increment_daily_quota("bbc", count=350, quota_limit=quota_limit)
    ledger.mark_quota_hit("bbc", items_remaining=100, quota_limit=quota_limit)

    # Second run: check quota (should still be hit)
    has_quota, remaining = ledger.check_quota_available("bbc", quota_limit)
    assert has_quota is False
    assert remaining == 0

    # Verify quota hit flag persists
    usage = ledger.get_daily_quota_usage("bbc")
    assert usage["quota_hit"] is True
    assert usage["items_remaining"] == 100


def test_quota_with_partial_processing(ledger):
    """Verify correct handling of partial batches when quota reached."""
    quota_limit = 350
    total_items = 500

    # Process up to quota
    for _i in range(quota_limit):
        ledger.increment_daily_quota("bbc", count=1, quota_limit=quota_limit)

    # Mark quota hit with remaining items
    items_remaining = total_items - quota_limit
    ledger.mark_quota_hit("bbc", items_remaining=items_remaining, quota_limit=quota_limit)

    # Verify quota status
    usage = ledger.get_daily_quota_usage("bbc")
    assert usage["records_ingested"] == quota_limit
    assert usage["quota_hit"] is True
    assert usage["items_remaining"] == items_remaining

    # Verify no more processing allowed
    has_quota, remaining = ledger.check_quota_available("bbc", quota_limit)
    assert has_quota is False
    assert remaining == 0
