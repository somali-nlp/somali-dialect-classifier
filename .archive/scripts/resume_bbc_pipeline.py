#!/usr/bin/env python3
"""
Resume BBC pipeline from existing raw data.

This script completes BBC pipeline when articles are downloaded but extraction/processing failed.
It rebuilds the staging file from individual raw article JSONs and then runs process().
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor
from somali_dialect_classifier.config import get_config


def find_incomplete_bbc_runs(raw_dir: Path) -> List[Dict[str, Any]]:
    """
    Find BBC runs with raw data but no staging file.

    Args:
        raw_dir: BBC raw data directory

    Returns:
        List of incomplete run info dicts
    """
    incomplete_runs = []

    # Find all BBC raw data directories
    bbc_dirs = list(raw_dir.glob("source=BBC-Somali/date_accessed=*"))

    for bbc_dir in bbc_dirs:
        # Find article files
        article_files = sorted(bbc_dir.glob("bbc-somali_*_raw_article-[0-9]*.json"))

        if not article_files:
            continue

        # Extract run_id from first article file
        # Pattern: bbc-somali_{run_id}_raw_article-NNNN.json
        first_file = article_files[0].name
        parts = first_file.split('_')
        if len(parts) < 4:
            continue

        # run_id is the part between timestamps
        # Example: bbc-somali_20251020_080608_bbc_somali_7a12a886_raw_article-0001.json
        # run_id = 20251020_080608_bbc_somali_7a12a886
        run_id_parts = []
        for i, part in enumerate(parts):
            if part.startswith('bbc-somali'):
                continue
            if part.startswith('raw-'):
                break
            if 'article-' in part:
                break
            run_id_parts.append(part)

        run_id = '_'.join(run_id_parts)

        if not run_id:
            print(f"Warning: Could not extract run_id from {first_file}")
            continue

        # Check if staging file exists
        date_accessed = bbc_dir.name.split('=')[1]
        staging_dir = bbc_dir.parent.parent / "staging" / f"source=BBC-Somali" / f"date_accessed={date_accessed}"
        staging_file = staging_dir / f"bbc-somali_{run_id}_staging_articles.jsonl"

        if not staging_file.exists():
            incomplete_runs.append({
                'run_id': run_id,
                'date_accessed': date_accessed,
                'raw_dir': bbc_dir,
                'staging_dir': staging_dir,
                'staging_file': staging_file,
                'article_files': article_files,
                'article_count': len(article_files),
            })

    return incomplete_runs


def rebuild_staging_file(run_info: Dict[str, Any]) -> Path:
    """
    Rebuild staging file from individual raw article JSONs.

    Args:
        run_info: Run information dict

    Returns:
        Path to rebuilt staging file
    """
    staging_dir = run_info['staging_dir']
    staging_file = run_info['staging_file']
    article_files = run_info['article_files']

    print(f"\nRebuilding staging file from {len(article_files)} raw articles...")

    # Create staging directory
    staging_dir.mkdir(parents=True, exist_ok=True)

    # Load all articles
    articles = []
    for article_file in sorted(article_files):
        with open(article_file, 'r', encoding='utf-8') as f:
            article = json.load(f)
            articles.append(article)

    # Write to staging file (combined JSON)
    with open(staging_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"✓ Staging file created: {staging_file}")
    print(f"  Articles: {len(articles)}")

    return staging_file


def resume_bbc_pipeline(run_info: Dict[str, Any]):
    """
    Resume BBC pipeline from existing raw data.

    Args:
        run_info: Run information dict
    """
    print("\n" + "=" * 60)
    print(f"RESUMING BBC PIPELINE")
    print("=" * 60)
    print(f"Run ID: {run_info['run_id']}")
    print(f"Date Accessed: {run_info['date_accessed']}")
    print(f"Raw Articles: {run_info['article_count']}")

    # Step 1: Rebuild staging file
    staging_file = rebuild_staging_file(run_info)

    # Step 2: Initialize processor
    # Note: We can't directly inject run_id/paths, so we'll need to manually
    # set the paths after initialization
    print("\nInitializing BBC processor...")
    processor = BBCSomaliProcessor(max_articles=None, force=True)

    # Override paths to match the existing run
    processor.staging_file = staging_file
    processor.processed_dir = (
        Path("data/processed") / f"source=BBC-Somali" / f"date_accessed={run_info['date_accessed']}"
    )
    processor.processed_file = (
        processor.processed_dir / f"bbc-somali_{run_info['run_id']}_processed_cleaned.txt"
    )

    print(f"✓ Processor initialized")
    print(f"  Staging: {processor.staging_file}")
    print(f"  Processed: {processor.processed_file}")

    # Step 3: Run process()
    print("\n" + "=" * 60)
    print("RUNNING PROCESS PHASE")
    print("=" * 60)

    try:
        result = processor.process()
        print("\n" + "=" * 60)
        print("✓ BBC PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Result: {result}")
        return True
    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ BBC PIPELINE FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    config = get_config()
    raw_dir = config.data.raw_dir

    print("=" * 60)
    print("BBC PIPELINE RECOVERY TOOL")
    print("=" * 60)
    print(f"Scanning: {raw_dir}")

    # Find incomplete runs
    incomplete_runs = find_incomplete_bbc_runs(raw_dir)

    if not incomplete_runs:
        print("\n✓ No incomplete BBC runs found")
        return 0

    print(f"\nFound {len(incomplete_runs)} incomplete BBC run(s):")
    for i, run in enumerate(incomplete_runs, 1):
        print(f"\n{i}. Run ID: {run['run_id']}")
        print(f"   Date: {run['date_accessed']}")
        print(f"   Articles: {run['article_count']}")
        print(f"   Raw Dir: {run['raw_dir']}")

    # Process each incomplete run
    success_count = 0
    for run in incomplete_runs:
        if resume_bbc_pipeline(run):
            success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Incomplete runs: {len(incomplete_runs)}")
    print(f"Successfully resumed: {success_count}")
    print(f"Failed: {len(incomplete_runs) - success_count}")

    return 0 if success_count == len(incomplete_runs) else 1


if __name__ == "__main__":
    sys.exit(main())
