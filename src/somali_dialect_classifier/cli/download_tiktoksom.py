#!/usr/bin/env python3
"""
Download and process TikTok Somali comments.

This script scrapes Somali comments from TikTok videos using Apify's
TikTok Comments Scraper actor.

Usage:
    # Create video URLs file
    cat > videos.txt <<EOF
    https://www.tiktok.com/@user/video/123
    https://www.tiktok.com/@user/video/456
    EOF

    # Download and process comments
    python -m somali_dialect_classifier.cli.download_tiktoksom --video-urls videos.txt

    # With comment limits
    python -m somali_dialect_classifier.cli.download_tiktoksom --video-urls videos.txt --max-comments 10000

    # Force reprocessing
    python -m somali_dialect_classifier.cli.download_tiktoksom --video-urls videos.txt --force
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from ..preprocessing.tiktok_somali_processor import TikTokSomaliProcessor
from ..config import get_config


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)

    # Configure logging to both file and console
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('logs/download_tiktoksom.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_video_urls(path: Path) -> List[str]:
    """
    Load video URLs from file (supports .txt and .json formats).

    Args:
        path: Path to video URLs file

    Returns:
        List of TikTok video URLs

    Raises:
        ValueError: If file format is invalid or no URLs found
    """
    if not path.exists():
        raise FileNotFoundError(f"Video URLs file not found: {path}")

    if path.suffix == '.json':
        # JSON format: {"video_urls": [...], "metadata": {...}}
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            urls = data.get('video_urls', [])
            if not urls:
                raise ValueError(f"No 'video_urls' key found in JSON file: {path}")
            return urls
    else:
        # Plain text format: one URL per line, # for comments
        urls = []
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                # Basic URL validation
                if not line.startswith('https://'):
                    logging.warning(f"Line {line_num}: Invalid URL (skipping): {line}")
                    continue
                urls.append(line)

        if not urls:
            raise ValueError(f"No valid URLs found in file: {path}")

        return urls


def estimate_cost(num_videos: int, avg_comments_per_video: int = 500) -> dict:
    """
    Estimate Apify cost for scraping.

    Args:
        num_videos: Number of videos to scrape
        avg_comments_per_video: Estimated average comments per video

    Returns:
        Dict with cost estimates
    """
    total_comments = num_videos * avg_comments_per_video

    # Apify pricing: ~$1 per 1,000 results
    # Effective cost after linguistic filtering: ~$3.67 per 1k linguistic comments
    # (27% of Apify results are emoji-only/non-linguistic)
    compute_units = total_comments / 1000 * 0.01  # Rough estimate
    cost_usd = total_comments / 1000 * 1.0

    return {
        'num_videos': num_videos,
        'estimated_comments': total_comments,
        'estimated_compute_units': round(compute_units, 4),
        'estimated_cost_usd': round(cost_usd, 2)
    }


def main():
    """Main entry point for TikTok downloader CLI."""
    parser = argparse.ArgumentParser(
        description='Download and process TikTok Somali comments via Apify',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--video-urls',
        type=Path,
        required=True,
        help='Path to file with TikTok video URLs (txt or json format)'
    )

    parser.add_argument(
        '--max-comments',
        type=int,
        default=None,
        help='Maximum total comments to scrape (default: from config or unlimited)'
    )

    parser.add_argument(
        '--max-per-video',
        type=int,
        default=None,
        help='Maximum comments per video (default: from config or unlimited)'
    )

    parser.add_argument(
        '--api-token',
        type=str,
        default=None,
        help='Apify API token (overrides SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN env var)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing even if output exists'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Load configuration
    config = get_config()

    # Get API token (CLI arg > env var)
    api_token = args.api_token or config.scraping.tiktok.apify_api_token
    if not api_token:
        logger.error("Apify API token not provided!")
        logger.error("Please set SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN environment variable")
        logger.error("or provide --api-token argument")
        sys.exit(1)

    # Load video URLs
    try:
        video_urls = load_video_urls(args.video_urls)
        logger.info(f"Loaded {len(video_urls)} video URLs from {args.video_urls}")
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load video URLs: {e}")
        sys.exit(1)

    # Display cost estimate
    cost_est = estimate_cost(len(video_urls), avg_comments_per_video=500)
    logger.info("=" * 60)
    logger.info("COST ESTIMATE (Apify)")
    logger.info("=" * 60)
    logger.info(f"Videos: {cost_est['num_videos']}")
    logger.info(f"Estimated comments: {cost_est['estimated_comments']:,}")
    logger.info(f"Estimated cost: ${cost_est['estimated_cost_usd']}")
    logger.info("Note: Actual cost depends on actual comment counts per video")
    logger.info("=" * 60)

    # Confirm if cost is significant
    if cost_est['estimated_cost_usd'] > 10:
        logger.warning(f"⚠️  Estimated cost is ${cost_est['estimated_cost_usd']}")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Aborted by user")
            sys.exit(0)

    # Initialize processor
    logger.info("Initializing TikTok processor...")

    processor = TikTokSomaliProcessor(
        apify_api_token=api_token,
        apify_user_id=config.scraping.tiktok.apify_user_id,
        video_urls=video_urls,
        force=args.force
    )

    # Run pipeline: download → extract → process → silver
    try:
        logger.info("Starting TikTok pipeline...")

        # Phase 1: Discovery (save video URLs)
        logger.info("\n[1/4] Discovery: Saving video URLs...")
        video_urls_file = processor.download()
        logger.info(f"✓ Video URLs saved: {video_urls_file}")

        # Phase 2: Extraction (scrape via Apify)
        logger.info("\n[2/4] Extraction: Scraping comments via Apify...")
        logger.info("This may take 10-30 minutes depending on video count...")
        staging_file = processor.extract()
        logger.info(f"✓ Comments extracted: {staging_file}")

        # Phase 3: Processing (clean, deduplicate)
        logger.info("\n[3/4] Processing: Cleaning and deduplicating...")
        processed_file = processor.process()
        logger.info(f"✓ Processing complete: {processed_file}")

        # Phase 4: Silver dataset creation
        logger.info("\n[4/4] Silver Dataset Creation...")
        if processor.silver_path:
            logger.info(f"✓ Silver dataset: {processor.silver_path}")
        else:
            logger.warning("⚠️  Silver dataset not created (check logs for details)")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TIKTOK PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Run ID: {processor.run_id}")
        logger.info(f"Source: {processor.source}")

        if processor.silver_path and processor.silver_path.exists():
            file_size_mb = processor.silver_path.stat().st_size / (1024 * 1024)
            logger.info(f"Silver dataset: {processor.silver_path}")
            logger.info(f"Dataset size: {file_size_mb:.2f} MB")
        else:
            logger.warning("Silver dataset not found")

        logger.info("\nNext steps:")
        logger.info("1. Check metrics: data/metrics/")
        logger.info("2. Inspect silver dataset: data/processed/silver/")
        logger.info("3. Review logs: logs/")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
