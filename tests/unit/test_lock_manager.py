"""Unit tests for somdialc.ingestion.lock_manager.LockManager.

Uses real FileLock objects against a tmp_path lock directory (no mocking) so
these tests exercise genuine filesystem-lock semantics.
"""

import time

import pytest

from somdialc.ingestion.lock_manager import LockManager


class TestLockManagerBasics:
    def test_init_creates_lock_dir(self, tmp_path):
        lock_dir = tmp_path / "locks"
        assert not lock_dir.exists()

        LockManager(lock_dir=lock_dir)

        assert lock_dir.exists()

    def test_get_lock_returns_filelock_for_source(self, tmp_path):
        manager = LockManager(lock_dir=tmp_path / "locks")
        lock = manager.get_lock("wikipedia")
        assert str(lock.lock_file).endswith("wikipedia.lock")

    def test_is_locked_false_when_no_lock_file(self, tmp_path):
        manager = LockManager(lock_dir=tmp_path / "locks")
        assert manager.is_locked("wikipedia") is False


class TestLockManagerAcquireRelease:
    def test_acquire_then_release_round_trip(self, tmp_path):
        manager = LockManager(lock_dir=tmp_path / "locks")

        lock = manager.acquire_lock("bbc", timeout=5)
        assert lock.is_locked

        manager.release_lock("bbc")
        assert not lock.is_locked

    def test_release_lock_is_noop_for_unknown_source(self, tmp_path):
        manager = LockManager(lock_dir=tmp_path / "locks")
        # Should not raise even though "ghost" was never acquired.
        manager.release_lock("ghost")

    def test_is_locked_true_while_held_by_another_manager(self, tmp_path):
        lock_dir = tmp_path / "locks"
        holder = LockManager(lock_dir=lock_dir)
        holder.acquire_lock("sprakbanken", timeout=5)

        checker = LockManager(lock_dir=lock_dir)
        assert checker.is_locked("sprakbanken") is True

        holder.release_lock("sprakbanken")
        assert checker.is_locked("sprakbanken") is False

    def test_acquire_lock_raises_runtime_error_on_timeout(self, tmp_path):
        lock_dir = tmp_path / "locks"
        holder = LockManager(lock_dir=lock_dir)
        holder.acquire_lock("tiktok", timeout=5)

        contender = LockManager(lock_dir=lock_dir)
        with pytest.raises(RuntimeError, match="another run is already active"):
            contender.acquire_lock("tiktok", timeout=0.2)

        holder.release_lock("tiktok")


class TestLockManagerCleanup:
    def test_cleanup_stale_locks_removes_old_files(self, tmp_path):
        lock_dir = tmp_path / "locks"
        manager = LockManager(lock_dir=lock_dir)

        stale_file = lock_dir / "old-source.lock"
        stale_file.write_text("")
        # Backdate the file's mtime well past the cleanup threshold.
        old_time = time.time() - (48 * 3600)
        import os

        os.utime(stale_file, (old_time, old_time))

        manager.cleanup_stale_locks(max_age_hours=24)

        assert not stale_file.exists()

    def test_cleanup_stale_locks_keeps_recent_files(self, tmp_path):
        lock_dir = tmp_path / "locks"
        manager = LockManager(lock_dir=lock_dir)

        fresh_file = lock_dir / "fresh-source.lock"
        fresh_file.write_text("")

        manager.cleanup_stale_locks(max_age_hours=24)

        assert fresh_file.exists()
