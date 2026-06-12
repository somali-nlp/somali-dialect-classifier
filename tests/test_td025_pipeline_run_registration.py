"""
Tests for TD-025: pipeline_runs registration from CLI path and BBC daily quota.

Verifies that:
1. BasePipeline.run() registers a pipeline_runs row when invoked via CLI
   (i.e. when the orchestrator has NOT pre-registered the run).
2. The row status ends as COMPLETED on success and FAILED on error.
3. When the orchestrator pre-registers the run, BasePipeline.run() does NOT
   create a duplicate row (idempotency).
4. BBC discovery records daily quota consumption in the daily_quotas table.
"""

import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from somdialc.ingestion.crawl_ledger import CrawlLedger, SQLiteLedger

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_ledger():
    """In-memory SQLite ledger for isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        backend = SQLiteLedger(db_path)
        ledger = CrawlLedger(backend=backend)
        yield ledger
        ledger.close()


def _make_minimal_pipeline(ledger, source="bbc-somali", run_seed="test_20260501_120000_abc"):
    """
    Construct a minimal concrete BasePipeline subclass wired to *ledger*.

    All heavy I/O methods are replaced with no-ops so the test controls the
    execution path without network access or filesystem writes.

    The ledger is injected BEFORE super().__init__().  Registration is now
    lazy (fires at first stage entry), so the row does NOT exist immediately
    after construction — it is created when run() or process() is called.
    """
    from somdialc.ingestion.base_pipeline import BasePipeline
    from somdialc.ingestion.raw_record import RawRecord
    from somdialc.quality.text_cleaners import TextCleaningPipeline

    _ledger = ledger  # captured in closure

    class _MinimalPipeline(BasePipeline):
        def __init__(self, **kwargs):
            # Inject the test ledger BEFORE super().__init__ so the
            # _ensure_pipeline_run_registered() call at the end of
            # BasePipeline.__init__ uses the in-memory ledger.
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
            return "test"

        def _get_source_metadata(self) -> dict[str, Any]:
            return {}

        def _get_domain(self) -> str:
            return "news"

        def _get_register(self) -> str:
            return "formal"

        def download(self) -> Optional[Path]:
            return Path("/tmp/fake_raw")

        def extract(self) -> Optional[Path]:
            return Path("/tmp/fake_staging")

        def process(self) -> Optional[Path]:
            return Path("/tmp/fake_silver")

    # Patch _log_configuration to avoid attempting real config serialisation
    with patch.object(_MinimalPipeline, "_log_configuration", lambda self: None):
        pipeline = _MinimalPipeline(source=source, run_seed=run_seed)

    return pipeline


# ---------------------------------------------------------------------------
# 1. CLI path: run() registers a pipeline_runs row
# ---------------------------------------------------------------------------


class TestBasePipelineRunRegistration:
    def test_run_registers_pipeline_run_when_not_pre_registered(self, tmp_ledger):
        """
        When the orchestrator has NOT pre-registered the run_id, run() creates
        the pipeline_runs row lazily (at first stage entry) and sets
        status=COMPLETED on success.

        The row must NOT exist before run() is called (lazy-registration
        design: construction is side-effect-free).
        """
        pipeline = _make_minimal_pipeline(tmp_ledger)
        run_id = pipeline.run_id

        # Lazy registration: row must NOT exist yet (TD-025 + CAMP-1 redesign).
        row_before = tmp_ledger.get_pipeline_run(run_id)
        assert row_before is None, (
            "pipeline_runs row must NOT be created at construction time "
            "(lazy-registration design: construction is side-effect-free)"
        )

        pipeline.run()

        row = tmp_ledger.get_pipeline_run(run_id)
        assert row is not None, "pipeline_runs row must exist after run()"
        assert row["run_id"] == run_id
        assert row["source"] == pipeline.source
        assert row["status"] == "COMPLETED"
        assert row["end_time"] is not None

    def test_run_sets_failed_status_on_exception(self, tmp_ledger):
        """
        If run() raises, the pipeline_runs row must have status=FAILED.
        """
        pipeline = _make_minimal_pipeline(tmp_ledger)

        def _raise(*_args, **_kwargs):
            raise RuntimeError("intentional test failure")

        pipeline.process = _raise

        with pytest.raises(RuntimeError, match="intentional test failure"):
            pipeline.run()

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row is not None
        assert row["status"] == "FAILED"
        assert "intentional test failure" in (row["errors"] or "")

    def test_run_does_not_duplicate_pre_registered_row(self, tmp_ledger):
        """
        When the orchestrator has already called register_pipeline_run()
        (the normal orchestrator path), run() must NOT create a second row.
        """
        pipeline = _make_minimal_pipeline(tmp_ledger)
        run_id = pipeline.run_id

        # Orchestrator pre-registers the run
        tmp_ledger.register_pipeline_run(
            run_id=run_id,
            source=pipeline.source,
            pipeline_type="web",
        )
        tmp_ledger.update_pipeline_run(run_id=run_id, status="RUNNING")

        pipeline.run()

        # Should still be exactly one row (no IntegrityError, no duplicate)
        history = tmp_ledger.get_pipeline_runs_history(pipeline.source, limit=50)
        matching = [r for r in history if r["run_id"] == run_id]
        assert len(matching) == 1, "Exactly one row expected (no duplicate insert)"

    def test_run_short_circuit_download_still_registers(self, tmp_ledger):
        """
        Even when download() returns None (short-circuit), the pipeline_runs
        row must be created and marked COMPLETED.
        """
        pipeline = _make_minimal_pipeline(tmp_ledger)
        pipeline.download = lambda: None  # type: ignore[method-assign]

        pipeline.run()

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row is not None
        assert row["status"] == "COMPLETED"


# ---------------------------------------------------------------------------
# 1b. Lazy registration: row appears at first stage entry, not at __init__
# ---------------------------------------------------------------------------


class TestInitTimeRegistration:
    """
    Verify lazy-registration semantics (TD-025 + CAMP-1 redesign):
    - Construction is side-effect-free (no ledger writes in __init__).
    - A pipeline_runs row is created the first time a pipeline stage is entered
      (run() or process()), not at construction time.
    - TD-025 is preserved: any CLI subset that reaches at least one stage
      still registers exactly one row.

    This class intentionally retains its original name so existing CI
    references continue to work.
    """

    def test_construction_does_not_register_pipeline_run(self, tmp_ledger):
        """Construction must NOT create a pipeline_runs row (lazy design)."""
        pipeline = _make_minimal_pipeline(tmp_ledger, source="wikipedia")
        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row is None, (
            "pipeline_runs row must NOT exist after construction — "
            "registration is now lazy (fires at first stage entry)"
        )

    # Keep one aliased test name for backward compatibility with CI scripts
    # that reference test_construction_registers_pipeline_run by ID.
    def test_construction_registers_pipeline_run(self, tmp_ledger):
        """Alias: construction is side-effect-free; row appears after run()."""
        pipeline = _make_minimal_pipeline(tmp_ledger, source="wikipedia")
        # No row yet
        assert tmp_ledger.get_pipeline_run(pipeline.run_id) is None
        # Row created by run()
        pipeline.run()
        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row is not None
        assert row["source"] == pipeline.source

    def test_construction_sets_correct_pipeline_type_wiki(self, tmp_ledger):
        """Wikipedia source → pipeline_type=file_processing (verified after run)."""
        pipeline = _make_minimal_pipeline(tmp_ledger, source="wikipedia")
        pipeline.run()
        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row["pipeline_type"] == "file_processing"

    def test_construction_sets_correct_pipeline_type_bbc(self, tmp_ledger):
        """BBC source → pipeline_type=web_scraping (verified after run)."""
        pipeline = _make_minimal_pipeline(tmp_ledger, source="bbc-somali")
        pipeline.run()
        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row["pipeline_type"] == "web_scraping"

    def test_construction_sets_correct_pipeline_type_hf(self, tmp_ledger):
        """HuggingFace source prefix → pipeline_type=stream_processing."""
        pipeline = _make_minimal_pipeline(tmp_ledger, source="huggingface-somali_c4-so")
        pipeline.run()
        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row["pipeline_type"] == "stream_processing"

    def test_construction_sets_correct_pipeline_type_sprakbanken(self, tmp_ledger):
        """Sprakbanken source → pipeline_type=file_processing."""
        pipeline = _make_minimal_pipeline(tmp_ledger, source="sprakbanken")
        pipeline.run()
        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row["pipeline_type"] == "file_processing"

    def test_construction_sets_correct_pipeline_type_tiktok(self, tmp_ledger):
        """TikTok source → pipeline_type=stream_processing."""
        pipeline = _make_minimal_pipeline(tmp_ledger, source="tiktok")
        pipeline.run()
        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row["pipeline_type"] == "stream_processing"

    def test_finalise_sets_records_processed_from_silver_writer(self, tmp_ledger, tmp_path):
        """
        After run() + _finalise_pipeline_run the records_processed column
        reflects the silver row count (non-zero when a silver file exists).
        """
        import pyarrow as pa
        import pyarrow.parquet as pq

        pipeline = _make_minimal_pipeline(tmp_ledger, source="wikipedia")

        # Write a tiny fake parquet file so _count_silver_records finds rows.
        silver_file = tmp_path / "test_silver.parquet"
        table = pa.table({"col": [1, 2, 3]})
        pq.write_table(table, silver_file)
        pipeline.silver_path = silver_file

        # Ensure row exists before _finalise (registration is lazy)
        pipeline._ensure_pipeline_run_registered()
        pipeline._finalise_pipeline_run(status="COMPLETED")

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row["records_processed"] == 3

    def test_tiktok_short_circuit_registers_zero_records(self, tmp_ledger):
        """
        When TikTok download() short-circuits, run() registers the row and
        marks it COMPLETED with records_processed=0.
        """
        pipeline = _make_minimal_pipeline(tmp_ledger, source="tiktok")
        pipeline.download = lambda: None  # type: ignore[method-assign]

        pipeline.run()

        row = tmp_ledger.get_pipeline_run(pipeline.run_id)
        assert row is not None
        assert row["status"] == "COMPLETED"
        assert row["records_processed"] == 0


# ---------------------------------------------------------------------------
# 2. BBC daily quota recorded in discovery
# ---------------------------------------------------------------------------


class TestBBCDailyQuotaRecording:
    """
    Verify that bbc/discovery.py increments daily_quotas after collecting
    links, so the 350 articles/day cap is enforced on every run path.
    """

    def _run_discovery_with_mock_links(
        self,
        tmp_ledger,
        n_links: int,
        max_articles: Optional[int] = None,
        *,
        bbc_quota: Optional[int] = 350,
    ):
        """
        Drive the discovery.download() function with a fake processor that
        has *n_links* article links available and is wired to *tmp_ledger*.

        Uses a real temp file for article_links_file to avoid open() patching
        complexity.  Patches get_config so the quota value is predictable.
        """
        import tempfile as _tempfile

        from somdialc.ingestion.processors.bbc import discovery as bbc_discovery

        with _tempfile.TemporaryDirectory() as tmpdir:
            links_file = Path(tmpdir) / "links.json"

            # Build minimal fake processor
            processor = MagicMock()
            processor.run_id = "test_bbc_quota_run"
            processor.date_accessed = "2026-05-01"
            processor.source = "bbc-somali"  # canonical source name (TD-019)
            processor.ledger = tmp_ledger
            processor.force = False
            processor.max_articles = max_articles
            processor.metrics = MagicMock()
            processor.logger = MagicMock()
            processor.article_links_file = links_file

            raw_dir = MagicMock(spec=Path)
            raw_dir.mkdir.return_value = None
            processor.raw_dir = raw_dir

            # Return enough RSS links to bypass the < 50 fallback to web scraping,
            # ensuring _get_article_links is not called.
            article_links = [
                f"https://www.bbc.com/somali/articles/test_{i}" for i in range(n_links)
            ]
            # Pad to 50+ so discovery uses RSS path exclusively.
            padded_links = article_links + [
                f"https://www.bbc.com/somali/articles/pad_{i}" for i in range(max(0, 50 - n_links))
            ]
            processor._check_robots_txt.return_value = None
            processor._scrape_rss_feeds.return_value = padded_links
            processor._get_article_links.return_value = []
            processor._export_stage_metrics.return_value = None

            # Patch get_config used inside the quota block
            mock_cfg = MagicMock()
            mock_cfg.orchestration.get_quota.return_value = bbc_quota

            with patch(
                "somdialc.infra.config.get_config",
                return_value=mock_cfg,
            ):
                bbc_discovery.download(processor)

    def test_quota_incremented_after_discovery(self, tmp_ledger):
        """
        After running discovery, daily_quotas must contain a row for 'bbc'
        with records_ingested > 0.
        """
        # max_articles=None means all padded_links (>=50) are scraped
        self._run_discovery_with_mock_links(tmp_ledger, n_links=10, max_articles=None)

        usage = tmp_ledger.get_daily_quota_usage("bbc")
        assert usage["records_ingested"] > 0, (
            f"Expected records_ingested > 0, got {usage['records_ingested']}"
        )

    def test_quota_hit_marked_when_limit_reached(self, tmp_ledger):
        """
        When max_articles equals bbc_quota and all articles are consumed,
        the daily_quotas row must have quota_hit=True.

        We use n_links=60 (>50 threshold) so all links come from the RSS
        path, and max_articles=bbc_quota=60 so links_to_scrape fills the cap.
        """
        limit = 60
        self._run_discovery_with_mock_links(
            tmp_ledger, n_links=limit, max_articles=limit, bbc_quota=limit
        )

        usage = tmp_ledger.get_daily_quota_usage("bbc")
        assert usage["quota_hit"] is True, "quota_hit must be True when limit reached"
