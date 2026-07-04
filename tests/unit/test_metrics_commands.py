"""Unit tests for somdialc.tools.metrics_commands.check_anomalies().

Focused on the missing/empty metrics-directory contract: a gitignored,
not-yet-created data/metrics directory (e.g. a fresh checkout, before any
pipeline has run) must be treated as "nothing to check" success, not an
error -- this is what CI's "Check for metrics anomalies" step and the
`somali-tools metrics check-anomalies` CLI command both rely on.
"""

import json

from click.testing import CliRunner

from somdialc.tools.cli import cli
from somdialc.tools.metrics_commands import check_anomalies


class TestCheckAnomaliesMissingOrEmptyDir:
    def test_missing_directory_returns_success_not_error(self, tmp_path):
        """A metrics_dir that does not exist at all must not raise."""
        missing_dir = tmp_path / "does_not_exist" / "data" / "metrics"
        assert not missing_dir.exists()

        result = check_anomalies(metrics_dir=missing_dir, threshold=3)

        assert result["total_files"] == 0
        assert result["total_anomalies"] == 0
        assert result["error_anomalies"] == 0
        assert result["warning_anomalies"] == 0
        assert "notice" in result and "not found" in result["notice"].lower()

    def test_empty_directory_returns_success_not_error(self, tmp_path):
        """A metrics_dir that exists but has no *_processing.json files is
        equally 'nothing to check', not an error."""
        empty_dir = tmp_path / "metrics"
        empty_dir.mkdir()

        result = check_anomalies(metrics_dir=empty_dir, threshold=3)

        assert result["total_files"] == 0
        assert result["total_anomalies"] == 0

    def test_missing_directory_result_includes_ci_parsed_aliases(self, tmp_path):
        """CI's anomaly-check step parses total_anomalies/error_count/
        warning_count/sources_affected out of the written JSON report --
        all four keys must be present even in the 'nothing to check' case."""
        missing_dir = tmp_path / "data" / "metrics"

        result = check_anomalies(metrics_dir=missing_dir, threshold=3)

        assert result["total_anomalies"] == 0
        assert result["error_count"] == 0
        assert result["warning_count"] == 0
        assert result["sources_affected"] == []

    def test_missing_directory_result_is_json_serializable(self, tmp_path):
        """The result must round-trip through json.dump/json.load exactly as
        the CLI writes it to --output."""
        missing_dir = tmp_path / "data" / "metrics"
        result = check_anomalies(metrics_dir=missing_dir, threshold=3)

        output_path = tmp_path / "anomalies.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f)

        with open(output_path, encoding="utf-8") as f:
            reloaded = json.load(f)

        assert reloaded["total_anomalies"] == 0
        assert reloaded["error_count"] == 0
        assert reloaded["warning_count"] == 0
        assert reloaded["sources_affected"] == []


class TestCheckAnomaliesCLIMissingDir:
    """Exercise the full Click command, not just the library function --
    the bug this guards against was a Click-level `exists=True` path
    validator rejecting the command before check_anomalies() ever ran."""

    def test_cli_exits_zero_on_missing_metrics_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "metrics",
                "check-anomalies",
                "--metrics-dir",
                str(tmp_path / "data" / "metrics"),
                "--threshold",
                "3",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "No significant anomalies found" in result.output

    def test_cli_writes_valid_report_for_missing_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        output_path = tmp_path / "test-results" / "anomalies.json"

        result = runner.invoke(
            cli,
            [
                "metrics",
                "check-anomalies",
                "--metrics-dir",
                str(tmp_path / "data" / "metrics"),
                "--output",
                str(output_path),
            ],
        )

        assert result.exit_code == 0, result.output
        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            report = json.load(f)

        assert report["total_anomalies"] == 0
        assert report["error_count"] == 0
        assert report["warning_count"] == 0
        assert report["sources_affected"] == []
