#!/usr/bin/env python3
"""
Download and process Språkbanken Somali corpora.

This script downloads and processes 66 Somali language corpora from
University of Gothenburg's Språkbanken repository.

Usage:
    # Download and process all corpora
    python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all

    # Download specific corpus
    python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus somali-ogaden

    # List available corpora
    python -m somali_dialect_classifier.cli.download_sprakbankensom --list

    # Show info about specific corpus
    python -m somali_dialect_classifier.cli.download_sprakbankensom --info somali-cilmi

    # Force reprocessing
    python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all --force
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from somali_dialect_classifier.preprocessing.sprakbanken_somali_processor import (
    CORPUS_INFO,
    SprakbankenSomaliProcessor,
    list_available_corpora,
)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)

    # Configure logging to both file and console
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler("logs/download_sprakbankensom.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def list_corpora():
    """List all available Språkbanken corpora with details."""
    print("\n" + "=" * 70)
    print("AVAILABLE SPRÅKBANKEN SOMALI CORPORA")
    print("=" * 70)
    print()

    # Group by domain
    domains = {}
    for corpus_id, info in CORPUS_INFO.items():
        domain = info.get("domain", "general")
        if domain not in domains:
            domains[domain] = []
        domains[domain].append((corpus_id, info))

    # Display by domain
    for domain in sorted(domains.keys()):
        print(f"\n📚 {domain.upper().replace('_', ' ')} DOMAIN:")
        print("-" * 40)

        for corpus_id, info in sorted(domains[domain]):
            print(f"  • {corpus_id:25}")

            # Add details if available
            if "period" in info:
                print(f"    Period: {info['period']}")
            if "source" in info:
                print(f"    Source: {info['source']}")
            if "genre" in info:
                print(f"    Genre: {info['genre']}")
            if "region" in info:
                print(f"    Region: {info['region']}")
            if "topic" in info:
                print(f"    Topic: {info['topic']}")

    print("\n" + "=" * 70)
    print(f"Total corpora: {len(CORPUS_INFO)}")
    print("License: CC BY 4.0 (all corpora)")
    print("Format: XML (bz2 compressed)")
    print("=" * 70)
    print()
    print("To download all corpora:")
    print("  python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus all")
    print()
    print("To download specific corpus:")
    print("  python -m somali_dialect_classifier.cli.download_sprakbankensom --corpus <corpus_id>")
    print()


def show_corpus_info(corpus_id: str):
    """Show detailed information about a specific corpus."""
    if corpus_id not in CORPUS_INFO:
        print(f"Error: Unknown corpus ID '{corpus_id}'")
        print(f"Available corpus IDs: {', '.join(list_available_corpora())}")
        return

    info = CORPUS_INFO[corpus_id]

    print("\n" + "=" * 60)
    print(f"CORPUS: {corpus_id}")
    print("=" * 60)

    print(f"Domain: {info.get('domain', 'general')}")

    if "period" in info:
        print(f"Period: {info['period']}")
    if "source" in info:
        print(f"Source: {info['source']}")
    if "genre" in info:
        print(f"Genre: {info['genre']}")
    if "region" in info:
        print(f"Region: {info['region']}")
    if "topic" in info:
        print(f"Topic: {info['topic']}")
    if "format" in info:
        print(f"Format: {info['format']}")
    if "type" in info:
        print(f"Type: {info['type']}")

    print("\nLicense: CC BY 4.0")
    print("Format: XML (bz2 compressed)")
    print("Download URL:")
    print(f"  https://spraakbanken.gu.se/lb/resurser/meningsmangder/{corpus_id}.xml.bz2")
    print("Korp Interface:")
    print(f"  https://spraakbanken.gu.se/korp/?mode=somali#?corpus={corpus_id}")
    print("=" * 60)
    print()


def download_and_process(
    corpus_id: str, force: bool = False, batch_size: Optional[int] = None, verbose: bool = False
):
    """
    Download and process Språkbanken corpus/corpora.

    Args:
        corpus_id: Corpus ID or "all" for all corpora
        force: Force reprocessing
        batch_size: Batch size for processing
        verbose: Enable verbose logging
    """
    setup_logging(verbose)

    # Validate corpus_id
    if corpus_id != "all" and corpus_id not in CORPUS_INFO:
        print(f"Error: Unknown corpus ID '{corpus_id}'")
        print(f"Available corpus IDs: {', '.join(list_available_corpora())} or 'all'")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SPRÅKBANKEN SOMALI CORPUS PROCESSOR")
    print("=" * 60)

    if corpus_id == "all":
        print(f"Processing: ALL {len(CORPUS_INFO)} corpora")
    else:
        print(f"Processing: {corpus_id}")
        info = CORPUS_INFO[corpus_id]
        print(f"Domain: {info.get('domain', 'general')}")

    print(f"Force reprocessing: {force}")
    if batch_size:
        print(f"Batch size: {batch_size}")
    print("=" * 60)
    print()

    try:
        # Initialize processor
        processor = SprakbankenSomaliProcessor(
            corpus_id=corpus_id,
            force=force,
            batch_size=batch_size,
        )

        # Run full pipeline
        print("Starting pipeline...")
        result = processor.run()

        print("\n" + "=" * 60)
        print("✅ PROCESSING COMPLETE")
        print("=" * 60)
        print(f"Output: {result}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download and process Språkbanken Somali corpora",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available corpora
  %(prog)s --list

  # Show info about specific corpus
  %(prog)s --info ogaden

  # Download and process all corpora
  %(prog)s --corpus all

  # Download specific corpus
  %(prog)s --corpus cilmi

  # Force reprocessing
  %(prog)s --corpus all --force

  # Process with custom batch size
  %(prog)s --corpus all --batch-size 10000
        """,
    )

    # Action arguments (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--list", action="store_true", help="List all available corpora with details"
    )
    action_group.add_argument(
        "--info", metavar="CORPUS_ID", help="Show detailed info about a specific corpus"
    )
    action_group.add_argument(
        "--corpus",
        metavar="CORPUS_ID",
        help="Download and process corpus (use 'all' for all corpora)",
    )

    # Processing options
    parser.add_argument(
        "--force", action="store_true", help="Force reprocessing even if files exist"
    )
    parser.add_argument(
        "--batch-size", type=int, default=5000, help="Batch size for processing (default: 5000)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Execute requested action
    if args.list:
        list_corpora()
    elif args.info:
        show_corpus_info(args.info)
    elif args.corpus:
        download_and_process(
            corpus_id=args.corpus,
            force=args.force,
            batch_size=args.batch_size,
            verbose=args.verbose,
        )
    else:
        # No action specified, show help
        parser.print_help()
        print("\nTip: Use --list to see available corpora")


if __name__ == "__main__":
    main()
