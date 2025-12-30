"""
RecordBuilder: Constructs standardized silver records.

Responsibilities:
- Build silver records from raw + processed data
- Merge metadata from multiple sources
- Add schema versioning fields
- Ensure consistent record structure
"""

import logging
from typing import Any, Optional

from ..version import __pipeline_version__
from .record_utils import build_silver_record

logger = logging.getLogger(__name__)


class RecordBuilder:
    """
    Builds standardized silver dataset records.

    Decouples record construction logic from pipeline orchestration.
    Provides consistent schema across all data sources.

    Example:
        >>> builder = RecordBuilder(
        ...     source="BBC-Somali",
        ...     date_accessed="2025-01-01",
        ...     run_id="20250101_120000_bbc-somali"
        ... )
        >>> record = builder.build_silver_record(
        ...     raw_record=RawRecord("Title", "Text", "https://example.com", {}),
        ...     cleaned_text="Cleaned text",
        ...     filter_metadata={},
        ...     source_type="news",
        ...     license_str="ODC-BY-1.0",
        ...     domain="news",
        ...     register="formal"
        ... )
    """

    def __init__(self, source: str, date_accessed: str, run_id: str, schema_version: str = "1.0"):
        """
        Initialize record builder.

        Args:
            source: Source identifier (e.g., "BBC-Somali")
            date_accessed: ISO date when data was accessed
            run_id: Unique run identifier for provenance
            schema_version: Schema version to use (default: "1.0")
        """
        self.source = source
        self.date_accessed = date_accessed
        self.run_id = run_id
        self.schema_version = schema_version

    def build_silver_record(
        self,
        raw_record: Any,  # RawRecord instance
        cleaned_text: str,
        filter_metadata: dict[str, Any],
        source_type: str,
        license_str: str,
        domain: str,
        register: str,
        pipeline_version: str = __pipeline_version__,
        language: str = "so",
        source_metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Build a standardized silver dataset record.

        Args:
            raw_record: RawRecord instance with title, text, url, metadata
            cleaned_text: Cleaned text content
            filter_metadata: Metadata updates from filters
            source_type: Type of source (wiki, news, social, corpus, web)
            license_str: License identifier
            domain: Content domain (news, encyclopedia, literature, etc.)
            register: Linguistic register (formal, informal, colloquial)
            pipeline_version: Version of processing pipeline (default: "2.1.0")
            language: ISO 639-1 language code (default: "so")
            source_metadata: Source-specific metadata (merged with raw_record.metadata)

        Returns:
            Dictionary with standardized schema including schema_version and run_id

        Example:
            >>> record = builder.build_silver_record(
            ...     raw_record=RawRecord("Title", "Text", "https://example.com", {"category": "sports"}),
            ...     cleaned_text="Cleaned text",
            ...     filter_metadata={"langid": "so"},
            ...     source_type="news",
            ...     license_str="ODC-BY-1.0",
            ...     domain="news",
            ...     register="formal"
            ... )
        """
        # Merge source-wide metadata with per-record metadata and filter metadata
        merged_metadata = {}
        if source_metadata:
            merged_metadata.update(source_metadata)
        merged_metadata.update(raw_record.metadata)
        merged_metadata.update(filter_metadata)

        # Extract source_id from metadata if available
        # This allows sources to populate source_id field (e.g., corpus_id for Språkbanken)
        source_id = raw_record.metadata.get("corpus_id") or raw_record.metadata.get("source_id")

        # Build silver record using shared utility
        record = build_silver_record(
            text=cleaned_text,
            title=raw_record.title,
            source=self.source,
            url=raw_record.url,
            date_accessed=self.date_accessed,
            source_type=source_type,
            language=language,
            license_str=license_str,
            pipeline_version=pipeline_version,
            source_metadata=merged_metadata,
            date_published=raw_record.metadata.get("date_published"),
            topic=raw_record.metadata.get("topic"),
            domain=domain,
            embedding=None,  # Placeholder for future embeddings
            register=register,
            source_id=source_id,
        )

        # Add schema versioning fields
        record["schema_version"] = self.schema_version
        record["run_id"] = self.run_id

        return record

    def add_metadata(self, record: dict[str, Any], **kwargs) -> dict[str, Any]:
        """
        Add additional metadata fields to a record.

        Args:
            record: Existing record dictionary
            **kwargs: Additional metadata fields to add

        Returns:
            Updated record dictionary

        Example:
            >>> record = builder.add_metadata(
            ...     record,
            ...     processing_duration=1.5,
            ...     quality_score=0.95
            ... )
        """
        record.update(kwargs)
        return record
