#!/usr/bin/env python3
"""
Validate Metrics Schema

CI-ready validation script that checks all metrics files against Phase 3 schema.
Fails the build if any validation errors are found.

This script is designed to be run in CI/CD pipelines to ensure data quality
and prevent publishing of invalid metrics.

Usage:
    python scripts/validate_metrics_schema.py
    python scripts/validate_metrics_schema.py --strict  # Fail on warnings

Exit Codes:
    0 - All validations passed
    1 - Validation errors found
    2 - No metrics files found (warning)
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import argparse

try:
    from somali_dialect_classifier.utils.metrics_schema import (
        validate_processing_json,
        validate_consolidated_metrics,
        validate_dashboard_summary,
    )
    SCHEMA_AVAILABLE = True
except ImportError:
    print("ERROR: Schema validation not available.", file=sys.stderr)
    print("Install with: pip install -e '.[config]'", file=sys.stderr)
    sys.exit(1)


class ValidationReport:
    """Collects validation results for reporting."""

    def __init__(self):
        self.total_files = 0
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.errors: List[Dict[str, Any]] = []
        self.warning_messages: List[Dict[str, Any]] = []

    def add_error(self, file_path: str, error_type: str, message: str):
        """Record a validation error."""
        self.failed += 1
        self.errors.append({
            "file": file_path,
            "type": error_type,
            "message": message
        })

    def add_warning(self, file_path: str, warning_type: str, message: str):
        """Record a validation warning."""
        self.warnings += 1
        self.warning_messages.append({
            "file": file_path,
            "type": warning_type,
            "message": message
        })

    def record_success(self):
        """Record a successful validation."""
        self.passed += 1

    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return self.failed > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were recorded."""
        return self.warnings > 0

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("METRICS SCHEMA VALIDATION REPORT")
        print("=" * 70)
        print(f"Total Files:  {self.total_files}")
        print(f"Passed:       {self.passed} ✓")
        print(f"Failed:       {self.failed} ✗")
        print(f"Warnings:     {self.warnings} ⚠")

        if self.has_errors():
            print("\n" + "-" * 70)
            print("ERRORS:")
            print("-" * 70)
            for error in self.errors:
                print(f"\n[{error['type']}] {error['file']}")
                print(f"  {error['message']}")

        if self.has_warnings():
            print("\n" + "-" * 70)
            print("WARNINGS:")
            print("-" * 70)
            for warning in self.warning_messages:
                print(f"\n[{warning['type']}] {warning['file']}")
                print(f"  {warning['message']}")

        print("\n" + "=" * 70)

        if self.has_errors():
            print("❌ VALIDATION FAILED")
        elif self.has_warnings():
            print("⚠️  VALIDATION PASSED WITH WARNINGS")
        else:
            print("✅ VALIDATION PASSED")

        print("=" * 70 + "\n")


def validate_processing_file(file_path: Path, report: ValidationReport) -> bool:
    """
    Validate a single *_processing.json file.

    Args:
        file_path: Path to processing JSON file
        report: ValidationReport to record results

    Returns:
        True if validation passed, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        report.add_error(
            str(file_path),
            "JSON_PARSE_ERROR",
            f"Failed to parse JSON: {e}"
        )
        return False
    except Exception as e:
        report.add_error(
            str(file_path),
            "FILE_READ_ERROR",
            f"Failed to read file: {e}"
        )
        return False

    # Validate against Phase 3 schema
    try:
        validated = validate_processing_json(data)
        report.record_success()

        # Additional checks
        if validated.layered_metrics.volume.records_written == 0:
            report.add_warning(
                str(file_path),
                "ZERO_RECORDS",
                "No records were written in this run"
            )

        if validated.legacy_metrics.statistics.quality_pass_rate < 0.5:
            report.add_warning(
                str(file_path),
                "LOW_QUALITY_PASS_RATE",
                f"Quality pass rate is low: {validated.legacy_metrics.statistics.quality_pass_rate:.1%}"
            )

        return True

    except Exception as e:
        report.add_error(
            str(file_path),
            "SCHEMA_VALIDATION_ERROR",
            f"Schema validation failed: {str(e)[:200]}"
        )
        return False


def validate_consolidated_file(file_path: Path, report: ValidationReport) -> bool:
    """
    Validate consolidated all_metrics.json file.

    Args:
        file_path: Path to all_metrics.json
        report: ValidationReport to record results

    Returns:
        True if validation passed, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        report.add_error(
            str(file_path),
            "JSON_PARSE_ERROR",
            f"Failed to parse JSON: {e}"
        )
        return False
    except Exception as e:
        report.add_error(
            str(file_path),
            "FILE_READ_ERROR",
            f"Failed to read file: {e}"
        )
        return False

    # Validate schema
    try:
        validated = validate_consolidated_metrics(data)
        report.record_success()

        # Consistency checks
        if validated.count != len(validated.metrics):
            report.add_error(
                str(file_path),
                "CONSISTENCY_ERROR",
                f"Count mismatch: count={validated.count}, len(metrics)={len(validated.metrics)}"
            )
            return False

        # Check for duplicate run_ids
        run_ids = [m.run_id for m in validated.metrics]
        if len(run_ids) != len(set(run_ids)):
            report.add_error(
                str(file_path),
                "DUPLICATE_RUN_IDS",
                "Duplicate run_ids found in consolidated metrics"
            )
            return False

        return True

    except Exception as e:
        report.add_error(
            str(file_path),
            "SCHEMA_VALIDATION_ERROR",
            f"Schema validation failed: {str(e)[:200]}"
        )
        return False


def validate_summary_file(file_path: Path, report: ValidationReport) -> bool:
    """
    Validate summary.json file.

    Args:
        file_path: Path to summary.json
        report: ValidationReport to record results

    Returns:
        True if validation passed, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        report.add_error(
            str(file_path),
            "JSON_PARSE_ERROR",
            f"Failed to parse JSON: {e}"
        )
        return False
    except Exception as e:
        report.add_error(
            str(file_path),
            "FILE_READ_ERROR",
            f"Failed to read file: {e}"
        )
        return False

    # Validate schema
    try:
        validated = validate_dashboard_summary(data)
        report.record_success()
        return True

    except Exception as e:
        report.add_error(
            str(file_path),
            "SCHEMA_VALIDATION_ERROR",
            f"Schema validation failed: {str(e)[:200]}"
        )
        return False


def validate_all_processing_files(
    metrics_dir: Path,
    report: ValidationReport
) -> bool:
    """
    Validate all *_processing.json files in metrics directory.

    Args:
        metrics_dir: Path to metrics directory
        report: ValidationReport to record results

    Returns:
        True if all validations passed, False otherwise
    """
    processing_files = sorted(metrics_dir.glob("*_processing.json"))

    if not processing_files:
        print(f"Warning: No *_processing.json files found in {metrics_dir}", file=sys.stderr)
        return False

    print(f"Found {len(processing_files)} processing file(s) to validate")

    all_passed = True
    for file_path in processing_files:
        report.total_files += 1
        print(f"Validating {file_path.name}...", end=" ")

        if validate_processing_file(file_path, report):
            print("✓")
        else:
            print("✗")
            all_passed = False

    return all_passed


def validate_output_files(output_dir: Path, report: ValidationReport) -> bool:
    """
    Validate output files (all_metrics.json, summary.json).

    Args:
        output_dir: Path to output directory (_site/data)
        report: ValidationReport to record results

    Returns:
        True if all validations passed, False otherwise
    """
    all_passed = True

    # Validate all_metrics.json
    all_metrics_file = output_dir / "all_metrics.json"
    if all_metrics_file.exists():
        report.total_files += 1
        print(f"Validating {all_metrics_file.name}...", end=" ")

        if validate_consolidated_file(all_metrics_file, report):
            print("✓")
        else:
            print("✗")
            all_passed = False
    else:
        report.add_warning(
            str(all_metrics_file),
            "MISSING_FILE",
            "all_metrics.json not found (may need to run generate_consolidated_metrics.py)"
        )

    # Validate summary.json
    summary_file = output_dir / "summary.json"
    if summary_file.exists():
        report.total_files += 1
        print(f"Validating {summary_file.name}...", end=" ")

        if validate_summary_file(summary_file, report):
            print("✓")
        else:
            print("✗")
            all_passed = False
    else:
        report.add_warning(
            str(summary_file),
            "MISSING_FILE",
            "summary.json not found (may need to run generate_consolidated_metrics.py)"
        )

    return all_passed


def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(
        description="Validate metrics files against Phase 3 schema"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings (default: warnings are non-fatal)"
    )
    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=Path("data/metrics"),
        help="Path to metrics directory (default: data/metrics)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("_site/data"),
        help="Path to output directory (default: _site/data)"
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("METRICS SCHEMA VALIDATION")
    print("=" * 70)
    print(f"Metrics Directory: {args.metrics_dir}")
    print(f"Output Directory:  {args.output_dir}")
    print(f"Strict Mode:       {'Yes' if args.strict else 'No'}")
    print("=" * 70 + "\n")

    report = ValidationReport()

    # Validate processing files
    print("Validating processing files...")
    processing_passed = validate_all_processing_files(args.metrics_dir, report)

    if not processing_passed:
        print("⚠️  Some processing files have validation errors")
    else:
        print("✅ All processing files passed validation\n")

    # Validate output files
    print("\nValidating output files...")
    output_passed = validate_output_files(args.output_dir, report)

    if not output_passed:
        print("⚠️  Some output files have validation errors")
    else:
        print("✅ All output files passed validation\n")

    # Print summary
    report.print_summary()

    # Determine exit code
    if report.has_errors():
        sys.exit(1)
    elif args.strict and report.has_warnings():
        print("ERROR: Strict mode enabled and warnings found", file=sys.stderr)
        sys.exit(1)
    elif report.total_files == 0:
        print("ERROR: No metrics files found", file=sys.stderr)
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
