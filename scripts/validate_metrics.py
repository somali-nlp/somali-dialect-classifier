#!/usr/bin/env python3
"""
Validate metrics JSON files against schema and perform quality checks.

This script validates:
- JSON schema compliance
- Data freshness (warns if metrics are older than threshold)
- Metrics quality (ensures success rates are within acceptable ranges)
- Required fields presence
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


class MetricsValidator:
    """Validates dashboard metrics JSON files."""

    def __init__(
        self,
        schema_path: Path,
        metrics_path: Path,
        max_age_days: int = 7,
        min_success_rate: float = 0.5,
    ):
        self.schema_path = schema_path
        self.metrics_path = metrics_path
        self.max_age_days = max_age_days
        self.min_success_rate = min_success_rate
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validation checks.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        print(f"🔍 Validating metrics file: {self.metrics_path}")
        print(f"📋 Using schema: {self.schema_path}")
        print()

        # Check file exists
        if not self.metrics_path.exists():
            self.errors.append(f"Metrics file not found: {self.metrics_path}")
            return False, self.errors, self.warnings

        # Load metrics
        try:
            with open(self.metrics_path) as f:
                metrics_data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            return False, self.errors, self.warnings

        # Run validation checks
        self._validate_schema_compliance(metrics_data)
        self._validate_required_fields(metrics_data)
        self._validate_data_freshness(metrics_data)
        self._validate_metrics_quality(metrics_data)
        self._validate_pipeline_types(metrics_data)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _validate_schema_compliance(self, data: Dict[str, Any]) -> None:
        """Validate against JSON schema using basic checks."""
        # Check top-level required fields
        required_fields = ["count", "records", "sources", "pipeline_types", "metrics", "schema_version"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            self.errors.append(f"Missing required fields: {', '.join(missing)}")

        # Validate field types
        if "count" in data and not isinstance(data["count"], int):
            self.errors.append("Field 'count' must be an integer")

        if "records" in data and not isinstance(data["records"], int):
            self.errors.append("Field 'records' must be an integer")

        if "sources" in data and not isinstance(data["sources"], list):
            self.errors.append("Field 'sources' must be an array")

        if "metrics" in data and not isinstance(data["metrics"], list):
            self.errors.append("Field 'metrics' must be an array")

    def _validate_required_fields(self, data: Dict[str, Any]) -> None:
        """Validate that all metrics entries have required fields."""
        if "metrics" not in data:
            return

        required_metric_fields = [
            "run_id",
            "source",
            "timestamp",
            "duration_seconds",
            "pipeline_type",
            "pipeline_metrics",
            "performance",
            "quality",
        ]

        for idx, metric in enumerate(data["metrics"]):
            missing = [f for f in required_metric_fields if f not in metric]
            if missing:
                self.errors.append(
                    f"Metric entry {idx} missing fields: {', '.join(missing)}"
                )

            # Validate nested objects
            if "performance" in metric:
                perf_required = ["urls_per_second", "bytes_per_second", "records_per_minute"]
                perf_missing = [f for f in perf_required if f not in metric["performance"]]
                if perf_missing:
                    self.errors.append(
                        f"Metric entry {idx} performance missing: {', '.join(perf_missing)}"
                    )

            if "quality" in metric:
                quality_required = ["min", "max", "mean", "median", "total_chars"]
                quality_missing = [f for f in quality_required if f not in metric["quality"]]
                if quality_missing:
                    self.errors.append(
                        f"Metric entry {idx} quality missing: {', '.join(quality_missing)}"
                    )

    def _validate_data_freshness(self, data: Dict[str, Any]) -> None:
        """Check if metrics data is fresh enough."""
        if "metrics" not in data or not data["metrics"]:
            self.warnings.append("No metrics data found")
            return

        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=self.max_age_days)

        stale_runs = []
        for metric in data["metrics"]:
            if "timestamp" not in metric:
                continue

            try:
                # Parse ISO 8601 timestamp
                timestamp_str = metric["timestamp"]
                # Handle both with and without timezone
                if timestamp_str.endswith("Z"):
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                elif "+" in timestamp_str or timestamp_str.count("-") > 2:
                    timestamp = datetime.fromisoformat(timestamp_str)
                else:
                    # Assume UTC if no timezone
                    timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)

                if timestamp < threshold:
                    age_days = (now - timestamp).days
                    stale_runs.append(f"{metric.get('source', 'Unknown')} ({age_days} days old)")
            except ValueError as e:
                self.warnings.append(f"Invalid timestamp format: {metric.get('timestamp')} - {e}")

        if stale_runs:
            self.warnings.append(
                f"Stale data detected (older than {self.max_age_days} days): {', '.join(stale_runs)}"
            )

    def _validate_metrics_quality(self, data: Dict[str, Any]) -> None:
        """Check that metrics values are within acceptable ranges."""
        if "metrics" not in data:
            return

        for metric in data["metrics"]:
            source = metric.get("source", "Unknown")
            pipeline_metrics = metric.get("pipeline_metrics", {})

            # Check for pipeline-specific success rates
            pipeline_type = pipeline_metrics.get("pipeline_type", "unknown")

            if pipeline_type == "web_scraping":
                http_success = pipeline_metrics.get("http_success_rate", 0)
                if http_success < self.min_success_rate:
                    self.warnings.append(
                        f"{source}: Low HTTP success rate ({http_success:.1%})"
                    )

            elif pipeline_type == "file_processing":
                file_extraction = pipeline_metrics.get("file_extraction_rate", 0)
                if file_extraction < self.min_success_rate:
                    self.warnings.append(
                        f"{source}: Low file extraction rate ({file_extraction:.1%})"
                    )

            elif pipeline_type == "stream_processing":
                retrieval = pipeline_metrics.get("retrieval_rate", 0)
                if retrieval < self.min_success_rate:
                    self.warnings.append(
                        f"{source}: Low record retrieval rate ({retrieval:.1%})"
                    )

            # Check quality metrics
            quality = metric.get("quality", {})
            if quality.get("mean", 0) < 100:
                self.warnings.append(
                    f"{source}: Very short average text length ({quality.get('mean', 0):.0f} chars)"
                )

            # Check for zero records
            if metric.get("records_written", 0) == 0:
                self.warnings.append(f"{source}: No records written")

    def _validate_pipeline_types(self, data: Dict[str, Any]) -> None:
        """Validate that pipeline types are recognized."""
        valid_types = ["web_scraping", "file_processing", "stream_processing", "unknown"]

        if "pipeline_types" in data:
            invalid = [pt for pt in data["pipeline_types"] if pt not in valid_types]
            if invalid:
                self.errors.append(
                    f"Invalid pipeline types found: {', '.join(invalid)}"
                )

        if "metrics" in data:
            for metric in data["metrics"]:
                pt = metric.get("pipeline_type")
                if pt and pt not in valid_types:
                    source = metric.get("source", "Unknown")
                    self.errors.append(
                        f"{source}: Invalid pipeline type '{pt}'"
                    )


def main() -> int:
    """Main entry point."""
    # Paths
    repo_root = Path(__file__).parent.parent
    schema_path = repo_root / "schemas" / "metrics_schema.json"
    metrics_path = repo_root / "_site" / "data" / "all_metrics.json"

    # Create validator
    validator = MetricsValidator(
        schema_path=schema_path,
        metrics_path=metrics_path,
        max_age_days=30,  # Warn if data older than 30 days
        min_success_rate=0.5,  # Warn if success rate below 50%
    )

    # Run validation
    is_valid, errors, warnings = validator.validate()

    # Print results
    print()
    print("=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    print()

    if errors:
        print("❌ ERRORS:")
        for error in errors:
            print(f"  • {error}")
        print()

    if warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  • {warning}")
        print()

    if is_valid and not warnings:
        print("✅ All checks passed!")
        print()
        return 0
    elif is_valid:
        print("✅ Validation passed with warnings")
        print()
        return 0
    else:
        print("❌ Validation failed")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
