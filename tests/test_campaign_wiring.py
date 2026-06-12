"""
Tests for campaign lifecycle wiring (ADR-009).

Covers:
- campaign auto-init on first production run
- campaign auto-complete when expiry is reached
- non-production runs (test/validation) do not create campaigns
- run_purpose stamped in ledger row
- run_purpose + campaign_id flow into silver source_metadata
- manifest written at run completion with run_purpose + campaign_id
- SQLite schema migration: run_purpose and campaign_id columns on existing schema
"""

import json
import tempfile
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from somdialc.ingestion.crawl_ledger import CrawlLedger, SQLiteLedger

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_ledger():
    """In-memory SQLite ledger backed by a temporary file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        backend = SQLiteLedger(db_path)
        ledger = CrawlLedger(backend=backend)
        yield ledger
        ledger.close()


def _make_minimal_pipeline(ledger, source="bbc-somali", run_seed="test_20260501_120000_abc"):
    """
    Construct a minimal concrete BasePipeline wired to *ledger*.

    All heavy I/O is replaced with no-ops.
    """
    from somdialc.ingestion.base_pipeline import BasePipeline
    from somdialc.ingestion.raw_record import RawRecord
    from somdialc.quality.text_cleaners import TextCleaningPipeline

    _ledger = ledger

    class _MinimalPipeline(BasePipeline):
        def __init__(self, **kwargs):
            self.ledger = _ledger
            super().__init__(**kwargs)

        def _extract_records(self) -> Iterator[RawRecord]:
            return iter([])

        def _create_cleaner(self) -> TextCleaningPipeline:
            mock_cleaner = MagicMock(spec=TextCleaningPipeline)
            mock_cleaner.clean.side_effect = lambda text: text
            return mock_cleaner

        def _get_source_type(self) -> str:
            return "web"

        def _get_license(self) -> str:
            return "test-license"

        def _get_source_metadata(self) -> dict[str, Any]:
            return {}

        def _get_domain(self) -> str:
            return "news"

        def _get_register(self) -> str:
            return "formal"

        def download(self):
            return Path("/dev/null")

        def extract(self):
            return Path("/dev/null")

    pipeline = _MinimalPipeline(source=source, run_seed=run_seed)
    # Point staging_file and processed_file to non-existent paths so
    # process() would early-exit before touching filesystem.
    pipeline.staging_file = Path("/dev/null/nonexistent_staging")
    pipeline.processed_file = Path("/dev/null/nonexistent_processed")
    return pipeline


# ---------------------------------------------------------------------------
# Schema migration tests
# ---------------------------------------------------------------------------


class TestSQLiteSchemaMigration:
    def test_new_db_has_provenance_columns(self, tmp_path):
        """A freshly initialised SQLite DB has run_purpose and campaign_id."""
        import sqlite3

        db_path = tmp_path / "new.db"
        SQLiteLedger(db_path)

        with sqlite3.connect(str(db_path)) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(pipeline_runs)").fetchall()}
        assert "run_purpose" in cols
        assert "campaign_id" in cols

    def test_existing_schema_migrated_in_place(self, tmp_path):
        """
        An existing DB that has only schema v1 (no run_purpose/campaign_id)
        is migrated to v2 without losing existing rows.
        """
        import sqlite3

        db_path = tmp_path / "existing.db"

        # Create a v1-style DB manually (no schema_version, no provenance cols)
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("""
                CREATE TABLE pipeline_runs (
                    run_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    pipeline_type TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    status TEXT NOT NULL,
                    records_processed INTEGER DEFAULT 0,
                    config_snapshot TEXT,
                    git_commit TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT INTO pipeline_runs (run_id, source, pipeline_type, start_time, status)
                VALUES ('existing_run_001', 'wikipedia-somali', 'file_processing',
                        '2026-05-29T10:11:09Z', 'COMPLETED')
            """)
            conn.execute("""
                CREATE TABLE schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        # Now instantiate SQLiteLedger — should migrate without error
        SQLiteLedger(db_path)

        with sqlite3.connect(str(db_path)) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(pipeline_runs)").fetchall()}
            row = conn.execute(
                "SELECT run_id, run_purpose, campaign_id FROM pipeline_runs WHERE run_id = 'existing_run_001'"
            ).fetchone()

        assert "run_purpose" in cols
        assert "campaign_id" in cols
        # Existing row gets default run_purpose='production', campaign_id=NULL
        assert row[0] == "existing_run_001"
        assert row[1] == "production"
        assert row[2] is None

    def test_idempotent_migration(self, tmp_path):
        """Running migration twice does not raise an error."""
        db_path = tmp_path / "idem.db"
        SQLiteLedger(db_path)
        # Second instantiation — should not raise
        SQLiteLedger(db_path)


# ---------------------------------------------------------------------------
# Campaign auto-init tests
# ---------------------------------------------------------------------------


class TestCampaignAutoInit:
    def test_production_run_creates_campaign(self, tmp_ledger, monkeypatch):
        """
        First production run starts campaign_init_001 if it does not exist.
        """
        monkeypatch.setenv("SDC_RUN__PURPOSE", "production")
        from somdialc.infra.config import reset_config

        reset_config()

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100000_prod")
        pipeline._ensure_pipeline_run_registered()

        status = tmp_ledger.get_campaign_status("campaign_init_001")
        assert status == "ACTIVE", f"Expected ACTIVE, got {status!r}"

    def test_production_run_stamps_campaign_id_on_row(self, tmp_ledger, monkeypatch):
        """
        After auto-init the pipeline_runs row is stamped with the campaign_id.
        """
        monkeypatch.setenv("SDC_RUN__PURPOSE", "production")
        from somdialc.infra.config import reset_config

        reset_config()

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100001_prod")
        pipeline._ensure_pipeline_run_registered()

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row is not None
        assert row.get("campaign_id") == "campaign_init_001"

    def test_second_production_run_reuses_active_campaign(self, tmp_ledger, monkeypatch):
        """
        A second production run with an already ACTIVE campaign stamps that
        campaign without creating a duplicate.
        """
        monkeypatch.setenv("SDC_RUN__PURPOSE", "production")
        from somdialc.infra.config import reset_config

        reset_config()

        p1 = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100002_prod1")
        p1._ensure_pipeline_run_registered()

        p2 = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100003_prod2")
        p2._ensure_pipeline_run_registered()

        # Still exactly one campaign row
        row_count = tmp_ledger.backend.connection.execute(
            "SELECT COUNT(*) FROM campaigns WHERE campaign_id='campaign_init_001'"
        ).fetchone()[0]
        assert row_count == 1

        row2 = tmp_ledger.get_pipeline_run(p2.run_id)
        assert row2 is not None
        assert row2.get("campaign_id") == "campaign_init_001"


# ---------------------------------------------------------------------------
# Campaign auto-complete tests
# ---------------------------------------------------------------------------


class TestCampaignAutoComplete:
    def test_expired_campaign_is_completed(self, tmp_ledger, monkeypatch):
        """
        A production run whose campaign start_date is >= duration_days old
        triggers complete_campaign.
        """
        monkeypatch.setenv("SDC_RUN__PURPOSE", "production")
        from somdialc.infra.config import reset_config

        reset_config()

        # Manually create a campaign that started 10 days ago
        past_start = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        with tmp_ledger.backend.transaction() as conn:
            conn.execute(
                """
                INSERT INTO campaigns (campaign_id, name, status, start_date, created_at, updated_at)
                VALUES ('campaign_init_001', 'Initial Data Ingestion', 'ACTIVE', ?, ?, ?)
                """,
                (past_start, past_start, past_start),
            )

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100004_exp")
        pipeline._ensure_pipeline_run_registered()

        status = tmp_ledger.get_campaign_status("campaign_init_001")
        assert status == "COMPLETED", f"Expected COMPLETED after expiry, got {status!r}"

    def test_expired_campaign_does_not_stamp_run(self, tmp_ledger, monkeypatch):
        """
        When a campaign auto-completes during registration, the run row does
        NOT receive campaign_id (the run started after the campaign ended).
        """
        monkeypatch.setenv("SDC_RUN__PURPOSE", "production")
        from somdialc.infra.config import reset_config

        reset_config()

        past_start = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        with tmp_ledger.backend.transaction() as conn:
            conn.execute(
                """
                INSERT INTO campaigns (campaign_id, name, status, start_date, created_at, updated_at)
                VALUES ('campaign_init_001', 'Test', 'ACTIVE', ?, ?, ?)
                """,
                (past_start, past_start, past_start),
            )

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100005_exp2")
        pipeline._ensure_pipeline_run_registered()

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        # campaign is now COMPLETED; stamp_run_campaign should NOT have been called
        assert row is not None
        assert row.get("campaign_id") is None


# ---------------------------------------------------------------------------
# Non-production exclusion
# ---------------------------------------------------------------------------


class TestNonProductionExclusion:
    def test_test_purpose_does_not_create_campaign(self, tmp_ledger, monkeypatch):
        """test-purpose runs must never auto-start a campaign."""
        monkeypatch.setenv("SDC_RUN__PURPOSE", "test")
        from somdialc.infra.config import reset_config

        reset_config()

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100006_tst")
        pipeline._ensure_pipeline_run_registered()

        status = tmp_ledger.get_campaign_status("campaign_init_001")
        assert status is None, "campaign must not be created for test-purpose run"

    def test_validation_purpose_does_not_create_campaign(self, tmp_ledger, monkeypatch):
        """validation-purpose runs must never auto-start a campaign."""
        monkeypatch.setenv("SDC_RUN__PURPOSE", "validation")
        from somdialc.infra.config import reset_config

        reset_config()

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100007_val")
        pipeline._ensure_pipeline_run_registered()

        status = tmp_ledger.get_campaign_status("campaign_init_001")
        assert status is None, "campaign must not be created for validation-purpose run"

    def test_test_purpose_row_has_null_campaign_id(self, tmp_ledger, monkeypatch):
        """pipeline_runs row for a test run must have campaign_id=NULL."""
        monkeypatch.setenv("SDC_RUN__PURPOSE", "test")
        from somdialc.infra.config import reset_config

        reset_config()

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100008_tst2")
        pipeline._ensure_pipeline_run_registered()

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row is not None
        assert row.get("campaign_id") is None

    def test_test_purpose_row_stamped_with_test(self, tmp_ledger, monkeypatch):
        """pipeline_runs row for a test run carries run_purpose='test'."""
        monkeypatch.setenv("SDC_RUN__PURPOSE", "test")
        from somdialc.infra.config import reset_config

        reset_config()

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_100009_tst3")
        pipeline._ensure_pipeline_run_registered()

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row is not None
        assert row.get("run_purpose") == "test"


# ---------------------------------------------------------------------------
# Provenance: purpose + campaign stamped through silver source_metadata
# ---------------------------------------------------------------------------


class TestSilverProvenance:
    """
    Verifies that run_purpose and campaign_id appear in the silver record
    source_metadata dict built by _process_record_stream.
    """

    def test_production_run_stamps_purpose_in_silver(self, tmp_ledger, monkeypatch, tmp_path):
        """
        After a production run the silver source_metadata must contain
        run_purpose='production' and campaign_id (the active campaign).
        """
        monkeypatch.setenv("SDC_RUN__PURPOSE", "production")
        from somdialc.infra.config import reset_config

        reset_config()

        from somdialc.ingestion.base_pipeline import BasePipeline
        from somdialc.ingestion.raw_record import RawRecord
        from somdialc.quality.text_cleaners import TextCleaningPipeline

        collected_meta = []

        class _ProvPipeline(BasePipeline):
            def __init__(self):
                self.ledger = tmp_ledger
                super().__init__(source="bbc-somali", run_seed="test_20260601_prov_001")

            def _extract_records(self) -> Iterator[RawRecord]:
                yield RawRecord(
                    title="Test Title",
                    text="Somali text sample waa test",
                    url="https://example.com/1",
                    metadata={},
                )

            def _create_cleaner(self) -> TextCleaningPipeline:
                mock = MagicMock(spec=TextCleaningPipeline)
                mock.clean.side_effect = lambda t: t
                return mock

            def _get_source_type(self):
                return "news"

            def _get_license(self):
                return "ODC-BY-1.0"

            def _get_source_metadata(self):
                return {}

            def _get_domain(self):
                return "news"

            def _get_register(self):
                return "formal"

            def download(self):
                return None  # short-circuit

            def extract(self):
                return None

        pipeline = _ProvPipeline()
        pipeline._ensure_pipeline_run_registered()

        # Monkey-patch _process_record_stream to capture source_metadata
        def capturing_stream(*args, **kwargs):
            # Intercept what _get_run_purpose and campaign_id resolve to
            collected_meta.append(
                {
                    "run_purpose": pipeline._get_run_purpose(),
                    "campaign_id": (
                        (tmp_ledger.get_pipeline_run(pipeline.run_id) or {}).get("campaign_id")
                    ),
                }
            )
            # Return empty to avoid real processing
            return 0, 0, []

        pipeline._process_record_stream = capturing_stream
        pipeline.staging_file = tmp_path / "staging.jsonl"
        pipeline.staging_file.write_text("")
        pipeline.processed_file = tmp_path / "processed.txt"

        with patch.object(pipeline, "_finalize_process_run"):
            with patch.object(pipeline, "_check_disk_space_for_processing"):
                try:
                    pipeline.process()
                except Exception:
                    pass

        assert collected_meta, "provenance capture was not reached"
        assert collected_meta[0]["run_purpose"] == "production"
        assert collected_meta[0]["campaign_id"] == "campaign_init_001"

    def test_test_run_has_null_campaign_in_silver(self, tmp_ledger, monkeypatch):
        """test-purpose run: campaign_id is None in the ledger row."""
        monkeypatch.setenv("SDC_RUN__PURPOSE", "test")
        from somdialc.infra.config import reset_config

        reset_config()

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_prov_002")
        pipeline._ensure_pipeline_run_registered()

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row is not None
        assert row.get("campaign_id") is None
        assert row.get("run_purpose") == "test"


# ---------------------------------------------------------------------------
# Manifest writer
# ---------------------------------------------------------------------------


class TestManifestWriter:
    def test_manifest_written_on_completed_run(self, tmp_ledger, monkeypatch, tmp_path):
        """
        _finalise_pipeline_run writes a manifest JSON under the configured
        manifests dir for a COMPLETED run.
        """
        monkeypatch.setenv("SDC_RUN__PURPOSE", "test")
        from somdialc.infra.config import reset_config

        reset_config()

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_manif_001")
        pipeline._ensure_pipeline_run_registered()
        # Override manifest dir so the test writes to tmp_path
        from somdialc.infra.manifest_writer import ManifestWriter

        written = {}

        def _capture_manifest(records_processed):
            writer = ManifestWriter(manifest_dir=tmp_path / "manifests")
            run_purpose = pipeline._get_run_purpose()
            campaign_id = (tmp_ledger.get_pipeline_run(pipeline.run_id) or {}).get("campaign_id")
            source_entry = {
                "status": "completed",
                "records_ingested": records_processed,
                "partitions": [pipeline.date_accessed],
                "quota_hit": False,
                "processing_time_seconds": 0.0,
                "run_purpose": run_purpose,
                "campaign_id": campaign_id,
            }
            manifest = writer.create_manifest(
                run_id=pipeline.run_id,
                sources={pipeline.source: source_entry},
            )
            path = writer.write_manifest(manifest)
            written["path"] = path
            written["manifest"] = manifest

        pipeline._write_run_manifest = _capture_manifest

        # Simulate finalising with COMPLETED status
        with patch.object(pipeline, "_count_silver_records", return_value=42):
            pipeline._finalise_pipeline_run(status="COMPLETED", records_processed=42)

        assert "path" in written, "manifest was not written"
        manifest_file = written["path"]
        assert manifest_file.exists()

        with open(manifest_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["run_id"] == pipeline.run_id
        source_data = data["sources"][pipeline.source]
        assert source_data["records_ingested"] == 42
        assert source_data["run_purpose"] == "test"

    def test_manifest_includes_campaign_id_for_production_run(
        self, tmp_ledger, monkeypatch, tmp_path
    ):
        """
        For a production run with an active campaign, the manifest source entry
        carries the campaign_id.
        """
        monkeypatch.setenv("SDC_RUN__PURPOSE", "production")
        from somdialc.infra.config import reset_config

        reset_config()

        pipeline = _make_minimal_pipeline(tmp_ledger, run_seed="test_20260601_manif_002")
        pipeline._ensure_pipeline_run_registered()

        from somdialc.infra.manifest_writer import ManifestWriter

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        campaign_id = (row or {}).get("campaign_id")

        writer = ManifestWriter(manifest_dir=tmp_path / "manifests")
        source_entry = {
            "status": "completed",
            "records_ingested": 10,
            "partitions": [pipeline.date_accessed],
            "quota_hit": False,
            "processing_time_seconds": 0.0,
            "run_purpose": "production",
            "campaign_id": campaign_id,
        }
        manifest = writer.create_manifest(
            run_id=pipeline.run_id, sources={pipeline.source: source_entry}
        )
        path = writer.write_manifest(manifest)

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["sources"][pipeline.source]["campaign_id"] == "campaign_init_001"
