"""
Record utilities for generating IDs, hashes, and metadata.

Pure functions with no side effects - easily testable and reusable.
"""

import hashlib
import json
from typing import Optional


def generate_text_hash(text: str) -> str:
    """
    Generate SHA256 hash of text content for deduplication.

    Args:
        text: Text content to hash

    Returns:
        Hex string of SHA256 hash

    Example:
        >>> generate_text_hash("hello world")
        '...' # 64-character hex string
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_record_id(*components: str) -> str:
    """
    Generate deterministic ID from components.

    Args:
        *components: String components to combine for ID generation

    Returns:
        Hex string of SHA256 hash

    Example:
        >>> generate_record_id("Wikipedia", "Somali", "article-title")
        '...' # 64-character hex string
    """
    combined = "".join(components)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def count_tokens(text: str) -> int:
    """
    Simple whitespace-based token counting.

    Args:
        text: Text to count tokens in

    Returns:
        Number of tokens

    Example:
        >>> count_tokens("hello world")
        2
    """
    return len(text.split())


def build_silver_record(
    text: str,
    title: str,
    source: str,
    url: str,
    date_accessed: str,
    source_type: str = "wiki",
    language: str = "so",
    license_str: str = "CC-BY-SA-3.0",
    pipeline_version: str = "2.1.0",
    source_metadata: Optional[dict] = None,
    date_published: Optional[str] = None,
    topic: Optional[str] = None,
    domain: Optional[str] = None,
    embedding: Optional[str] = None,
    register: Optional[str] = None,
    source_id: Optional[str] = None,
) -> dict:
    """
    Build a standardized silver dataset record.

    This function creates a consistent schema for all data sources.

    Args:
        text: Cleaned text content
        title: Document title
        source: Source name (e.g., "Wikipedia-Somali")
        url: Source URL
        date_accessed: ISO date when data was accessed
        source_type: Type of source (wiki, news, social, corpus, web)
        language: ISO 639-1 language code
        license_str: License identifier
        pipeline_version: Version of processing pipeline (default: "2.1.0")
        source_metadata: Additional source-specific metadata
        date_published: ISO date when content was published (if known)
        topic: Content topic/category (if known)
        domain: Content domain (news, literature, science, etc.)
        embedding: Embedding representation (JSON string or None)
        register: Linguistic register ("formal", "informal", "colloquial")
                  Defaults based on source_type:
                  - wiki, news, corpus, web → "formal"
                  - social → "informal"
        source_id: Source-specific identifier (e.g., corpus_id for Språkbanken,
                   article_id for BBC, page_id for Wikipedia)

    Returns:
        Dictionary with standardized schema

    Example:
        >>> record = build_silver_record(
        ...     text="Hello world",
        ...     title="Test",
        ...     source="Wikipedia-Somali",
        ...     url="https://so.wikipedia.org/wiki/Test",
        ...     date_accessed="2025-01-01",
        ...     domain="encyclopedia",
        ...     register="formal"
        ... )
        >>> record["id"]
        '...' # 64-character hex string
    """
    text_hash = generate_text_hash(text)
    record_id = generate_record_id(title, url)
    tokens = count_tokens(text)

    # JSON-serialize source_metadata to match schema and prevent schema drift
    metadata_json = json.dumps(source_metadata or {}, sort_keys=True)

    # Infer register from source_type if not explicitly provided
    if register is None:
        if source_type in {"wiki", "news", "corpus", "web"}:
            register = "formal"
        elif source_type == "social":
            register = "informal"
        else:
            register = "formal"  # Default

    return {
        "id": record_id,
        "text": text,
        "title": title,
        "source": source,
        "source_type": source_type,
        "url": url,
        "source_id": source_id,  # Source-specific ID (e.g., corpus_id, article_id)
        "date_published": date_published,
        "date_accessed": date_accessed,
        "language": language,
        "license": license_str,
        "topic": topic,
        "tokens": tokens,
        "text_hash": text_hash,
        "pipeline_version": pipeline_version,
        "source_metadata": metadata_json,  # JSON string, not dict
        "domain": domain,  # Content domain (news, literature, science, etc.)
        "embedding": embedding,  # Placeholder for future embeddings
        "register": register,  # Linguistic register (formal, informal, colloquial)
    }
