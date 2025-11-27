"""
Integration tests for WikipediaSomaliProcessor.

Tests the full pipeline with offline fixture data to ensure:
- Extract phase correctly parses XML
- Process phase produces valid silver records
- Schema compliance across all records
- Correct filtering of namespace pages
"""

import bz2
import shutil
from pathlib import Path

import pyarrow.parquet as pq
import pytest

# Skip integration tests - require full pipeline with external data
pytestmark = pytest.mark.skip(
    reason="Integration tests require full pipeline run with external data"
)

from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
    WikipediaSomaliProcessor,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    yield data_dir
    # Cleanup handled by tmp_path


@pytest.fixture
def wiki_fixture_path():
    """Path to mini Wikipedia XML fixture."""
    return Path(__file__).parent / "fixtures" / "mini_wiki_dump.xml"


@pytest.fixture
def compressed_wiki_fixture(wiki_fixture_path, temp_data_dir):
    """Create a compressed bz2 version of the Wiki fixture."""
    # Read the XML fixture
    with open(wiki_fixture_path, "rb") as f_in:
        xml_content = f_in.read()

    # Compress it
    compressed_path = temp_data_dir / "sowiki-test.xml.bz2"
    with bz2.open(compressed_path, "wb") as f_out:
        f_out.write(xml_content)

    return compressed_path


class TestWikipediaIntegration:
    """Integration tests for Wikipedia processor with fixture data."""

    def test_extract_from_fixture(self, compressed_wiki_fixture, temp_data_dir, monkeypatch):
        """Test that extract phase correctly parses XML fixture."""
        # Change working directory to temp dir
        monkeypatch.chdir(temp_data_dir.parent)

        processor = WikipediaSomaliProcessor()

        # Override dump file path to use fixture
        processor.dump_file = compressed_wiki_fixture

        # Run extract
        staging_file = processor.extract()

        # Verify staging file was created
        assert staging_file.exists()

        # Read and verify content
        with open(staging_file, encoding="utf-8") as f:
            content = f.read()

        # Should contain the 3 main articles (not Template: or User:)
        assert "Soomaaliya" in content
        assert "Muqdisho" in content
        assert "Afrika" in content

        # Should NOT contain filtered pages
        assert "Template:Infobox Country" not in content
        assert "User:TestUser" not in content

        # Count pages using the page marker
        page_count = content.count(processor.page_marker_prefix)
        assert page_count == 3, f"Expected 3 pages, got {page_count}"

    def test_process_creates_silver_dataset(
        self, compressed_wiki_fixture, temp_data_dir, monkeypatch
    ):
        """Test that process phase creates valid silver dataset."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = WikipediaSomaliProcessor()
        processor.dump_file = compressed_wiki_fixture

        # Run extract then process
        processor.extract()
        processed_file = processor.process()

        # Verify processed file exists
        assert processed_file.exists()

        # Verify silver dataset was created
        # Silver writer creates: data/processed/silver/source=X/date_accessed=Y/
        silver_base = Path("data/processed/silver")
        assert silver_base.exists(), f"Silver base dir not found: {silver_base}"

        # Find the parquet file
        parquet_files = list(silver_base.rglob("*.parquet"))
        assert len(parquet_files) > 0, f"No parquet files created in {silver_base}"

        # Read and verify parquet
        table = pq.read_table(parquet_files[0])

        # Verify schema
        expected_columns = [
            "id",
            "text",
            "title",
            "source",
            "source_type",
            "url",
            "source_id",
            "date_published",
            "date_accessed",
            "language",
            "license",
            "topic",
            "tokens",
            "text_hash",
            "pipeline_version",
            "source_metadata",
        ]
        actual_columns = table.column_names
        assert set(expected_columns) == set(actual_columns)

        # Verify records
        df = table.to_pandas()
        assert len(df) == 3, f"Expected 3 records, got {len(df)}"

        # Verify content
        titles = set(df["title"].tolist())
        assert titles == {"Soomaaliya", "Muqdisho", "Afrika"}

        # Verify all records have Wikipedia source
        assert all(df["source"] == "Wikipedia-Somali")
        assert all(df["source_type"] == "wiki")
        assert all(df["language"] == "so")
        assert all(df["license"] == "CC-BY-SA-3.0")

    def test_text_cleaning_applied(self, compressed_wiki_fixture, temp_data_dir, monkeypatch):
        """Test that wiki markup is properly cleaned."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = WikipediaSomaliProcessor()
        processor.dump_file = compressed_wiki_fixture

        processor.extract()
        processor.process()

        # Read silver dataset
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])
        df = table.to_pandas()

        # Check that wiki markup is removed
        soomaaliya_text = df[df["title"] == "Soomaaliya"]["text"].iloc[0]

        # Should not contain wiki markup
        assert "[[" not in soomaaliya_text, "Wiki links not cleaned"
        assert "]]" not in soomaaliya_text, "Wiki links not cleaned"
        assert "'''" not in soomaaliya_text, "Bold markup not cleaned"
        assert "{{" not in soomaaliya_text, "Templates not cleaned"
        assert "}}" not in soomaaliya_text, "Templates not cleaned"
        assert "==" not in soomaaliya_text, "Headings not cleaned"
        assert "<ref>" not in soomaaliya_text, "References not cleaned"

        # Should contain actual content
        assert "Soomaaliya" in soomaaliya_text
        assert "Afrika" in soomaaliya_text

    def test_record_ids_are_unique(self, compressed_wiki_fixture, temp_data_dir, monkeypatch):
        """Test that all record IDs are unique."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = WikipediaSomaliProcessor()
        processor.dump_file = compressed_wiki_fixture

        processor.extract()
        processor.process()

        # Read silver dataset
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])
        df = table.to_pandas()

        ids = df["id"].tolist()
        assert len(ids) == len(set(ids)), "Record IDs are not unique"

    def test_full_pipeline_run_method(self, compressed_wiki_fixture, temp_data_dir, monkeypatch):
        """Test the complete pipeline via run() method."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = WikipediaSomaliProcessor()
        processor.dump_file = compressed_wiki_fixture

        # Skip download by marking dump as existing
        processor.raw_dir.mkdir(parents=True, exist_ok=True)
        if compressed_wiki_fixture != processor.dump_file:
            shutil.copy(compressed_wiki_fixture, processor.dump_file)

        # Run full pipeline
        result_path = processor.run()

        # Verify result
        assert result_path.exists()

        # Verify all stages completed
        assert processor.dump_file.exists()
        assert processor.staging_file.exists()
        assert processor.processed_file.exists()

        # Verify silver dataset
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        assert len(parquet_files) > 0

    def test_idempotency(self, compressed_wiki_fixture, temp_data_dir, monkeypatch):
        """Test that running process twice produces same results."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = WikipediaSomaliProcessor()
        processor.dump_file = compressed_wiki_fixture

        # Run twice
        processor.extract()
        processor.process()

        # Read first result
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        table1 = pq.read_table(parquet_files[0])
        df1 = table1.to_pandas()

        # Run again (should use cached files)
        processor.process()
        table2 = pq.read_table(parquet_files[0])
        df2 = table2.to_pandas()

        # Results should be identical
        assert len(df1) == len(df2)
        assert set(df1["id"]) == set(df2["id"])
