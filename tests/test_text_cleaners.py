"""
Unit tests for text cleaning utilities.

These tests demonstrate how separation of concerns improves testability.
"""

from somali_dialect_classifier.preprocessing.text_cleaners import (
    HTMLCleaner,
    TextCleaningPipeline,
    WhitespaceCleaner,
    WikiMarkupCleaner,
    create_html_cleaner,
    create_wikipedia_cleaner,
)


class TestWikiMarkupCleaner:
    """Test Wikipedia markup removal."""

    def test_link_with_display_text(self):
        cleaner = WikiMarkupCleaner()
        result = cleaner.clean("[[Article|display text]]")
        assert result == "display text"

    def test_simple_link(self):
        cleaner = WikiMarkupCleaner()
        result = cleaner.clean("[[Article]]")
        assert result == "Article"

    def test_remove_templates(self):
        cleaner = WikiMarkupCleaner()
        result = cleaner.clean("Text {{template}} more text")
        assert result == "Text  more text"

    def test_remove_references(self):
        cleaner = WikiMarkupCleaner()
        result = cleaner.clean("Text<ref>citation</ref> continues")
        assert result == "Text continues"

    def test_remove_headings(self):
        cleaner = WikiMarkupCleaner()
        result = cleaner.clean("== Heading ==\nContent")
        assert result == "\nContent"


class TestWhitespaceCleaner:
    """Test whitespace normalization."""

    def test_collapse_newlines(self):
        cleaner = WhitespaceCleaner()
        result = cleaner.clean("line1\n\n\nline2")
        assert result == "line1\nline2"

    def test_collapse_spaces(self):
        cleaner = WhitespaceCleaner()
        result = cleaner.clean("word1    word2")
        assert result == "word1 word2"

    def test_strip_whitespace(self):
        cleaner = WhitespaceCleaner()
        result = cleaner.clean("  text  ")
        assert result == "text"


class TestTextCleaningPipeline:
    """Test composable pipeline."""

    def test_pipeline_composition(self):
        pipeline = TextCleaningPipeline(
            [
                WikiMarkupCleaner(),
                WhitespaceCleaner(),
            ]
        )
        result = pipeline.clean("[[Link|text]]   with    spaces")
        assert result == "text with spaces"

    def test_minimum_length_filter(self):
        pipeline = TextCleaningPipeline([WikiMarkupCleaner()])
        result = pipeline.clean("short", min_length=10)
        assert result is None

    def test_minimum_length_pass(self):
        pipeline = TextCleaningPipeline([WikiMarkupCleaner()])
        result = pipeline.clean("this is long enough", min_length=10)
        assert result == "this is long enough"


class TestHTMLCleaner:
    """Test HTML tag and entity removal."""

    def test_remove_html_tags(self):
        cleaner = HTMLCleaner()
        result = cleaner.clean("<p>Hello</p><div>World</div>")
        assert result == "HelloWorld"

    def test_decode_html_entities(self):
        cleaner = HTMLCleaner()
        result = cleaner.clean("Hello &amp; world")
        assert result == "Hello & world"

    def test_decode_common_entities(self):
        cleaner = HTMLCleaner()
        input_text = "&lt;tag&gt; &quot;quoted&quot; &#39;apostrophe&#39; &nbsp;space"
        result = cleaner.clean(input_text)
        assert "<tag>" in result
        assert '"quoted"' in result
        assert "'apostrophe'" in result
        assert " space" in result

    def test_remove_tags_and_decode_entities(self):
        cleaner = HTMLCleaner()
        result = cleaner.clean("<p>Hello &amp; <strong>world</strong></p>")
        assert result == "Hello & world"

    def test_bbc_article_like_html(self):
        """Test with BBC-like HTML structure."""
        cleaner = HTMLCleaner()
        input_html = """
        <article>
            <h1>News Title</h1>
            <p>First paragraph with &quot;quotes&quot;.</p>
            <p>Second paragraph &amp; more text.</p>
        </article>
        """
        result = cleaner.clean(input_html)
        assert "News Title" in result
        assert "First paragraph" in result
        assert '"quotes"' in result
        assert "& more text" in result
        assert "<article>" not in result
        assert "<p>" not in result


class TestWikipediaCleanerFactory:
    """Test factory function."""

    def test_create_wikipedia_cleaner(self):
        cleaner = create_wikipedia_cleaner()
        assert isinstance(cleaner, TextCleaningPipeline)

    def test_wikipedia_cleaner_end_to_end(self):
        cleaner = create_wikipedia_cleaner()
        input_text = "== Heading ==\n[[Link|text]]  {{template}}\n\n\nMore text"
        result = cleaner.clean(input_text)
        assert "Heading" not in result
        assert "text" in result
        assert "template" not in result
        assert "More text" in result


class TestHTMLCleanerFactory:
    """Test HTML cleaner factory function."""

    def test_create_html_cleaner(self):
        cleaner = create_html_cleaner()
        assert isinstance(cleaner, TextCleaningPipeline)

    def test_html_cleaner_end_to_end(self):
        cleaner = create_html_cleaner()
        input_html = "<p>Hello &amp; world</p>   <div>More   text</div>\n\n\n"
        result = cleaner.clean(input_html)
        assert result == "Hello & world More text"

    def test_html_cleaner_min_length_filter(self):
        """Test that HTML cleaner respects min_length."""
        cleaner = create_html_cleaner()
        result = cleaner.clean("<p>short</p>", min_length=10)
        assert result is None

    def test_html_cleaner_pass_length_filter(self):
        """Test that longer content passes min_length."""
        cleaner = create_html_cleaner()
        result = cleaner.clean("<p>This is long enough content</p>", min_length=10)
        assert result is not None
        assert "This is long enough content" in result
