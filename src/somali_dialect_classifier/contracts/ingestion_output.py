"""
Ingestion Output Contract v1.0

This contract defines the expected output schema from the ingestion phase
for consumption by preprocessing and downstream stages.

VERSIONING STRATEGY:
- `schema_version` field in records indicates schema version
- Major version changes (1.x → 2.x) require migration scripts
- Minor version changes (1.0 → 1.1) are backward compatible (new optional fields only)
- Breaking changes MUST increment major version

CONTRACT DESIGN RATIONALE:
This contract sits between the full SchemaV1_0 Pydantic model (which validates
all fields for storage) and downstream consumers who only need a subset of fields.

The contract specifies:
1. REQUIRED fields that downstream consumers can depend on
2. OPTIONAL fields that may be present for enrichment
3. Validation rules that complement Pydantic schema validation

RELATIONSHIP TO SchemaV1_0:
- IngestionOutputV1 is a SUBSET of SchemaV1_0
- All fields in this contract map 1:1 to SchemaV1_0 fields
- SchemaV1_0 includes additional fields for storage (title, source_id, etc.)
- This contract focuses on the minimum interface for downstream consumption
"""

from typing import Literal, Optional, TypedDict


class IngestionOutputV1(TypedDict, total=False):
    """
    Schema for ingestion output records.

    This contract defines the interface between ingestion and preprocessing stages.
    All records written to silver Parquet files MUST include required fields.

    REQUIRED FIELDS (must be present and non-null):
    - id: Unique identifier for deduplication across pipeline runs
    - text: Cleaned text content (non-empty after quality filters)
    - source: Source identifier for filtering and metrics
    - run_id: Links record to logs/metrics for provenance
    - schema_version: Enables schema migration and version compatibility checks
    - tokens: Word count for filtering and analysis
    - text_hash: Content-based deduplication key
    - linguistic_register: Formality level for dialect analysis

    OPTIONAL FIELDS (may be present depending on source):
    - topic: Content classification (if inferred by filters or extracted from source)
    - detected_lang: Language detection result (if language filter applied)
    - lang_confidence: Confidence score for language detection (0.0-1.0)
    - url: Source URL (for web-based sources like BBC, Wikipedia, HuggingFace)
    - timestamp: Record creation timestamp (ISO 8601 format)

    EVOLUTION NOTES:
    Future v1.1 might add:
    - quality_score: float (composite quality metric)
    - dialect_hints: list[str] (lexical markers for dialect classification)

    Future v2.0 breaking changes might include:
    - Splitting linguistic_register into register + formality_score
    - Adding required dialect_label field after annotation
    """

    # REQUIRED - Core identification
    id: str  # SHA256 hash of title + URL, globally unique
    text: str  # Cleaned, non-empty text content
    source: str  # Source identifier (e.g., "wikipedia-somali", "bbc-somali")

    # REQUIRED - Processing metadata
    tokens: int  # Whitespace token count (used for length-based filtering)
    text_hash: str  # SHA256 hash of text for cross-run deduplication
    linguistic_register: str  # "formal", "informal", or "colloquial" (stored as "register")

    # REQUIRED - Provenance tracking
    run_id: str  # Links to metrics/logs for pipeline traceability
    schema_version: Literal["1.0"]  # Version tracking for schema evolution

    # OPTIONAL - Enrichment fields (may be absent)
    topic: Optional[str]  # Extracted or inferred topic category
    detected_lang: Optional[str]  # Language detection result (ISO 639 code)
    lang_confidence: Optional[float]  # Confidence score (0.0-1.0)
    url: Optional[str]  # Source URL if applicable
    timestamp: Optional[str]  # ISO 8601 timestamp (e.g., "2025-12-29T10:00:00Z")


# Required fields that MUST be present and non-null
# Note: "linguistic_register" is the canonical name in this contract
# However, Parquet storage uses "register" as the field name (PyArrow schema)
#
# STRICT VALIDATION (2025-12-29):
# All fields below are REQUIRED and must be present with non-null values.
# No patching or defaulting is allowed - validation must FAIL FAST on missing fields.
REQUIRED_FIELDS = {
    "id",
    "text",
    "source",
    "run_id",  # Required for provenance tracking
    "schema_version",  # Required for schema evolution
    "tokens",
    "text_hash",
    "linguistic_register",  # or "register" in Parquet storage
}

# Valid values for linguistic_register field
VALID_REGISTERS = {"formal", "informal", "colloquial"}


def validate_ingestion_output(record: dict) -> tuple[bool, list[str]]:
    """
    Validate a record against IngestionOutputV1 contract with STRICT fail-fast semantics.

    STRICT VALIDATION PHILOSOPHY:
    - NO patching or fixing of invalid records
    - NO defaulting of missing required fields
    - FAIL FAST with clear, actionable error messages
    - All required fields must be present and non-null

    This validation is COMPLEMENTARY to SchemaV1_0 Pydantic validation:
    - Pydantic validates ALL fields for storage correctness
    - This validates the SUBSET of fields required by downstream consumers

    NOTE ON FIELD NAMES:
    - Contract uses "linguistic_register" as the canonical name
    - Parquet storage uses "register" (PyArrow schema field name)
    - This validation accepts BOTH names for compatibility

    Args:
        record: Dictionary to validate against contract

    Returns:
        Tuple of (is_valid, error_messages)
            - is_valid: True if record satisfies contract requirements
            - error_messages: List of validation errors (empty if valid)

    Validation Rules (STRICT - no tolerance):
    1. All REQUIRED_FIELDS must be present (accepts both "linguistic_register" and "register")
    2. Required fields cannot be None or empty
    3. schema_version must be EXACTLY "1.0" (string comparison)
    4. linguistic_register/register must be in VALID_REGISTERS
    5. tokens must be int >= 0
    6. text must be non-empty string
    7. text_hash must be non-empty string
    8. id must be non-empty string
    9. source must be non-empty string
    10. run_id must be non-empty string
    11. lang_confidence must be 0.0-1.0 (if present)

    Example:
        >>> record = {
        ...     "id": "abc123",
        ...     "text": "Test text",
        ...     "source": "wikipedia-somali",
        ...     "run_id": "20251229_100000_wikipedia",
        ...     "schema_version": "1.0",
        ...     "tokens": 2,
        ...     "text_hash": "hash123",
        ...     "linguistic_register": "formal"
        ... }
        >>> is_valid, errors = validate_ingestion_output(record)
        >>> assert is_valid
    """
    errors = []

    # STRICT CHECK: All required fields must be present and non-null
    # Special case: accept both "linguistic_register" and "register" (Parquet field name)
    for field in REQUIRED_FIELDS:
        if field == "linguistic_register":
            # Accept either canonical name or Parquet storage name
            has_field = "linguistic_register" in record or "register" in record
            if not has_field:
                errors.append("Field 'linguistic_register' is missing (required)")
                continue

            # Check for null values
            register_value = record.get("linguistic_register") or record.get("register")
            if register_value is None:
                errors.append("Field 'linguistic_register' is None (required, must be non-null)")
                continue

            # Check for empty string (strict)
            if not isinstance(register_value, str) or not register_value.strip():
                errors.append("Field 'linguistic_register' is empty or whitespace (required, must be non-empty)")
        else:
            # Standard field check - STRICT
            if field not in record:
                errors.append(f"Field '{field}' is missing (required)")
                continue

            field_value = record[field]

            # Check for null
            if field_value is None:
                errors.append(f"Field '{field}' is None (required, must be non-null)")
                continue

            # Check for empty strings on string fields
            if field in {"id", "text", "source", "run_id", "text_hash", "schema_version"}:
                if not isinstance(field_value, str):
                    errors.append(
                        f"Field '{field}' has invalid type: {type(field_value).__name__} (expected str)"
                    )
                elif not field_value.strip():
                    errors.append(f"Field '{field}' is empty or whitespace (required, must be non-empty)")

    # STRICT: schema_version must be EXACTLY "1.0"
    if "schema_version" in record:
        schema_ver = record["schema_version"]
        if schema_ver != "1.0":
            errors.append(
                f"Field 'schema_version' has invalid value: '{schema_ver}' (expected exactly '1.0')"
            )

    # STRICT: linguistic_register must be in VALID_REGISTERS
    register_value = record.get("linguistic_register") or record.get("register")
    if register_value is not None:
        if register_value not in VALID_REGISTERS:
            errors.append(
                f"Field 'linguistic_register' has invalid value: '{register_value}' "
                f"(must be one of {sorted(VALID_REGISTERS)})"
            )

    # STRICT: tokens must be int >= 0
    if "tokens" in record:
        tokens_value = record["tokens"]
        if tokens_value is not None:
            if not isinstance(tokens_value, int):
                errors.append(f"Field 'tokens' has invalid type: {type(tokens_value).__name__} (expected int)")
            elif tokens_value < 0:
                errors.append(f"Field 'tokens' has invalid value: {tokens_value} (must be >= 0)")

    # STRICT: text must be non-empty string (already checked above, but double-check for clarity)
    if "text" in record and record["text"] is not None:
        text_value = record["text"]
        if not isinstance(text_value, str):
            # Already caught above, but include for completeness
            pass
        elif not text_value.strip():
            # Already caught above
            pass

    # OPTIONAL field validation: lang_confidence (if present, must be valid)
    if "lang_confidence" in record and record["lang_confidence"] is not None:
        conf_value = record["lang_confidence"]
        if not isinstance(conf_value, (int, float)):
            errors.append(
                f"Field 'lang_confidence' has invalid type: {type(conf_value).__name__} (expected float)"
            )
        elif not 0.0 <= conf_value <= 1.0:
            errors.append(
                f"Field 'lang_confidence' has invalid value: {conf_value} (must be in range [0.0, 1.0])"
            )

    return (len(errors) == 0, errors)
