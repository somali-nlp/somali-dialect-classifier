"""
Text cleaning utilities for Somali NLP preprocessing.

Pure functions with no side effects - easily testable and reusable.
"""

import re
from typing import Optional, List, Protocol


class Cleaner(Protocol):
    """Protocol for text cleaner objects."""
    def clean(self, text: str) -> str:
        ...


class WikiMarkupCleaner:
    """Removes Wikipedia-specific markup from text."""

    def __init__(self):
        # Compile patterns once for performance
        self.link_with_text_pattern = re.compile(r'\[\[([^|\]]+)\|([^\]]+)\]\]')
        self.simple_link_pattern = re.compile(r'\[\[([^\]]+)\]\]')
        self.external_link_pattern = re.compile(r'\[([^\]]+)\]')
        self.template_pattern = re.compile(r'{{[^}]+}}')
        self.ref_pattern = re.compile(r'<ref[^>]*>.*?</ref>', re.DOTALL)
        self.html_pattern = re.compile(r'<[^>]+>')
        self.heading_pattern = re.compile(r'={2,}.*?={2,}')
        self.list_marker_pattern = re.compile(r'[#*:;]+')

    def clean(self, text: str) -> str:
        """
        Remove Wikipedia markup from text.

        Args:
            text: Raw Wikipedia text with markup

        Returns:
            Cleaned text without markup

        Example:
            >>> cleaner = WikiMarkupCleaner()
            >>> cleaner.clean("[[Link|display text]]")
            'display text'
        """
        # Links: [[link|text]] -> text
        text = self.link_with_text_pattern.sub(r'\2', text)
        # Links: [[link]] -> link
        text = self.simple_link_pattern.sub(r'\1', text)
        # External: [link] -> link
        text = self.external_link_pattern.sub(r'\1', text)
        # Remove templates: {{template}}
        text = self.template_pattern.sub('', text)
        # Remove references: <ref>...</ref>
        text = self.ref_pattern.sub('', text)
        # Remove HTML tags
        text = self.html_pattern.sub('', text)
        # Remove section headings: == Heading ==
        text = self.heading_pattern.sub('', text)
        # Remove list markers: *, #, :, ;
        text = self.list_marker_pattern.sub('', text)

        return text


class WhitespaceCleaner:
    """Normalizes whitespace in text."""

    def __init__(self):
        self.newline_pattern = re.compile(r'\n+')
        self.space_pattern = re.compile(r' +')

    def clean(self, text: str) -> str:
        """
        Normalize whitespace (collapse multiple spaces/newlines).

        Args:
            text: Text with potentially excessive whitespace

        Returns:
            Text with normalized whitespace

        Example:
            >>> cleaner = WhitespaceCleaner()
            >>> cleaner.clean("hello\\n\\n\\nworld")
            'hello\\nworld'
        """
        # Collapse multiple newlines
        text = self.newline_pattern.sub('\n', text)
        # Collapse multiple spaces
        text = self.space_pattern.sub(' ', text)
        return text.strip()


class TextCleaningPipeline:
    """
    Composable text cleaning pipeline.

    Example:
        >>> pipeline = TextCleaningPipeline([
        ...     WikiMarkupCleaner(),
        ...     WhitespaceCleaner()
        ... ])
        >>> pipeline.clean("[[Link|text]]  with   spaces")
        'text with spaces'
    """

    def __init__(self, cleaners: List['Cleaner']):
        """
        Initialize pipeline with list of cleaners.

        Args:
            cleaners: List of cleaner objects with clean() method
        """
        self.cleaners = cleaners

    def clean(self, text: str, min_length: int = 10) -> Optional[str]:
        """
        Run text through all cleaners in sequence.

        Args:
            text: Raw text to clean
            min_length: Minimum length threshold (return None if below)

        Returns:
            Cleaned text or None if below min_length threshold
        """
        for cleaner in self.cleaners:
            text = cleaner.clean(text)

        # Filter out very short text (likely not meaningful content)
        if len(text) < min_length:
            return None

        return text


class HTMLCleaner:
    """Removes HTML tags and entities from text."""

    def __init__(self):
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        self.html_entity_pattern = re.compile(r'&[a-zA-Z]+;|&#\d+;')

    def clean(self, text: str) -> str:
        """
        Remove HTML tags and entities.

        Args:
            text: Text with HTML markup

        Returns:
            Plain text without HTML

        Example:
            >>> cleaner = HTMLCleaner()
            >>> cleaner.clean("<p>Hello &amp; world</p>")
            'Hello & world'
        """
        # Remove HTML tags
        text = self.html_tag_pattern.sub('', text)
        # Decode common HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&nbsp;', ' ')
        # Remove any remaining entities
        text = self.html_entity_pattern.sub('', text)
        return text


def create_wikipedia_cleaner() -> TextCleaningPipeline:
    """
    Factory function to create standard Wikipedia cleaning pipeline.

    Returns:
        TextCleaningPipeline configured for Wikipedia text
    """
    return TextCleaningPipeline([
        WikiMarkupCleaner(),
        WhitespaceCleaner(),
    ])


def create_html_cleaner() -> TextCleaningPipeline:
    """
    Factory function to create HTML cleaning pipeline for news articles.

    Returns:
        TextCleaningPipeline configured for HTML content (BBC, VOA, etc.)
    """
    return TextCleaningPipeline([
        HTMLCleaner(),
        WhitespaceCleaner(),
    ])
