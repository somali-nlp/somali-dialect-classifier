"""
PostgreSQL backend for CrawlLedger.

Provides scalable, concurrent-write capable ledger with row-level locking
and connection pooling for production deployments.

Features:
- Connection pooling (ThreadedConnectionPool)
- Row-level locking for concurrent writes
- Proper indexes for query performance
- JSONB support for metadata
- Backward compatible with SQLiteLedger API
- Automatic schema initialization
- Transaction support with rollback
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from ..preprocessing.crawl_ledger import CrawlState, LedgerBackend

logger = logging.getLogger(__name__)


class PostgresLedger(LedgerBackend):
    """
    PostgreSQL-backed ledger with connection pooling and row-level locking.

    Designed for production scale with:
    - 10x concurrent writes without deadlocks
    - Row-level locking (no table-level locks like SQLite)
    - Connection pooling (2-10 connections)
    - < 100ms query latency (p95)
    - ACID transactions with proper isolation
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "somali_nlp",
        user: str = "somali",
        password: str = "somali_dev_password",
        min_connections: int = 2,
        max_connections: int = 10,
    ):
        """
        Initialize PostgreSQL ledger with connection pooling.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
        """
        self.connection_string = (
            f"host={host} port={port} dbname={database} user={user} password={password}"
        )

        # Create connection pool
        try:
            self.pool = ThreadedConnectionPool(
                min_connections, max_connections, self.connection_string
            )
            logger.info(
                f"PostgreSQL connection pool created ({min_connections}-{max_connections} connections)"
            )
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

        # Initialize schema
        self.initialize_schema()

    @contextmanager
    def _get_connection(self):
        """Get connection from pool with automatic return."""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    @contextmanager
    def transaction(self):
        """Context manager for database transactions with rollback support."""
        with self._get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed, rolled back: {e}")
                raise

    def initialize_schema(self, schema_version: int = 1) -> None:
        """
        Initialize or migrate database schema.

        This method is idempotent - safe to run multiple times.
        """
        schema_sql = """
        -- Schema version table
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- URLs table
        CREATE TABLE IF NOT EXISTS crawl_ledger (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            discovered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            last_fetched_at TIMESTAMP WITH TIME ZONE,
            http_status INTEGER,

            -- Deduplication fields
            text_hash TEXT,
            minhash_signature TEXT,

            -- Record linkage
            silver_id TEXT,

            -- State tracking
            state TEXT NOT NULL,
            retry_count INTEGER DEFAULT 0,
            error_message TEXT,

            -- HTTP metadata
            etag TEXT,
            last_modified TEXT,
            content_length INTEGER,

            -- Generic metadata (JSONB)
            metadata JSONB,

            -- Audit fields
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Performance indexes
        CREATE INDEX IF NOT EXISTS idx_crawl_ledger_source ON crawl_ledger(source);
        CREATE INDEX IF NOT EXISTS idx_crawl_ledger_state ON crawl_ledger(state);
        CREATE INDEX IF NOT EXISTS idx_crawl_ledger_source_state ON crawl_ledger(source, state);
        CREATE INDEX IF NOT EXISTS idx_crawl_ledger_text_hash ON crawl_ledger(text_hash) WHERE text_hash IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_crawl_ledger_minhash ON crawl_ledger(minhash_signature) WHERE minhash_signature IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_crawl_ledger_silver_id ON crawl_ledger(silver_id) WHERE silver_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_crawl_ledger_discovered_at ON crawl_ledger(discovered_at);
        CREATE INDEX IF NOT EXISTS idx_crawl_ledger_updated_at ON crawl_ledger(updated_at);
        CREATE INDEX IF NOT EXISTS idx_crawl_ledger_metadata ON crawl_ledger USING GIN (metadata);

        -- RSS feeds table
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id SERIAL PRIMARY KEY,
            feed_url TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            last_fetched_at TIMESTAMP WITH TIME ZONE,
            items_found INTEGER,
            fetch_count INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_rss_feeds_source ON rss_feeds(source);
        CREATE INDEX IF NOT EXISTS idx_rss_feeds_last_fetched ON rss_feeds(last_fetched_at);

        -- Mark schema as initialized
        INSERT INTO schema_version (version) VALUES (1)
        ON CONFLICT (version) DO NOTHING;
        """

        try:
            with self.transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(schema_sql)
            logger.info("PostgreSQL schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

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
        """
        Insert or update URL record using PostgreSQL UPSERT.

        Uses INSERT ... ON CONFLICT for atomic upsert operation.
        Row-level locking ensures no deadlocks during concurrent writes.
        """
        now = datetime.now(timezone.utc)

        # Use PostgreSQL's INSERT ... ON CONFLICT for atomic upsert
        query = """
            INSERT INTO crawl_ledger (
                url, source, state, discovered_at,
                text_hash, minhash_signature, silver_id,
                http_status, etag, last_modified, content_length,
                error_message, metadata, created_at, updated_at,
                last_fetched_at, retry_count
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                CASE WHEN %s = 'fetched' THEN %s ELSE NULL END,
                0
            )
            ON CONFLICT (url) DO UPDATE SET
                state = EXCLUDED.state,
                text_hash = COALESCE(EXCLUDED.text_hash, crawl_ledger.text_hash),
                minhash_signature = COALESCE(EXCLUDED.minhash_signature, crawl_ledger.minhash_signature),
                silver_id = COALESCE(EXCLUDED.silver_id, crawl_ledger.silver_id),
                http_status = COALESCE(EXCLUDED.http_status, crawl_ledger.http_status),
                etag = COALESCE(EXCLUDED.etag, crawl_ledger.etag),
                last_modified = COALESCE(EXCLUDED.last_modified, crawl_ledger.last_modified),
                content_length = COALESCE(EXCLUDED.content_length, crawl_ledger.content_length),
                error_message = EXCLUDED.error_message,
                metadata = COALESCE(EXCLUDED.metadata, crawl_ledger.metadata),
                last_fetched_at = CASE WHEN EXCLUDED.state = 'fetched' THEN %s ELSE crawl_ledger.last_fetched_at END,
                retry_count = CASE WHEN EXCLUDED.state = 'failed' THEN crawl_ledger.retry_count + 1 ELSE crawl_ledger.retry_count END,
                updated_at = %s
        """

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
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
                        Json(metadata) if metadata else None,
                        now,
                        now,
                        state.value,
                        now,
                        now,
                        now,
                    ),
                )

    def get_url_state(self, url: str) -> Optional[dict[str, Any]]:
        """Get current state for URL."""
        query = """
            SELECT id, url, source, state, text_hash, minhash_signature, silver_id,
                   http_status, etag, last_modified, content_length,
                   error_message, retry_count, metadata,
                   discovered_at, last_fetched_at, created_at, updated_at
            FROM crawl_ledger
            WHERE url = %s
        """

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (url,))
                result = cur.fetchone()

        if result:
            # Convert RealDictRow to regular dict
            return dict(result)
        return None

    def get_urls_by_state(
        self, source: str, state: CrawlState, limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Get URLs in specific state for a source."""
        query = """
            SELECT id, url, source, state, text_hash, minhash_signature, silver_id,
                   http_status, etag, last_modified, content_length,
                   error_message, retry_count, metadata,
                   discovered_at, last_fetched_at, created_at, updated_at
            FROM crawl_ledger
            WHERE source = %s AND state = %s
            ORDER BY discovered_at ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (source, state.value))
                results = cur.fetchall()

        return [dict(row) for row in results]

    def mark_url_state(
        self, url: str, state: CrawlState, error_message: Optional[str] = None
    ) -> None:
        """Update URL state."""
        now = datetime.now(timezone.utc)

        if state == CrawlState.FAILED:
            query = """
                UPDATE crawl_ledger SET
                    state = %s,
                    error_message = %s,
                    retry_count = retry_count + 1,
                    updated_at = %s
                WHERE url = %s
            """
            params = (state.value, error_message, now, url)
        else:
            query = """
                UPDATE crawl_ledger SET
                    state = %s,
                    updated_at = %s
                WHERE url = %s
            """
            params = (state.value, now, url)

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)

    def check_duplicate_by_hash(self, text_hash: str) -> Optional[str]:
        """Check if text hash already exists, return URL if found."""
        query = "SELECT url FROM crawl_ledger WHERE text_hash = %s LIMIT 1"

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (text_hash,))
                result = cur.fetchone()

        return result[0] if result else None

    def check_near_duplicate_by_minhash(
        self, minhash_signature: str, threshold: float = 0.85
    ) -> Optional[list[tuple[str, float]]]:
        """
        Check for near-duplicates using MinHash.

        Note: This is a placeholder for exact signature match.
        Real implementation would compute Jaccard similarity.
        """
        query = "SELECT url, minhash_signature FROM crawl_ledger WHERE minhash_signature IS NOT NULL"

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                results = cur.fetchall()

        similar_urls = []
        for row in results:
            # Placeholder: real implementation would compute similarity
            if row[1] == minhash_signature:
                similar_urls.append((row[0], 1.0))

        return similar_urls if similar_urls else None

    def get_last_rss_fetch(self, feed_url: str) -> Optional[datetime]:
        """Get last RSS feed fetch time."""
        query = "SELECT last_fetched_at FROM rss_feeds WHERE feed_url = %s"

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (feed_url,))
                result = cur.fetchone()

        return result[0] if result and result[0] else None

    def record_rss_fetch(self, feed_url: str, items_found: int) -> None:
        """Record RSS feed fetch using PostgreSQL UPSERT."""
        now = datetime.now(timezone.utc)

        query = """
            INSERT INTO rss_feeds (feed_url, source, last_fetched_at, items_found, fetch_count)
            VALUES (%s, 'bbc', %s, %s, 1)
            ON CONFLICT (feed_url) DO UPDATE SET
                last_fetched_at = EXCLUDED.last_fetched_at,
                items_found = EXCLUDED.items_found,
                fetch_count = rss_feeds.fetch_count + 1
        """

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (feed_url, now, items_found))

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

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Total URLs
                if source:
                    cur.execute("SELECT COUNT(*) FROM crawl_ledger WHERE source = %s", (source,))
                else:
                    cur.execute("SELECT COUNT(*) FROM crawl_ledger")
                stats["total_urls"] = cur.fetchone()[0]

                # URLs by state
                if source:
                    cur.execute(
                        """
                        SELECT state, COUNT(*) as count
                        FROM crawl_ledger
                        WHERE source = %s
                        GROUP BY state
                    """,
                        (source,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT state, COUNT(*) as count
                        FROM crawl_ledger
                        GROUP BY state
                    """
                    )

                state_counts = {}
                for row in cur.fetchall():
                    state_counts[row[0]] = row[1]
                stats["by_state"] = state_counts

                # Duplicate statistics
                if source:
                    cur.execute(
                        """
                        SELECT
                            COUNT(DISTINCT text_hash) as unique_hashes,
                            COUNT(*) FILTER (WHERE text_hash IS NOT NULL) as total_hashed
                        FROM crawl_ledger
                        WHERE source = %s
                    """,
                        (source,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT
                            COUNT(DISTINCT text_hash) as unique_hashes,
                            COUNT(*) FILTER (WHERE text_hash IS NOT NULL) as total_hashed
                        FROM crawl_ledger
                    """
                    )

                result = cur.fetchone()
                stats["unique_documents"] = result[0] or 0
                stats["total_hashed"] = result[1] or 0

                if stats["total_hashed"] > 0:
                    stats["dedup_rate"] = 1 - (stats["unique_documents"] / stats["total_hashed"])
                else:
                    stats["dedup_rate"] = 0

                # Error statistics
                if source:
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM crawl_ledger
                        WHERE source = %s AND state = %s AND retry_count >= 3
                    """,
                        (source, "failed"),
                    )
                else:
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM crawl_ledger
                        WHERE state = %s AND retry_count >= 3
                    """,
                        ("failed",),
                    )
                stats["permanent_failures"] = cur.fetchone()[0]

                # RSS statistics (BBC only)
                if not source or source == "bbc":
                    cur.execute(
                        """
                        SELECT
                            COUNT(*) as feed_count,
                            SUM(fetch_count) as total_fetches,
                            AVG(items_found) as avg_items_per_fetch
                        FROM rss_feeds
                    """
                    )
                    result = cur.fetchone()
                    stats["rss"] = {
                        "feed_count": result[0] or 0,
                        "total_fetches": result[1] or 0,
                        "avg_items_per_fetch": result[2] or 0,
                    }

        return stats

    def cleanup_old_entries(self, days: int = 30) -> int:
        """Remove entries older than specified days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        query = """
            DELETE FROM crawl_ledger
            WHERE state = %s
            AND retry_count >= 3
            AND updated_at < %s
        """

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, ("failed", cutoff))
                return cur.rowcount

    def close(self) -> None:
        """Close all connections in pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")

    @property
    def connection(self):
        """
        Property for backward compatibility with SQLiteLedger.

        Note: For PostgreSQL, always use _get_connection() context manager
        instead of direct connection access.
        """
        # This is for compatibility only - return a connection but log warning
        logger.warning(
            "Direct connection access is not recommended for PostgreSQL. "
            "Use _get_connection() context manager instead."
        )
        return self.pool.getconn()
