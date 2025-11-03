"""
CLI entrypoint for downloading and processing BBC Somali news.

This module provides the command-line interface for:
- Scraping BBC Somali articles ethically
- Processing and cleaning news content
- Creating silver datasets
"""

import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from somali_dialect_classifier.preprocessing import BBCSomaliProcessor


def _setup_logging() -> None:
    """
    Set up logging for BBC pipeline.

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

    # Create handler for BBC-specific log file
    fh = RotatingFileHandler(logs_dir / "download_bbcsom.log", maxBytes=5_000_000, backupCount=3)
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
    Main entry point for executing the BBC Somali data scraping pipeline.

    This function sets up logging, initializes the `BBCSomaliProcessor`,
    and explicitly orchestrates discover, scrape, and process steps.
    After completion, it prints the paths to the raw, staging, and processed files.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Download and process BBC Somali news articles")
    parser.add_argument(
        "--max-articles",
        type=int,
        default=None,
        help="Maximum number of articles to scrape (default: unlimited - scrapes all discovered articles)",
    )
    parser.add_argument(
        "--min-delay",
        type=int,
        default=1,
        help="Minimum delay between requests in seconds (default: 1)",
    )
    parser.add_argument(
        "--max-delay",
        type=int,
        default=3,
        help="Maximum delay between requests in seconds (default: 3)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force reprocessing even if output files exist"
    )
    args = parser.parse_args()

    _setup_logging()

    try:
        # Initialize with user-specified parameters
        processor = BBCSomaliProcessor(
            max_articles=args.max_articles,
            delay_range=(args.min_delay, args.max_delay),
            force=args.force,
        )

        article_links_file = processor.download()
        staging_file = processor.extract()
        processed_file = processor.process()

        print("\n✓ Pipeline completed successfully!")
        print(f"  Article links: {article_links_file}")
        print(f"  Scraped articles: {staging_file}")
        print(f"  Processed: {processed_file}")

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
