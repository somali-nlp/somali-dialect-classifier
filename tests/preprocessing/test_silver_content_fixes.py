"""
Unit tests for silver schema content fixes TD-018, TD-020, TD-022, TD-023, TD-024.
"""

import json

import pytest

from somdialc.ingestion.raw_record import RawRecord
from somdialc.quality.record_builder import RecordBuilder
from somdialc.quality.record_utils import generate_record_id, generate_text_hash
from somdialc.quality.text_cleaners import WikiMarkupCleaner, create_wikipedia_cleaner


# ---------------------------------------------------------------------------
# TD-018: generate_record_id must include text so same title+url but different
#         text produces distinct ids.
# ---------------------------------------------------------------------------
class TestTD018RecordIdIncludesText:
    def test_same_title_url_different_text_yields_distinct_ids(self):
        """Two records with the same title+url but different text must not collide."""
        title = "Af Soomaali, Fasalka kowaad"
        url = "https://spraakbanken.gu.se/korp/?mode=somali#?corpus=somali-cilmi"
        text_a = "Erayga hore ee fasalka."
        text_b = "Erayga dambe ee fasalka."

        id_a = generate_record_id(title, url, generate_text_hash(text_a))
        id_b = generate_record_id(title, url, generate_text_hash(text_b))

        assert id_a != id_b, "IDs must differ when text differs"

    def test_same_title_url_same_text_yields_same_id(self):
        """Identical records must always produce the same id (determinism)."""
        title = "Test Article"
        url = "https://so.wikipedia.org/wiki/Test_Article"
        text = "Halkan waa qoraalka."

        id_1 = generate_record_id(title, url, generate_text_hash(text))
        id_2 = generate_record_id(title, url, generate_text_hash(text))

        assert id_1 == id_2

    def test_build_silver_record_id_uses_text(self):
        """build_silver_record produces distinct ids for same title+url, different text."""
        from somdialc.quality.record_utils import build_silver_record

        common = dict(
            title="Same Title",
            source="sprakbanken-somali",
            url="https://spraakbanken.gu.se/korp/?mode=somali#?corpus=somali-cilmi",
            date_accessed="2026-01-01",
        )
        rec_a = build_silver_record(text="First page text content here.", **common)
        rec_b = build_silver_record(text="Second page text content here.", **common)

        assert rec_a["id"] != rec_b["id"]


# ---------------------------------------------------------------------------
# TD-020: WikiMarkupCleaner removes image links, bold/italic markup, wtr fragments.
# ---------------------------------------------------------------------------
class TestTD020WikiMarkupCleaner:
    def setup_method(self):
        self.cleaner = WikiMarkupCleaner()

    def test_image_link_removed(self):
        """[[File:...]] should be stripped entirely."""
        result = self.cleaner.clean("[[File:Bush.jpg|thumb|200px|Caption]] Some text.")
        assert "File:" not in result
        assert "thumb" not in result
        assert "Some text." in result

    def test_image_link_case_insensitive(self):
        """[[image:...]] (lowercase) should also be removed."""
        result = self.cleaner.clean("[[image:photo.png|200px]] More content.")
        assert "image:" not in result
        assert "More content." in result

    def test_bold_markup_stripped_keeps_text(self):
        """'''bold text''' should become 'bold text'."""
        result = self.cleaner.clean("'''George W. Bush''' waa dambiile dagaal.")
        assert "'''" not in result
        assert "George W. Bush" in result

    def test_italic_markup_stripped_keeps_text(self):
        """''italic text'' should become 'italic text'."""
        result = self.cleaner.clean("''Somali language'' is beautiful.")
        assert "''" not in result
        assert "Somali language" in result

    def test_wtr_fragment_removed(self):
        """Isolated 'wtr' token (Wiktionary inter-wiki residue) should be removed."""
        result = self.cleaner.clean("wtrGeorge W. Bush waa nin.")
        # After wtr removal the fragment "wtr" is gone
        assert "wtr" not in result
        assert "George W. Bush" in result

    def test_realistic_wiki_sample(self):
        """Simulate the sample silver row from TD-020 bug report."""
        raw = (
            "thumb|200px|Bush (2003)\nwtrGeorge W. Bush\n"
            "'''George W. Bush''' waa dambiile dagaal, "
            "[[Madaxweyne|Madaxweynihii]] [[Maraykanka]]."
        )
        result = self.cleaner.clean(raw)
        assert "thumb" not in result
        assert "wtr" not in result
        assert "'''" not in result
        assert "George W. Bush" in result
        assert "Maraykanka" in result  # simple link kept as text

    def test_pipeline_factory_includes_new_patterns(self):
        """create_wikipedia_cleaner() pipeline handles all TD-020 cases end-to-end."""
        pipeline = create_wikipedia_cleaner()
        # wtr is always fused with an uppercase article name (e.g. wtrGeorge)
        raw = "[[File:test.jpg|thumb]] '''Bold''' ''italic'' wtrGeorge more text"
        result = pipeline.clean(raw)
        assert result is not None
        assert "File:" not in result
        assert "'''" not in result
        assert "''" not in result
        assert "wtr" not in result
        assert "Bold" in result
        assert "italic" in result
        assert "more text" in result

    # --- TD-020 followup: orphan ''' and wes/wit interwiki fragments ---

    def test_orphan_bold_before_digit(self):
        """Orphan ''' not followed by closing ''' must be stripped (row 23 sample)."""
        raw = "waxaa dagan dad gaadhaya ilaa '''9.98 milyan oo qof"
        result = self.cleaner.clean(raw)
        assert "'''" not in result
        assert "9.98 milyan" in result

    def test_orphan_bold_after_html_entity(self):
        """Orphan ''' after HTML entity must be stripped (row 65 sample)."""
        raw = "&lt;/small&gt;'''\n|-\n| 1 || KwaZulu-Natal Province ||"
        result = self.cleaner.clean(raw)
        assert "'''" not in result

    def test_wes_interwiki_fragment_removed(self):
        """'wes' inter-wiki prefix (row 60 sample) must be removed."""
        raw = "ta Arktika\n|}\nwesindian ocean\nwtrHint\nwitOceano In"
        result = self.cleaner.clean(raw)
        assert "wes" not in result
        assert "wtr" not in result
        assert "wit" not in result

    def test_wit_interwiki_fragment_removed(self):
        """Standalone 'wit' inter-wiki prefix must be removed."""
        raw = "witOceano Indico bayuu ahaa"
        result = self.cleaner.clean(raw)
        assert "wit" not in result
        assert "Oceano" in result

    def test_row60_full_sample(self):
        """Exact context from silver row 60: wes, wtr, wit all absent after clean."""
        raw = "ta Arktika\n|}\nwesindian ocean\nwtrHint altkıtası\nwitOceano In"
        result = self.cleaner.clean(raw)
        assert "wtr" not in result
        assert "wes" not in result
        assert "wit" not in result


# ---------------------------------------------------------------------------
# TD-022: source_id propagation via RecordBuilder.
# ---------------------------------------------------------------------------
class TestTD022SourceIdPropagation:
    def _make_builder(self):
        return RecordBuilder(
            source="test-source", date_accessed="2026-01-01", run_id="run_test_001"
        )

    def _build(self, metadata: dict) -> dict:
        builder = self._make_builder()
        raw = RawRecord(title="Title", text="Text", url="https://example.com", metadata=metadata)
        return builder.build_silver_record(
            raw_record=raw,
            cleaned_text="Cleaned text for record builder",
            filter_metadata={},
            source_type="news",
            license_str="CC-BY-SA-3.0",
            domain="news",
            register="formal",
        )

    def test_source_id_from_source_id_key(self):
        record = self._build({"source_id": "slug-abc123"})
        assert record["source_id"] == "slug-abc123"

    def test_source_id_from_corpus_id_key(self):
        record = self._build({"corpus_id": "somali-cilmi"})
        assert record["source_id"] == "somali-cilmi"

    def test_source_id_from_page_id_key(self):
        record = self._build({"page_id": "12345"})
        assert record["source_id"] == "12345"

    def test_source_id_from_comment_id_key(self):
        record = self._build({"comment_id": "7564909554666193671"})
        assert record["source_id"] == "7564909554666193671"

    def test_source_id_none_when_absent(self):
        record = self._build({})
        assert record["source_id"] is None

    def test_source_id_prefers_source_id_over_corpus_id(self):
        """Explicit source_id key wins over corpus_id fallback."""
        record = self._build({"source_id": "explicit", "corpus_id": "fallback"})
        assert record["source_id"] == "explicit"


# ---------------------------------------------------------------------------
# TD-023: primary_topic hoisted from filter metadata into top-level topic column.
# ---------------------------------------------------------------------------
class TestTD023TopicHoisting:
    def _make_builder(self):
        return RecordBuilder(
            source="bbc-somali", date_accessed="2026-01-01", run_id="run_test_002"
        )

    def test_topic_hoisted_from_filter_metadata(self):
        """primary_topic in filter_metadata should populate the topic column."""
        builder = self._make_builder()
        raw = RawRecord(
            title="Title", text="Text", url="https://bbc.com/somali/articles/c12345",
            metadata={"date_published": "2026-01-01"}
        )
        record = builder.build_silver_record(
            raw_record=raw,
            cleaned_text="Xukuumadda Soomaaliya ayaa war soo saartay.",
            filter_metadata={"primary_topic": "politics"},
            source_type="news",
            license_str="BBC Terms of Use",
            domain="news",
            register="formal",
        )
        assert record["topic"] == "politics"

    def test_explicit_topic_not_overridden_by_filter(self):
        """If raw_record.metadata already has topic, that takes precedence."""
        builder = self._make_builder()
        raw = RawRecord(
            title="Title", text="Text", url="https://bbc.com/somali/articles/c99",
            metadata={"topic": "explicit_topic"}
        )
        record = builder.build_silver_record(
            raw_record=raw,
            cleaned_text="Kubadda cagta ayaa la ciyaaray.",
            filter_metadata={"primary_topic": "sports"},
            source_type="news",
            license_str="BBC Terms of Use",
            domain="news",
            register="formal",
        )
        assert record["topic"] == "explicit_topic"

    def test_topic_none_when_no_primary_topic(self):
        """topic stays None when neither metadata.topic nor primary_topic is present."""
        builder = self._make_builder()
        raw = RawRecord(title="T", text="T", url="https://example.com", metadata={})
        record = builder.build_silver_record(
            raw_record=raw,
            cleaned_text="Enough text to pass length filter.",
            filter_metadata={},
            source_type="news",
            license_str="CC-BY",
            domain="news",
            register="formal",
        )
        assert record["topic"] is None

    # --- TD-023 followup: 'unknown' must NOT be hoisted as a real topic ---

    def test_unknown_primary_topic_treated_as_no_signal(self):
        """primary_topic='unknown' (all-zero markers) must not populate topic column."""
        builder = self._make_builder()
        raw = RawRecord(
            title="Title", text="Text", url="https://bbc.com/somali/articles/c00",
            metadata={"date_published": "2026-01-01"}
        )
        record = builder.build_silver_record(
            raw_record=raw,
            cleaned_text="Enough text to pass length filter.",
            filter_metadata={
                "primary_topic": "unknown",
                "topic_markers": {"economy": 0, "politics": 0, "sports": 0},
            },
            source_type="news",
            license_str="BBC Terms of Use",
            domain="news",
            register="formal",
        )
        assert record["topic"] is None, (
            "topic must be None when primary_topic='unknown', got: " + repr(record["topic"])
        )

    def test_empty_string_primary_topic_treated_as_no_signal(self):
        """primary_topic='' must not populate topic column."""
        builder = self._make_builder()
        raw = RawRecord(title="T", text="T", url="https://example.com", metadata={})
        record = builder.build_silver_record(
            raw_record=raw,
            cleaned_text="Enough text to pass length filter.",
            filter_metadata={"primary_topic": ""},
            source_type="news",
            license_str="CC-BY",
            domain="news",
            register="formal",
        )
        assert record["topic"] is None

    def test_unknown_in_raw_record_metadata_treated_as_no_signal(self):
        """metadata.topic='unknown' on the raw record must also be suppressed."""
        builder = self._make_builder()
        raw = RawRecord(
            title="T", text="T", url="https://example.com",
            metadata={"topic": "unknown"}
        )
        record = builder.build_silver_record(
            raw_record=raw,
            cleaned_text="Enough text to pass length filter.",
            filter_metadata={"primary_topic": "sports"},
            source_type="news",
            license_str="CC-BY",
            domain="news",
            register="formal",
        )
        # 'unknown' on raw_record is suppressed; sports from filter_metadata is used
        assert record["topic"] == "sports"

    def test_dominant_marker_topic_preserved(self):
        """When topic_markers are present with a dominant marker, topic is set correctly."""
        builder = self._make_builder()
        raw = RawRecord(
            title="Title", text="Text", url="https://bbc.com/somali/articles/c02",
            metadata={}
        )
        record = builder.build_silver_record(
            raw_record=raw,
            cleaned_text="Kubadda cagta Soomaaliya ayaa la ciyaaray toddobaadkan.",
            filter_metadata={
                "primary_topic": "sports",
                "topic_markers": {"economy": 0, "politics": 1, "sports": 4},
            },
            source_type="news",
            license_str="BBC Terms of Use",
            domain="news",
            register="formal",
        )
        assert record["topic"] == "sports"


# ---------------------------------------------------------------------------
# TD-024: date_published from Sprakbanken _extract_text_metadata.
# ---------------------------------------------------------------------------
class TestTD024SprakbankenDatePublished:
    """Unit tests for Sprakbanken date_published derivation logic."""

    def _make_fake_text_elem(self, attribs: dict):
        """Build a minimal fake XML Element with given attributes."""
        from xml.etree.ElementTree import Element
        elem = Element("text", attrib={k: v for k, v in attribs.items() if v})
        return elem

    def _call_extract_metadata(self, attribs: dict) -> dict:
        """Call SprakbankenSomaliProcessor._extract_text_metadata without full init."""
        # Test the logic directly via a subclass-free function call
        from somdialc.ingestion.processors.sprakbanken_somali_processor import (
            SprakbankenSomaliProcessor,
        )

        # Instantiate via __new__ to skip __init__ network calls
        proc = object.__new__(SprakbankenSomaliProcessor)
        elem = self._make_fake_text_elem(attribs)
        return proc._extract_text_metadata(elem)

    def test_datefrom_compact_normalised(self):
        """datefrom='19830101' should produce date_published='1983-01-01'."""
        meta = self._call_extract_metadata({"datefrom": "19830101"})
        assert meta["date_published"] == "1983-01-01"

    def test_datefrom_iso_passthrough(self):
        """datefrom already in ISO format is passed through."""
        meta = self._call_extract_metadata({"datefrom": "1983-01-01"})
        assert meta["date_published"] == "1983-01-01"

    def test_year_fallback(self):
        """When no datefrom, year field is used."""
        meta = self._call_extract_metadata({"year": "2001"})
        assert meta["date_published"] == "2001"

    def test_period_fallback(self):
        """When no datefrom/year, first year of period is used."""
        meta = self._call_extract_metadata({"period": "1993-1994"})
        assert meta["date_published"] == "1993"

    def test_no_date_fields(self):
        """When no date attributes present, date_published is not set."""
        meta = self._call_extract_metadata({"id": "text_1"})
        assert "date_published" not in meta

    def test_datefrom_preferred_over_year(self):
        """datefrom takes priority over year."""
        meta = self._call_extract_metadata({"datefrom": "19830101", "year": "1990"})
        assert meta["date_published"] == "1983-01-01"
