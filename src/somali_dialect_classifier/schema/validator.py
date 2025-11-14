"""
Schema validation for silver layer data.

Validates data against versioned schemas before writing.
"""

import logging
from typing import Any, Optional

import pandas as pd
from pydantic import ValidationError

from .registry import CURRENT_SCHEMA_VERSION, get_schema

logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    Validates data against versioned schemas.

    Provides both record-level and DataFrame-level validation.
    """

    def validate_record(
        self, record: dict[str, Any], version: Optional[str] = None
    ) -> tuple[bool, list[str]]:
        """
        Validate a single record against schema.

        Args:
            record: Data record to validate
            version: Schema version (default: current)

        Returns:
            Tuple of (is_valid, error_messages)
                - is_valid: True if record passes validation
                - error_messages: List of validation error messages (empty if valid)

        Example:
            >>> validator = SchemaValidator()
            >>> record = {"id": "abc", "text": "hello", ...}
            >>> is_valid, errors = validator.validate_record(record)
            >>> if not is_valid:
            ...     print(f"Validation failed: {errors}")
        """
        if version is None:
            version = CURRENT_SCHEMA_VERSION

        schema = get_schema(version)

        try:
            # Pydantic validation
            schema(**record)
            return True, []
        except ValidationError as e:
            # Extract error messages in readable format
            errors = []
            for err in e.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                msg = err["msg"]
                errors.append(f"{field}: {msg}")
            return False, errors

    def validate_dataframe(
        self, df: pd.DataFrame, version: Optional[str] = None
    ) -> tuple[bool, pd.DataFrame]:
        """
        Validate entire DataFrame against schema.

        Args:
            df: DataFrame to validate
            version: Schema version (default: current)

        Returns:
            Tuple of (all_valid, df_with_validation_status)
                - all_valid: True if all records pass validation
                - df_with_validation_status: DataFrame with added validation columns:
                    - _validation_valid: bool indicating if record is valid
                    - _validation_errors: list of error messages

        Example:
            >>> validator = SchemaValidator()
            >>> df = pd.DataFrame([...])
            >>> all_valid, validated_df = validator.validate_dataframe(df)
            >>> invalid_records = validated_df[~validated_df["_validation_valid"]]
            >>> print(f"Found {len(invalid_records)} invalid records")
        """
        if version is None:
            version = CURRENT_SCHEMA_VERSION

        validation_results = []

        for idx, row in df.iterrows():
            is_valid, errors = self.validate_record(row.to_dict(), version)
            validation_results.append(
                {"index": idx, "valid": is_valid, "errors": errors if not is_valid else []}
            )

        # Add validation columns to df (make a copy to avoid modifying original)
        df = df.copy()
        df["_validation_valid"] = [r["valid"] for r in validation_results]
        df["_validation_errors"] = [r["errors"] for r in validation_results]

        all_valid = all(r["valid"] for r in validation_results)

        if not all_valid:
            invalid_count = sum(1 for r in validation_results if not r["valid"])
            logger.warning(
                f"Schema validation failed for {invalid_count}/{len(df)} records "
                f"(schema v{version})"
            )

            # Log first few validation errors for debugging
            for _i, result in enumerate(validation_results[:5]):
                if not result["valid"]:
                    logger.debug(
                        f"Record {result['index']} validation errors: {result['errors']}"
                    )

        return all_valid, df

    def add_schema_version(
        self, df: pd.DataFrame, version: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Add schema_version field to all records in DataFrame.

        Args:
            df: DataFrame to modify
            version: Schema version to add (default: current)

        Returns:
            DataFrame with schema_version column (copy, original not modified)

        Example:
            >>> validator = SchemaValidator()
            >>> df = pd.DataFrame([...])
            >>> df_with_version = validator.add_schema_version(df)
            >>> assert all(df_with_version["schema_version"] == "1.0")
        """
        if version is None:
            version = CURRENT_SCHEMA_VERSION

        df = df.copy()
        df["schema_version"] = version
        return df

    def get_validation_report(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Generate validation report for a DataFrame.

        Must be called after validate_dataframe().

        Args:
            df: DataFrame with validation columns (_validation_valid, _validation_errors)

        Returns:
            Dictionary with validation statistics:
                - total_records: Total number of records
                - valid_records: Number of valid records
                - invalid_records: Number of invalid records
                - validation_rate: Percentage of valid records
                - error_summary: Count of each error type

        Raises:
            ValueError: If DataFrame doesn't have validation columns

        Example:
            >>> validator = SchemaValidator()
            >>> all_valid, df = validator.validate_dataframe(df)
            >>> report = validator.get_validation_report(df)
            >>> print(f"Validation rate: {report['validation_rate']:.1f}%")
        """
        if "_validation_valid" not in df.columns or "_validation_errors" not in df.columns:
            raise ValueError(
                "DataFrame must be validated first using validate_dataframe()"
            )

        total_records = len(df)
        valid_records = df["_validation_valid"].sum()
        invalid_records = total_records - valid_records
        validation_rate = (valid_records / total_records * 100) if total_records > 0 else 0.0

        # Count error types
        error_summary = {}
        for errors in df[~df["_validation_valid"]]["_validation_errors"]:
            for error in errors:
                # Extract error type (before first colon)
                error_type = error.split(":")[0] if ":" in error else error
                error_summary[error_type] = error_summary.get(error_type, 0) + 1

        return {
            "total_records": total_records,
            "valid_records": int(valid_records),
            "invalid_records": invalid_records,
            "validation_rate": validation_rate,
            "error_summary": error_summary,
        }
