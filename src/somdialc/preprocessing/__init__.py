"""
Preprocessing module for Somali Dialect Classifier.

This module provides validation and entry points for preprocessing pipeline stages.
It ensures that all ingestion output conforms to the IngestionOutputV1 contract
before allowing data to proceed to preprocessing.
"""

from .validator import (
    ValidationError,
    iter_validated_records,
    validate_silver_parquet,
)

__all__ = [
    "ValidationError",
    "validate_silver_parquet",
    "iter_validated_records",
]
