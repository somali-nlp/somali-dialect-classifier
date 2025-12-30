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
- Schema verification (requires migrations to be run)
- Transaction support with rollback

Schema Management:
- Database schema is defined in migrations/database/alembic/versions/
- Tables are created via Alembic migrations or Docker init scripts
- This code verifies tables exist but does NOT create them
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from ..ingestion.crawl_ledger import CrawlState, LedgerBackend
from .migrations import get_migration_instructions, verify_schema_initialized

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
        password: str | None = None,
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
            password: Database password (required, must be provided via SDC_DB_PASSWORD
                     or POSTGRES_PASSWORD environment variable)
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool

        Raises:
            ValueError: If password is not provided
        """
        # SECURITY: Password must be provided via environment variable
        if password is None:
            raise ValueError(
                "Database password is required. "
                "Set SDC_DB_PASSWORD or POSTGRES_PASSWORD environment variable."
            )

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
        Verify database schema is initialized.

        IMPORTANT: This method does NOT create tables. Tables must be created via:
        - Docker: docker-compose up (runs migrations automatically)
        - Manual: cd migrations/database && alembic upgrade head

        This is a verification step to ensure migrations have been run.

        Raises:
            RuntimeError: If required tables are missing
        """
        with self._get_connection() as conn:
            all_exist, missing_tables = verify_schema_initialized(conn)

            if not all_exist:
                instructions = get_migration_instructions("postgresql")
                error_msg = (
                    f"PostgreSQL database schema not initialized.\n"
                    f"Missing tables: {', '.join(missing_tables)}\n"
                    f"\n{instructions}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            logger.info("PostgreSQL schema verification passed")

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
        # SECURITY: Validate limit parameter to prevent SQL injection
        if limit is not None:
            if not isinstance(limit, int) or limit <= 0:
                raise ValueError(f"limit must be a positive integer, got: {limit}")

        query = """
            SELECT id, url, source, state, text_hash, minhash_signature, silver_id,
                   http_status, etag, last_modified, content_length,
                   error_message, retry_count, metadata,
                   discovered_at, last_fetched_at, created_at, updated_at
            FROM crawl_ledger
            WHERE source = %s AND state = %s
            ORDER BY discovered_at ASC
        """

        params = [source, state.value]

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, tuple(params))
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
        query = (
            "SELECT url, minhash_signature FROM crawl_ledger WHERE minhash_signature IS NOT NULL"
        )

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

    def get_daily_quota_usage(self, source: str, date: Optional[str] = None) -> dict[str, Any]:
        """Get daily quota usage for a source."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        query = """
            SELECT records_ingested, quota_limit, quota_hit, items_remaining
            FROM daily_quotas
            WHERE date = %s AND source = %s
        """

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (date, source))
                result = cur.fetchone()

        if result:
            return {
                "date": date,
                "source": source,
                "records_ingested": result[0],
                "quota_limit": result[1],
                "quota_hit": bool(result[2]),
                "items_remaining": result[3],
            }
        return {
            "date": date,
            "source": source,
            "records_ingested": 0,
            "quota_limit": None,
            "quota_hit": False,
            "items_remaining": None,
        }

    def increment_daily_quota(
        self,
        source: str,
        count: int = 1,
        quota_limit: Optional[int] = None,
        date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Increment daily quota counter."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        now = datetime.now(timezone.utc)

        query = """
            INSERT INTO daily_quotas (date, source, records_ingested, quota_limit, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (date, source) DO UPDATE SET
                records_ingested = daily_quotas.records_ingested + EXCLUDED.records_ingested,
                quota_limit = COALESCE(EXCLUDED.quota_limit, daily_quotas.quota_limit),
                updated_at = EXCLUDED.updated_at
        """

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (date, source, count, quota_limit, now))

        return self.get_daily_quota_usage(source, date)

    def mark_quota_hit(
        self,
        source: str,
        items_remaining: int,
        quota_limit: int,
        date: Optional[str] = None,
    ) -> None:
        """Mark that daily quota has been reached."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        now = datetime.now(timezone.utc)

        query = """
            UPDATE daily_quotas SET
                quota_hit = true,
                items_remaining = %s,
                quota_limit = %s,
                updated_at = %s
            WHERE date = %s AND source = %s
        """

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (items_remaining, quota_limit, now, date, source))

    def check_quota_available(
        self, source: str, quota_limit: Optional[int] = None, date: Optional[str] = None
    ) -> tuple[bool, int]:
        """Check if quota is still available."""
        if quota_limit is None:
            return True, -1

        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        usage = self.get_daily_quota_usage(source, date)
        used = usage["records_ingested"]
        remaining = quota_limit - used

        return remaining > 0, max(0, remaining)

    def register_pipeline_run(
        self,
        run_id: str,
        source: str,
        pipeline_type: str,
        config: Optional[dict] = None,
        git_commit: Optional[str] = None,
    ) -> None:
        """Register a new pipeline run."""
        now = datetime.now(timezone.utc)
        config_json = Json(config) if config else None

        query = """
            INSERT INTO pipeline_runs (
                run_id, source, pipeline_type, start_time, status,
                config_snapshot, git_commit, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (run_id, source, pipeline_type, now, "STARTED", config_json, git_commit, now, now),
                )

    def update_pipeline_run(
        self,
        run_id: str,
        status: Optional[str] = None,
        records_discovered: Optional[int] = None,
        records_processed: Optional[int] = None,
        records_failed: Optional[int] = None,
        errors: Optional[str] = None,
        metrics_path: Optional[str] = None,
        end_time: Optional[datetime] = None,
    ) -> None:
        """Update pipeline run with new information."""
        now = datetime.now(timezone.utc)

        updates = []
        params = []

        if status is not None:
            updates.append("status = %s")
            params.append(status)

        if records_discovered is not None:
            updates.append("records_discovered = %s")
            params.append(records_discovered)

        if records_processed is not None:
            updates.append("records_processed = %s")
            params.append(records_processed)

        if records_failed is not None:
            updates.append("records_failed = %s")
            params.append(records_failed)

        if errors is not None:
            updates.append("errors = %s")
            params.append(errors)

        if metrics_path is not None:
            updates.append("metrics_path = %s")
            params.append(metrics_path)

        if end_time is not None:
            updates.append("end_time = %s")
            params.append(end_time)

        updates.append("updated_at = %s")
        params.append(now)

        params.append(run_id)

        if updates:
            query = f"UPDATE pipeline_runs SET {', '.join(updates)} WHERE run_id = %s"
            with self.transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)

    def get_pipeline_run(self, run_id: str) -> Optional[dict]:
        """Retrieve pipeline run details."""
        query = "SELECT * FROM pipeline_runs WHERE run_id = %s"

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (run_id,))
                result = cur.fetchone()

        if result:
            return dict(result)
        return None

    def get_pipeline_runs_history(self, source: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent pipeline runs for a source."""
        # SECURITY: Validate limit parameter
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"limit must be a positive integer, got: {limit}")

        query = """
            SELECT * FROM pipeline_runs
            WHERE source = %s
            ORDER BY start_time DESC
            LIMIT %s
        """

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, (source, limit))
                results = cur.fetchall()

        return [dict(row) for row in results]

    def get_last_successful_run(self, source: str) -> Optional[datetime]:
        """Get timestamp of last successful pipeline run."""
        query = """
            SELECT MAX(end_time) as last_run_time
            FROM pipeline_runs
            WHERE source = %s AND status = %s
        """

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (source, "COMPLETED"))
                result = cur.fetchone()

        if result and result[0]:
            return result[0]
        return None

    def get_first_successful_run(self, source: str) -> Optional[datetime]:
        """Get timestamp of first successful pipeline run."""
        query = """
            SELECT MIN(end_time) as first_run_time
            FROM pipeline_runs
            WHERE source = %s AND status = %s
        """

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (source, "COMPLETED"))
                result = cur.fetchone()

        if result and result[0]:
            return result[0]
        return None

    def get_campaign_status(self, campaign_id: str) -> Optional[str]:
        """Get status of a campaign."""
        query = "SELECT status FROM campaigns WHERE campaign_id = %s"

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (campaign_id,))
                result = cur.fetchone()

        return result[0] if result else None

    def start_campaign(self, campaign_id: str, name: str, config: Optional[dict] = None) -> None:
        """Start a new campaign."""
        now = datetime.now(timezone.utc)
        config_json = Json(config) if config else None

        query = """
            INSERT INTO campaigns (campaign_id, name, status, start_date, config, created_at, updated_at)
            VALUES (%s, %s, 'ACTIVE', %s, %s, %s, %s)
            ON CONFLICT(campaign_id) DO NOTHING
        """

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (campaign_id, name, now, config_json, now, now))

    def complete_campaign(self, campaign_id: str) -> None:
        """Mark a campaign as completed."""
        now = datetime.now(timezone.utc)

        query = """
            UPDATE campaigns
            SET status = 'COMPLETED', end_date = %s, updated_at = %s
            WHERE campaign_id = %s
        """

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (now, now, campaign_id))

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
