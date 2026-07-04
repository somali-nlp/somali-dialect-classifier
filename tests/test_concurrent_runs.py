"""
Tests for concurrent run locking.

Validates that file-based locking prevents race conditions in concurrent pipeline runs.
"""

import os
import time
from multiprocessing import Manager, Process
from pathlib import Path

import pytest

from somdialc.ingestion.crawl_ledger import LockManager


def _holder_worker(
    source: str,
    worker_id: int,
    lock_dir: Path,
    results_list,
    acquired_event,
    release_event,
    acquire_timeout: float = 10.0,
    release_wait_timeout: float = 10.0,
) -> None:
    """Acquire the lock, signal `acquired_event`, then block on `release_event`.

    Deterministic replacement for sleep-based "hold the lock for N seconds"
    synchronization: this worker holds the lock for exactly as long as it
    takes the contending worker to observe the lock is held and record its
    own (expected-to-fail) acquisition attempt, regardless of how slow or
    loaded the runner is.
    """
    try:
        lock_mgr = LockManager(lock_dir)
        lock_mgr.acquire_lock(source, timeout=acquire_timeout)
        results_list.append(f"worker_{worker_id}_acquired")
    except RuntimeError:
        results_list.append(f"worker_{worker_id}_timeout")
        # Unblock the contender even if we unexpectedly failed to acquire,
        # so the test doesn't hang.
        acquired_event.set()
        return

    acquired_event.set()
    # Hold the lock until the contender has made and recorded its attempt.
    release_event.wait(timeout=release_wait_timeout)
    lock_mgr.release_lock(source)
    results_list.append(f"worker_{worker_id}_released")


def _contender_worker(
    source: str,
    worker_id: int,
    lock_dir: Path,
    results_list,
    acquired_event,
    release_event,
    acquired_wait_timeout: float = 10.0,
    acquire_timeout: float = 0.2,
) -> None:
    """Wait for the holder to genuinely hold the lock, then attempt to acquire it.

    The acquisition attempt only happens after `acquired_event` is observed
    set, so this worker's attempt is guaranteed to race against a lock that
    is actually held -- no polling or sleeping is used to approximate that.
    """
    holder_acquired = acquired_event.wait(timeout=acquired_wait_timeout)
    if not holder_acquired:
        results_list.append(f"worker_{worker_id}_holder_never_acquired")
        release_event.set()
        return

    try:
        lock_mgr = LockManager(lock_dir)
        lock_mgr.acquire_lock(source, timeout=acquire_timeout)
        results_list.append(f"worker_{worker_id}_acquired")
        lock_mgr.release_lock(source)
        results_list.append(f"worker_{worker_id}_released")
    except RuntimeError:
        results_list.append(f"worker_{worker_id}_timeout")
    finally:
        # Let the holder release now that our attempt has been recorded.
        release_event.set()


def _different_source_worker(source: str, worker_id: int, lock_dir: Path, results_list) -> None:
    """Worker used by cross-source concurrency tests."""
    try:
        lock_mgr = LockManager(lock_dir)
        lock_mgr.acquire_lock(source, timeout=5)
        results_list.append(f"{source}_worker_{worker_id}_acquired")
        time.sleep(0.3)
        lock_mgr.release_lock(source)
        results_list.append(f"{source}_worker_{worker_id}_released")
    except RuntimeError as err:
        results_list.append(f"{source}_worker_{worker_id}_timeout: {err}")


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
    """Test that two processes cannot run same source simultaneously.

    Overlap between the holder and the contender is enforced with
    multiprocessing Events, not sleeps/polling: the contender only attempts
    its acquisition after observing that the holder has genuinely acquired
    the lock, and the holder only releases after observing that the
    contender has made and recorded its (expected-to-fail) attempt. This is
    deterministic regardless of runner speed/load -- a slow, contended CI
    runner cannot make the two workers run sequentially instead of
    overlapping, which is what previously made this test flaky on macOS
    runners (both workers would legitimately acquire the lock one after the
    other if the pre-p2.start() poll loop timed out before worker 1 had even
    started).
    """
    manager = Manager()
    results = manager.list()
    acquired_event = manager.Event()
    release_event = manager.Event()

    # Worker 1 holds the lock; worker 2 is the contender expected to fail.
    p1 = Process(
        target=_holder_worker,
        args=("wikipedia", 1, test_lock_dir, results, acquired_event, release_event),
    )
    p2 = Process(
        target=_contender_worker,
        args=("wikipedia", 2, test_lock_dir, results, acquired_event, release_event),
    )

    p1.start()
    p2.start()

    p1.join(timeout=15)
    p2.join(timeout=15)

    assert not p1.is_alive(), "Holder process did not terminate (deadlock?)"
    assert not p2.is_alive(), "Contender process did not terminate (deadlock?)"

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

    # Run two workers for DIFFERENT sources
    p1 = Process(target=_different_source_worker, args=("wikipedia", 1, test_lock_dir, results))
    p2 = Process(target=_different_source_worker, args=("bbc", 2, test_lock_dir, results))

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
