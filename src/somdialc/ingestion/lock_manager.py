"""File-based lock management utilities for pipeline runs."""

import logging
import time
from pathlib import Path

from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)


class LockManager:
    """
    Manages file-based locks for pipeline runs.

    Prevents concurrent runs for the same source from interfering with each other.
    """

    def __init__(self, lock_dir: Path = Path(".locks")):
        self.lock_dir = lock_dir
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._active_locks: dict[str, FileLock] = {}

    def get_lock(self, source: str, timeout: int = 30) -> FileLock:
        """Get a file lock for a specific source."""
        return FileLock(self.lock_dir / f"{source}.lock", timeout=timeout)

    def acquire_lock(self, source: str, timeout: int = 30) -> FileLock:
        """Acquire a lock for a source."""
        lock = self.get_lock(source, timeout)
        try:
            lock.acquire(timeout=timeout)
            logger.info(f"Acquired lock for source: {source}")
            self._active_locks[source] = lock
            return lock
        except Timeout as err:
            logger.error(f"Failed to acquire lock for {source} (timeout={timeout}s)")
            logger.error(f"Another run for {source} is likely still active")
            raise RuntimeError(
                f"Cannot start run for {source}: another run is already active. "
                f"If the previous run crashed, manually delete .locks/{source}.lock"
            ) from err

    def release_lock(self, source: str) -> None:
        """Release a lock for a source."""
        if source in self._active_locks:
            lock = self._active_locks[source]
            if lock.is_locked:
                lock.release()
                logger.info(f"Released lock for source: {source}")
            del self._active_locks[source]

    def is_locked(self, source: str) -> bool:
        """Check if a source is currently locked."""
        lock_file = self.lock_dir / f"{source}.lock"
        if not lock_file.exists():
            return False

        lock = FileLock(lock_file, timeout=0)
        try:
            lock.acquire(timeout=0.1)
            lock.release()
            return False
        except Timeout:
            return True

    def cleanup_stale_locks(self, max_age_hours: int = 24) -> None:
        """Remove stale lock files older than max_age_hours."""
        current_time = time.time()
        for lock_file in self.lock_dir.glob("*.lock"):
            file_age_hours = (current_time - lock_file.stat().st_mtime) / 3600
            if file_age_hours > max_age_hours:
                logger.warning(
                    f"Removing stale lock file: {lock_file} (age: {file_age_hours:.1f}h)"
                )
                lock_file.unlink()
