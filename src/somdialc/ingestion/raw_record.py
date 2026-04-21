"""
RawRecord: Intermediate representation between extraction and processing.

Decouples source-specific extraction from shared processing logic.
"""

from typing import Any, Optional


class RawRecord:
    """Intermediate record format between extract() and process() stages."""

    def __init__(
        self,
        title: str,
        text: str,
        url: str,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize raw record with title, text, url, and optional metadata."""
        self.title = title
        self.text = text
        self.url = url
        self.metadata = metadata or {}
