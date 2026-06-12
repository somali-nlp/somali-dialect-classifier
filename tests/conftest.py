"""
Pytest configuration and fixtures for the Somali Dialect Classifier test suite.

This module provides session-level fixtures including:
- Warning aggregation for CI metrics anomaly detection
- Ledger and data-path isolation to prevent test runs from writing to the
  production ledger at data/ledger/crawl_ledger.db or the production data
  directories at data/raw, data/staging, and data/processed.

Test-isolation design
---------------------
BasePipeline.__init__ calls _ensure_pipeline_run_registered(), which opens a
CrawlLedger backed by the SQLite file whose path is resolved from:

  1. SDC_LEDGER_SQLITE_PATH environment variable (highest priority)
  2. config.data.raw_dir.parent / "ledger" / "crawl_ledger.db"   (default)

The autouse ``isolated_pipeline_env`` fixture (session scope) sets the three
env vars below *before any test module is imported*, ensuring all processor
constructions within the test session resolve to temporary directories:

  SDC_LEDGER_SQLITE_PATH  → <tmp>/ledger/crawl_ledger.db
  SDC_DATA__RAW_DIR       → <tmp>/raw
  SDC_DATA__STAGING_DIR   → <tmp>/staging
  SDC_DATA__PROCESSED_DIR → <tmp>/processed
  SDC_DATA__METRICS_DIR   → <tmp>/metrics          (RFU-5: prevents data/metrics pollution)
  SDC_DATA__SILVER_DIR    → <tmp>/silver

It also calls reset_config() so the already-cached singleton is invalidated
before the first processor is constructed.

CI ledger guard
---------------
The ``session_ledger_guard`` session-finish hook records the production ledger
row count at session start and asserts it is unchanged at session end.  Any
test that somehow bypasses the isolation fixture will cause this guard to fail,
making re-pollution structurally impossible to introduce silently.
"""

import json
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Production-ledger path — used by the CI guard only (read-only).
# ---------------------------------------------------------------------------

_PRODUCTION_LEDGER = Path(__file__).parent.parent / "data" / "ledger" / "crawl_ledger.db"


def _read_ledger_count(db_path: Path) -> int:
    """Return pipeline_runs row count from an SQLite DB, or -1 if unavailable."""
    try:
        import sqlite3

        uri = f"file:{db_path}?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            row = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return -1


class WarningAggregator:
    """Aggregate warnings during test run for CI analysis."""

    def __init__(self):
        self.warnings: list[dict[str, Any]] = []
        self._original_showwarning = None

    def add_warning(self, warning_message: str, test_name: str = None, test_file: str = None):
        """Record a warning with context."""
        self.warnings.append(
            {
                "message": str(warning_message),
                "test_name": test_name or "unknown",
                "test_file": test_file or "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def export_to_json(self, output_path: Path):
        """Export warnings to JSON for CI parsing."""
        # Categorize warnings by severity
        metrics_anomalies = [w for w in self.warnings if "METRICS_ANOMALY" in w["message"]]
        other_warnings = [w for w in self.warnings if "METRICS_ANOMALY" not in w["message"]]

        output = {
            "total_warnings": len(self.warnings),
            "metrics_anomalies": len(metrics_anomalies),
            "warnings": self.warnings,
            "summary": {"critical": len(metrics_anomalies), "warning": len(other_warnings)},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(output, f, indent=2)

    def get_metrics_anomaly_count(self) -> int:
        """Count METRICS_ANOMALY warnings specifically."""
        return sum(1 for w in self.warnings if "METRICS_ANOMALY" in w["message"])


@pytest.fixture(scope="session")
def warning_aggregator():
    """Session-scoped warning aggregator for collecting warnings during tests."""
    aggregator = WarningAggregator()
    return aggregator


def pytest_configure(config):
    """Pytest configuration hook to set up warning capture."""
    # Create session-level warning aggregator
    config._warning_aggregator = WarningAggregator()

    # Store original warning handler
    config._original_showwarning = warnings.showwarning

    # Create custom warning handler that logs to aggregator
    def custom_showwarning(message, category, filename, lineno, file=None, line=None):
        # Add to aggregator
        config._warning_aggregator.add_warning(
            warning_message=str(message),
            test_name=getattr(config, "_current_test", None),
            test_file=filename,
        )
        # Also call original handler to maintain normal behavior
        if config._original_showwarning:
            config._original_showwarning(message, category, filename, lineno, file, line)

    # Install custom handler
    warnings.showwarning = custom_showwarning


def pytest_unconfigure(config):
    """Pytest unconfigure hook to restore warning handler and export results."""
    # Restore original warning handler
    if hasattr(config, "_original_showwarning") and config._original_showwarning:
        warnings.showwarning = config._original_showwarning

    # Export warnings to JSON
    if hasattr(config, "_warning_aggregator"):
        output_path = Path("test-results/warnings-summary.json")
        config._warning_aggregator.export_to_json(output_path)

        # Print summary to console
        metrics_anomalies = config._warning_aggregator.get_metrics_anomaly_count()
        total_warnings = len(config._warning_aggregator.warnings)

        if total_warnings > 0:
            print(f"\n{'=' * 70}")
            print("WARNING SUMMARY")
            print(f"{'=' * 70}")
            print(f"Total warnings: {total_warnings}")
            print(f"Metrics anomalies: {metrics_anomalies}")

            if metrics_anomalies > 0:
                print(f"\n⚠️  {metrics_anomalies} METRICS_ANOMALY warnings detected")
                print(f"   See: {output_path}")

            print(f"{'=' * 70}\n")


def pytest_runtest_setup(item):
    """Hook called before each test to track current test name."""
    item.config._current_test = item.nodeid


# ---------------------------------------------------------------------------
# Test-isolation fixture: redirect ledger + data dirs away from production.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def isolated_pipeline_env(tmp_path_factory):
    """
    Route all processor-level I/O (ledger writes, data directory creation) to
    a temporary directory for the duration of the test session.

    This fixture is session-scoped and autouse so it activates for every test
    without any explicit request.  It sets the environment variables that the
    CrawlLedger and DataConfig singletons read at construction time, then
    resets the Config singleton so subsequent imports pick up the new paths.

    On teardown it restores the original environment and resets the singleton
    again so any post-session code runs with the original configuration.

    Env vars set:
        SDC_LEDGER_SQLITE_PATH  — redirects the SQLite ledger file
        SDC_DATA__RAW_DIR       — redirects raw data directory
        SDC_DATA__STAGING_DIR   — redirects staging directory
        SDC_DATA__PROCESSED_DIR — redirects processed directory
        SDC_DATA__METRICS_DIR   — redirects metrics output (RFU-5)
        SDC_DATA__SILVER_DIR    — redirects silver Parquet output
    """
    tmp_root = tmp_path_factory.mktemp("pipeline_isolation")
    (tmp_root / "ledger").mkdir(parents=True, exist_ok=True)
    (tmp_root / "raw").mkdir(parents=True, exist_ok=True)
    (tmp_root / "staging").mkdir(parents=True, exist_ok=True)
    (tmp_root / "processed").mkdir(parents=True, exist_ok=True)

    # RFU-5: also redirect metrics writes so tests do not emit discovery JSONs
    # into data/metrics/ and contaminate production telemetry.
    (tmp_root / "metrics").mkdir(parents=True, exist_ok=True)
    (tmp_root / "silver").mkdir(parents=True, exist_ok=True)

    overrides = {
        "SDC_LEDGER_SQLITE_PATH": str(tmp_root / "ledger" / "crawl_ledger.db"),
        "SDC_DATA__RAW_DIR": str(tmp_root / "raw"),
        "SDC_DATA__STAGING_DIR": str(tmp_root / "staging"),
        "SDC_DATA__PROCESSED_DIR": str(tmp_root / "processed"),
        "SDC_DATA__METRICS_DIR": str(tmp_root / "metrics"),
        "SDC_DATA__SILVER_DIR": str(tmp_root / "silver"),
        # Campaign/provenance: tests run as purpose=test so they never
        # auto-start campaigns or write campaign_id onto the test ledger rows.
        "SDC_RUN__PURPOSE": "test",
    }

    # Snapshot originals so teardown can restore precisely.
    originals = {k: os.environ.get(k) for k in overrides}

    for k, v in overrides.items():
        os.environ[k] = v

    # Invalidate the already-cached Config singleton so the first processor
    # construction in this session picks up the new paths.
    try:
        from somdialc.infra.config import reset_config

        reset_config()
    except Exception:
        pass

    yield tmp_root

    # Teardown: restore original env and invalidate the test-scoped singleton.
    for k, original_v in originals.items():
        if original_v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = original_v

    try:
        from somdialc.infra.config import reset_config

        reset_config()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CI ledger guard: fail if any test wrote to the production ledger.
# ---------------------------------------------------------------------------


def pytest_sessionstart(session):
    """Record the production ledger row count before any tests run."""
    session._ledger_count_before = _read_ledger_count(_PRODUCTION_LEDGER)


def pytest_sessionfinish(session, exitstatus):
    """
    Assert that the production ledger row count is unchanged after the session.

    If any processor construction reached the production database despite the
    isolation fixture, this hook will fail loudly so the regression is caught
    in CI rather than silently corrupting the ledger.
    """
    count_before = getattr(session, "_ledger_count_before", -1)
    count_after = _read_ledger_count(_PRODUCTION_LEDGER)

    if count_before == -1 or count_after == -1:
        # DB not accessible; skip the guard to avoid false failures in
        # environments where the production DB does not exist.
        return

    if count_after != count_before:
        delta = count_after - count_before
        raise AssertionError(
            f"LEDGER POLLUTION DETECTED: production ledger row count changed "
            f"during test session (before={count_before}, after={count_after}, "
            f"delta=+{delta}). A processor construction bypassed the "
            f"isolated_pipeline_env fixture and wrote to "
            f"data/ledger/crawl_ledger.db. Fix the test that triggered this."
        )
