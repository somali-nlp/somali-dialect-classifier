"""
CLI entrypoint for downloading and processing Somali Wikipedia.

This module provides the command-line interface for:
- Downloading Somali Wikipedia dumps
- Extracting and processing articles
- Creating silver datasets
"""

import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from somdialc.ingestion.processors.wikipedia_somali_processor import (
    WikipediaSomaliProcessor,
)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    ``--help``/``-h`` is handled entirely by argparse: it prints usage and
    exits with status 0 before any pipeline object is constructed, so it can
    never trigger a real download or touch the ledger.
    """
    parser = argparse.ArgumentParser(
        prog="wikisom-download",
        description="Download and process the Somali Wikipedia dump",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download and reprocessing even if a cached dump or output files exist",
    )
    return parser.parse_args()


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

    This function parses CLI arguments, sets up logging, initializes the
    `WikipediaSomaliProcessor`, and explicitly orchestrates download, extract,
    and process steps. After completion, it prints the paths to the raw,
    staging, and processed files.
    """
    args = _parse_args()

    _setup_logging()

    try:
        processor = WikipediaSomaliProcessor(force=args.force)
        dump_file = processor.download()
        if dump_file is None:
            # 304 Not Modified — dump unchanged since last run, nothing to do.
            processor._finalise_pipeline_run(status="COMPLETED", records_processed=0)
            print(
                "\n✓ Wikipedia dump unchanged since last run (304 Not Modified). Nothing to process."
            )
            return

        staging_file = processor.extract()
        if staging_file is None:
            # All articles already in ledger — Level-2 dedup short-circuits.
            processor._finalise_pipeline_run(status="COMPLETED", records_processed=0)
            print("\n✓ No new Wikipedia articles to process (all already in ledger).")
            return

        processed_file = processor.process()
        processor._finalise_pipeline_run(status="COMPLETED")

        print("\n✓ Pipeline completed successfully!")
        print(f"  Dump: {dump_file}")
        print(f"  Staging: {staging_file}")
        print(f"  Processed: {processed_file}")

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        try:
            processor._finalise_pipeline_run(status="FAILED", error=str(e))
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
