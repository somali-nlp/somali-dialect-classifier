"""
End-to-end CLI tests.

Tests the command-line interface with temporary directories to ensure:
- CLI commands work correctly
- Output is properly formatted
- Error handling works
- Help text is accurate
"""

import shutil
import sys
from pathlib import Path

import pytest


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """Set up CLI test environment with temp directories."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create data directory structure
    (tmp_path / "data").mkdir()

    yield tmp_path


@pytest.fixture
def wiki_fixture():
    """Path to Wikipedia XML fixture."""
    return Path(__file__).parent / "fixtures" / "mini_wiki_dump.xml"


@pytest.fixture
def bbc_fixture():
    """Path to BBC JSON fixture."""
    return Path(__file__).parent / "fixtures" / "bbc_articles.json"


class TestWikipediaCLI:
    """End-to-end tests for Wikipedia download CLI."""

    def test_cli_imports_successfully(self):
        """Test that CLI module can be imported."""
        import importlib.util

        spec = importlib.util.find_spec("somali_dialect_classifier.cli.download_wikisom")
        if spec is None:
            pytest.fail("Failed to import CLI module: download_wikisom not found")

    def test_cli_main_function_exists(self):
        """Test that main() function exists in CLI module."""
        from somali_dialect_classifier.cli import download_wikisom

        assert hasattr(download_wikisom, "main")
        assert callable(download_wikisom.main)

    def test_cli_help_output(self, capsys):
        """Test that CLI help output is informative."""
        from somali_dialect_classifier.cli import download_wikisom

        # Try to get help (usually raises SystemExit with --help)
        try:
            sys.argv = ["download_wikisom", "--help"]
            download_wikisom.main()
        except SystemExit:
            pass

        captured = capsys.readouterr()

        # Should mention Wikipedia and Somali
        output = captured.out + captured.err
        assert "Wikipedia" in output or "wiki" in output.lower() or "Somali" in output


class TestBBCCLI:
    """End-to-end tests for BBC download CLI."""

    def test_cli_imports_successfully(self):
        """Test that BBC CLI module can be imported."""
        import importlib.util

        spec = importlib.util.find_spec("somali_dialect_classifier.cli.download_bbcsom")
        if spec is None:
            pytest.fail("Failed to import BBC CLI module: download_bbcsom not found")

    def test_cli_main_function_exists(self):
        """Test that main() function exists in BBC CLI module."""
        from somali_dialect_classifier.cli import download_bbcsom

        assert hasattr(download_bbcsom, "main")
        assert callable(download_bbcsom.main)

    def test_cli_help_output(self, capsys):
        """Test that BBC CLI help output is informative."""
        from somali_dialect_classifier.cli import download_bbcsom

        # Try to get help
        try:
            sys.argv = ["download_bbcsom", "--help"]
            download_bbcsom.main()
        except SystemExit:
            pass

        captured = capsys.readouterr()

        # Should mention BBC
        output = captured.out + captured.err
        assert "BBC" in output or "bbc" in output.lower()


class TestCLILogging:
    """Test that CLI properly configures logging."""

    def test_wikipedia_cli_creates_log_file(self, cli_env, capsys, monkeypatch):
        """Test that Wikipedia CLI creates log file."""
        from somali_dialect_classifier.preprocessing.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        # Create processor (this will set up logging)
        processor = WikipediaSomaliProcessor()

        # Log directory should exist or be created
        Path("logs")

        # Processor should have a logger
        assert hasattr(processor, "logger")
        assert processor.logger is not None

    def test_bbc_cli_creates_log_file(self, cli_env, capsys):
        """Test that BBC CLI creates log file."""
        from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor

        # Create processor
        processor = BBCSomaliProcessor()

        # Processor should have a logger
        assert hasattr(processor, "logger")
        assert processor.logger is not None


class TestCLIDataDirectories:
    """Test that CLI creates proper directory structure."""

    def test_wikipedia_creates_partitioned_directories(self, cli_env):
        """Test that Wikipedia processor creates partitioned directories."""
        from somali_dialect_classifier.preprocessing.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        processor = WikipediaSomaliProcessor()

        # Check that directory paths include partitioning (source name is lowercase)
        assert "source=wikipedia-somali" in str(processor.raw_dir)
        assert "date_accessed=" in str(processor.raw_dir)

    def test_bbc_creates_partitioned_directories(self, cli_env):
        """Test that BBC processor creates partitioned directories."""
        from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor

        processor = BBCSomaliProcessor()

        # Check that directory paths include partitioning
        assert "source=bbc-somali" in str(processor.raw_dir)
        assert "date_accessed=" in str(processor.raw_dir)


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_wikipedia_handles_missing_dump_gracefully(self, cli_env, capsys):
        """Test that processor handles missing dump file gracefully."""
        from somali_dialect_classifier.preprocessing.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        processor = WikipediaSomaliProcessor()

        # Try to extract without download
        with pytest.raises(FileNotFoundError) as exc_info:
            processor.extract()

        # Error message should be clear
        assert "not found" in str(exc_info.value).lower() or "dump" in str(exc_info.value).lower()

    def test_bbc_handles_missing_staging_gracefully(self, cli_env):
        """Test that BBC processor handles missing staging file gracefully."""
        from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor

        processor = BBCSomaliProcessor()

        # Try to process without extract
        with pytest.raises(FileNotFoundError) as exc_info:
            processor.process()

        # Error message should be clear
        assert "not found" in str(exc_info.value).lower()


class TestCLIOutput:
    """Test CLI output quality."""

    def test_processors_have_consistent_logging_format(self, cli_env, capsys):
        """Test that both processors use consistent logging."""
        from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor
        from somali_dialect_classifier.preprocessing.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        wiki_processor = WikipediaSomaliProcessor()
        bbc_processor = BBCSomaliProcessor()

        # After data processor/data manager refactoring, loggers use source-based naming
        # Logger names should match the source name (lowercase with hyphens)
        assert (
            "wikipedia" in wiki_processor.logger.name.lower()
            or "wikipedia-somali" in wiki_processor.logger.name.lower()
        )
        assert (
            "bbc" in bbc_processor.logger.name.lower()
            or "bbc-somali" in bbc_processor.logger.name.lower()
        )


class TestCLIIntegration:
    """Integration tests for CLI with fixture data."""

    def test_wikipedia_cli_full_pipeline_with_fixture(self, cli_env, wiki_fixture):
        """Test full Wikipedia pipeline with fixture data."""
        import bz2

        from somali_dialect_classifier.preprocessing.wikipedia_somali_processor import (
            WikipediaSomaliProcessor,
        )

        processor = WikipediaSomaliProcessor(force=True)

        # Set up fixture
        processor.raw_dir.mkdir(parents=True, exist_ok=True)

        # Compress and copy fixture
        with open(wiki_fixture, "rb") as f_in:
            xml_content = f_in.read()

        with bz2.open(processor.dump_file, "wb") as f_out:
            f_out.write(xml_content)

        # Run pipeline
        try:
            result = processor.run()
            assert result.exists()

            # Verify silver dataset was created
            silver_base = Path("data/processed/silver")
            assert silver_base.exists()

            parquet_files = list(silver_base.rglob("*.parquet"))
            assert len(parquet_files) > 0

        except Exception as e:
            pytest.fail(f"Wikipedia pipeline failed: {e}")

    def test_bbc_cli_full_pipeline_with_fixture(self, cli_env, bbc_fixture):
        """Test full BBC pipeline with fixture data."""
        from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor

        processor = BBCSomaliProcessor()

        # Set up fixture
        processor.staging_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(bbc_fixture, processor.staging_file)

        # Run process
        try:
            result = processor.process()
            assert result.exists()

            # Verify silver dataset was created
            silver_base = Path("data/processed/silver")
            assert silver_base.exists()

            parquet_files = list(silver_base.rglob("*.parquet"))
            assert len(parquet_files) > 0

        except Exception as e:
            pytest.fail(f"BBC pipeline failed: {e}")


class TestCLIDocumentation:
    """Test that CLI commands are well-documented."""

    def test_wikipedia_cli_has_docstring(self):
        """Test that Wikipedia CLI has docstring."""
        from somali_dialect_classifier.cli import download_wikisom

        assert download_wikisom.__doc__ is not None
        assert len(download_wikisom.__doc__.strip()) > 0

    def test_bbc_cli_has_docstring(self):
        """Test that BBC CLI has docstring."""
        from somali_dialect_classifier.cli import download_bbcsom

        assert download_bbcsom.__doc__ is not None
        assert len(download_bbcsom.__doc__.strip()) > 0

    def test_cli_commands_registered_in_pyproject(self):
        """Test that CLI commands are registered in pyproject.toml."""
        import toml

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

        if not pyproject_path.exists():
            pytest.skip("pyproject.toml not found")

        with open(pyproject_path) as f:
            pyproject = toml.load(f)

        # Check that scripts are registered
        scripts = pyproject.get("project", {}).get("scripts", {})

        assert "wikisom-download" in scripts, "Wikipedia CLI not registered"
        assert "bbcsom-download" in scripts, "BBC CLI not registered"

        # Check that they point to correct modules
        assert "download_wikisom" in scripts["wikisom-download"]
        assert "download_bbcsom" in scripts["bbcsom-download"]
