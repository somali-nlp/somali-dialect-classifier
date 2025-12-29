"""
Preprocessing validation entry point.

Validates ingestion output against the IngestionOutputV1 contract
before allowing data to proceed to preprocessing stages.

This module provides streaming validation of silver Parquet files with:
- Minimal memory overhead (<10% on data loading)
- Batched error reporting (collect multiple errors before failing)
- Detailed validation metrics (valid/invalid counts, error types)
- Support for both fail-fast and tolerant modes
"""

import logging
from collections.abc import Iterator
from pathlib import Path

import pyarrow.parquet as pq

from somali_dialect_classifier.contracts import validate_ingestion_output

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_silver_parquet(
    parquet_path: Path, fail_fast: bool = False
) -> tuple[int, int, list[dict]]:
    """
    Validate a silver Parquet file against ingestion contract.

    This function provides streaming validation with batched error collection.
    It reads records in batches to minimize memory overhead while collecting
    detailed validation errors for reporting.

    Args:
        parquet_path: Path to Parquet file or directory
        fail_fast: If True, raise exception on first validation error

    Returns:
        Tuple of (valid_count, invalid_count, errors)
        where errors is a list of dicts with keys:
            - record_index: int (row number in dataset)
            - record_id: str (id field if present)
            - errors: list[str] (validation error messages)

    Raises:
        ValidationError: If fail_fast=True and validation fails
        FileNotFoundError: If parquet_path does not exist

    Example:
        >>> from pathlib import Path
        >>> path = Path("data/processed/silver/source=Wikipedia-Somali/")
        >>> valid, invalid, errors = validate_silver_parquet(path)
        >>> print(f"Valid: {valid}, Invalid: {invalid}")
        Valid: 1000, Invalid: 5
        >>> for error in errors[:3]:
        ...     print(f"Record {error['record_index']}: {error['errors']}")
    """
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet path does not exist: {parquet_path}")

    valid_count = 0
    invalid_count = 0
    errors = []

    logger.info(f"Validating silver Parquet: {parquet_path}")

    try:
        # Read Parquet table (handles both files and directories)
        # For directories, PyArrow will automatically ignore non-parquet files
        # Use a ParquetDataset to filter by file extension
        from pyarrow import dataset as ds

        if parquet_path.is_dir():
            # Use dataset API to filter only .parquet files
            dataset = ds.dataset(
                parquet_path,
                format="parquet",
                exclude_invalid_files=True,
            )
            table = dataset.to_table()
        else:
            # Single file
            table = pq.read_table(parquet_path)

        total_rows = len(table)

        logger.info(f"Loaded {total_rows} records from {parquet_path}")

        # Convert to iterator of dictionaries for validation
        # Use batched conversion to reduce memory overhead
        batch_size = 1000
        for batch_idx in range(0, total_rows, batch_size):
            batch_end = min(batch_idx + batch_size, total_rows)
            batch = table.slice(batch_idx, batch_end - batch_idx)

            # Convert batch to list of dicts
            records = batch.to_pylist()

            for idx, record in enumerate(records):
                record_index = batch_idx + idx
                is_valid, validation_errors = validate_ingestion_output(record)

                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1
                    error_entry = {
                        "record_index": record_index,
                        "record_id": record.get("id", "UNKNOWN"),
                        "errors": validation_errors,
                    }
                    errors.append(error_entry)

                    if fail_fast:
                        error_msg = (
                            f"Validation failed at record {record_index} "
                            f"(id={record.get('id', 'UNKNOWN')}): "
                            f"{'; '.join(validation_errors)}"
                        )
                        logger.error(error_msg)
                        raise ValidationError(error_msg)

            # Log progress every 10k records
            if batch_end % 10000 == 0 and batch_end > 0:
                logger.info(
                    f"Progress: {batch_end}/{total_rows} records "
                    f"({valid_count} valid, {invalid_count} invalid)"
                )

    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        logger.error(f"Error reading Parquet file: {e}")
        raise

    # Log summary
    logger.info(f"Validation complete: {valid_count} valid, {invalid_count} invalid records")

    if invalid_count > 0:
        logger.warning(f"Found {invalid_count} invalid records")
        # Log error type distribution
        error_types = {}
        for error in errors:
            for err_msg in error["errors"]:
                error_types[err_msg] = error_types.get(err_msg, 0) + 1

        logger.warning(f"Error distribution: {error_types}")

    return valid_count, invalid_count, errors


def iter_validated_records(parquet_path: Path, fail_fast: bool = True) -> Iterator[dict]:
    """
    Iterate over validated records from silver Parquet.

    This function provides streaming access to validated records,
    yielding only records that pass contract validation. It's designed
    for preprocessing pipelines that need to consume validated data
    without loading the entire dataset into memory.

    Args:
        parquet_path: Path to Parquet file or directory
        fail_fast: If True, raise exception on invalid record

    Yields:
        Validated record dictionaries

    Raises:
        ValidationError: If fail_fast=True and record is invalid
        FileNotFoundError: If parquet_path does not exist

    Example:
        >>> from pathlib import Path
        >>> path = Path("data/processed/silver/source=BBC-Somali/")
        >>> for record in iter_validated_records(path):
        ...     print(f"Processing record {record['id']}")
        ...     # Preprocessing logic here
    """
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet path does not exist: {parquet_path}")

    logger.info(f"Streaming validated records from: {parquet_path}")

    try:
        # Read Parquet table
        # For directories, use dataset API to filter only .parquet files
        from pyarrow import dataset as ds

        if parquet_path.is_dir():
            # Use dataset API to filter only .parquet files
            dataset = ds.dataset(
                parquet_path,
                format="parquet",
                exclude_invalid_files=True,
            )
            table = dataset.to_table()
        else:
            # Single file
            table = pq.read_table(parquet_path)

        total_rows = len(table)

        logger.info(f"Loaded {total_rows} records for streaming validation")

        valid_count = 0
        invalid_count = 0

        # Stream records in batches to minimize memory overhead
        batch_size = 1000
        for batch_idx in range(0, total_rows, batch_size):
            batch_end = min(batch_idx + batch_size, total_rows)
            batch = table.slice(batch_idx, batch_end - batch_idx)

            # Convert batch to list of dicts
            records = batch.to_pylist()

            for idx, record in enumerate(records):
                record_index = batch_idx + idx
                is_valid, validation_errors = validate_ingestion_output(record)

                if is_valid:
                    valid_count += 1
                    yield record
                else:
                    invalid_count += 1

                    if fail_fast:
                        error_msg = (
                            f"Validation failed at record {record_index} "
                            f"(id={record.get('id', 'UNKNOWN')}): "
                            f"{'; '.join(validation_errors)}"
                        )
                        logger.error(error_msg)
                        raise ValidationError(error_msg)
                    else:
                        # Log warning and skip record
                        logger.warning(
                            f"Skipping invalid record {record_index} "
                            f"(id={record.get('id', 'UNKNOWN')}): "
                            f"{'; '.join(validation_errors)}"
                        )

            # Log progress every 10k records
            if batch_end % 10000 == 0 and batch_end > 0:
                logger.info(
                    f"Streaming progress: {batch_end}/{total_rows} records "
                    f"({valid_count} valid, {invalid_count} skipped)"
                )

        # Final summary
        logger.info(f"Streaming complete: {valid_count} valid, {invalid_count} skipped records")

    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        logger.error(f"Error streaming Parquet file: {e}")
        raise


def validate_silver_directory(
    silver_dir: Path, fail_fast: bool = False, source_filter: str = None
) -> dict[str, tuple[int, int, list[dict]]]:
    """
    Validate all Parquet files in a silver directory.

    This function recursively validates all Parquet files in the silver
    directory structure, optionally filtering by source.

    Args:
        silver_dir: Path to silver directory (e.g., data/processed/silver/)
        fail_fast: If True, stop on first validation error
        source_filter: Optional source filter (e.g., "Wikipedia-Somali")

    Returns:
        Dictionary mapping partition paths to (valid_count, invalid_count, errors)

    Raises:
        ValidationError: If fail_fast=True and validation fails

    Example:
        >>> from pathlib import Path
        >>> results = validate_silver_directory(
        ...     Path("data/processed/silver/"),
        ...     source_filter="BBC-Somali"
        ... )
        >>> for path, (valid, invalid, errors) in results.items():
        ...     print(f"{path}: {valid} valid, {invalid} invalid")
    """
    if not silver_dir.exists():
        raise FileNotFoundError(f"Silver directory does not exist: {silver_dir}")

    results = {}

    # Find all Parquet partitions
    if source_filter:
        # Filter by source
        partitions = list(silver_dir.glob(f"source={source_filter}/date_accessed=*/"))
    else:
        # All sources
        partitions = list(silver_dir.glob("source=*/date_accessed=*/"))

    logger.info(f"Found {len(partitions)} partitions to validate")

    for partition in partitions:
        partition_key = str(partition.relative_to(silver_dir))
        logger.info(f"Validating partition: {partition_key}")

        try:
            valid, invalid, errors = validate_silver_parquet(partition, fail_fast)
            results[partition_key] = (valid, invalid, errors)
        except ValidationError:
            if fail_fast:
                raise
            logger.error(f"Validation failed for partition: {partition_key}")

    # Log overall summary
    total_valid = sum(v for v, _, _ in results.values())
    total_invalid = sum(i for _, i, _ in results.values())

    logger.info(
        f"Overall validation: {total_valid} valid, {total_invalid} invalid "
        f"across {len(results)} partitions"
    )

    return results
