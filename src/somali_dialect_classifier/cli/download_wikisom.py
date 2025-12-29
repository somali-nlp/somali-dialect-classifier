"""
CLI entrypoint for downloading and processing Somali Wikipedia.

This module provides the command-line interface for:
- Downloading Somali Wikipedia dumps
- Extracting and processing articles
- Creating silver datasets
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from somali_dialect_classifier.ingestion.processors.wikipedia_somali_processor import (
    WikipediaSomaliProcessor,
)


def _setup_logging() -> None:
    """
    Set up logging for Wikipedia pipeline.

    Uses module-specific logger to prevent cross-contamination with other pipelines.
    """
    # Console logs
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Reset existing handlers
    )

    # File logs (rotating) under logs/
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create handler for Wikipedia-specific log file
    fh = RotatingFileHandler(logs_dir / "download_wikisom.log", maxBytes=5_000_000, backupCount=3)
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    # Add handler to capture all logs from processors
    # Use root logger but with module filter
    root_logger = logging.getLogger()

    # Remove any existing file handlers to prevent duplication
    root_logger.handlers = [
        h for h in root_logger.handlers if not isinstance(h, RotatingFileHandler)
    ]

    # Add our file handler
    root_logger.addHandler(fh)


def main() -> None:
    """
    Main entry point for executing the Somali Wikipedia data processing pipeline.

    This function sets up logging, initializes the `SomaliWikipediaProcessor`,
    and explicitly orchestrates download, extract, and process steps.
    After completion, it prints the paths to the raw, staging, and processed files.
    """
    _setup_logging()

    try:
        processor = WikipediaSomaliProcessor()
        dump_file = processor.download()
        staging_file = processor.extract()
        processed_file = processor.process()

        print("\n✓ Pipeline completed successfully!")
        print(f"  Dump: {dump_file}")
        print(f"  Staging: {staging_file}")
        print(f"  Processed: {processed_file}")

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
