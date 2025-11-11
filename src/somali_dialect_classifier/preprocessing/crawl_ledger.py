"""
Crawl ledger system for persistent state tracking.

Provides an abstract interface for state persistence with SQLite default
implementation and migration path to PostgreSQL.

Features:
- URL state tracking (discovered, fetched, processed, failed, skipped, duplicate)
- HTTP metadata storage (etag, last-modified for conditional requests)
- Deduplication support (text_hash, minhash_signature)
- RSS feed throttling for ethical scraping
- Migration versioning system
- Thread-safe operations
"""

import json
import logging
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)


class CrawlState(Enum):
    """URL processing states."""

    DISCOVERED = "discovered"
    FETCHED = "fetched"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"
    DUPLICATE = "duplicate"


class LockManager:
    """
    Manages file-based locks for pipeline runs.

    Prevents concurrent runs for the same source from interfering with each other.
    Uses file-based locking which is:
    - Free (no external service needed)
    - Cross-process (works across multiple runs)
    - Simple (no Redis, ZooKeeper, etc.)
    - Portable (works on all OS)
    - Industry-standard (used by Git, npm, pip)
    """

    def __init__(self, lock_dir: Path = Path(".locks")):
        """
        Initialize lock manager.

        Args:
            lock_dir: Directory to store lock files (default: .locks/)
        """
        self.lock_dir = lock_dir
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._active_locks: dict[str, FileLock] = {}

    def get_lock(self, source: str, timeout: int = 30) -> FileLock:
        """
        Get a file lock for a specific source.

        Args:
            source: Source identifier (wikipedia, bbc, etc.)
            timeout: Lock timeout in seconds (default: 30)

        Returns:
            FileLock instance
        """
        lock_file = self.lock_dir / f"{source}.lock"
        lock = FileLock(lock_file, timeout=timeout)
        return lock

    def acquire_lock(self, source: str, timeout: int = 30) -> FileLock:
        """
        Acquire a lock for a source.

        Args:
            source: Source identifier
            timeout: Lock timeout in seconds

        Returns:
            Acquired FileLock

        Raises:
            RuntimeError: If lock cannot be acquired within timeout
        """
        lock = self.get_lock(source, timeout)

        try:
            lock.acquire(timeout=timeout)
            logger.info(f"Acquired lock for source: {source}")
            self._active_locks[source] = lock
            return lock
        except Timeout:
            logger.error(f"Failed to acquire lock for {source} (timeout={timeout}s)")
            logger.error(f"Another run for {source} is likely still active")
            raise RuntimeError(
                f"Cannot start run for {source}: another run is already active. "
                f"If the previous run crashed, manually delete .locks/{source}.lock"
            )

    def release_lock(self, source: str):
        """Release a lock for a source."""
        if source in self._active_locks:
            lock = self._active_locks[source]
            if lock.is_locked:
                lock.release()
                logger.info(f"Released lock for source: {source}")
            del self._active_locks[source]

    def is_locked(self, source: str) -> bool:
        """
        Check if a source is currently locked.

        Args:
            source: Source identifier

        Returns:
            True if locked by another process, False otherwise
        """
        lock_file = self.lock_dir / f"{source}.lock"
        if not lock_file.exists():
            return False

        # Try to acquire lock with 0 timeout to test
        lock = FileLock(lock_file, timeout=0)
        try:
            lock.acquire(timeout=0.1)
            lock.release()  # Not locked, release immediately
            return False
        except Timeout:
            return True  # Locked by another process

    def cleanup_stale_locks(self, max_age_hours: int = 24):
        """
        Remove stale lock files older than max_age_hours.

        This is a safety mechanism for crashed runs that didn't release locks.

        Args:
            max_age_hours: Maximum age of lock files in hours (default: 24)
        """
        current_time = time.time()

        for lock_file in self.lock_dir.glob("*.lock"):
            file_age_hours = (current_time - lock_file.stat().st_mtime) / 3600
            if file_age_hours > max_age_hours:
                logger.warning(
                    f"Removing stale lock file: {lock_file} (age: {file_age_hours:.1f}h)"
                )
                lock_file.unlink()


class LedgerBackend(ABC):
    """
    Abstract interface for ledger backends.

    Enables swapping between SQLite and PostgreSQL implementations.
    """

    @abstractmethod
    def initialize_schema(self, schema_version: int = 1) -> None:
        """Initialize database schema."""
        pass

    @abstractmethod
    def upsert_url(
        self,
        url: str,
        source: str,
        state: CrawlState,
        text_hash: Optional[str] = None,
        minhash_signature: Optional[str] = None,
        silver_id: Optional[str] = None,
        http_status: Optional[int] = None,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        content_length: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Insert or update URL record."""
        pass

    @abstractmethod
    def get_url_state(self, url: str) -> Optional[dict[str, Any]]:
        """Get current state for URL."""
        pass

    @abstractmethod
    def get_urls_by_state(
        self, source: str, state: CrawlState, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Get URLs in specific state."""
        pass

    @abstractmethod
    def mark_url_state(
        self, url: str, state: CrawlState, error_message: Optional[str] = None
    ) -> None:
        """Update URL state."""
        pass

    @abstractmethod
    def check_duplicate_by_hash(self, text_hash: str) -> Optional[str]:
        """Check if text hash already exists, return URL if found."""
        pass

    @abstractmethod
    def check_near_duplicate_by_minhash(
        self, minhash_signature: str, threshold: float = 0.85
    ) -> Optional[list[tuple[str, float]]]:
        """Check for near-duplicates using MinHash."""
        pass

    @abstractmethod
    def get_last_rss_fetch(self, feed_url: str) -> Optional[datetime]:
        """Get last RSS feed fetch time."""
        pass

    @abstractmethod
    def record_rss_fetch(self, feed_url: str, items_found: int) -> None:
        """Record RSS feed fetch."""
        pass

    @abstractmethod
    def get_statistics(self, source: Optional[str] = None) -> dict[str, Any]:
        """Get ledger statistics."""
        pass

    @abstractmethod
    def cleanup_old_entries(self, days: int = 30) -> int:
        """Remove entries older than specified days."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""
        pass


class SQLiteLedger(LedgerBackend):
    """
    SQLite implementation of crawl ledger.

    Default implementation for development and small-scale production.
    Thread-safe with connection pooling.
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path, check_same_thread: bool = False):
        """
        Initialize SQLite ledger.

        Args:
            db_path: Path to SQLite database file
            check_same_thread: Allow multi-threaded access
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local storage for connections
        self._local = threading.local()
        self._check_same_thread = check_same_thread

        # Initialize schema
        self.initialize_schema()

    @property
    def connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=self._check_same_thread,
                timeout=60.0,  # 60 second timeout for lock acquisition
                isolation_level=None,  # Autocommit mode for better concurrency
            )
            # Configure for maximum concurrency
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn.execute("PRAGMA journal_mode = WAL")
            # Increase busy timeout to 60 seconds to handle write contention
            self._local.conn.execute("PRAGMA busy_timeout = 60000")
            # Enable synchronous mode for better write performance
            self._local.conn.execute("PRAGMA synchronous = NORMAL")
            # Increase WAL checkpoint threshold for better write batching
            self._local.conn.execute("PRAGMA wal_autocheckpoint = 1000")
            # Return rows as dictionaries
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        conn = self.connection
        # Manually start transaction since we're in autocommit mode
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

    def initialize_schema(self, schema_version: int = 1) -> None:
        """Initialize or migrate database schema."""
        with self.transaction() as conn:
            # Create schema version table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Check current version
            result = conn.execute("SELECT MAX(version) as v FROM schema_version").fetchone()
            current_version = result["v"] if result["v"] is not None else 0

            if current_version < 1:
                self._apply_schema_v1(conn)
                conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (1)")
                logger.info("Applied schema version 1")

    def _apply_schema_v1(self, conn: sqlite3.Connection) -> None:
        """Apply version 1 schema."""
        # Main crawl ledger table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_ledger (
                url TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                discovered_at TIMESTAMP NOT NULL,
                last_fetched_at TIMESTAMP,
                http_status INTEGER,

                -- Deduplication fields (aligned with silver_writer.SCHEMA)
                text_hash TEXT,
                minhash_signature TEXT,

                -- Record linkage
                silver_id TEXT,

                -- State tracking
                state TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,

                -- HTTP metadata for conditional requests
                etag TEXT,
                last_modified TEXT,
                content_length INTEGER,

                -- Generic metadata (JSON)
                metadata TEXT,

                -- Audit fields
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # RSS feed tracking table for ethical scraping
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rss_feeds (
                feed_url TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                last_fetched_at TIMESTAMP,
                items_found INTEGER,
                fetch_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source_state ON crawl_ledger(source, state)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_text_hash ON crawl_ledger(text_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_minhash ON crawl_ledger(minhash_signature)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_silver_id ON crawl_ledger(silver_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_discovered_at ON crawl_ledger(discovered_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON crawl_ledger(updated_at)")

    def upsert_url(
        self,
        url: str,
        source: str,
        state: CrawlState,
        text_hash: Optional[str] = None,
        minhash_signature: Optional[str] = None,
        silver_id: Optional[str] = None,
        http_status: Optional[int] = None,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        content_length: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Insert or update URL record."""
        now = datetime.now(timezone.utc)
        metadata_json = json.dumps(metadata) if metadata else None

        with self.transaction() as conn:
            # Check if URL exists
            existing = conn.execute(
                "SELECT url, retry_count FROM crawl_ledger WHERE url = ?", (url,)
            ).fetchone()

            if existing:
                # Update existing record
                retry_count = existing["retry_count"]
                if state == CrawlState.FAILED:
                    retry_count += 1

                conn.execute(
                    """
                    UPDATE crawl_ledger SET
                        state = ?,
                        text_hash = COALESCE(?, text_hash),
                        minhash_signature = COALESCE(?, minhash_signature),
                        silver_id = COALESCE(?, silver_id),
                        http_status = COALESCE(?, http_status),
                        etag = COALESCE(?, etag),
                        last_modified = COALESCE(?, last_modified),
                        content_length = COALESCE(?, content_length),
                        error_message = ?,
                        retry_count = ?,
                        metadata = COALESCE(?, metadata),
                        last_fetched_at = CASE WHEN ? = 'fetched' THEN ? ELSE last_fetched_at END,
                        updated_at = ?
                    WHERE url = ?
                """,
                    (
                        state.value,
                        text_hash,
                        minhash_signature,
                        silver_id,
                        http_status,
                        etag,
                        last_modified,
                        content_length,
                        error_message,
                        retry_count,
                        metadata_json,
                        state.value,
                        now,
                        now,
                        url,
                    ),
                )
            else:
                # Insert new record
                conn.execute(
                    """
                    INSERT INTO crawl_ledger (
                        url, source, state, discovered_at,
                        text_hash, minhash_signature, silver_id,
                        http_status, etag, last_modified, content_length,
                        error_message, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        url,
                        source,
                        state.value,
                        now,
                        text_hash,
                        minhash_signature,
                        silver_id,
                        http_status,
                        etag,
                        last_modified,
                        content_length,
                        error_message,
                        metadata_json,
                        now,
                        now,
                    ),
                )

    def get_url_state(self, url: str) -> Optional[dict[str, Any]]:
        """Get current state for URL."""
        result = self.connection.execute(
            "SELECT * FROM crawl_ledger WHERE url = ?", (url,)
        ).fetchone()

        if result:
            return dict(result)
        return None

    def get_urls_by_state(
        self, source: str, state: CrawlState, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Get URLs in specific state."""
        query = """
            SELECT * FROM crawl_ledger
            WHERE source = ? AND state = ?
            ORDER BY discovered_at ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        results = self.connection.execute(query, (source, state.value)).fetchall()
        return [dict(row) for row in results]

    def mark_url_state(
        self, url: str, state: CrawlState, error_message: Optional[str] = None
    ) -> None:
        """Update URL state."""
        now = datetime.now(timezone.utc)

        with self.transaction() as conn:
            if state == CrawlState.FAILED:
                conn.execute(
                    """
                    UPDATE crawl_ledger SET
                        state = ?,
                        error_message = ?,
                        retry_count = retry_count + 1,
                        updated_at = ?
                    WHERE url = ?
                """,
                    (state.value, error_message, now, url),
                )
            else:
                conn.execute(
                    """
                    UPDATE crawl_ledger SET
                        state = ?,
                        updated_at = ?
                    WHERE url = ?
                """,
                    (state.value, now, url),
                )

    def check_duplicate_by_hash(self, text_hash: str) -> Optional[str]:
        """Check if text hash already exists, return URL if found."""
        result = self.connection.execute(
            "SELECT url FROM crawl_ledger WHERE text_hash = ? LIMIT 1", (text_hash,)
        ).fetchone()

        return result["url"] if result else None

    def check_near_duplicate_by_minhash(
        self, minhash_signature: str, threshold: float = 0.85
    ) -> Optional[list[tuple[str, float]]]:
        """
        Check for near-duplicates using MinHash.

        Note: This is a placeholder. Actual MinHash similarity requires
        comparing signature components, which will be implemented with
        the datasketch library in dedup.py
        """
        # For now, just do exact match on signature
        # Real implementation would compute Jaccard similarity
        results = self.connection.execute(
            "SELECT url, minhash_signature FROM crawl_ledger WHERE minhash_signature IS NOT NULL"
        ).fetchall()

        similar_urls = []
        for row in results:
            # Placeholder: real implementation would compute similarity
            # For now, just return exact matches
            if row["minhash_signature"] == minhash_signature:
                similar_urls.append((row["url"], 1.0))

        return similar_urls if similar_urls else None

    def get_last_rss_fetch(self, feed_url: str) -> Optional[datetime]:
        """Get last RSS feed fetch time."""
        result = self.connection.execute(
            "SELECT last_fetched_at FROM rss_feeds WHERE feed_url = ?", (feed_url,)
        ).fetchone()

        if result and result["last_fetched_at"]:
            # Parse ISO format timestamp
            return datetime.fromisoformat(result["last_fetched_at"].replace("Z", "+00:00"))
        return None

    def record_rss_fetch(self, feed_url: str, items_found: int) -> None:
        """Record RSS feed fetch."""
        now = datetime.now(timezone.utc)

        with self.transaction() as conn:
            # Upsert RSS feed record
            conn.execute(
                """
                INSERT INTO rss_feeds (feed_url, source, last_fetched_at, items_found, fetch_count)
                VALUES (?, 'bbc', ?, ?, 1)
                ON CONFLICT(feed_url) DO UPDATE SET
                    last_fetched_at = excluded.last_fetched_at,
                    items_found = excluded.items_found,
                    fetch_count = fetch_count + 1
            """,
                (feed_url, now.isoformat(), items_found),
            )

    def should_fetch_rss(self, feed_url: str, min_hours: int = 6) -> bool:
        """Check if enough time has passed since last RSS fetch."""
        last_fetch = self.get_last_rss_fetch(feed_url)

        if not last_fetch:
            return True  # Never fetched

        time_since = datetime.now(timezone.utc) - last_fetch
        return time_since > timedelta(hours=min_hours)

    def get_statistics(self, source: Optional[str] = None) -> dict[str, Any]:
        """Get ledger statistics."""
        stats = {}

        # Total URLs (parameterized query - SECURITY FIX: prevents SQL injection)
        if source:
            result = self.connection.execute(
                "SELECT COUNT(*) as count FROM crawl_ledger WHERE source = ?",
                (source,)
            ).fetchone()
        else:
            result = self.connection.execute(
                "SELECT COUNT(*) as count FROM crawl_ledger"
            ).fetchone()
        stats["total_urls"] = result["count"]

        # URLs by state (parameterized query - SECURITY FIX: prevents SQL injection)
        if source:
            state_query = """
                SELECT state, COUNT(*) as count
                FROM crawl_ledger
                WHERE source = ?
                GROUP BY state
            """
            state_results = self.connection.execute(state_query, (source,))
        else:
            state_query = """
                SELECT state, COUNT(*) as count
                FROM crawl_ledger
                GROUP BY state
            """
            state_results = self.connection.execute(state_query)

        state_counts = {}
        for row in state_results:
            state_counts[row["state"]] = row["count"]
        stats["by_state"] = state_counts

        # Duplicate statistics (parameterized query - SECURITY FIX: prevents SQL injection)
        if source:
            result = self.connection.execute("""
                SELECT
                    COUNT(DISTINCT text_hash) as unique_hashes,
                    COUNT(CASE WHEN text_hash IS NOT NULL THEN 1 END) as total_hashed
                FROM crawl_ledger
                WHERE source = ?
            """, (source,)).fetchone()
        else:
            result = self.connection.execute("""
                SELECT
                    COUNT(DISTINCT text_hash) as unique_hashes,
                    COUNT(CASE WHEN text_hash IS NOT NULL THEN 1 END) as total_hashed
                FROM crawl_ledger
            """).fetchone()

        stats["unique_documents"] = result["unique_hashes"] or 0
        stats["total_hashed"] = result["total_hashed"] or 0

        if stats["total_hashed"] > 0:
            stats["dedup_rate"] = 1 - (stats["unique_documents"] / stats["total_hashed"])
        else:
            stats["dedup_rate"] = 0

        # Error statistics (parameterized query - SECURITY FIX: prevents SQL injection)
        if source:
            result = self.connection.execute("""
                SELECT COUNT(*) as count
                FROM crawl_ledger
                WHERE source = ? AND state = ? AND retry_count >= 3
            """, (source, 'failed')).fetchone()
        else:
            result = self.connection.execute("""
                SELECT COUNT(*) as count
                FROM crawl_ledger
                WHERE state = ? AND retry_count >= 3
            """, ('failed',)).fetchone()
        stats["permanent_failures"] = result["count"]

        # RSS statistics (BBC only)
        if not source or source == "bbc":
            result = self.connection.execute("""
                SELECT
                    COUNT(*) as feed_count,
                    SUM(fetch_count) as total_fetches,
                    AVG(items_found) as avg_items_per_fetch
                FROM rss_feeds
            """).fetchone()

            stats["rss"] = {
                "feed_count": result["feed_count"] or 0,
                "total_fetches": result["total_fetches"] or 0,
                "avg_items_per_fetch": result["avg_items_per_fetch"] or 0,
            }

        return stats

    def cleanup_old_entries(self, days: int = 30) -> int:
        """Remove entries older than specified days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        with self.transaction() as conn:
            # Only cleanup failed entries with high retry count
            result = conn.execute(
                """
                DELETE FROM crawl_ledger
                WHERE state = 'failed'
                AND retry_count >= 3
                AND updated_at < ?
            """,
                (cutoff.isoformat(),),
            )

            return result.rowcount

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "conn"):
            self._local.conn.close()
            delattr(self._local, "conn")


class PostgresLedger(LedgerBackend):
    """
    PostgreSQL implementation of crawl ledger.

    For production deployments at scale.
    Requires psycopg2 or asyncpg.
    """

    def __init__(self, connection_string: str):
        """
        Initialize PostgreSQL ledger.

        Args:
            connection_string: PostgreSQL connection string
        """
        raise NotImplementedError(
            "PostgreSQL backend is a skeleton for future implementation. "
            "Use SQLiteLedger for current production."
        )

    def initialize_schema(self, schema_version: int = 1) -> None:
        """Initialize database schema."""
        # Implementation would be similar to SQLite but with PostgreSQL syntax
        # - Use JSONB for metadata field
        # - Use proper timestamp types
        # - Add partitioning by source/date for scale
        pass

    def upsert_url(self, url: str, source: str, state: CrawlState, **kwargs) -> None:
        """Insert or update URL record."""
        # Use PostgreSQL UPSERT (INSERT ... ON CONFLICT)
        pass

    def get_url_state(self, url: str) -> Optional[dict[str, Any]]:
        """Get current state for URL."""
        pass

    def get_urls_by_state(
        self, source: str, state: CrawlState, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Get URLs in specific state."""
        pass

    def mark_url_state(
        self, url: str, state: CrawlState, error_message: Optional[str] = None
    ) -> None:
        """Update URL state."""
        pass

    def check_duplicate_by_hash(self, text_hash: str) -> Optional[str]:
        """Check if text hash already exists."""
        pass

    def check_near_duplicate_by_minhash(
        self, minhash_signature: str, threshold: float = 0.85
    ) -> Optional[list[tuple[str, float]]]:
        """Check for near-duplicates using MinHash."""
        # Could use PostgreSQL's pg_trgm extension for similarity
        pass

    def get_last_rss_fetch(self, feed_url: str) -> Optional[datetime]:
        """Get last RSS feed fetch time."""
        pass

    def record_rss_fetch(self, feed_url: str, items_found: int) -> None:
        """Record RSS feed fetch."""
        pass

    def get_statistics(self, source: Optional[str] = None) -> dict[str, Any]:
        """Get ledger statistics."""
        pass

    def cleanup_old_entries(self, days: int = 30) -> int:
        """Remove entries older than specified days."""
        pass

    def close(self) -> None:
        """Close database connection."""
        pass


class CrawlLedger:
    """
    High-level crawl ledger interface.

    Wraps backend implementation and provides convenience methods.
    Includes distributed locking to prevent race conditions in concurrent runs.
    """

    def __init__(self, backend: Optional[LedgerBackend] = None, db_path: Optional[Path] = None):
        """
        Initialize crawl ledger.

        Args:
            backend: Backend implementation (None = SQLite default)
            db_path: Path for SQLite database (None = default location)
        """
        if backend:
            self.backend = backend
        else:
            # Default to SQLite
            if db_path is None:
                from ..config import get_config

                config = get_config()
                db_path = config.data.raw_dir.parent / "ledger" / "crawl_ledger.db"

            self.backend = SQLiteLedger(db_path)

        self.logger = logging.getLogger(__name__)
        self.lock_manager = LockManager()

    def discover_url(self, url: str, source: str, metadata: Optional[dict] = None) -> bool:
        """
        Mark URL as discovered.

        Returns:
            True if newly discovered, False if already exists
        """
        existing = self.backend.get_url_state(url)

        if not existing:
            self.backend.upsert_url(
                url=url, source=source, state=CrawlState.DISCOVERED, metadata=metadata
            )
            return True
        return False

    def mark_fetched(
        self,
        url: str,
        http_status: int,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        content_length: Optional[int] = None,
        source: Optional[str] = None,
    ) -> None:
        """Mark URL as successfully fetched with HTTP metadata."""
        self.backend.upsert_url(
            url=url,
            source=source or "",  # Use provided source or empty
            state=CrawlState.FETCHED,
            http_status=http_status,
            etag=etag,
            last_modified=last_modified,
            content_length=content_length,
        )

    def mark_processed(
        self,
        url: str,
        text_hash: str,
        silver_id: str,
        minhash_signature: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        """Mark URL as successfully processed."""
        self.backend.upsert_url(
            url=url,
            source=source or "",  # Use provided source or empty
            state=CrawlState.PROCESSED,
            text_hash=text_hash,
            silver_id=silver_id,
            minhash_signature=minhash_signature,
        )

    def mark_duplicate(self, url: str, original_url: str, source: Optional[str] = None) -> None:
        """Mark URL as duplicate of another URL."""
        self.backend.upsert_url(
            url=url,
            source=source or "",  # Use provided source or empty
            state=CrawlState.DUPLICATE,
            metadata={"original_url": original_url},
        )

    def mark_failed(self, url: str, error: str) -> None:
        """Mark URL as failed with error message."""
        self.backend.mark_url_state(url=url, state=CrawlState.FAILED, error_message=error)

    def is_duplicate(self, text_hash: str) -> Optional[str]:
        """Check if text hash is duplicate, return original URL if found."""
        return self.backend.check_duplicate_by_hash(text_hash)

    def find_near_duplicates(
        self, minhash_signature: str, threshold: float = 0.85
    ) -> Optional[list[tuple[str, float]]]:
        """Find near-duplicate URLs."""
        return self.backend.check_near_duplicate_by_minhash(minhash_signature, threshold)

    def should_fetch_url(self, url: str, force: bool = False) -> bool:
        """
        Check if URL should be fetched.

        Returns False if:
        - Already processed successfully
        - Already marked as duplicate
        - Failed too many times (unless force=True)
        """
        if force:
            return True

        state = self.backend.get_url_state(url)

        if not state:
            return True  # Not in ledger, should fetch

        # Skip if already processed or duplicate
        if state["state"] in ["processed", "duplicate"]:
            return False

        # Skip if failed too many times
        if state["state"] == "failed" and state.get("retry_count", 0) >= 3:
            return False

        return True

    def get_conditional_headers(self, url: str) -> dict[str, str]:
        """Get conditional request headers for URL."""
        state = self.backend.get_url_state(url)
        headers = {}

        if state:
            if state.get("etag"):
                headers["If-None-Match"] = state["etag"]
            if state.get("last_modified"):
                headers["If-Modified-Since"] = state["last_modified"]

        return headers

    def should_fetch_rss(self, feed_url: str, min_hours: int = 6) -> bool:
        """Check if RSS feed should be fetched."""
        if hasattr(self.backend, "should_fetch_rss"):
            return self.backend.should_fetch_rss(feed_url, min_hours)
        return True  # Default to allow if not implemented

    def record_rss_fetch(self, feed_url: str, items_found: int) -> None:
        """Record RSS feed fetch."""
        self.backend.record_rss_fetch(feed_url, items_found)

    def get_pending_urls(self, source: str, limit: int = 100) -> list[str]:
        """Get URLs pending processing."""
        discovered = self.backend.get_urls_by_state(source, CrawlState.DISCOVERED, limit)
        fetched = self.backend.get_urls_by_state(
            source, CrawlState.FETCHED, limit - len(discovered)
        )

        urls = [r["url"] for r in discovered] + [r["url"] for r in fetched]
        return urls

    def get_last_processing_time(self, source: str) -> Optional[datetime]:
        """
        Get timestamp of last successful processing for a source.

        This enables incremental processing by allowing pipelines to filter
        records based on when they were last processed.

        Args:
            source: Source identifier (wikipedia, bbc, etc.)

        Returns:
            datetime of last successful processing, or None if never processed

        Example:
            >>> ledger = CrawlLedger()
            >>> last_time = ledger.get_last_processing_time("wikipedia")
            >>> if last_time:
            ...     # Only process records newer than last_time
            ...     pass
        """
        query = """
            SELECT MAX(updated_at) as last_processing_time
            FROM crawl_ledger
            WHERE source = ? AND state = ?
        """

        result = self.backend.connection.execute(
            query, (source, CrawlState.PROCESSED.value)
        ).fetchone()

        if result and result["last_processing_time"]:
            # Parse ISO format timestamp
            return datetime.fromisoformat(
                result["last_processing_time"].replace("Z", "+00:00")
            )

        return None

    def get_processed_urls(
        self, source: str, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Get all processed URLs for a source.

        Used for incremental processing to identify already-processed resources.

        Args:
            source: Source identifier
            limit: Maximum number of URLs to return (None = all)

        Returns:
            List of URL records with metadata

        Example:
            >>> ledger = CrawlLedger()
            >>> processed = ledger.get_processed_urls("sprakbanken")
            >>> corpus_ids = {extract_corpus_id(r['url']) for r in processed}
        """
        return self.backend.get_urls_by_state(source, CrawlState.PROCESSED, limit)

    def get_statistics(self, source: Optional[str] = None) -> dict[str, Any]:
        """Get ledger statistics."""
        return self.backend.get_statistics(source)

    def cleanup(self, days: int = 30) -> int:
        """Cleanup old failed entries."""
        return self.backend.cleanup_old_entries(days)

    def acquire_source_lock(self, source: str, timeout: int = 30) -> FileLock:
        """
        Acquire exclusive lock for a source before starting pipeline run.

        This prevents concurrent runs of the same source from causing:
        - Duplicate URL processing (waste API costs)
        - Conflicting SQLite writes (database corruption risk)
        - Duplicate file creation (data integrity issues)

        Args:
            source: Source identifier (wikipedia, bbc, tiktok, etc.)
            timeout: Lock timeout in seconds (default: 30)

        Returns:
            FileLock instance (to be used in context manager)

        Raises:
            RuntimeError: If lock cannot be acquired (another run is active)

        Example:
            >>> ledger = CrawlLedger()
            >>> lock = ledger.acquire_source_lock("wikipedia")
            >>> with lock:
            ...     # Run pipeline
            ...     pass
        """
        return self.lock_manager.acquire_lock(source, timeout)

    def release_source_lock(self, source: str):
        """
        Release lock for a source after pipeline run completes.

        Args:
            source: Source identifier
        """
        self.lock_manager.release_lock(source)

    def is_source_locked(self, source: str) -> bool:
        """
        Check if another run is active for this source.

        Args:
            source: Source identifier

        Returns:
            True if source is locked by another process, False otherwise
        """
        return self.lock_manager.is_locked(source)

    def cleanup_stale_locks(self, max_age_hours: int = 24):
        """
        Clean up stale lock files older than max_age_hours.

        Safety mechanism for crashed runs that didn't release locks.

        Args:
            max_age_hours: Maximum age of lock files in hours (default: 24)
        """
        self.lock_manager.cleanup_stale_locks(max_age_hours)

    def close(self) -> None:
        """Close ledger connection."""
        self.backend.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Factory function for getting ledger instance
_ledger_instance = None


def get_ledger(
    backend: Optional[LedgerBackend] = None, db_path: Optional[Path] = None
) -> CrawlLedger:
    """
    Get or create crawl ledger instance (singleton pattern).

    Args:
        backend: Optional backend implementation (None = use default SQLite)
        db_path: Optional database path (None = use default from config)

    Returns:
        CrawlLedger instance
    """
    global _ledger_instance

    if _ledger_instance is None:
        _ledger_instance = CrawlLedger(backend=backend, db_path=db_path)

    return _ledger_instance


def reset_ledger():
    """Reset ledger singleton (useful for testing)."""
    global _ledger_instance
    if _ledger_instance:
        _ledger_instance.close()
    _ledger_instance = None
