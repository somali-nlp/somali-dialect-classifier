"""
Tests for Språkbanken Somali corpora processor.
"""

import json
import tempfile
import xml.etree.ElementTree as ET
import bz2
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import (
    SprakbankenSomaliProcessor,
    list_available_corpora,
    get_corpus_info,
    CORPUS_INFO,
)
from somali_dialect_classifier.preprocessing.base_pipeline import RawRecord


class TestSprakbankenSomaliProcessor:
    """Test Språkbanken processor functionality."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create processor instance with temp directory."""
        with patch('somali_dialect_classifier.config.get_config') as mock_config:
            # Mock config
            config = Mock()
            config.data.raw_dir = tmp_path / "raw"
            config.data.staging_dir = tmp_path / "staging"
            config.data.processed_dir = tmp_path / "processed"
            config.data.silver_dir = tmp_path / "silver"
            mock_config.return_value = config

            processor = SprakbankenSomaliProcessor(corpus_id="somali-cilmi", force=True)
            return processor

    def test_processor_initialization(self, processor):
        """Test processor initializes correctly."""
        assert processor.corpus_id == "somali-cilmi"
        assert processor.corpora_to_process == ["somali-cilmi"]
        assert processor.source == "Sprakbanken-Somali"  # Consistent source name

    def test_processor_all_corpora(self, tmp_path):
        """Test processor with all corpora."""
        with patch('somali_dialect_classifier.config.get_config') as mock_config:
            config = Mock()
            config.data.raw_dir = tmp_path / "raw"
            config.data.staging_dir = tmp_path / "staging"
            config.data.processed_dir = tmp_path / "processed"
            config.data.silver_dir = tmp_path / "silver"
            mock_config.return_value = config

            processor = SprakbankenSomaliProcessor(corpus_id="all")
            assert processor.corpus_id == "all"
            assert len(processor.corpora_to_process) == len(CORPUS_INFO)
            assert processor.source == "Sprakbanken-Somali"  # Consistent source name regardless of corpus_id

    def test_invalid_corpus_id(self, tmp_path):
        """Test that invalid corpus ID raises error."""
        with patch('somali_dialect_classifier.config.get_config') as mock_config:
            config = Mock()
            config.data.raw_dir = tmp_path / "raw"
            config.data.staging_dir = tmp_path / "staging"
            config.data.processed_dir = tmp_path / "processed"
            config.data.silver_dir = tmp_path / "silver"
            mock_config.return_value = config

            with pytest.raises(ValueError, match="Unknown corpus_id"):
                SprakbankenSomaliProcessor(corpus_id="invalid_corpus")

    def test_get_domain(self, processor):
        """Test domain extraction."""
        # Set current corpus metadata
        processor.current_corpus_metadata = {"domain": "science"}
        assert processor._get_domain() == "science"

        # Test fallback
        processor.current_corpus_metadata = {}
        assert processor._get_domain() == "general"

    def test_extract_sentence_text(self, processor):
        """Test sentence text extraction from XML."""
        # Create sample sentence element
        sentence = ET.Element("sentence", id="s1")
        tokens = [
            ("Waxaan", "Waxaan"),
            ("baran", "baran"),
            ("doonaa", "doonaa"),
            ("cilmi", "cilmi"),
            (".", "."),
        ]
        for word, _ in tokens:
            token = ET.SubElement(sentence, "token")
            token.set("word", word)

        text = processor._extract_sentence_text(sentence)
        assert text == "Waxaan baran doonaa cilmi ."

    def test_extract_text_metadata(self, processor):
        """Test metadata extraction from text element."""
        text_elem = ET.Element("text")
        text_elem.set("author", "Test Author")
        text_elem.set("date", "2020")
        text_elem.set("title", "Test Title")
        text_elem.set("publisher", "Test Publisher")

        metadata = processor._extract_text_metadata(text_elem)

        assert metadata["author"] == "Test Author"
        assert metadata["date"] == "2020"
        assert metadata["title"] == "Test Title"
        assert metadata["publisher"] == "Test Publisher"

    def test_download_manifest_creation(self, processor):
        """Test that download creates manifest correctly."""
        # Mock HTTP session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": "1000"}
        mock_response.iter_content = Mock(return_value=[b"test_data"])
        mock_session.get.return_value = mock_response

        with patch.object(processor, '_get_http_session', return_value=mock_session):
            manifest_path = processor.download()

            # Check manifest was created
            assert manifest_path.exists()

            # Load and verify manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            assert manifest["corpora_ids"] == ["somali-cilmi"]
            assert len(manifest["corpora"]) > 0
            assert manifest["corpora"][0]["id"] == "somali-cilmi"

    def test_extract_corpus_xml_parsing(self, processor, tmp_path):
        """Test XML corpus extraction."""
        # Create sample XML corpus
        corpus_xml = """<?xml version='1.0' encoding='UTF-8'?>
        <corpus id="test-corpus">
            <corpus>
                <text author="Test Author" date="2020" title="Test Text">
                    <page n="1">
                        <sentence id="s1">
                            <token word="Waxaan">Waxaan</token>
                            <token word="baran">baran</token>
                            <token word="doonaa">doonaa</token>
                            <token word="cilmi">cilmi</token>
                            <token word=".">.</token>
                        </sentence>
                    </page>
                </text>
            </corpus>
        </corpus>"""

        # Create compressed XML file
        corpus_file = tmp_path / "test.xml.bz2"
        with bz2.open(corpus_file, 'wt', encoding='utf-8') as f:
            f.write(corpus_xml)

        # Create output file
        output_file = tmp_path / "output.jsonl"

        with open(output_file, 'w') as out_f:
            corpus_info = {"id": "test", "domain": "science"}
            texts_count, sentences_count = processor._extract_corpus(
                corpus_file, corpus_info, out_f
            )

        assert texts_count == 1
        assert sentences_count == 1

        # Verify output
        with open(output_file, 'r') as f:
            record = json.loads(f.readline())

        assert record["corpus_id"] == "test-corpus"
        assert record["title"] == "Test Text"
        assert record["text"] == "Waxaan baran doonaa cilmi ."
        assert record["metadata"]["domain"] == "science"

    def test_extract_records_iteration(self, processor, tmp_path):
        """Test that _extract_records yields RawRecords correctly."""
        # Create staging file with test data
        staging_data = [
            {
                "corpus_id": "somali-cilmi",
                "title": "Test Title 1",
                "text": "Test text 1",
                "metadata": {"domain": "science"},
            },
            {
                "corpus_id": "somali-cilmi",
                "title": "Test Title 2",
                "text": "Test text 2",
                "metadata": {"domain": "science"},
            },
        ]

        processor.staging_file.parent.mkdir(parents=True, exist_ok=True)
        with open(processor.staging_file, 'w') as f:
            for record in staging_data:
                f.write(json.dumps(record) + '\n')

        # Extract records
        records = list(processor._extract_records())

        assert len(records) == 2
        assert isinstance(records[0], RawRecord)
        assert records[0].title == "Test Title 1"
        assert records[0].text == "Test text 1"
        assert records[0].metadata["domain"] == "science"
        # Verify corpus_id is added to metadata for source_id population
        assert records[0].metadata["corpus_id"] == "somali-cilmi"
        assert records[1].metadata["corpus_id"] == "somali-cilmi"

    def test_processor_filters(self, processor):
        """Test that proper filters are registered."""
        # Filters are already registered during __init__, don't call again
        # Should have min_length and langid filters
        assert len(processor.record_filters) == 2

        filter_names = [f[0].__name__ for f in processor.record_filters]
        assert "min_length_filter" in filter_names
        assert "langid_filter" in filter_names


class TestSprakbankenHelperFunctions:
    """Test helper functions for Språkbanken."""

    def test_list_available_corpora(self):
        """Test listing available corpora."""
        corpora = list_available_corpora()

        assert isinstance(corpora, list)
        assert len(corpora) == 66
        assert "somali-cilmi" in corpora
        assert "somali-ogaden" in corpora
        assert "somali-sheekooyin-carruureed" in corpora

    def test_get_corpus_info(self):
        """Test getting corpus information."""
        # Test valid corpus
        info = get_corpus_info("somali-cilmi")
        assert info["domain"] == "science"
        assert info["topic"] == "knowledge/science"

        # Test another corpus
        info = get_corpus_info("somali-ogaden")
        assert info["domain"] == "general"
        assert info["region"] == "Ogaden"

        # Test invalid corpus
        info = get_corpus_info("invalid")
        assert info == {}


class TestCorpusMetadata:
    """Test corpus metadata definitions."""

    def test_all_corpora_have_domain(self):
        """Test that all corpora have a domain defined."""
        for corpus_id, info in CORPUS_INFO.items():
            assert "domain" in info, f"Corpus {corpus_id} missing domain"
            assert info["domain"] in [
                "general", "news", "literature", "science", "health",
                "immigrant", "education"
            ], f"Invalid domain {info['domain']} for corpus {corpus_id}"

    def test_corpus_metadata_consistency(self):
        """Test that corpus metadata is consistent."""
        # Check turjuman corpora have translation info
        for corpus_id, info in CORPUS_INFO.items():
            if "turjuman" in corpus_id:
                assert "topic" in info and "translat" in info["topic"].lower(), f"Expected translation topic for {corpus_id}"

        # Check specific news corpora (CB News and BBC are news domain)
        news_corpora = ["somali-cb", "somali-bbc", "somali-wardheer", "somali-wakiillada",
                       "somali-cb-1980-89", "somali-cb-2001-03-soomaaliya", "somali-cb-2010",
                       "somali-cb-2011", "somali-cb-2016", "somali-cb-2018", "somali-cd-2012-itoobiya",
                       "somali-radioden2014", "somali-radioswe2014", "somali-radiomuq"]
        news_corpora.extend([f"somali-haatuf-news-{year}" for year in range(2002, 2010)])

        for corpus_id in news_corpora:
            if corpus_id in CORPUS_INFO:
                assert CORPUS_INFO[corpus_id]["domain"] == "news", f"Expected news domain for {corpus_id}"

        # Check immigrant domain corpora
        assert CORPUS_INFO["somali-ah-1992-02-kanada"]["domain"] == "immigrant"
        assert CORPUS_INFO["somali-ah-2010-19"]["domain"] == "immigrant"

        # Check literature corpus
        assert CORPUS_INFO["somali-sheekooyin-carruureed"]["domain"] == "literature"

        # Check science corpora
        assert CORPUS_INFO["somali-cilmi"]["domain"] == "science"
        assert CORPUS_INFO["somali-saynis-1980-89"]["domain"] == "science"