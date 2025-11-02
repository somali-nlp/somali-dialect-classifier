#!/usr/bin/env python3
"""
Export filter catalog to JSON for dashboard consumption.

This script generates a JSON file containing all filter metadata (labels,
descriptions, categories) from the Python filter catalog for use by the
dashboard JavaScript code.

Usage:
    python scripts/export_filter_catalog.py
    python scripts/export_filter_catalog.py --output _site/data/filter_catalog.json

Output Format:
    {
        "filters": {
            "min_length_filter": {
                "label": "Minimum length (50 chars)",
                "description": "Text must be at least 50 characters...",
                "category": "length"
            },
            ...
        },
        "categories": {
            "length": ["min_length_filter", "text_too_short_after_cleanup"],
            ...
        },
        "metadata": {
            "version": "1.13.0",
            "generated_at": "2025-11-02T12:00:00Z",
            "filter_count": 13,
            "schema_version": "1.0"
        }
    }
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Add src to path to import filter catalog
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def export_full_catalog(output_path: Path) -> Dict[str, Any]:
    """
    Export complete filter catalog with labels, descriptions, and categories.

    Args:
        output_path: Path where JSON file should be written

    Returns:
        Dictionary containing the exported catalog data

    Raises:
        ImportError: If filter catalog module cannot be imported
        IOError: If output file cannot be written
    """
    try:
        from somali_dialect_classifier.pipeline.filters.catalog import (
            FILTER_CATALOG,
            get_all_categories
        )
    except ImportError as e:
        error_msg = (
            f"Failed to import filter catalog: {e}\n"
            f"Ensure src/somali_dialect_classifier/pipeline/filters/catalog.py exists"
        )
        logger.error(error_msg)
        raise ImportError(error_msg) from e

    # Build filters dictionary with all metadata
    filters: Dict[str, Dict[str, str]] = {}

    for key, (label, description, category) in FILTER_CATALOG.items():
        filters[key] = {
            "label": label,
            "description": description,
            "category": category
        }

    # Get categories grouped by filter keys
    categories = get_all_categories()

    # Calculate semantic version based on filter count
    # Major.Minor.Patch format: MAJOR=1 (stable), MINOR=filter_count, PATCH=0
    version = f"1.{len(FILTER_CATALOG)}.0"

    # Build output structure
    catalog_export = {
        "filters": filters,
        "categories": categories,
        "metadata": {
            "version": version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filter_count": len(filters),
            "category_count": len(categories),
            "schema_version": "1.0"
        }
    }

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(catalog_export, f, indent=2, ensure_ascii=False)

    logger.info(f"Exported {len(filters)} filters to {output_path}")
    logger.info(f"Categories: {', '.join(categories.keys())}")
    logger.info(f"Version: {version}")

    return catalog_export


def validate_catalog_export(catalog_data: Dict[str, Any]) -> bool:
    """
    Validate exported catalog structure.

    Args:
        catalog_data: Exported catalog dictionary

    Returns:
        True if valid, False otherwise
    """
    required_keys = ["filters", "categories", "metadata"]

    if not all(key in catalog_data for key in required_keys):
        logger.error(f"Missing required keys. Expected: {required_keys}")
        return False

    if not isinstance(catalog_data["filters"], dict):
        logger.error("'filters' must be a dictionary")
        return False

    if len(catalog_data["filters"]) == 0:
        logger.warning("No filters found in catalog")
        return False

    # Validate filter structure
    for key, filter_data in catalog_data["filters"].items():
        required_filter_keys = ["label", "description", "category"]
        if not all(k in filter_data for k in required_filter_keys):
            logger.error(f"Filter '{key}' missing required keys: {required_filter_keys}")
            return False

    # Validate metadata
    metadata = catalog_data["metadata"]
    required_metadata = ["version", "generated_at", "filter_count", "schema_version"]
    if not all(key in metadata for key in required_metadata):
        logger.error(f"Metadata missing required keys: {required_metadata}")
        return False

    logger.info("✓ Catalog validation passed")
    return True


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Export filter catalog to JSON for dashboard consumption"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_site/data/filter_catalog.json"),
        help="Output path for filter catalog JSON (default: _site/data/filter_catalog.json)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate catalog structure after export"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Export catalog
    try:
        print(f"Exporting filter catalog to: {args.output}")
        catalog_data = export_full_catalog(args.output)

        # Validate if requested
        if args.validate:
            print("\nValidating exported catalog...")
            if not validate_catalog_export(catalog_data):
                print("✗ Validation failed")
                sys.exit(1)

        # Print summary
        metadata = catalog_data["metadata"]
        print(f"\n✓ Filter catalog exported successfully")
        print(f"  Version: {metadata['version']}")
        print(f"  Filters: {metadata['filter_count']}")
        print(f"  Categories: {metadata['category_count']}")
        print(f"  Output: {args.output}")
        print(f"\n  Use in dashboard: fetch('/data/filter_catalog.json')")

    except ImportError as e:
        print(f"\n✗ Import Error: {e}", file=sys.stderr)
        print("\nTroubleshooting:")
        print("  1. Verify filter catalog exists: src/somali_dialect_classifier/pipeline/filters/catalog.py")
        print("  2. Check Python path includes 'src' directory")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        logger.exception("Unexpected error during export")
        sys.exit(1)


if __name__ == "__main__":
    main()
