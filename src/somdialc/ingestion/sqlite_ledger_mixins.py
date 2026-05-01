"""Mixin classes that keep SQLite ledger concerns in smaller units."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional


class SQLiteCampaignMixin:
    """Campaign lifecycle helpers for the SQLite ledger."""

    @property
    def connection(self) -> sqlite3.Connection:  # pragma: no cover
        raise NotImplementedError

    def transaction(self):  # pragma: no cover
        raise NotImplementedError

    def get_campaign_status(self, campaign_id: str) -> Optional[str]:
        result = self.connection.execute(
            "SELECT status FROM campaigns WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()
        return result["status"] if result else None

    def start_campaign(self, campaign_id: str, name: str, config: Optional[dict] = None) -> None:
        now = datetime.now(timezone.utc)
        config_json = json.dumps(config) if config else None
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO campaigns (campaign_id, name, status, start_date, config, created_at, updated_at)
                VALUES (?, ?, 'ACTIVE', ?, ?, ?, ?)
                ON CONFLICT(campaign_id) DO NOTHING
                """,
                (campaign_id, name, now, config_json, now, now),
            )

    def complete_campaign(self, campaign_id: str) -> None:
        now = datetime.now(timezone.utc)
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE campaigns
                SET status = 'COMPLETED', end_date = ?, updated_at = ?
                WHERE campaign_id = ?
                """,
                (now, now, campaign_id),
            )


class SQLiteQuotaMixin:
    """Quota and checksum helpers for the SQLite ledger."""

    @property
    def connection(self) -> sqlite3.Connection:  # pragma: no cover
        raise NotImplementedError

    def transaction(self):  # pragma: no cover
        raise NotImplementedError

    def get_daily_quota_usage(self, source: str, date: Optional[str] = None) -> dict[str, Any]:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            from ..infra.logging_utils import validate_iso_date

            date = validate_iso_date(date)

        result = self.connection.execute(
            """
            SELECT records_ingested, quota_limit, quota_hit, items_remaining
            FROM daily_quotas
            WHERE date = ? AND source = ?
            """,
            (date, source),
        ).fetchone()

        if result:
            return {
                "date": date,
                "source": source,
                "records_ingested": result["records_ingested"],
                "quota_limit": result["quota_limit"],
                "quota_hit": bool(result["quota_hit"]),
                "items_remaining": result["items_remaining"],
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
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            from ..infra.logging_utils import validate_iso_date

            date = validate_iso_date(date)

        now = datetime.now(timezone.utc)
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO daily_quotas (date, source, records_ingested, quota_limit, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date, source) DO UPDATE SET
                    records_ingested = records_ingested + excluded.records_ingested,
                    quota_limit = COALESCE(excluded.quota_limit, quota_limit),
                    updated_at = excluded.updated_at
                """,
                (date, source, count, quota_limit, now.isoformat()),
            )

        return self.get_daily_quota_usage(source, date)

    def mark_quota_hit(
        self,
        source: str,
        items_remaining: int,
        quota_limit: int,
        date: Optional[str] = None,
    ) -> None:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            from ..infra.logging_utils import validate_iso_date

            date = validate_iso_date(date)

        now = datetime.now(timezone.utc)
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO daily_quotas (
                    date, source, records_ingested, quota_limit,
                    quota_hit, items_remaining, updated_at
                )
                VALUES (?, ?, 0, ?, 1, ?, ?)
                ON CONFLICT(date, source) DO UPDATE SET
                    quota_hit = 1,
                    items_remaining = excluded.items_remaining,
                    quota_limit = excluded.quota_limit,
                    updated_at = excluded.updated_at
                """,
                (date, source, quota_limit, items_remaining, now.isoformat()),
            )

    def check_quota_available(
        self, source: str, quota_limit: Optional[int] = None, date: Optional[str] = None
    ) -> tuple[bool, int]:
        if quota_limit is None:
            return True, -1
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            from ..infra.logging_utils import validate_iso_date

            date = validate_iso_date(date)

        usage = self.get_daily_quota_usage(source, date)
        used = usage["records_ingested"]
        remaining = quota_limit - used
        return remaining > 0, max(0, remaining)

    def check_file_checksum(self, checksum: str, source: str) -> Optional[dict[str, Any]]:
        query = """
            SELECT url, source, state, created_at, metadata
            FROM crawl_ledger
            WHERE source = ?
              AND json_extract(metadata, '$.file_checksum') = ?
            LIMIT 1
        """
        result = self.connection.execute(query, (source, checksum)).fetchone()
        if result:
            return {
                "url": result["url"],
                "source": result["source"],
                "state": result["state"],
                "created_at": result["created_at"],
                "metadata": result["metadata"],
            }
        return None


class SQLitePipelineRunsMixin:
    """Pipeline run tracking helpers for the SQLite ledger."""

    @property
    def connection(self) -> sqlite3.Connection:  # pragma: no cover
        raise NotImplementedError

    def transaction(self):  # pragma: no cover
        raise NotImplementedError

    def register_pipeline_run(
        self,
        run_id: str,
        source: str,
        pipeline_type: str,
        config: Optional[dict] = None,
        git_commit: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        config_json = json.dumps(config) if config else None
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_runs (
                    run_id, source, pipeline_type, start_time, status,
                    config_snapshot, git_commit, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    source,
                    pipeline_type,
                    now.isoformat(),
                    "STARTED",
                    config_json,
                    git_commit,
                    now.isoformat(),
                    now.isoformat(),
                ),
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
        now = datetime.now(timezone.utc)
        updates = []
        params = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if records_discovered is not None:
            updates.append("records_discovered = ?")
            params.append(records_discovered)
        if records_processed is not None:
            updates.append("records_processed = ?")
            params.append(records_processed)
        if records_failed is not None:
            updates.append("records_failed = ?")
            params.append(records_failed)
        if errors is not None:
            updates.append("errors = ?")
            params.append(errors)
        if metrics_path is not None:
            updates.append("metrics_path = ?")
            params.append(metrics_path)
        if end_time is not None:
            updates.append("end_time = ?")
            params.append(end_time.isoformat())
        updates.append("updated_at = ?")
        params.append(now.isoformat())
        params.append(run_id)
        if updates:
            with self.transaction() as conn:
                query = f"UPDATE pipeline_runs SET {', '.join(updates)} WHERE run_id = ?"
                conn.execute(query, params)

    def get_pipeline_run(self, run_id: str) -> Optional[dict]:
        result = self.connection.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if result:
            return dict(result)
        return None

    def get_pipeline_runs_history(self, source: str, limit: int = 10) -> list[dict[str, Any]]:
        query = """
            SELECT * FROM pipeline_runs
            WHERE source = ?
            ORDER BY start_time DESC
            LIMIT ?
        """
        results = self.connection.execute(query, (source, limit)).fetchall()
        return [dict(row) for row in results]

    def get_last_successful_run(self, source: str) -> Optional[datetime]:
        query = """
            SELECT MAX(end_time) as last_run_time
            FROM pipeline_runs
            WHERE source = ? AND status = ?
        """
        result = self.connection.execute(query, (source, "COMPLETED")).fetchone()
        if result and result["last_run_time"]:
            return datetime.fromisoformat(result["last_run_time"].replace("Z", "+00:00"))
        return None

    def get_first_successful_run(self, source: str) -> Optional[datetime]:
        query = """
            SELECT MIN(end_time) as first_run_time
            FROM pipeline_runs
            WHERE source = ? AND status = ?
        """
        result = self.connection.execute(query, (source, "COMPLETED")).fetchone()
        if result and result["first_run_time"]:
            return datetime.fromisoformat(result["first_run_time"].replace("Z", "+00:00"))
        return None

    def get_last_processing_time(self, source: str) -> Optional[datetime]:
        query = """
            SELECT MAX(updated_at) as last_processing_time
            FROM crawl_ledger
            WHERE source = ? AND state = ?
        """
        result = self.connection.execute(
            query, (source, "processed")
        ).fetchone()
        if result and result["last_processing_time"]:
            return datetime.fromisoformat(result["last_processing_time"].replace("Z", "+00:00"))
        return None
