"""
Data command implementations for somali-tools CLI.

This module contains testable library code for data validation and quality checks.
Separated from CLI to enable unit testing without Click framework.

Functions include:
- Silver dataset validation
- Sample record export
- Data quality checks
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# SILVER DATASET VALIDATION
# ============================================================================


def validate_silver_dataset(
    silver_path: Path, source_filter: list[str] | None = None, strict: bool = False
) -> dict[str, Any]:
    """
    Validate silver dataset integrity.

    Args:
        silver_path: Path to silver dataset directory
        source_filter: Optional list of sources to validate
        strict: If True, treat warnings as errors

    Returns:
        Validation report with findings

    Raises:
        FileNotFoundError: If silver_path doesn't exist
    """
    if not silver_path.exists():
        raise FileNotFoundError(f"Silver dataset directory not found: {silver_path}")

    # Find all source directories
    source_dirs = [d for d in silver_path.iterdir() if d.is_dir() and d.name.startswith("source=")]

    if not source_dirs:
        logger.warning(f"No source directories found in {silver_path}")
        return {
            "total_sources": 0,
            "validated_sources": 0,
            "errors": 0,
            "warnings": 0,
            "sources": [],
        }

    # Filter by source if specified
    if source_filter:
        source_dirs = [d for d in source_dirs if d.name.split("=")[1] in source_filter]

    results = []
    total_errors = 0
    total_warnings = 0

    for source_dir in source_dirs:
        source_name = source_dir.name.split("=")[1]
        logger.info(f"Validating source: {source_name}")

        source_result = validate_source_directory(source_dir, strict)
        results.append(source_result)

        total_errors += source_result["errors"]
        total_warnings += source_result["warnings"]

    return {
        "total_sources": len(source_dirs),
        "validated_sources": len(results),
        "errors": total_errors,
        "warnings": total_warnings,
        "strict": strict,
        "sources": results,
    }


def validate_source_directory(source_dir: Path, strict: bool = False) -> dict[str, Any]:
    """
    Validate a single source directory.

    Args:
        source_dir: Path to source directory
        strict: If True, treat warnings as errors

    Returns:
        Validation result for source
    """
    source_name = source_dir.name.split("=")[1]
    errors = []
    warnings = []

    # Check for parquet files
    parquet_files = list(source_dir.rglob("*.parquet"))

    if not parquet_files:
        errors.append({"type": "no_data", "message": "No parquet files found in source directory"})
        return {
            "source": source_name,
            "status": "error",
            "errors": len(errors),
            "warnings": len(warnings),
            "details": {"errors": errors, "warnings": warnings},
        }

    # Try to load with DuckDB for validation
    try:
        import duckdb

        conn = duckdb.connect()

        # Load first file for schema check
        first_file = parquet_files[0]
        result = conn.execute(f"SELECT * FROM '{first_file}' LIMIT 1").fetchone()

        if not result:
            warnings.append(
                {
                    "type": "empty_data",
                    "message": "Parquet file exists but contains no records",
                    "file": str(first_file),
                }
            )

        # Check for required columns
        df = conn.execute(f"DESCRIBE SELECT * FROM '{first_file}'").fetchall()
        columns = [row[0] for row in df]

        required_columns = ["text", "url", "text_hash", "source"]
        missing_columns = [col for col in required_columns if col not in columns]

        if missing_columns:
            errors.append(
                {
                    "type": "schema_error",
                    "message": f"Missing required columns: {', '.join(missing_columns)}",
                    "file": str(first_file),
                }
            )

    except ImportError:
        warnings.append(
            {
                "type": "validation_skipped",
                "message": "DuckDB not available, skipping detailed validation",
            }
        )
    except Exception as e:
        errors.append({"type": "validation_error", "message": f"Failed to validate: {e}"})

    # Determine status
    if errors:
        status = "error"
    elif warnings and strict:
        status = "error"
    elif warnings:
        status = "warning"
    else:
        status = "valid"

    return {
        "source": source_name,
        "status": status,
        "file_count": len(parquet_files),
        "errors": len(errors),
        "warnings": len(warnings),
        "details": {"errors": errors, "warnings": warnings},
    }


# ============================================================================
# SAMPLE EXPORT
# ============================================================================


def export_sample_records(
    silver_path: Path, output_path: Path, count: int = 10, source: str | None = None
) -> Path:
    """
    Export sample records for inspection.

    Args:
        silver_path: Path to silver dataset directory
        output_path: Output file path (JSON or CSV)
        count: Number of sample records to export
        source: Optional source to sample from

    Returns:
        Path to written sample file

    Raises:
        FileNotFoundError: If silver_path doesn't exist
        ValueError: If no data found
    """
    if not silver_path.exists():
        raise FileNotFoundError(f"Silver dataset directory not found: {silver_path}")

    # Find parquet files
    if source:
        pattern = silver_path / f"source={source}" / "**" / "*.parquet"
        parquet_files = list(silver_path.glob(str(pattern.relative_to(silver_path))))
    else:
        parquet_files = list(silver_path.rglob("*.parquet"))

    if not parquet_files:
        raise ValueError(f"No parquet files found in {silver_path}")

    # Load sample records
    try:
        import duckdb

        conn = duckdb.connect()

        # Read all parquet files
        file_pattern = "'" + "', '".join(str(f) for f in parquet_files) + "'"
        query = f"SELECT * FROM read_parquet([{file_pattern}])"

        # Get total count
        total = conn.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

        if total == 0:
            raise ValueError("No records found in parquet files")

        # Sample records
        sample_size = min(count, total)
        sample_query = f"{query} USING SAMPLE {sample_size}"

        df = conn.execute(sample_query).fetchdf()

        # Convert to desired format
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix == ".json":
            df.to_json(output_path, orient="records", indent=2)
        elif output_path.suffix == ".csv":
            df.to_csv(output_path, index=False)
        else:
            # Default to JSON
            df.to_json(output_path, orient="records", indent=2)

        logger.info(f"Exported {len(df)} sample records to {output_path}")
        return output_path

    except ImportError:
        raise ImportError("DuckDB required for sample export. Install with: pip install duckdb")


# ============================================================================
# QUALITY CHECKS
# ============================================================================


def check_data_quality(silver_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    """
    Run quality checks on datasets.

    Args:
        silver_path: Path to silver dataset directory
        output_path: Optional output path for quality report (JSON)

    Returns:
        Quality report with metrics

    Raises:
        FileNotFoundError: If silver_path doesn't exist
    """
    if not silver_path.exists():
        raise FileNotFoundError(f"Silver dataset directory not found: {silver_path}")

    # Find all parquet files
    parquet_files = list(silver_path.rglob("*.parquet"))

    if not parquet_files:
        logger.warning(f"No parquet files found in {silver_path}")
        return {"total_files": 0, "quality_metrics": {}}

    try:
        import duckdb

        conn = duckdb.connect()

        # Read all parquet files
        file_pattern = "'" + "', '".join(str(f) for f in parquet_files) + "'"

        # Basic statistics
        total_records = conn.execute(
            f"SELECT COUNT(*) FROM read_parquet([{file_pattern}])"
        ).fetchone()[0]

        # Text length statistics
        text_length_stats = conn.execute(f"""
            SELECT
                MIN(LENGTH(text)) as min_length,
                MAX(LENGTH(text)) as max_length,
                AVG(LENGTH(text)) as avg_length,
                MEDIAN(LENGTH(text)) as median_length
            FROM read_parquet([{file_pattern}])
            WHERE text IS NOT NULL
        """).fetchone()

        # Duplicate check
        duplicates = conn.execute(f"""
            SELECT COUNT(*) - COUNT(DISTINCT text_hash) as duplicates
            FROM read_parquet([{file_pattern}])
            WHERE text_hash IS NOT NULL
        """).fetchone()[0]

        # Source breakdown
        source_breakdown = conn.execute(f"""
            SELECT source, COUNT(*) as count
            FROM read_parquet([{file_pattern}])
            GROUP BY source
            ORDER BY count DESC
        """).fetchall()

        quality_metrics = {
            "total_records": total_records,
            "total_files": len(parquet_files),
            "text_length": {
                "min": text_length_stats[0],
                "max": text_length_stats[1],
                "avg": round(text_length_stats[2], 2),
                "median": round(text_length_stats[3], 2),
            },
            "duplicates": duplicates,
            "deduplication_rate": round(duplicates / total_records * 100, 2)
            if total_records > 0
            else 0,
            "source_breakdown": {row[0]: row[1] for row in source_breakdown},
        }

        # Write report if output path specified
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(quality_metrics, f, indent=2)
            logger.info(f"Wrote quality report to {output_path}")

        return quality_metrics

    except ImportError:
        raise ImportError("DuckDB required for quality checks. Install with: pip install duckdb")
