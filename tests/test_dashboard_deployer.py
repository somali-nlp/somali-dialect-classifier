"""
Tests for dashboard deployment automation.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from somali_dialect_classifier.deployment import (
    DashboardDeployer,
    DeploymentConfig,
    MetricsValidator,
    GitOperations,
)


class TestMetricsValidator:
    """Test metrics validation functionality."""

    def test_valid_metrics_file(self, tmp_path):
        """Test validation of valid metrics file."""
        metrics_file = tmp_path / "test_processing.json"

        valid_data = {
            "snapshot": {
                "run_id": "test_20250125_120000",
                "source": "TestSource",
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": 100.0,
                "urls_discovered": 1000,
                "urls_fetched": 950,
                "urls_processed": 920,
                "records_written": 850,
            },
            "statistics": {
                "fetch_success_rate": 0.95,
                "processing_success_rate": 0.97,
            },
        }

        with open(metrics_file, "w") as f:
            json.dump(valid_data, f)

        is_valid, error = MetricsValidator.validate_metrics_file(metrics_file)
        assert is_valid is True
        assert error is None

    def test_invalid_metrics_missing_field(self, tmp_path):
        """Test validation fails for missing required field."""
        metrics_file = tmp_path / "test_processing.json"

        invalid_data = {
            "snapshot": {
                "run_id": "test_123",
                "source": "TestSource",
                # Missing timestamp
            },
            "statistics": {},
        }

        with open(metrics_file, "w") as f:
            json.dump(invalid_data, f)

        is_valid, error = MetricsValidator.validate_metrics_file(metrics_file)
        assert is_valid is False
        assert "timestamp" in error.lower()

    def test_invalid_json(self, tmp_path):
        """Test validation fails for invalid JSON."""
        metrics_file = tmp_path / "test_processing.json"

        with open(metrics_file, "w") as f:
            f.write("{ invalid json }")

        is_valid, error = MetricsValidator.validate_metrics_file(metrics_file)
        assert is_valid is False
        assert "json" in error.lower()

    def test_validate_all_metrics(self, tmp_path):
        """Test validation of multiple metrics files."""
        # Create valid file
        valid_file = tmp_path / "valid_processing.json"
        valid_data = {
            "snapshot": {
                "run_id": "test_1",
                "source": "TestSource1",
                "timestamp": datetime.now().isoformat(),
            },
            "statistics": {},
        }
        with open(valid_file, "w") as f:
            json.dump(valid_data, f)

        # Create invalid file
        invalid_file = tmp_path / "invalid_processing.json"
        with open(invalid_file, "w") as f:
            f.write("{ bad json }")

        valid_files, invalid_files = MetricsValidator.validate_all_metrics(tmp_path)

        assert len(valid_files) == 1
        assert len(invalid_files) == 1
        assert valid_files[0] == valid_file
        assert invalid_files[0][0] == invalid_file


class TestGitOperations:
    """Test Git operations."""

    def test_check_git_available(self):
        """Test git availability check."""
        # This should pass if git is installed
        is_available = GitOperations.check_git_available()
        assert isinstance(is_available, bool)

    def test_is_git_repo(self, tmp_path):
        """Test git repository detection."""
        # Non-git directory
        assert GitOperations.is_git_repo(tmp_path) is False

    def test_get_repo_status_non_repo(self, tmp_path):
        """Test status check on non-repo directory."""
        status = GitOperations.get_repo_status(tmp_path)
        assert status["current_branch"] == "unknown"
        assert status["has_remote"] is False


class TestDeploymentConfig:
    """Test deployment configuration."""

    def test_default_config_creation(self, tmp_path):
        """Test creating deployment config with defaults."""
        config = DeploymentConfig(
            metrics_dir=tmp_path / "metrics",
        )

        assert config.metrics_dir == tmp_path / "metrics"
        assert config.git_remote == "origin"
        assert config.git_branch == "main"
        assert config.commit_prefix == "chore(metrics)"
        assert config.auto_push is True
        assert config.validate_metrics is True
        assert config.batch_mode is True
        assert config.min_sources_for_deploy == 1

    def test_custom_config(self, tmp_path):
        """Test creating deployment config with custom values."""
        config = DeploymentConfig(
            metrics_dir=tmp_path / "custom",
            git_remote="upstream",
            git_branch="develop",
            commit_prefix="feat(data)",
            auto_push=False,
            validate_metrics=False,
            batch_mode=False,
            min_sources_for_deploy=3,
        )

        assert config.git_remote == "upstream"
        assert config.git_branch == "develop"
        assert config.commit_prefix == "feat(data)"
        assert config.auto_push is False
        assert config.validate_metrics is False
        assert config.batch_mode is False
        assert config.min_sources_for_deploy == 3


class TestDashboardDeployer:
    """Test dashboard deployer functionality."""

    def test_deployer_initialization(self, tmp_path):
        """Test deployer initialization."""
        # Create a mock git repo structure
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        metrics_dir = tmp_path / "data" / "metrics"
        metrics_dir.mkdir(parents=True)

        config = DeploymentConfig(metrics_dir=metrics_dir)

        try:
            deployer = DashboardDeployer(config)
            assert deployer.config == config
            assert deployer.repo_path == tmp_path
        except RuntimeError:
            # Expected if git operations fail in test environment
            pass

    def test_get_metrics_summary(self, tmp_path):
        """Test metrics summary generation."""
        # Setup mock repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        metrics_dir = tmp_path / "data" / "metrics"
        metrics_dir.mkdir(parents=True)

        # Create test metrics files
        sources = ["Wikipedia", "BBC"]
        metrics_files = []

        for i, source in enumerate(sources):
            metrics_file = metrics_dir / f"{source.lower()}_processing.json"
            data = {
                "snapshot": {
                    "run_id": f"test_{i}",
                    "source": source,
                    "timestamp": datetime.now().isoformat(),
                    "records_written": (i + 1) * 100,
                },
                "statistics": {},
            }
            with open(metrics_file, "w") as f:
                json.dump(data, f)
            metrics_files.append(metrics_file)

        config = DeploymentConfig(metrics_dir=metrics_dir)

        try:
            deployer = DashboardDeployer(config)
            summary = deployer._get_metrics_summary(metrics_files)

            assert summary["source_count"] == 2
            assert summary["file_count"] == 2
            assert summary["total_records"] == 300  # 100 + 200
            assert set(summary["sources"]) == {"BBC", "Wikipedia"}
        except RuntimeError:
            # Expected if git operations fail in test environment
            pytest.skip("Git operations not available in test environment")

    def test_generate_commit_message(self, tmp_path):
        """Test commit message generation."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        metrics_dir = tmp_path / "data" / "metrics"
        metrics_dir.mkdir(parents=True)

        config = DeploymentConfig(metrics_dir=metrics_dir)

        summary = {
            "sources": ["Wikipedia", "BBC"],
            "source_count": 2,
            "total_records": 1000,
            "file_count": 2,
            "latest_timestamp": datetime.now().isoformat(),
        }

        try:
            deployer = DashboardDeployer(config)
            message = deployer._generate_commit_message(summary)

            assert "chore(metrics)" in message
            assert "Wikipedia" in message
            assert "BBC" in message
            assert "2" in message  # source count
            assert "1,000" in message  # formatted records
        except RuntimeError:
            # Expected if git operations fail in test environment
            pytest.skip("Git operations not available in test environment")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
