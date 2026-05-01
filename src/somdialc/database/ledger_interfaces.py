"""Shared ledger interfaces used by ingestion and database backends."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CrawlState(Enum):
    """URL processing states."""

    DISCOVERED = "discovered"
    FETCHED = "fetched"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"
    DUPLICATE = "duplicate"


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
    def get_daily_quota_usage(self, source: str, date: Optional[str] = None) -> dict[str, Any]:
        """Get daily quota usage for a source."""
        pass

    @abstractmethod
    def increment_daily_quota(
        self,
        source: str,
        count: int = 1,
        quota_limit: Optional[int] = None,
        date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Increment daily quota counter."""
        pass

    @abstractmethod
    def mark_quota_hit(
        self,
        source: str,
        items_remaining: int,
        quota_limit: int,
        date: Optional[str] = None,
    ) -> None:
        """Mark that daily quota has been reached."""
        pass

    @abstractmethod
    def check_quota_available(
        self, source: str, quota_limit: Optional[int] = None, date: Optional[str] = None
    ) -> tuple[bool, int]:
        """Check if quota is still available."""
        pass

    @abstractmethod
    def check_file_checksum(self, checksum: str, source: str) -> Optional[dict[str, Any]]:
        """Check if file with checksum already exists in ledger."""
        pass

    @abstractmethod
    def register_pipeline_run(
        self,
        run_id: str,
        source: str,
        pipeline_type: str,
        config: Optional[dict] = None,
        git_commit: Optional[str] = None,
    ) -> None:
        """Register a new pipeline run at start."""
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_pipeline_run(self, run_id: str) -> Optional[dict]:
        """Retrieve pipeline run details."""
        pass

    @abstractmethod
    def get_pipeline_runs_history(self, source: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent pipeline runs for a source."""
        pass

    @abstractmethod
    def get_last_successful_run(self, source: str) -> Optional[datetime]:
        """Get timestamp of last successful pipeline run for source."""
        pass

    @abstractmethod
    def get_first_successful_run(self, source: str) -> Optional[datetime]:
        """Get timestamp of first successful pipeline run for source."""
        pass

    @abstractmethod
    def get_last_processing_time(self, source: str) -> Optional[datetime]:
        """Get timestamp of last successful processing for a source."""
        pass

    @abstractmethod
    def get_campaign_status(self, campaign_id: str) -> Optional[str]:
        """Get status of a campaign."""
        pass

    @abstractmethod
    def start_campaign(self, campaign_id: str, name: str, config: Optional[dict] = None) -> None:
        """Start a new campaign."""
        pass

    @abstractmethod
    def complete_campaign(self, campaign_id: str) -> None:
        """Mark a campaign as completed."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""
        pass
