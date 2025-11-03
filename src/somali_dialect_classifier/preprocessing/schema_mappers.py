"""
Schema mappers for HuggingFace datasets.

Different HuggingFace datasets use different field names for the same concepts.
This module provides standardized mappers to extract text, URL, and metadata
from various dataset schemas.

Supported datasets:
- MC4 (Multilingual C4)
- OSCAR
- CulturaX
- mC4-like datasets
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class SchemaMapping:
    """
    Defines how to map dataset fields to standard schema.

    Attributes:
        text_field: Field containing main text content
        url_field: Field containing source URL (optional)
        timestamp_field: Field containing timestamp (optional)
        metadata_fields: Additional fields to include in metadata
        transform_fn: Optional transformation function for text
    """

    text_field: str
    url_field: Optional[str] = None
    timestamp_field: Optional[str] = None
    metadata_fields: list = None
    transform_fn: Optional[Callable] = None

    def __post_init__(self):
        """Set defaults."""
        if self.metadata_fields is None:
            self.metadata_fields = []


class DatasetSchemaMapper:
    """
    Maps various HuggingFace dataset schemas to standardized format.
    """

    # Predefined schema mappings
    SCHEMAS = {
        "mc4": SchemaMapping(
            text_field="text", url_field="url", timestamp_field="timestamp", metadata_fields=[]
        ),
        "oscar": SchemaMapping(
            text_field="text",
            url_field=None,  # OSCAR doesn't include URLs
            timestamp_field=None,
            metadata_fields=["meta"],  # OSCAR has 'meta' field with additional info
        ),
        "culturax": SchemaMapping(
            text_field="text",
            url_field="url",
            timestamp_field="timestamp",
            metadata_fields=["source", "language_score"],
        ),
        "madlad": SchemaMapping(
            text_field="text", url_field="url", timestamp_field=None, metadata_fields=["score"]
        ),
        "cc100": SchemaMapping(
            text_field="text",
            url_field=None,  # CC100 doesn't include URLs
            timestamp_field=None,
            metadata_fields=[],
        ),
    }

    def __init__(self, dataset_name: str, custom_mapping: Optional[SchemaMapping] = None):
        """
        Initialize schema mapper.

        Args:
            dataset_name: Name of the dataset (e.g., "mc4", "oscar")
            custom_mapping: Custom schema mapping (overrides predefined)
        """
        self.dataset_name = dataset_name.lower()

        if custom_mapping:
            self.mapping = custom_mapping
        elif self.dataset_name in self.SCHEMAS:
            self.mapping = self.SCHEMAS[self.dataset_name]
        else:
            # Default fallback mapping
            logger.warning(
                f"No predefined schema for dataset '{dataset_name}'. "
                f"Using default mapping (text_field='text')."
            )
            self.mapping = SchemaMapping(text_field="text")

    def extract_text(self, record: dict[str, Any]) -> Optional[str]:
        """
        Extract text content from record.

        Args:
            record: Dataset record dictionary

        Returns:
            Extracted text, or None if field missing
        """
        text = record.get(self.mapping.text_field)

        if text is None:
            logger.debug(
                f"Text field '{self.mapping.text_field}' not found in record. "
                f"Available fields: {list(record.keys())}"
            )
            return None

        # Apply transformation if defined
        if self.mapping.transform_fn:
            text = self.mapping.transform_fn(text)

        return text

    def extract_url(self, record: dict[str, Any]) -> Optional[str]:
        """
        Extract URL from record.

        Args:
            record: Dataset record dictionary

        Returns:
            Extracted URL, or None if field missing or not defined
        """
        if not self.mapping.url_field:
            return None

        return record.get(self.mapping.url_field)

    def extract_timestamp(self, record: dict[str, Any]) -> Optional[str]:
        """
        Extract timestamp from record.

        Args:
            record: Dataset record dictionary

        Returns:
            Extracted timestamp, or None if field missing or not defined
        """
        if not self.mapping.timestamp_field:
            return None

        return record.get(self.mapping.timestamp_field)

    def extract_metadata(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Extract additional metadata fields from record.

        Args:
            record: Dataset record dictionary

        Returns:
            Dictionary of metadata fields
        """
        metadata = {}

        for field in self.mapping.metadata_fields:
            if field in record:
                metadata[field] = record[field]

        return metadata

    def map_record(self, record: dict[str, Any], index: Optional[int] = None) -> dict[str, Any]:
        """
        Map dataset record to standardized format.

        Args:
            record: Dataset record dictionary
            index: Optional record index (used for synthetic URL if no URL field)

        Returns:
            Standardized record with fields:
            - text: Main text content
            - url: Source URL (or synthetic)
            - timestamp: Optional timestamp
            - metadata: Additional metadata
        """
        # Extract fields
        text = self.extract_text(record)
        url = self.extract_url(record)
        timestamp = self.extract_timestamp(record)
        metadata = self.extract_metadata(record)

        # Generate synthetic URL if missing
        if url is None and index is not None:
            url = f"huggingface://{self.dataset_name}/record/{index}"
        elif url is None:
            url = f"huggingface://{self.dataset_name}/record/unknown"

        # Add dataset info to metadata
        metadata["dataset_name"] = self.dataset_name
        if timestamp:
            metadata["timestamp"] = timestamp

        return {"text": text, "url": url, "timestamp": timestamp, "metadata": metadata}

    def validate_record(self, record: dict[str, Any]) -> bool:
        """
        Validate that record contains required fields.

        Args:
            record: Dataset record dictionary

        Returns:
            True if valid, False otherwise
        """
        # Check required text field
        if self.mapping.text_field not in record:
            logger.warning(f"Record missing required text field: {self.mapping.text_field}")
            return False

        # Check that text is not empty
        text = record.get(self.mapping.text_field)
        if not text or not isinstance(text, str):
            logger.debug(f"Text field empty or invalid type: {type(text)}")
            return False

        return True


# Convenience factory function


def get_schema_mapper(dataset_name: str) -> DatasetSchemaMapper:
    """
    Get schema mapper for dataset.

    Args:
        dataset_name: Name of the dataset

    Returns:
        DatasetSchemaMapper instance

    Example:
        >>> mapper = get_schema_mapper("mc4")
        >>> record = {"text": "Hello", "url": "http://example.com", "timestamp": "2023-01-01"}
        >>> mapped = mapper.map_record(record)
        >>> print(mapped["text"])
        Hello
    """
    return DatasetSchemaMapper(dataset_name)


# Example usage and testing
if __name__ == "__main__":
    # Test MC4 mapping
    mc4_mapper = get_schema_mapper("mc4")
    mc4_record = {
        "text": "Waa maxay barnaamijkan?",
        "url": "https://example.so/article",
        "timestamp": "2023-01-15T10:30:00",
    }

    mapped = mc4_mapper.map_record(mc4_record, index=0)
    print("MC4 Mapping:", mapped)

    # Test OSCAR mapping (no URL field)
    oscar_mapper = get_schema_mapper("oscar")
    oscar_record = {"text": "Magaalada Muqdisho", "meta": {"source": "web", "quality": 0.95}}

    mapped = oscar_mapper.map_record(oscar_record, index=123)
    print("OSCAR Mapping:", mapped)

    # Test custom mapping
    custom_mapping = SchemaMapping(
        text_field="content", url_field="link", metadata_fields=["author", "category"]
    )

    custom_mapper = DatasetSchemaMapper("custom", custom_mapping)
    custom_record = {
        "content": "Custom text",
        "link": "https://custom.com",
        "author": "John Doe",
        "category": "news",
    }

    mapped = custom_mapper.map_record(custom_record)
    print("Custom Mapping:", mapped)
