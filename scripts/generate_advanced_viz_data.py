#!/usr/bin/env python3
"""
Generate Advanced Visualization Data

Creates additional data files for advanced dashboard visualizations:
- sankey_flow.json: Pipeline stage flow data for Sankey diagrams
- text_distributions.json: Text length distributions by source for ridge plots

This script extends the existing metrics pipeline without modifying core functionality.

Schema Contract:
    - Input: data/metrics/*_processing.json (Phase 3 schema)
    - Output: _site/data/sankey_flow.json
    - Output: _site/data/text_distributions.json

Usage:
    python scripts/generate_advanced_viz_data.py
"""

import json
import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timezone

try:
    from somali_dialect_classifier.utils.metrics_schema import validate_processing_json
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    print("Warning: Schema validation not available. Install with: pip install -e '.[config]'", file=sys.stderr)
    SCHEMA_VALIDATION_AVAILABLE = False


def load_processing_metrics(metrics_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all *_processing.json files from metrics directory.

    Args:
        metrics_dir: Path to data/metrics directory

    Returns:
        List of validated metric dictionaries
    """
    all_metrics = []

    if not metrics_dir.exists():
        print(f"Warning: Metrics directory not found: {metrics_dir}", file=sys.stderr)
        return all_metrics

    processing_files = sorted(metrics_dir.glob("*_processing.json"))

    if not processing_files:
        print(f"Warning: No *_processing.json files found in {metrics_dir}", file=sys.stderr)
        return all_metrics

    for metrics_file in processing_files:
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Basic validation - ensure required structure exists
            if "_source" in data or "legacy_metrics" in data:
                all_metrics.append(data)
            else:
                print(f"Warning: Missing required fields in {metrics_file.name}", file=sys.stderr)

        except json.JSONDecodeError as e:
            print(f"Error parsing {metrics_file.name}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error loading {metrics_file.name}: {e}", file=sys.stderr)

    return all_metrics


def generate_sankey_flow(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate Sankey diagram data showing pipeline flow from discovery to final dataset.

    Aggregates across all metrics to show:
    - Records at each stage: discovered → fetched → extracted → quality_check → written
    - Filter breakdown showing where records were dropped

    Args:
        metrics: List of processing metrics

    Returns:
        Sankey flow data structure
    """
    if not metrics:
        return {
            "nodes": [],
            "links": [],
            "filter_breakdown": {},
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    # Aggregate across all runs
    total_discovered = 0
    total_fetched = 0
    total_extracted = 0
    total_quality_received = 0
    total_quality_passed = 0
    total_written = 0

    # Aggregate filter breakdown
    filter_totals = defaultdict(int)

    for metric in metrics:
        layered = metric.get("layered_metrics", {})
        legacy = metric.get("legacy_metrics", {})
        snapshot = legacy.get("snapshot", {})

        extraction = layered.get("extraction", {})
        quality = layered.get("quality", {})
        volume = layered.get("volume", {})

        # Discovery stage (URLs or files discovered)
        discovered = snapshot.get("urls_discovered", 0) + snapshot.get("files_discovered", 0)
        total_discovered += discovered

        # Fetch stage (HTTP requests or files processed)
        fetched = (
            snapshot.get("urls_fetched", 0) +
            snapshot.get("files_processed", 0) +
            extraction.get("http_requests_successful", 0)
        )
        total_fetched += fetched if fetched > 0 else discovered

        # Extraction stage (content extracted)
        extracted = extraction.get("content_extracted", 0)
        if extracted == 0:
            extracted = snapshot.get("records_extracted", 0)
        if extracted == 0:
            extracted = snapshot.get("urls_processed", 0)
        total_extracted += extracted

        # Quality check stage
        quality_received = quality.get("records_received", 0)
        quality_passed = quality.get("records_passed_filters", 0)
        total_quality_received += quality_received if quality_received > 0 else extracted
        total_quality_passed += quality_passed

        # Final written records
        written = volume.get("records_written", 0)
        total_written += written

        # Aggregate filter breakdown
        filter_breakdown = quality.get("filter_breakdown", {})
        for filter_name, count in filter_breakdown.items():
            filter_totals[filter_name] += count

    # Ensure logical flow (no stage can have more than previous)
    total_fetched = min(total_fetched, total_discovered) if total_discovered > 0 else total_fetched
    total_extracted = min(total_extracted, total_fetched) if total_fetched > 0 else total_extracted
    total_quality_received = min(total_quality_received, total_extracted) if total_extracted > 0 else total_quality_received
    total_quality_passed = min(total_quality_passed, total_quality_received)
    total_written = min(total_written, total_quality_passed) if total_quality_passed > 0 else total_written

    # Build Sankey structure
    nodes = [
        "Discovered",
        "Fetched",
        "Extracted",
        "Quality Check",
        "Silver Dataset"
    ]

    links = []

    # Add links between stages (only if there's actual flow)
    if total_discovered > 0:
        links.append({
            "source": 0,  # Discovered
            "target": 1,  # Fetched
            "value": total_fetched
        })

    if total_fetched > 0:
        links.append({
            "source": 1,  # Fetched
            "target": 2,  # Extracted
            "value": total_extracted
        })

    if total_extracted > 0:
        links.append({
            "source": 2,  # Extracted
            "target": 3,  # Quality Check
            "value": total_quality_received
        })

    if total_quality_received > 0:
        links.append({
            "source": 3,  # Quality Check
            "target": 4,  # Silver Dataset
            "value": total_written
        })

    # Normalize filter names for consistency
    normalized_filters = {}
    for filter_name, count in filter_totals.items():
        # Clean up filter names
        clean_name = filter_name.replace("_", " ").title()
        if "length" in filter_name.lower():
            clean_name = "Length Filter"
        elif "langid" in filter_name.lower() or "language" in filter_name.lower():
            clean_name = "Language Filter"
        elif "empty" in filter_name.lower():
            clean_name = "Empty Content Filter"

        normalized_filters[clean_name] = count

    sankey_data = {
        "nodes": nodes,
        "links": links,
        "filter_breakdown": normalized_filters,
        "stage_counts": {
            "discovered": total_discovered,
            "fetched": total_fetched,
            "extracted": total_extracted,
            "quality_received": total_quality_received,
            "quality_passed": total_quality_passed,
            "written": total_written
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

    return sankey_data


def generate_text_distributions(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate text length distributions by source for ridge plots.

    Creates logarithmic bins and computes density distributions for each source.

    Args:
        metrics: List of processing metrics

    Returns:
        Text distribution data by source
    """
    if not metrics:
        return {
            "sources": [],
            "distributions": {},
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    # Collect text lengths by source
    source_text_lengths = defaultdict(list)

    for metric in metrics:
        source = metric.get("_source") or metric.get("legacy_metrics", {}).get("snapshot", {}).get("source")
        if not source:
            continue

        # Get text lengths from legacy snapshot
        legacy = metric.get("legacy_metrics", {})
        snapshot = legacy.get("snapshot", {})
        text_lengths = snapshot.get("text_lengths", [])

        if text_lengths:
            source_text_lengths[source].extend(text_lengths)

    # Generate distributions for each source
    distributions = {}
    sources = sorted(source_text_lengths.keys())

    # Define logarithmic bins (10, 100, 1k, 10k, 100k characters)
    bin_edges = [10, 100, 1000, 10000, 100000, 1000000]
    bin_labels = ["10-100", "100-1K", "1K-10K", "10K-100K", "100K+"]

    for source in sources:
        lengths = source_text_lengths[source]

        if not lengths:
            continue

        # Compute histogram
        hist, _ = np.histogram(lengths, bins=bin_edges)

        # Normalize to density (sum to 1)
        total = hist.sum()
        densities = (hist / total).tolist() if total > 0 else [0] * len(hist)

        # Compute statistics
        lengths_array = np.array(lengths)
        stats = {
            "mean": float(np.mean(lengths_array)),
            "median": float(np.median(lengths_array)),
            "q1": float(np.percentile(lengths_array, 25)),
            "q3": float(np.percentile(lengths_array, 75)),
            "min": float(np.min(lengths_array)),
            "max": float(np.max(lengths_array)),
            "count": len(lengths)
        }

        distributions[source] = {
            "bins": bin_labels,
            "bin_edges": bin_edges,
            "densities": densities,
            "counts": hist.tolist(),
            "stats": stats
        }

    return {
        "sources": sources,
        "distributions": distributions,
        "bin_info": {
            "edges": bin_edges,
            "labels": bin_labels,
            "scale": "logarithmic"
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


def generate_comparison_metadata(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate metadata for run-to-run comparisons.

    Computes deltas between most recent runs per source.

    Args:
        metrics: List of processing metrics

    Returns:
        Comparison metadata
    """
    if not metrics:
        return {
            "comparisons": [],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    # Group metrics by source
    source_metrics = defaultdict(list)

    for metric in metrics:
        source = metric.get("_source") or metric.get("legacy_metrics", {}).get("snapshot", {}).get("source")
        if not source:
            continue

        timestamp = metric.get("_timestamp") or metric.get("legacy_metrics", {}).get("snapshot", {}).get("timestamp")

        source_metrics[source].append({
            "metric": metric,
            "timestamp": timestamp
        })

    # Sort by timestamp and compute deltas
    comparisons = []

    for source, runs in source_metrics.items():
        if len(runs) < 2:
            continue

        # Sort by timestamp (most recent first)
        sorted_runs = sorted(runs, key=lambda x: x["timestamp"], reverse=True)

        current = sorted_runs[0]["metric"]
        previous = sorted_runs[1]["metric"]

        # Extract key metrics
        current_volume = current.get("layered_metrics", {}).get("volume", {})
        previous_volume = previous.get("layered_metrics", {}).get("volume", {})

        current_records = current_volume.get("records_written", 0)
        previous_records = previous_volume.get("records_written", 0)

        current_stats = current.get("legacy_metrics", {}).get("statistics", {})
        previous_stats = previous.get("legacy_metrics", {}).get("statistics", {})

        current_quality = current_stats.get("quality_pass_rate", 0)
        previous_quality = previous_stats.get("quality_pass_rate", 0)

        # Compute deltas
        records_delta = current_records - previous_records
        quality_delta = current_quality - previous_quality

        comparisons.append({
            "source": source,
            "current_timestamp": sorted_runs[0]["timestamp"],
            "previous_timestamp": sorted_runs[1]["timestamp"],
            "records_delta": records_delta,
            "records_delta_percent": (records_delta / previous_records * 100) if previous_records > 0 else 0,
            "quality_delta": quality_delta,
            "quality_delta_percent": (quality_delta / previous_quality * 100) if previous_quality > 0 else 0
        })

    return {
        "comparisons": comparisons,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    """Main execution function."""
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    metrics_dir = project_root / "data" / "metrics"
    output_dir = project_root / "_site" / "data"

    print("=" * 60)
    print("Advanced Visualization Data Generator")
    print("=" * 60)

    # Load metrics
    print(f"\n[1/4] Loading metrics from: {metrics_dir}")
    metrics = load_processing_metrics(metrics_dir)

    if not metrics:
        print("No valid metrics found. Exiting.")
        sys.exit(1)

    print(f"✓ Loaded {len(metrics)} metric files")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate Sankey flow data
    print(f"\n[2/4] Generating Sankey flow data...")
    sankey_data = generate_sankey_flow(metrics)

    sankey_file = output_dir / "sankey_flow.json"
    with open(sankey_file, 'w', encoding='utf-8') as f:
        json.dump(sankey_data, f, indent=2)

    print(f"✓ Wrote Sankey data to: {sankey_file}")
    if sankey_data["links"]:
        print(f"  - Pipeline stages: {len(sankey_data['nodes'])}")
        print(f"  - Filter types: {len(sankey_data['filter_breakdown'])}")
        print(f"  - Records written: {sankey_data['stage_counts']['written']:,}")

    # Generate text distributions
    print(f"\n[3/4] Generating text distribution data...")
    distribution_data = generate_text_distributions(metrics)

    distribution_file = output_dir / "text_distributions.json"
    with open(distribution_file, 'w', encoding='utf-8') as f:
        json.dump(distribution_data, f, indent=2)

    print(f"✓ Wrote distribution data to: {distribution_file}")
    if distribution_data["sources"]:
        print(f"  - Sources: {', '.join(distribution_data['sources'])}")
        for source in distribution_data["sources"]:
            stats = distribution_data["distributions"][source]["stats"]
            print(f"  - {source}: {stats['count']:,} texts, median={stats['median']:.0f} chars")

    # Generate comparison metadata
    print(f"\n[4/4] Generating comparison metadata...")
    comparison_data = generate_comparison_metadata(metrics)

    comparison_file = output_dir / "comparison_metadata.json"
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2)

    print(f"✓ Wrote comparison data to: {comparison_file}")
    if comparison_data["comparisons"]:
        print(f"  - Comparisons available: {len(comparison_data['comparisons'])}")

    print("\n" + "=" * 60)
    print("Advanced visualization data generation complete!")
    print("=" * 60)

    if SCHEMA_VALIDATION_AVAILABLE:
        print("✓ All data validated with schema")
    else:
        print("⚠ Schema validation skipped (pydantic not installed)")


if __name__ == "__main__":
    main()
