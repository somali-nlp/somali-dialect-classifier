"""
Text cleaning utilities for Somali NLP preprocessing.

Pure functions with no side effects - easily testable and reusable.
"""

import re
import unicodedata
from typing import Optional, Protocol


class Cleaner(Protocol):
    """Protocol for text cleaner objects."""

    def clean(self, text: str) -> str: ...


class UnicodeNormalizationCleaner:
    """Applies NFKC Unicode normalisation to canonicalise characters."""

    def clean(self, text: str) -> str:
        return unicodedata.normalize("NFKC", text)


class WikiMarkupCleaner:
    """Removes Wikipedia-specific markup from text."""

    def __init__(self):
        # Compile patterns once for performance

        # Image/file links: [[File:foo.jpg|thumb|200px|caption]] — strip whole match
        self.image_file_pattern = re.compile(
            r"\[\[(File|Image|file|image):[^\]]*\]\]", re.IGNORECASE
        )
        # Bold: '''text''' → text
        self.bold_pattern = re.compile(r"'''(.*?)'''", re.DOTALL)
        # Italic: ''text'' → text
        self.italic_pattern = re.compile(r"''(.*?)''", re.DOTALL)
        # Pipe-delimited image attributes like "thumb|200px|" that precede captions
        self.thumb_pipe_pattern = re.compile(r"\bthumb\|[^|]*\|")
        # Inter-wiki prefix fragments left after partial link stripping.
        # Known residues observed in Somali silver (not exhaustive):
        #   wtr  — [[wikt:...]]  (Wiktionary); fused as e.g. "wtrGeorge"
        #   wes  — [[es:...]]    (Spanish Wikipedia); fused as e.g. "wesindian"
        #   wit  — [[wit:...]]   (Wiktionary variant); fused as e.g. "witOceano"
        # Require position context (start-of-string/line/whitespace/pipe) and
        # specific lookahead so common English words (with, west, witness) are
        # not accidentally stripped.
        self.interwiki_fragment_pattern = re.compile(
            r"(?:(?<=\n)|(?<=\s)|(?<=\|)|\A)"
            r"(?:wtr(?=[A-Z])|wit(?=[A-Z])|wes(?=[A-Z]|indian\b))"
        )

        # Orphan (unpaired) triple-quote: any remaining ''' not consumed by
        # the bold_pattern above (e.g. truncated markup, ''' followed by digits).
        self.orphan_bold_pattern = re.compile(r"'{3}")

        self.link_with_text_pattern = re.compile(r"\[\[([^|\]]+)\|([^\]]+)\]\]")
        # Interwiki / sister-project links — strip whole, not just brackets.
        # Examples: [[w:tr:Foo]] (Turkish Wikipedia), [[w:es:Foo]],
        # [[wikt:Foo]] / [[wiktionary:Foo]], [[wikipedia:Foo]]. If we let
        # simple_link_pattern unwrap them to "w:tr:Foo", the colons get
        # consumed downstream by list_marker_pattern and we end up with
        # residue like "wtrFoo" / "wesFoo" / "witFoo" leaking into silver.
        self.interwiki_link_pattern = re.compile(
            r"\[\[(?:w|wikt|wiktionary|wikipedia|w:[a-z]{2,3}):[^\]]*\]\]",
            re.IGNORECASE,
        )
        self.simple_link_pattern = re.compile(r"\[\[([^\]]+)\]\]")
        self.external_link_pattern = re.compile(r"\[([^\]]+)\]")
        # Match templates/infoboxes - greedy to consume entire template blocks
        # Simple approach: match from {{ to }} greedily (handles most templates)
        self.template_pattern = re.compile(r"{{[^}]*}}", re.DOTALL)
        self.ref_pattern = re.compile(r"<ref[^>]*>.*?</ref>", re.DOTALL)
        self.html_pattern = re.compile(r"<[^>]+>")
        self.heading_pattern = re.compile(r"={2,}.*?={2,}")
        self.list_marker_pattern = re.compile(r"[#*:;]+")

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
        # Strip image/file links entirely (before generic link processing)
        text = self.image_file_pattern.sub("", text)
        # Strip pipe-delimited thumb attributes (residue when image tags are partially matched)
        text = self.thumb_pipe_pattern.sub("", text)
        # Bold markup: '''text''' → text (paired)
        text = self.bold_pattern.sub(r"\1", text)
        # Strip any orphan ''' that weren't consumed by the paired pattern
        text = self.orphan_bold_pattern.sub("", text)
        # Italic markup: ''text'' → text
        text = self.italic_pattern.sub(r"\1", text)
        # Remove inter-wiki prefix fragments (wtr, wes, wit, …) — defensive
        # fallback for residue from sources we haven't matched in the link
        # pass below.
        text = self.interwiki_fragment_pattern.sub("", text)

        # Strip interwiki / sister-project links entirely BEFORE generic
        # link unwrapping; otherwise the colons inside them get consumed
        # later by list_marker_pattern and leave residue (wtrFoo, wesFoo).
        text = self.interwiki_link_pattern.sub("", text)
        # Links: [[link|text]] -> text
        text = self.link_with_text_pattern.sub(r"\2", text)
        # Links: [[link]] -> link
        text = self.simple_link_pattern.sub(r"\1", text)
        # External: [link] -> link
        text = self.external_link_pattern.sub(r"\1", text)
        # Remove templates: {{template}}
        text = self.template_pattern.sub("", text)
        # Remove references: <ref>...</ref>
        text = self.ref_pattern.sub("", text)
        # Remove HTML tags
        text = self.html_pattern.sub("", text)
        # Remove section headings: == Heading ==
        text = self.heading_pattern.sub("", text)
        # Remove list markers: *, #, :, ;
        text = self.list_marker_pattern.sub("", text)

        return text


class WhitespaceCleaner:
    """Normalizes whitespace in text."""

    def __init__(self):
        self.newline_pattern = re.compile(r"\n+")
        self.space_pattern = re.compile(r" +")

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
        text = self.newline_pattern.sub("\n", text)
        # Collapse multiple spaces
        text = self.space_pattern.sub(" ", text)
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

    def __init__(self, cleaners: list["Cleaner"]):
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
        self.html_tag_pattern = re.compile(r"<[^>]+>")
        self.html_entity_pattern = re.compile(r"&[a-zA-Z]+;|&#\d+;")

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
        text = self.html_tag_pattern.sub("", text)
        # Decode common HTML entities
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        text = text.replace("&nbsp;", " ")
        # Remove any remaining entities
        text = self.html_entity_pattern.sub("", text)
        return text


def create_wikipedia_cleaner() -> TextCleaningPipeline:
    """
    Factory function to create standard Wikipedia cleaning pipeline.

    Returns:
        TextCleaningPipeline configured for Wikipedia text
    """
    return TextCleaningPipeline(
        [
            UnicodeNormalizationCleaner(),
            WikiMarkupCleaner(),
            WhitespaceCleaner(),
        ]
    )


def create_html_cleaner() -> TextCleaningPipeline:
    """
    Factory function to create HTML cleaning pipeline for news articles.

    Returns:
        TextCleaningPipeline configured for HTML content (BBC, VOA, etc.)
    """
    return TextCleaningPipeline(
        [
            UnicodeNormalizationCleaner(),
            HTMLCleaner(),
            WhitespaceCleaner(),
        ]
    )
