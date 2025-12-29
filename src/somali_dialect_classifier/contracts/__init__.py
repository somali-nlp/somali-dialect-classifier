"""
Contracts for pipeline stage interfaces.

Provides explicit TypedDict contracts that define the expected data schemas
between pipeline stages (ingestion → preprocessing → training).
"""

from .ingestion_output import (
    REQUIRED_FIELDS,
    IngestionOutputV1,
    validate_ingestion_output,
)

__all__ = [
    "IngestionOutputV1",
    "validate_ingestion_output",
    "REQUIRED_FIELDS",
]
