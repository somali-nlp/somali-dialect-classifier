"""
Integration tests for BBCSomaliProcessor.

Tests the full pipeline with offline fixture data to ensure:
- Process phase correctly handles JSON articles
- HTML cleaning works properly
- Silver records have correct metadata
- Empty articles are filtered out
"""

import pytest
import shutil
from pathlib import Path
import pyarrow.parquet as pq

from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    yield data_dir


@pytest.fixture
def bbc_fixture_path():
    """Path to BBC articles JSON fixture."""
    return Path(__file__).parent / "fixtures" / "bbc_articles.json"


class TestBBCIntegration:
    """Integration tests for BBC processor with fixture data."""

    def test_process_from_fixture(self, bbc_fixture_path, temp_data_dir, monkeypatch):
        """Test that process phase correctly handles fixture JSON."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = BBCSomaliProcessor()

        # Create staging directory and copy fixture
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bbc_fixture_path, processor.staging_file)

        # Run process
        processed_file = processor.process()

        # Verify processed file was created
        assert processed_file.exists()

        # Read and verify content
        with open(processed_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should contain the 3 valid articles (4th is empty)
        assert "Soomaaliya: Xaalada Amniga" in content
        assert "Caafimaadka: Tallaalka Cusub" in content
        assert "Ciyaaraha: Kooxda Qaranka" in content

        # Should not contain the empty article
        assert "Maqaal Banaan" not in content or content.count("Maqaal Banaan") == 0

    def test_creates_silver_dataset(self, bbc_fixture_path, temp_data_dir, monkeypatch):
        """Test that silver dataset is created with correct schema."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = BBCSomaliProcessor()
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bbc_fixture_path, processor.staging_file)

        processor.process()

        # Verify silver dataset was created
        silver_base = Path("data/processed/silver")
        assert silver_base.exists()

        # Find the parquet file
        parquet_files = list(silver_base.rglob("*.parquet"))
        assert len(parquet_files) > 0, "No parquet files created"

        # Read and verify parquet
        table = pq.read_table(parquet_files[0])

        # Verify schema
        expected_columns = [
            'id', 'text', 'title', 'source', 'source_type', 'url', 'source_id',
            'date_published', 'date_accessed', 'language', 'license', 'topic',
            'tokens', 'text_hash', 'pipeline_version', 'source_metadata'
        ]
        actual_columns = table.column_names
        assert set(expected_columns) == set(actual_columns)

        # Verify records
        df = table.to_pandas()
        # Should have 3 records (4th article is empty)
        assert len(df) == 3, f"Expected 3 records, got {len(df)}"

        # Verify content
        titles = set(df['title'].tolist())
        expected_titles = {
            'Soomaaliya: Xaalada Amniga',
            'Caafimaadka: Tallaalka Cusub',
            'Ciyaaraha: Kooxda Qaranka'
        }
        assert titles == expected_titles

        # Verify all records have BBC source
        assert all(df['source'] == 'BBC-Somali')
        assert all(df['source_type'] == 'news')
        assert all(df['language'] == 'so')
        assert all(df['license'] == 'BBC Terms of Use')

    def test_html_cleaning_applied(self, bbc_fixture_path, temp_data_dir, monkeypatch):
        """Test that HTML tags and entities are properly cleaned."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = BBCSomaliProcessor()
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bbc_fixture_path, processor.staging_file)

        processor.process()

        # Read silver dataset
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])
        df = table.to_pandas()

        # Check that HTML is removed
        for _, row in df.iterrows():
            text = row['text']

            # Should not contain HTML tags
            assert "<p>" not in text, f"HTML tags not cleaned in: {row['title']}"
            assert "</p>" not in text, f"HTML tags not cleaned in: {row['title']}"
            assert "<div>" not in text, f"HTML tags not cleaned in: {row['title']}"
            assert "<script>" not in text, f"Script tags not cleaned in: {row['title']}"

            # Should not contain raw HTML entities
            assert "&amp;" not in text, f"HTML entities not decoded in: {row['title']}"
            assert "&ldquo;" not in text, f"HTML entities not decoded in: {row['title']}"

        # Verify specific content
        health_article = df[df['title'] == 'Caafimaadka: Tallaalka Cusub']['text'].iloc[0]
        # HTML entity &ldquo; should be decoded to "
        assert '"Waa guul weyn,"' in health_article or 'Waa guul weyn' in health_article

    def test_metadata_preservation(self, bbc_fixture_path, temp_data_dir, monkeypatch):
        """Test that article metadata is preserved in silver records."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = BBCSomaliProcessor()
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bbc_fixture_path, processor.staging_file)

        processor.process()

        # Read silver dataset
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])
        df = table.to_pandas()

        # Check URLs are preserved
        urls = set(df['url'].tolist())
        assert 'https://www.bbc.com/somali/articles/c1234567890' in urls
        assert 'https://www.bbc.com/somali/articles/c0987654321' in urls

        # Check date_published is preserved
        assert df['date_published'].notna().sum() == 3  # All 3 valid articles have dates

    def test_empty_article_filtering(self, bbc_fixture_path, temp_data_dir, monkeypatch):
        """Test that empty/whitespace-only articles are filtered out."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = BBCSomaliProcessor()
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bbc_fixture_path, processor.staging_file)

        processor.process()

        # Read silver dataset
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])
        df = table.to_pandas()

        # Fixture has 4 articles, but 1 is empty
        # Should only have 3 records
        assert len(df) == 3

        # Verify empty article is not present
        titles = df['title'].tolist()
        assert 'Maqaal Banaan' not in titles

    def test_ids_unique(self, bbc_fixture_path, temp_data_dir, monkeypatch):
        """Test that all record IDs are unique."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = BBCSomaliProcessor()
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bbc_fixture_path, processor.staging_file)

        processor.process()

        # Read silver dataset
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])
        df = table.to_pandas()

        ids = df['id'].tolist()
        assert len(ids) == len(set(ids)), "Record IDs are not unique"

    def test_token_counts_positive(self, bbc_fixture_path, temp_data_dir, monkeypatch):
        """Test that all processed records have positive token counts."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = BBCSomaliProcessor()
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bbc_fixture_path, processor.staging_file)

        processor.process()

        # Read silver dataset
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])
        df = table.to_pandas()

        # All records should have positive token counts
        assert all(df['tokens'] > 0), "Some records have zero or negative token counts"

    def test_schema_consistency_with_wikipedia(self, bbc_fixture_path, temp_data_dir, monkeypatch):
        """Test that BBC silver schema matches Wikipedia silver schema."""
        monkeypatch.chdir(temp_data_dir.parent)

        processor = BBCSomaliProcessor()
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bbc_fixture_path, processor.staging_file)

        processor.process()

        # Read silver dataset
        silver_base = Path("data/processed/silver")
        parquet_files = list(silver_base.rglob("*.parquet"))
        table = pq.read_table(parquet_files[0])

        # Verify schema matches expected (same as Wikipedia)
        from somali_dialect_classifier.preprocessing.silver_writer import SilverDatasetWriter
        writer = SilverDatasetWriter()

        # Schema should match exactly
        assert table.schema == writer.SCHEMA, "BBC schema doesn't match expected silver schema"
