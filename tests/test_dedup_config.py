"""
Tests for centralized deduplication configuration.

Validates that dedup settings from config system correctly propagate
to DedupEngine via PipelineSetup.
"""

import os

import pytest

from somali_dialect_classifier.infra.config import get_config, reset_config
from somali_dialect_classifier.ingestion.dedup import DedupEngine
from somali_dialect_classifier.ingestion.pipeline_setup import PipelineSetup


class TestDedupConfiguration:
    """Test centralized deduplication configuration."""

    def test_default_config_values(self):
        """Test dedup config uses correct defaults."""
        reset_config()
        config = get_config()

        assert config.dedup.hash_fields == ["text", "url"]
        assert config.dedup.enable_minhash is True
        assert config.dedup.similarity_threshold == 0.85
        assert config.dedup.cache_size == 100_000
        assert config.dedup.num_shards == 10

    def test_dedup_similarity_threshold_environment_override(self, monkeypatch):
        """Test similarity threshold can be overridden via environment variable."""
        monkeypatch.setenv("SDC_DEDUP__SIMILARITY_THRESHOLD", "0.90")
        reset_config()

        config = get_config()
        assert config.dedup.similarity_threshold == 0.90

    def test_dedup_cache_size_environment_override(self, monkeypatch):
        """Test cache size can be overridden via environment variable."""
        monkeypatch.setenv("SDC_DEDUP__CACHE_SIZE", "50000")
        reset_config()

        config = get_config()
        assert config.dedup.cache_size == 50_000

    def test_dedup_enable_minhash_environment_override(self, monkeypatch):
        """Test MinHash can be disabled via environment variable."""
        monkeypatch.setenv("SDC_DEDUP__ENABLE_MINHASH", "false")
        reset_config()

        config = get_config()
        assert config.dedup.enable_minhash is False

    def test_dedup_num_shards_environment_override(self, monkeypatch):
        """Test LSH shards can be configured via environment variable."""
        monkeypatch.setenv("SDC_DEDUP__NUM_SHARDS", "20")
        reset_config()

        config = get_config()
        assert config.dedup.num_shards == 20

    def test_pipeline_setup_creates_engine_with_config(self):
        """Test PipelineSetup.create_dedup_engine uses centralized config."""
        reset_config()
        engine = PipelineSetup.create_dedup_engine()

        assert engine is not None
        assert isinstance(engine, DedupEngine)
        assert engine.config.similarity_threshold == 0.85
        assert engine.config.enable_minhash is True
        assert engine.config.num_shards == 10

    def test_pipeline_setup_respects_environment_config(self, monkeypatch):
        """Test PipelineSetup respects environment overrides."""
        monkeypatch.setenv("SDC_DEDUP__SIMILARITY_THRESHOLD", "0.95")
        monkeypatch.setenv("SDC_DEDUP__NUM_SHARDS", "5")
        reset_config()

        engine = PipelineSetup.create_dedup_engine()

        assert engine.config.similarity_threshold == 0.95
        assert engine.config.num_shards == 5

    def test_dedup_config_validation_bounds(self):
        """Test config validates similarity_threshold bounds."""
        reset_config()
        config = get_config()

        # Valid range: 0.0 to 1.0
        assert 0.0 <= config.dedup.similarity_threshold <= 1.0

    def test_dedup_cache_size_validation(self):
        """Test cache size has minimum bound."""
        reset_config()
        config = get_config()

        # Minimum: 1000
        assert config.dedup.cache_size >= 1000

    def test_multiple_engines_share_config(self):
        """Test multiple engines created from PipelineSetup share same config values."""
        reset_config()

        engine1 = PipelineSetup.create_dedup_engine()
        engine2 = PipelineSetup.create_dedup_engine()

        # Same config values
        assert engine1.config.similarity_threshold == engine2.config.similarity_threshold
        assert engine1.config.num_shards == engine2.config.num_shards

        # But different instances
        assert engine1 is not engine2

    def test_dedup_config_hash_fields_list(self):
        """Test hash_fields is a list with expected default values."""
        reset_config()
        config = get_config()

        assert isinstance(config.dedup.hash_fields, list)
        assert "text" in config.dedup.hash_fields
        assert "url" in config.dedup.hash_fields


@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Environment pollution in CI",
)
class TestDedupConfigIntegration:
    """Integration tests for dedup config with processors."""

    def test_wikipedia_processor_uses_centralized_config(self, monkeypatch):
        """Test Wikipedia processor gets config from central system."""
        from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        monkeypatch.setenv("SDC_DEDUP__SIMILARITY_THRESHOLD", "0.88")
        reset_config()

        processor = WikipediaSomaliProcessor(force=True)

        # Processor's dedup engine should use configured threshold
        assert processor.dedup.config.similarity_threshold == 0.88

    def test_bbc_processor_uses_centralized_config(self, monkeypatch):
        """Test BBC processor gets config from central system."""
        from somali_dialect_classifier.ingestion.processors.bbc_somali_processor import (
            BBCSomaliProcessor,
        )

        monkeypatch.setenv("SDC_DEDUP__CACHE_SIZE", "75000")
        reset_config()

        processor = BBCSomaliProcessor(force=True)

        # Cache size should propagate through to LRUHashSet
        # Note: Cache size is read from env directly in dedup.py (os.environ.get)
        # This test verifies the config system integration
        assert processor.config.dedup.cache_size == 75_000
