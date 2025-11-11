"""
Schema Registry for Silver Layer Data.

Defines all schema versions with Pydantic models for validation.
Starting fresh at v1.0 - no legacy data migration needed.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ProcessingStage(str, Enum):
    """Valid processing stages."""

    RAW = "raw"
    STAGING = "staging"
    SILVER = "silver"


class SourceType(str, Enum):
    """Valid source types."""

    WIKI = "wiki"
    NEWS = "news"
    CORPUS = "corpus"
    WEB = "web"
    SOCIAL = "social"


class Register(str, Enum):
    """Valid linguistic registers."""

    FORMAL = "formal"
    INFORMAL = "informal"
    COLLOQUIAL = "colloquial"


class SchemaV1_0(BaseModel):
    """
    Silver layer schema version 1.0.

    This is the initial production schema, starting fresh with no legacy data.
    All future data will include schema_version and run_id fields from day one.

    Matches the output of build_silver_record() function.
    """

    # Core fields
    id: str = Field(..., description="Unique record identifier (SHA256 hash of title + URL)")
    text: str = Field(..., description="Cleaned text content")
    title: str = Field(..., description="Document title or heading")

    # Source information
    source: str = Field(..., description="Source identifier (Wikipedia-Somali, BBC-Somali, etc.)")
    source_type: str = Field(..., description="Source category (wiki, news, corpus, web, social)")
    url: str = Field(..., description="Source URL or identifier")
    source_id: Optional[str] = Field(
        None, description="Source-specific identifier (corpus_id, article_id, etc.)"
    )

    # Temporal metadata
    date_published: Optional[str] = Field(None, description="Publication date (ISO 8601 format)")
    date_accessed: str = Field(..., description="Access date (ISO 8601 format)")

    # Content metadata
    language: str = Field(default="so", description="ISO 639-1 language code")
    license: str = Field(..., description="License identifier")  # Fixed: 'license' not 'licence'
    topic: Optional[str] = Field(None, description="Content topic/category")
    tokens: int = Field(..., ge=0, description="Token count (whitespace-based)")

    # Processing metadata
    text_hash: str = Field(..., description="SHA256 hash of text (for deduplication)")
    pipeline_version: str = Field(..., description="Processing pipeline version")
    source_metadata: str = Field(
        default="{}", description="Source-specific metadata (JSON string)"
    )

    # Domain and embedding (part of v1.0 schema)
    domain: str = Field(..., description="Content domain (news, encyclopedia, literature, etc.)")
    embedding: Optional[str] = Field(
        None, description="Embedding representation (JSON string, optional)"
    )

    # Register (part of v1.0 schema)
    linguistic_register: str = Field(
        ...,
        alias="register",
        description="Linguistic register (formal, informal, colloquial)"
    )

    # Provenance (NEW in schema v1.0)
    schema_version: Literal["1.0"] = Field(
        default="1.0", description="Schema version for tracking evolution"
    )
    run_id: str = Field(
        ..., description="Run identifier for provenance (links to logs and metrics)"
    )

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Ensure text is not empty."""
        if not v or not v.strip():
            raise ValueError("text cannot be empty")
        return v

    @field_validator("source")
    @classmethod
    def source_valid(cls, v: str) -> str:
        """Validate source identifier."""
        allowed_sources = {
            "wikipedia-somali",
            "bbc-somali",
            "sprakbanken-somali",
            "tiktok-somali",
            "huggingface-somali",
        }
        source_lower = v.lower().replace("_", "-")
        # Check if source starts with any allowed prefix
        is_valid = any(source_lower.startswith(prefix) for prefix in allowed_sources)
        if not is_valid:
            raise ValueError(f"source must start with one of {allowed_sources}, got: {v}")
        return v

    @field_validator("source_type")
    @classmethod
    def source_type_valid(cls, v: str) -> str:
        """Validate source type."""
        try:
            SourceType(v)
        except ValueError:
            valid_types = [st.value for st in SourceType]
            raise ValueError(f"source_type must be one of {valid_types}, got: {v}")
        return v

    @field_validator("linguistic_register")
    @classmethod
    def register_valid(cls, v: str) -> str:
        """Validate linguistic register."""
        try:
            Register(v)
        except ValueError:
            valid_registers = [r.value for r in Register]
            raise ValueError(f"register must be one of {valid_registers}, got: {v}")
        return v

    @field_validator("language")
    @classmethod
    def language_valid(cls, v: str) -> str:
        """Validate language code (currently only Somali supported)."""
        if v not in {"so", "som"}:
            raise ValueError(f"language must be 'so' or 'som', got: {v}")
        return v

    @field_validator("tokens")
    @classmethod
    def tokens_reasonable(cls, v: int) -> int:
        """Ensure token count is reasonable (not negative or suspiciously high)."""
        if v < 0:
            raise ValueError("tokens cannot be negative")
        if v > 1_000_000:
            raise ValueError("tokens suspiciously high (>1M), possible counting error")
        return v

    @field_validator("date_accessed", "date_published")
    @classmethod
    def date_format_valid(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO 8601 date format."""
        if v is None:
            return v
        # Try parsing as ISO date
        try:
            # Accept both date-only (YYYY-MM-DD) and datetime formats
            if "T" in v:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            else:
                datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"date must be in ISO 8601 format, got: {v}")
        return v

    model_config = {"extra": "forbid", "validate_assignment": True, "populate_by_name": True}


# Schema registry mapping
SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "1.0": SchemaV1_0,
    # Future versions will be added here:
    # "1.1": SchemaV1_1,
    # "2.0": SchemaV2_0,
}

CURRENT_SCHEMA_VERSION = "1.0"


def get_schema(version: str) -> type[BaseModel]:
    """
    Get schema model for a specific version.

    Args:
        version: Schema version (e.g., "1.0", "1.1")

    Returns:
        Pydantic model class for the schema

    Raises:
        ValueError: If version is not in registry
    """
    if version not in SCHEMA_REGISTRY:
        available = list(SCHEMA_REGISTRY.keys())
        raise ValueError(
            f"Unknown schema version: {version}. Available versions: {available}"
        )
    return SCHEMA_REGISTRY[version]


def get_current_schema() -> type[BaseModel]:
    """
    Get the current production schema.

    Returns:
        Pydantic model class for current schema version
    """
    return SCHEMA_REGISTRY[CURRENT_SCHEMA_VERSION]
