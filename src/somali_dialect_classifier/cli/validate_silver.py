"""
CLI tool to validate silver Parquet files against ingestion contract.

This tool provides a command-line interface for validating silver Parquet
files against the IngestionOutputV1 contract. It supports both individual
file validation and bulk directory validation.

Usage:
    # Validate specific partition
    somali-validate-silver --input data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-11-27/

    # Validate all silver data
    somali-validate-silver --input data/processed/silver/

    # Validate with fail-fast mode
    somali-validate-silver --input data/processed/silver/ --fail-fast

    # Validate specific source
    somali-validate-silver --input data/processed/silver/ --source BBC-Somali

    # Show detailed errors
    somali-validate-silver --input data/processed/silver/ --verbose
"""

import json
import logging
import sys
from pathlib import Path

import click

from somali_dialect_classifier.preprocessing.validator import (
    ValidationError,
    validate_silver_directory,
    validate_silver_parquet,
)

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--input",
    "-i",
    "input_path",
    type=click.Path(exists=True),
    required=True,
    help="Path to silver Parquet file or directory",
)
@click.option(
    "--fail-fast/--no-fail-fast",
    default=False,
    help="Stop on first validation error",
)
@click.option(
    "--source",
    "-s",
    default=None,
    help="Filter by source (e.g., 'Wikipedia-Somali', 'BBC-Somali')",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed error messages",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Write validation results to JSON file",
)
def main(input_path: str, fail_fast: bool, source: str, verbose: bool, output: str) -> None:
    """
    Validate silver Parquet files against ingestion contract.

    This tool validates that all records in silver Parquet files conform to
    the IngestionOutputV1 contract, ensuring data quality before preprocessing.
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    path = Path(input_path)

    click.echo(f"Validating: {path}")
    click.echo(f"Fail-fast mode: {fail_fast}")
    if source:
        click.echo(f"Source filter: {source}")

    try:
        # Determine if path is a directory or file
        if path.is_dir():
            # Check if it's a partitioned directory (contains source= subdirs)
            has_partitions = any(path.glob("source=*/"))

            if has_partitions:
                # Validate all partitions
                click.echo("\nValidating all partitions in directory...")
                results = validate_silver_directory(path, fail_fast, source)

                # Display results
                click.echo("\n" + "=" * 80)
                click.echo("VALIDATION RESULTS")
                click.echo("=" * 80)

                total_valid = 0
                total_invalid = 0
                all_errors = []

                for partition_path, (valid, invalid, errors) in results.items():
                    total_valid += valid
                    total_invalid += invalid
                    all_errors.extend([{**err, "partition": partition_path} for err in errors])

                    status = "✓ PASS" if invalid == 0 else "✗ FAIL"
                    click.echo(f"\n{status} {partition_path}\n  Valid: {valid}, Invalid: {invalid}")

                    if verbose and errors:
                        click.echo("  Errors:")
                        for err in errors[:5]:  # Show first 5 errors
                            click.echo(
                                f"    - Record {err['record_index']} "
                                f"(id={err['record_id']}): "
                                f"{'; '.join(err['errors'])}"
                            )
                        if len(errors) > 5:
                            click.echo(f"    ... and {len(errors) - 5} more errors")

                # Overall summary
                click.echo("\n" + "=" * 80)
                click.echo("OVERALL SUMMARY")
                click.echo("=" * 80)
                click.echo(f"Total partitions: {len(results)}")
                click.echo(f"Total valid records: {total_valid}")
                click.echo(f"Total invalid records: {total_invalid}")

                if total_invalid > 0:
                    click.echo(
                        f"\n✗ Validation FAILED: {total_invalid} invalid records found",
                        err=True,
                    )

                    # Show error type distribution
                    error_types = {}
                    for err in all_errors:
                        for err_msg in err["errors"]:
                            error_types[err_msg] = error_types.get(err_msg, 0) + 1

                    click.echo("\nError type distribution:")
                    for err_type, count in sorted(
                        error_types.items(), key=lambda x: x[1], reverse=True
                    ):
                        click.echo(f"  {count:4d}x {err_type}")
                else:
                    click.echo("\n✓ Validation PASSED: All records valid")

                # Write output file if specified
                if output:
                    output_path = Path(output)
                    output_data = {
                        "summary": {
                            "total_partitions": len(results),
                            "total_valid": total_valid,
                            "total_invalid": total_invalid,
                        },
                        "partitions": {
                            p: {"valid": v, "invalid": i, "errors": e}
                            for p, (v, i, e) in results.items()
                        },
                    }
                    with open(output_path, "w") as f:
                        json.dump(output_data, f, indent=2)
                    click.echo(f"\nResults written to: {output_path}")

                # Exit with error code if validation failed
                if total_invalid > 0:
                    sys.exit(1)

            else:
                # Single partition directory
                click.echo("\nValidating single partition directory...")
                valid, invalid, errors = validate_silver_parquet(path, fail_fast)

                # Display results
                _display_single_result(path, valid, invalid, errors, verbose, output)

                if invalid > 0:
                    sys.exit(1)
        else:
            # Single Parquet file
            click.echo("\nValidating single Parquet file...")
            valid, invalid, errors = validate_silver_parquet(path, fail_fast)

            # Display results
            _display_single_result(path, valid, invalid, errors, verbose, output)

            if invalid > 0:
                sys.exit(1)

    except ValidationError as e:
        click.echo(f"\n✗ VALIDATION ERROR: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n✗ ERROR: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def _display_single_result(
    path: Path,
    valid: int,
    invalid: int,
    errors: list,
    verbose: bool,
    output: str,
) -> None:
    """Display validation results for a single file/partition."""
    click.echo("\n" + "=" * 80)
    click.echo("VALIDATION RESULTS")
    click.echo("=" * 80)
    click.echo(f"File: {path}")
    click.echo(f"Valid records: {valid}")
    click.echo(f"Invalid records: {invalid}")

    if invalid > 0:
        click.echo(f"\n✗ Validation FAILED: {invalid} invalid records found", err=True)

        if verbose and errors:
            click.echo("\nError details:")
            for err in errors[:10]:  # Show first 10 errors
                click.echo(
                    f"  - Record {err['record_index']} "
                    f"(id={err['record_id']}): "
                    f"{'; '.join(err['errors'])}"
                )
            if len(errors) > 10:
                click.echo(f"  ... and {len(errors) - 10} more errors")

        # Show error type distribution
        error_types = {}
        for err in errors:
            for err_msg in err["errors"]:
                error_types[err_msg] = error_types.get(err_msg, 0) + 1

        click.echo("\nError type distribution:")
        for err_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"  {count:4d}x {err_type}")
    else:
        click.echo("\n✓ Validation PASSED: All records valid")

    # Write output file if specified
    if output:
        output_path = Path(output)
        output_data = {
            "file": str(path),
            "valid": valid,
            "invalid": invalid,
            "errors": errors,
        }
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
        click.echo(f"\nResults written to: {output_path}")


if __name__ == "__main__":
    main()
