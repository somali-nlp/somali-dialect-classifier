"""
Pytest configuration and fixtures for the Somali Dialect Classifier test suite.

This module provides session-level fixtures including warning aggregation
for CI metrics anomaly detection.
"""

import pytest
import warnings
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any


class WarningAggregator:
    """Aggregate warnings during test run for CI analysis."""

    def __init__(self):
        self.warnings: List[Dict[str, Any]] = []
        self._original_showwarning = None

    def add_warning(self, warning_message: str, test_name: str = None, test_file: str = None):
        """Record a warning with context."""
        self.warnings.append({
            "message": str(warning_message),
            "test_name": test_name or "unknown",
            "test_file": test_file or "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def export_to_json(self, output_path: Path):
        """Export warnings to JSON for CI parsing."""
        # Categorize warnings by severity
        metrics_anomalies = [w for w in self.warnings if "METRICS_ANOMALY" in w["message"]]
        other_warnings = [w for w in self.warnings if "METRICS_ANOMALY" not in w["message"]]

        output = {
            "total_warnings": len(self.warnings),
            "metrics_anomalies": len(metrics_anomalies),
            "warnings": self.warnings,
            "summary": {
                "critical": len(metrics_anomalies),
                "warning": len(other_warnings)
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(output, f, indent=2)

    def get_metrics_anomaly_count(self) -> int:
        """Count METRICS_ANOMALY warnings specifically."""
        return sum(
            1 for w in self.warnings
            if "METRICS_ANOMALY" in w["message"]
        )


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
            test_name=getattr(config, '_current_test', None),
            test_file=filename
        )
        # Also call original handler to maintain normal behavior
        if config._original_showwarning:
            config._original_showwarning(message, category, filename, lineno, file, line)

    # Install custom handler
    warnings.showwarning = custom_showwarning


def pytest_unconfigure(config):
    """Pytest unconfigure hook to restore warning handler and export results."""
    # Restore original warning handler
    if hasattr(config, '_original_showwarning') and config._original_showwarning:
        warnings.showwarning = config._original_showwarning

    # Export warnings to JSON
    if hasattr(config, '_warning_aggregator'):
        output_path = Path("test-results/warnings-summary.json")
        config._warning_aggregator.export_to_json(output_path)

        # Print summary to console
        metrics_anomalies = config._warning_aggregator.get_metrics_anomaly_count()
        total_warnings = len(config._warning_aggregator.warnings)

        if total_warnings > 0:
            print(f"\n{'='*70}")
            print(f"WARNING SUMMARY")
            print(f"{'='*70}")
            print(f"Total warnings: {total_warnings}")
            print(f"Metrics anomalies: {metrics_anomalies}")

            if metrics_anomalies > 0:
                print(f"\n⚠️  {metrics_anomalies} METRICS_ANOMALY warnings detected")
                print(f"   See: {output_path}")

            print(f"{'='*70}\n")


def pytest_runtest_setup(item):
    """Hook called before each test to track current test name."""
    item.config._current_test = item.nodeid
