"""
Schema versioning system for silver layer data.

This module provides:
- Schema registry with versioned Pydantic models
- Schema validation
"""

from .registry import (
    CURRENT_SCHEMA_VERSION,
    SCHEMA_REGISTRY,
    SchemaV1_0,
    get_current_schema,
    get_schema,
)
from .validator import SchemaValidator

__all__ = [
    "SchemaV1_0",
    "SCHEMA_REGISTRY",
    "CURRENT_SCHEMA_VERSION",
    "get_schema",
    "get_current_schema",
    "SchemaValidator",
]
