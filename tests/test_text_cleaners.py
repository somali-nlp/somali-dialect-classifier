"""
Unit tests for text cleaning utilities.

These tests demonstrate how separation of concerns improves testability.
"""

from somdialc.quality.text_cleaners import (
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

    # --- Fix 1: table blocks, pipe cells, HTML entities, category residue ---

    def test_strip_table_block_simple(self):
        """A complete {| ... |} block is removed entirely."""
        cleaner = WikiMarkupCleaner()
        text = "Before\n{|\n! Header\n|-\n| Cell\n|}\nAfter"
        result = cleaner.clean(text)
        assert "{|" not in result
        assert "|}" not in result
        assert "Before" in result
        assert "After" in result

    def test_strip_table_block_with_infobox_content(self):
        """Infobox-style table block is stripped, surrounding prose preserved."""
        cleaner = WikiMarkupCleaner()
        text = (
            "Maqaal muhiim ah.\n"
            "{|\n"
            "| magac = Soomaaliya\n"
            "| dadka = 17,000,000\n"
            "|}\n"
            "Qoraalka ku xiga waa muhiim."
        )
        result = cleaner.clean(text)
        assert "magac" not in result
        assert "dadka" not in result
        assert "Maqaal muhiim ah" in result
        assert "Qoraalka ku xiga waa muhiim" in result

    def test_strip_adjacent_table_blocks(self):
        """Two adjacent {| ... |} blocks are both removed (non-greedy)."""
        cleaner = WikiMarkupCleaner()
        text = "{| table one |} prose {| table two |}"
        result = cleaner.clean(text)
        assert "table one" not in result
        assert "table two" not in result
        assert "prose" in result

    def test_strip_pipe_cell_lines(self):
        """Lines starting with | (pipe-prefixed table cells) are removed."""
        cleaner = WikiMarkupCleaner()
        text = "Intro sentence.\n| field = value\n| another = data\nReal content."
        result = cleaner.clean(text)
        assert "field = value" not in result
        assert "another = data" not in result
        assert "Intro sentence" in result
        assert "Real content" in result

    def test_strip_pipe_cell_with_leading_whitespace(self):
        """Pipe cell lines with leading whitespace are also stripped."""
        cleaner = WikiMarkupCleaner()
        text = "Prose.\n   | indented cell\nMore prose."
        result = cleaner.clean(text)
        assert "indented cell" not in result
        assert "Prose" in result
        assert "More prose" in result

    def test_html_entity_decoding_amp(self):
        """&amp; is decoded to & before tag stripping."""
        cleaner = WikiMarkupCleaner()
        result = cleaner.clean("Somali &amp; Arabic")
        assert "&" in result
        assert "&amp;" not in result

    def test_html_entity_decoding_lt_gt(self):
        """&lt; and &gt; entities are decoded; the resulting tags are stripped but content remains."""
        cleaner = WikiMarkupCleaner()
        # &lt;ref&gt;citation&lt;/ref&gt;
        #   step 1: ref_pattern does NOT match (still entity-encoded)
        #   step 2: html.unescape → <ref>citation</ref>
        #   step 3: html_pattern strips tags but leaves inner content
        # So "citation" is preserved (it is not inside a real <ref>...</ref> pair
        # that ref_pattern could have consumed in the raw pass).
        result = cleaner.clean("Text &lt;ref&gt;citation&lt;/ref&gt; continues.")
        assert "&lt;" not in result
        assert "&gt;" not in result
        # Tags are stripped, inner text preserved
        assert "<ref>" not in result
        assert "</ref>" not in result
        assert "Text" in result
        assert "continues" in result

    def test_html_entity_nbsp_decoded(self):
        """&nbsp; is decoded (html.unescape converts it to non-breaking space)."""
        cleaner = WikiMarkupCleaner()
        result = cleaner.clean("word&nbsp;word")
        assert "&nbsp;" not in result
        # html.unescape converts &nbsp; to \xa0; both are acceptable post-clean
        assert "word" in result

    def test_category_residue_stripped(self):
        """'Category:Foo' strings left by link unwrapping are removed."""
        cleaner = WikiMarkupCleaner()
        # simple_link_pattern unwraps [[Category:Foo]] → Category:Foo; we then strip it
        text = "[[Category:Soomaaliya]]\n[[Category:Taariikh]]\nReal text here."
        result = cleaner.clean(text)
        assert "Category:Soomaaliya" not in result
        assert "Category:Taariikh" not in result
        assert "Real text here" in result

    def test_category_multiword_name_no_residue(self):
        """Multi-word category names must not leave trailing word residue in silver text.

        Prior bug: [[Category:Taariikhda Afrika]] would produce ' Afrika' because
        category_residue_pattern stopped at the space after stripping 'CategoryTaariikhda'.
        The new category_link_pattern strips the entire [[Category:...]] form first.
        """
        cleaner = WikiMarkupCleaner()
        text = "[[Category:Taariikhda Afrika]]\nQoraalka asalka ah ee maqaalka."
        result = cleaner.clean(text)
        assert "Category" not in result
        assert "Taariikhda" not in result
        assert "Afrika" not in result
        assert "Qoraalka asalka ah ee maqaalka" in result

    def test_category_lowercase_start_no_residue(self):
        """Lowercase-start category names must not leak 'Categoryhore' into silver text.

        Prior bug: [[Category:hore]] → after list_marker strips ':' → 'Categoryhore';
        pattern required [A-Z] after 'Category' so lowercase 'h' was not matched.
        The new category_link_pattern strips [[Category:hore]] at the source.
        """
        cleaner = WikiMarkupCleaner()
        text = "[[Category:hore]]\nTaariikhda Soomaaliya."
        result = cleaner.clean(text)
        assert "Category" not in result
        assert "Categoryhore" not in result
        assert "Taariikhda Soomaaliya" in result

    def test_category_multiple_multiword_stripped(self):
        """Real Somali Wikipedia category names with multiple words are all removed."""
        cleaner = WikiMarkupCleaner()
        text = (
            "[[Category:Taariikh Afrika]]\n"
            "[[Category:Magaalooyinka Soomaaliya]]\n"
            "Maqaalka wuxuu ka hadlayaa taariikhda."
        )
        result = cleaner.clean(text)
        assert "Category" not in result
        assert "Afrika" not in result
        assert "Magaalooyinka" not in result
        assert "Maqaalka wuxuu ka hadlayaa taariikhda" in result

    def test_existing_template_removal_still_works(self):
        """Existing {{template}} stripping continues to function after refactor."""
        cleaner = WikiMarkupCleaner()
        result = cleaner.clean("Text {{infobox country}} more text")
        assert "{{" not in result
        assert "}}" not in result

    def test_existing_link_unwrapping_still_works(self):
        """Existing [[Link|display]] unwrapping continues to function."""
        cleaner = WikiMarkupCleaner()
        result = cleaner.clean("See [[Muqdisho|Mogadishu]] for details.")
        assert "Mogadishu" in result
        assert "[[" not in result


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
