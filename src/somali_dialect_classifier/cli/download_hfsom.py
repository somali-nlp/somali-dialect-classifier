"""
CLI for downloading and processing HuggingFace datasets.

Usage:
    hfsom-download mc4 --max-records 10000               # Process MC4
    hfsom-download mc4 --force                           # Reprocess MC4
    hfsom-download mc4                                    # Process full MC4 dataset

Supports:
    - mc4 (Multilingual C4) - Primary HuggingFace data source

Note: OSCAR and MADLAD-400 have been removed. See:
    - docs/decisions/001-oscar-exclusion.md (OSCAR - requires auth, less data)
    - docs/decisions/003-madlad-400-exclusion.md (MADLAD - incompatible with datasets>=3.0)
"""

import argparse
import logging
import sys
import os
from pathlib import Path

from somali_dialect_classifier.preprocessing.huggingface_somali_processor import (
    HuggingFaceSomaliProcessor,
    create_mc4_processor,
)

# Note: Progress bars are ENABLED so users can see download progress
# To suppress, uncomment: os.environ['HF_DATASETS_DISABLE_PROGRESS_BARS'] = '1'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/download_hfsom.log'),  # Updated filename
        logging.StreamHandler(sys.stdout)
    ]
)

# Keep datasets logging at WARNING level (show important messages, not DEBUG spam)
logging.getLogger('datasets').setLevel(logging.WARNING)
logging.getLogger('filelock').setLevel(logging.WARNING)
logging.getLogger('huggingface_hub').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description='Download and process HuggingFace datasets for Somali NLP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process MC4 Somali subset (limit 10k records)
  %(prog)s mc4 --max-records 10000

  # Process full MC4 dataset
  %(prog)s mc4

  # Force reprocessing
  %(prog)s mc4 --force

  # Custom dataset (advanced)
  %(prog)s custom --dataset-name allenai/gdelt --config so --split train

Note: Only MC4 is supported. OSCAR and MADLAD-400 have been removed.
See docs/decisions/ for details.
        """
    )

    parser.add_argument(
        'dataset',
        nargs='?',  # Make optional - shows help if missing
    )

    parser.add_argument(
        '--max-records',
        type=int,
        default=None,
        help='Maximum number of records to process (None = unlimited)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing even if output exists'
    )

    # Note: --all flag removed since only MC4 is supported
    # Kept for backwards compatibility but now processes only MC4

    # Custom dataset options
    custom_group = parser.add_argument_group('custom dataset options')
    custom_group.add_argument(
        '--dataset-name',
        type=str,
        help='HuggingFace dataset name (e.g., "mc4", "allenai/gdelt")'
    )
    custom_group.add_argument(
        '--config',
        type=str,
        default=None,
        help='Dataset configuration/subset (e.g., "so")'
    )
    custom_group.add_argument(
        '--split',
        type=str,
        default='train',
        help='Dataset split (default: train)'
    )
    custom_group.add_argument(
        '--text-field',
        type=str,
        default='text',
        help='Field containing text content (default: text)'
    )
    custom_group.add_argument(
        '--title-field',
        type=str,
        default=None,
        help='Field containing title (optional)'
    )
    custom_group.add_argument(
        '--url-field',
        type=str,
        default=None,
        help='Field containing URL (optional)'
    )
    custom_group.add_argument(
        '--metadata-fields',
        type=str,
        nargs='+',
        default=None,
        help='Additional metadata fields to include'
    )

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Show help if no dataset specified
    if not args.dataset:
        parser.print_help()
        print("\n" + "="*70)
        print("ERROR: Please specify a dataset to process")
        print("="*70)
        print("\nAvailable datasets:")
        print("  mc4       - Multilingual C4 (large web corpus)")
        print("  custom    - Custom HuggingFace dataset")
        print("\nNote: Only MC4 is supported. OSCAR and MADLAD-400 have been removed.")
        print("See docs/decisions/ for details.")
        print("\nExamples:")
        print("  hfsom-download mc4 --max-records 1000")
        print("  hfsom-download mc4 --force")
        print("="*70)
        sys.exit(1)

    # Create logs directory if not exists
    Path('logs').mkdir(exist_ok=True)

    # ============================================================================
    # REMOVED: --all flag processing
    # ============================================================================
    #
    # The --all flag has been REMOVED because only MC4 is now supported.
    # OSCAR and MADLAD-400 have been excluded from the project.
    #
    # See:
    # - docs/decisions/001-oscar-exclusion.md (OSCAR)
    # - docs/decisions/003-madlad-400-exclusion.md (MADLAD-400)
    #
    # To process MC4, simply use: hfsom-download mc4
    # ============================================================================

    # Single dataset processing
    logger.info(f"Starting HuggingFace dataset processing: {args.dataset}")

    try:
        # Create processor based on dataset type
        if args.dataset == 'mc4':
            logger.info("Using MC4 (Multilingual C4) processor")
            processor = create_mc4_processor(
                max_records=args.max_records,
                force=args.force
            )

        # ============================================================================
        # REMOVED: OSCAR and MADLAD-400 Processing
        # ============================================================================
        #
        # OSCAR removed - requires authentication and has less data than MC4
        # See: docs/decisions/001-oscar-exclusion.md
        #
        # MADLAD-400 removed - incompatible with datasets>=3.0
        # See: docs/decisions/003-madlad-400-exclusion.md
        # ============================================================================

        elif args.dataset == 'custom':
            if not args.dataset_name:
                logger.error("--dataset-name required for custom datasets")
                sys.exit(1)

            logger.info(f"Using custom dataset: {args.dataset_name}")
            processor = HuggingFaceSomaliProcessor(
                dataset_name=args.dataset_name,
                dataset_config=args.config,
                split=args.split,
                text_field=args.text_field,
                title_field=args.title_field,
                url_field=args.url_field,
                metadata_fields=args.metadata_fields,
                max_records=args.max_records,
                force=args.force,
            )

        else:
            logger.error(f"Unknown dataset: {args.dataset}")
            sys.exit(1)

        # Run pipeline
        logger.info("Step 1/3: Creating manifest...")
        manifest_path = processor.download()
        logger.info(f"Manifest created: {manifest_path}")

        logger.info("Step 2/3: Extracting and batching records...")
        staging_dir = processor.extract()
        logger.info(f"Extraction complete: {staging_dir}")

        logger.info("Step 3/3: Processing and writing silver dataset...")
        silver_path = processor.process()
        logger.info(f"Silver dataset written: {silver_path}")

        logger.info("✓ HuggingFace dataset processing complete!")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
