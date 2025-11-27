"""
Tests for force reprocessing functionality.

These tests ensure that:
1. Processors skip existing files by default
2. The force flag enables reprocessing
3. Reprocessing removes old files before creating new ones
4. BBC caching respects parameter changes
"""

import json

import pytest

# Skip integration tests - require full pipeline with external data
pytestmark = pytest.mark.skip(
    reason="Integration tests require full pipeline run with external data"
)

from somali_dialect_classifier.ingestion.processors.bbc_somali_processor import BBCSomaliProcessor


@pytest.fixture
def temp_work_dir(tmp_path, monkeypatch):
    """Set up temporary working directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    yield tmp_path


class TestForceReprocessing:
    """Tests for force reprocessing flag."""

    def test_process_skips_existing_file_by_default(self, temp_work_dir):
        """Test that process() skips when processed file exists."""
        processor = BBCSomaliProcessor(max_articles=5)

        # Create mock staging file
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        with open(processor.staging_file, "w") as f:
            json.dump(
                [
                    {
                        "title": "Test Article",
                        "text": "Test content",
                        "url": "https://example.com",
                        "date": "2025-01-01",
                        "scraped_at": "2025-01-01T00:00:00Z",
                        "category": "news",
                    }
                ],
                f,
            )

        # Create mock processed file
        processor.processed_dir.mkdir(parents=True, exist_ok=True)
        with open(processor.processed_file, "w") as f:
            f.write("=== Test Article ===\nOld processed content\n\n")

        # Process should skip
        result = processor.process()

        # Verify file wasn't changed
        with open(processor.processed_file) as f:
            content = f.read()
        assert "Old processed content" in content
        assert result == processor.processed_file

    def test_process_with_force_flag_reprocesses(self, temp_work_dir):
        """Test that force=True causes reprocessing."""
        processor = BBCSomaliProcessor(max_articles=5, force=True)

        # Create mock staging file with proper Somali text
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        with open(processor.staging_file, "w") as f:
            json.dump(
                [
                    {
                        "title": "Wararka Cusub",
                        "text": "<p>Waxaan waa maqaal cusub oo ku saabsan xaalada wadanka Soomaaliya. Dowladda way sheegtay in ay tahay mid fiican.</p>",
                        "url": "https://example.com",
                        "date": "2025-01-01",
                        "scraped_at": "2025-01-01T00:00:00Z",
                        "category": "news",
                    }
                ],
                f,
            )

        # Create mock processed file
        processor.processed_dir.mkdir(parents=True, exist_ok=True)
        with open(processor.processed_file, "w") as f:
            f.write("=== Test Article ===\nOld processed content\n\n")

        # Process with force should reprocess
        result = processor.process()

        # Verify file was changed
        with open(processor.processed_file) as f:
            content = f.read()
        assert "Old processed content" not in content
        # Check for Somali words from the new content
        assert any(word in content.lower() for word in ["waxaan", "cusub", "wadanka", "soomaaliya"])
        assert result == processor.processed_file

    def test_extract_skips_existing_staging_by_default(self, temp_work_dir):
        """Test that extract() skips when staging file exists."""
        processor = BBCSomaliProcessor(max_articles=5)

        # Create mock article links file
        processor.raw_dir.mkdir(parents=True, exist_ok=True)
        with open(processor.article_links_file, "w") as f:
            json.dump(
                {
                    "links": ["https://example.com/article1"],
                    "total_discovered": 1,
                    "total_to_scrape": 1,
                    "discovered_at": "2025-01-01",
                    "max_articles_limit": 5,
                },
                f,
            )

        # Create mock staging file
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        with open(processor.staging_file, "w") as f:
            json.dump([{"title": "Old Article"}], f)

        # Extract should skip
        result = processor.extract()

        # Verify file wasn't changed
        with open(processor.staging_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["title"] == "Old Article"
        assert result == processor.staging_file


class TestBBCCacheInvalidation:
    """Tests for BBC article link caching with parameter changes."""

    def test_bbc_reuses_cache_with_same_parameters(self, temp_work_dir):
        """Test that BBC reuses cached links when max_articles matches."""
        processor = BBCSomaliProcessor(max_articles=10)

        # Create cached article links
        processor.raw_dir.mkdir(parents=True, exist_ok=True)
        cached_data = {
            "links": [f"https://example.com/article{i}" for i in range(10)],
            "total_discovered": 50,
            "total_to_scrape": 10,
            "discovered_at": "2025-01-01",
            "max_articles_limit": 10,
        }
        with open(processor.article_links_file, "w") as f:
            json.dump(cached_data, f)

        # download() should reuse cache
        result = processor.download()

        # Verify cache was reused
        with open(processor.article_links_file) as f:
            data = json.load(f)
        assert data["max_articles_limit"] == 10
        assert len(data["links"]) == 10
        assert result == processor.article_links_file

    def test_bbc_invalidates_cache_on_parameter_change(self, temp_work_dir, monkeypatch):
        """Test that BBC re-discovers when max_articles changes."""
        # Create initial cache with max_articles=10
        processor1 = BBCSomaliProcessor(max_articles=10)
        processor1.raw_dir.mkdir(parents=True, exist_ok=True)
        cached_data = {
            "links": [f"https://example.com/article{i}" for i in range(10)],
            "total_discovered": 50,
            "total_to_scrape": 10,
            "discovered_at": "2025-01-01",
            "max_articles_limit": 10,
        }
        with open(processor1.article_links_file, "w") as f:
            json.dump(cached_data, f)

        # Mock _get_article_links to avoid actual network calls
        def mock_get_article_links(self):
            return [f"https://example.com/article{i}" for i in range(100)]

        # Mock robots.txt check
        def mock_check_robots_txt(self):
            pass

        monkeypatch.setattr(BBCSomaliProcessor, "_get_article_links", mock_get_article_links)
        monkeypatch.setattr(BBCSomaliProcessor, "_check_robots_txt", mock_check_robots_txt)

        # Create new processor with different max_articles
        processor2 = BBCSomaliProcessor(max_articles=20)

        # download() should re-discover
        result = processor2.download()

        # Verify cache was updated with new limit
        with open(processor2.article_links_file) as f:
            data = json.load(f)
        assert data["max_articles_limit"] == 20
        assert len(data["links"]) == 20  # Should have 20 links now
        assert result == processor2.article_links_file

    def test_bbc_force_flag_rediscovers_articles(self, temp_work_dir, monkeypatch):
        """Test that force=True bypasses cache even with same parameters."""
        # Create initial cache
        processor = BBCSomaliProcessor(max_articles=10, force=True)
        processor.raw_dir.mkdir(parents=True, exist_ok=True)
        cached_data = {
            "links": ["https://example.com/old-article"],
            "total_discovered": 1,
            "total_to_scrape": 1,
            "discovered_at": "2025-01-01",
            "max_articles_limit": 10,
        }
        with open(processor.article_links_file, "w") as f:
            json.dump(cached_data, f)

        # Mock methods to avoid network calls
        def mock_get_article_links(self):
            return ["https://example.com/new-article"]

        def mock_check_robots_txt(self):
            pass

        monkeypatch.setattr(BBCSomaliProcessor, "_get_article_links", mock_get_article_links)
        monkeypatch.setattr(BBCSomaliProcessor, "_check_robots_txt", mock_check_robots_txt)

        # download() with force should re-discover
        processor.download()

        # Verify new articles were discovered
        with open(processor.article_links_file) as f:
            data = json.load(f)
        assert "new-article" in data["links"][0]


class TestForceParameter:
    """Tests for force parameter inheritance."""

    def test_force_parameter_passed_to_base_pipeline(self, temp_work_dir):
        """Test that force parameter is properly passed to BasePipeline."""
        processor_default = BBCSomaliProcessor(max_articles=5)
        processor_force = BBCSomaliProcessor(max_articles=5, force=True)

        assert processor_default.force is False
        assert processor_force.force is True

    def test_all_processors_support_force_parameter(self, temp_work_dir):
        """Test that all processors accept force parameter."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        # Both processors should accept force parameter
        bbc = BBCSomaliProcessor(max_articles=5, force=True)
        wiki = WikipediaSomaliProcessor(force=True)

        assert bbc.force is True
        assert wiki.force is True
