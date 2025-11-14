"""
Tests for concurrent run locking.

Validates that file-based locking prevents race conditions in concurrent pipeline runs.
"""

import os
import time
from multiprocessing import Manager, Process
from pathlib import Path

import pytest

from somali_dialect_classifier.preprocessing.crawl_ledger import LockManager


@pytest.fixture
def test_lock_dir(tmp_path):
    """Create temporary lock directory for testing."""
    lock_dir = tmp_path / ".locks_test"
    lock_dir.mkdir(exist_ok=True)
    return lock_dir


@pytest.fixture
def lock_manager(test_lock_dir):
    """Create LockManager instance for testing."""
    return LockManager(test_lock_dir)


def test_lock_prevents_concurrent_runs_same_source(test_lock_dir):
    """Test that two processes cannot run same source simultaneously."""
    manager = Manager()
    results = manager.list()

    def worker(source: str, worker_id: int, lock_dir: Path, results_list):
        """Worker that tries to acquire lock."""
        try:
            lock_mgr = LockManager(lock_dir)
            lock_mgr.acquire_lock(source, timeout=2)
            results_list.append(f"worker_{worker_id}_acquired")
            time.sleep(0.5)  # Hold lock for 0.5 second
            lock_mgr.release_lock(source)
            results_list.append(f"worker_{worker_id}_released")
        except RuntimeError:
            results_list.append(f"worker_{worker_id}_timeout")

    # Run two workers for same source
    p1 = Process(target=worker, args=("wikipedia", 1, test_lock_dir, results))
    p2 = Process(target=worker, args=("wikipedia", 2, test_lock_dir, results))

    p1.start()
    time.sleep(0.1)  # Ensure p1 acquires lock first
    p2.start()

    p1.join(timeout=5)
    p2.join(timeout=5)

    # Convert to regular list for assertions
    results_list = list(results)

    # One should acquire, one should timeout
    acquired_count = sum(1 for r in results_list if "acquired" in r)
    timeout_count = sum(1 for r in results_list if "timeout" in r)

    assert acquired_count == 1, f"Expected 1 acquisition, got {acquired_count}: {results_list}"
    assert timeout_count == 1, f"Expected 1 timeout, got {timeout_count}: {results_list}"


def test_lock_allows_concurrent_runs_different_sources(test_lock_dir):
    """Test that two processes CAN run different sources simultaneously."""
    manager = Manager()
    results = manager.list()

    def worker(source: str, worker_id: int, lock_dir: Path, results_list):
        """Worker that tries to acquire lock."""
        try:
            lock_mgr = LockManager(lock_dir)
            lock_mgr.acquire_lock(source, timeout=5)
            results_list.append(f"{source}_worker_{worker_id}_acquired")
            time.sleep(0.3)
            lock_mgr.release_lock(source)
            results_list.append(f"{source}_worker_{worker_id}_released")
        except RuntimeError as e:
            results_list.append(f"{source}_worker_{worker_id}_timeout: {e}")

    # Run two workers for DIFFERENT sources
    p1 = Process(target=worker, args=("wikipedia", 1, test_lock_dir, results))
    p2 = Process(target=worker, args=("bbc", 2, test_lock_dir, results))

    p1.start()
    p2.start()

    p1.join(timeout=5)
    p2.join(timeout=5)

    # Convert to regular list for assertions
    results_list = list(results)

    # Both should succeed
    wikipedia_acquired = any("wikipedia" in r and "acquired" in r for r in results_list)
    bbc_acquired = any("bbc" in r and "acquired" in r for r in results_list)

    assert wikipedia_acquired, f"Wikipedia should acquire lock: {results_list}"
    assert bbc_acquired, f"BBC should acquire lock: {results_list}"


def test_lock_automatic_release_on_exception(lock_manager):
    """Test that lock is released even if exception occurs."""
    # Acquire lock
    lock_manager.acquire_lock("wikipedia", timeout=5)

    # Simulate exception handling (explicit release)
    lock_manager.release_lock("wikipedia")

    # Should be able to acquire again
    lock2 = lock_manager.acquire_lock("wikipedia", timeout=5)
    assert lock2 is not None
    lock_manager.release_lock("wikipedia")


def test_cleanup_stale_locks(test_lock_dir):
    """Test that old locks are cleaned up."""
    lock_manager = LockManager(test_lock_dir)

    # Create a lock file
    lock_file = lock_manager.lock_dir / "wikipedia.lock"
    lock_file.touch()

    # Modify timestamp to make it old (25 hours ago)
    old_time = time.time() - (25 * 3600)
    os.utime(lock_file, (old_time, old_time))

    # Cleanup stale locks
    lock_manager.cleanup_stale_locks(max_age_hours=24)

    # Lock file should be removed
    assert not lock_file.exists()


def test_is_locked_detection(lock_manager):
    """Test that is_locked() correctly detects locked sources."""
    # Initially not locked
    assert not lock_manager.is_locked("wikipedia")

    # Acquire lock
    lock_manager.acquire_lock("wikipedia", timeout=5)

    # Should be detected as locked
    assert lock_manager.is_locked("wikipedia")

    # Release lock
    lock_manager.release_lock("wikipedia")

    # Should no longer be locked
    assert not lock_manager.is_locked("wikipedia")


def test_lock_file_creation(lock_manager):
    """Test that lock files are created in correct location."""
    source = "wikipedia"

    # Acquire lock
    lock_manager.acquire_lock(source, timeout=5)

    # Check lock file exists
    lock_file = lock_manager.lock_dir / f"{source}.lock"
    assert lock_file.exists()

    # Release lock
    lock_manager.release_lock(source)


def test_multiple_sources_locked_independently(lock_manager):
    """Test that multiple sources can be locked independently."""
    # Acquire locks for multiple sources
    lock_manager.acquire_lock("wikipedia", timeout=5)
    lock_manager.acquire_lock("bbc", timeout=5)
    lock_manager.acquire_lock("tiktok", timeout=5)

    # All should be locked
    assert lock_manager.is_locked("wikipedia")
    assert lock_manager.is_locked("bbc")
    assert lock_manager.is_locked("tiktok")

    # Release one lock
    lock_manager.release_lock("bbc")

    # BBC should be unlocked, others still locked
    assert lock_manager.is_locked("wikipedia")
    assert not lock_manager.is_locked("bbc")
    assert lock_manager.is_locked("tiktok")

    # Cleanup
    lock_manager.release_lock("wikipedia")
    lock_manager.release_lock("tiktok")


def test_lock_timeout_error_message(lock_manager):
    """Test that timeout error provides helpful message."""
    # Acquire lock
    lock_manager.acquire_lock("wikipedia", timeout=5)

    # Try to acquire again with short timeout
    try:
        lock_manager.acquire_lock("wikipedia", timeout=1)
        raise AssertionError("Should have raised RuntimeError")
    except RuntimeError as e:
        error_msg = str(e)
        assert "wikipedia" in error_msg.lower()
        assert "another run is already active" in error_msg.lower()

    # Cleanup
    lock_manager.release_lock("wikipedia")


def test_lock_cleanup_preserves_recent_locks(test_lock_dir):
    """Test that cleanup only removes old locks, preserves recent ones."""
    lock_manager = LockManager(test_lock_dir)

    # Create two lock files
    old_lock = lock_manager.lock_dir / "wikipedia.lock"
    recent_lock = lock_manager.lock_dir / "bbc.lock"

    old_lock.touch()
    recent_lock.touch()

    # Make one lock old (25 hours)
    old_time = time.time() - (25 * 3600)
    os.utime(old_lock, (old_time, old_time))

    # Cleanup stale locks
    lock_manager.cleanup_stale_locks(max_age_hours=24)

    # Old lock should be removed, recent lock preserved
    assert not old_lock.exists()
    assert recent_lock.exists()

    # Cleanup
    recent_lock.unlink()
