"""
Advanced data aggregation for dashboard visualizations.

This module provides aggregation functions for advanced visualizations:
- Sankey diagrams (pipeline flow)
- Ridge plots (text length distributions)
- Time-series trends
- Comparison data

All functions work with Phase 3 metrics schema and export to JSON format
compatible with static hosting (GitHub Pages).
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import math
import statistics

logger = logging.getLogger(__name__)


# ============================================================================
# SANKEY DIAGRAM AGGREGATION
# ============================================================================

def calculate_pipeline_flow(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate Sankey diagram data for pipeline flow visualization.

    Tracks data flow through pipeline stages:
    raw → cleaned → filtered → silver

    Args:
        metrics: List of consolidated metrics

    Returns:
        Dictionary with nodes and links for Sankey diagram

    Example:
        {
            "nodes": [
                {"id": "raw", "name": "Raw Data"},
                {"id": "cleaned", "name": "Cleaned"},
                {"id": "filtered", "name": "Quality Filtered"},
                {"id": "silver", "name": "Silver Layer"}
            ],
            "links": [
                {"source": "raw", "target": "cleaned", "value": 10000},
                {"source": "cleaned", "target": "filtered", "value": 9500},
                {"source": "filtered", "target": "silver", "value": 9000}
            ],
            "drop_reasons": {
                "deduplication": 500,
                "length_filter": 300,
                "language_filter": 150,
                "empty_content": 50
            }
        }
    """
    # Define nodes
    nodes = [
        {"id": "discovered", "name": "Discovered"},
        {"id": "fetched", "name": "Fetched"},
        {"id": "extracted", "name": "Content Extracted"},
        {"id": "deduplicated", "name": "Deduplicated"},
        {"id": "quality_passed", "name": "Quality Passed"},
        {"id": "written", "name": "Written to Silver"}
    ]

    # Aggregate flows across all metrics
    total_discovered = 0
    total_fetched = 0
    total_extracted = 0
    total_after_dedup = 0
    total_quality_passed = 0
    total_written = 0

    drop_reasons = defaultdict(int)

    for metric in metrics:
        # Extract counts based on pipeline type
        pipeline_type = metric.get("pipeline_type", "web_scraping")

        if pipeline_type == "web_scraping":
            discovered = metric.get("urls_discovered", 0)
            fetched = metric.get("urls_fetched", 0)
            extracted = fetched  # For web scraping, fetched = extracted
            deduplicated = metric.get("urls_deduplicated", 0)
            written = metric.get("records_written", 0)

        elif pipeline_type == "file_processing":
            # For file processing, map to equivalent stages
            files_discovered = metric.get("files_discovered", 0)
            files_processed = metric.get("files_processed", 0)
            discovered = metric.get("records_extracted", 0)
            fetched = discovered
            extracted = discovered
            deduplicated = 0  # Will calculate from duplicates if available
            written = metric.get("records_written", 0)

        elif pipeline_type == "stream_processing":
            # For streaming, map to equivalent stages
            discovered = metric.get("records_fetched", 0)
            fetched = discovered
            extracted = discovered
            deduplicated = 0
            written = metric.get("records_written", 0)
        else:
            # Default fallback
            discovered = metric.get("urls_discovered", 0)
            fetched = metric.get("urls_fetched", 0)
            extracted = fetched
            deduplicated = 0
            written = metric.get("records_written", 0)

        after_dedup = extracted - deduplicated
        quality_passed = written  # Assume written = quality passed

        total_discovered += discovered
        total_fetched += fetched
        total_extracted += extracted
        total_after_dedup += after_dedup
        total_quality_passed += quality_passed
        total_written += written

        # Collect filter reasons
        filter_breakdown = metric.get("filter_breakdown", {})
        for reason, count in filter_breakdown.items():
            drop_reasons[reason] += count

    # Build links (flows between stages)
    links = []

    if total_discovered > 0 and total_fetched > 0:
        links.append({
            "source": "discovered",
            "target": "fetched",
            "value": total_fetched
        })

    if total_fetched > 0 and total_extracted > 0:
        links.append({
            "source": "fetched",
            "target": "extracted",
            "value": total_extracted
        })

    if total_extracted > 0 and total_after_dedup > 0:
        links.append({
            "source": "extracted",
            "target": "deduplicated",
            "value": total_after_dedup
        })

    if total_after_dedup > 0 and total_quality_passed > 0:
        links.append({
            "source": "deduplicated",
            "target": "quality_passed",
            "value": total_quality_passed
        })

    if total_quality_passed > 0 and total_written > 0:
        links.append({
            "source": "quality_passed",
            "target": "written",
            "value": total_written
        })

    # Calculate drop-off at each stage
    drops = {
        "fetch_failures": total_discovered - total_fetched if total_discovered > total_fetched else 0,
        "extraction_failures": total_fetched - total_extracted if total_fetched > total_extracted else 0,
        "deduplication": total_extracted - total_after_dedup if total_extracted > total_after_dedup else 0,
        "quality_filters": total_after_dedup - total_quality_passed if total_after_dedup > total_quality_passed else 0,
        "write_failures": total_quality_passed - total_written if total_quality_passed > total_written else 0
    }

    return {
        "nodes": nodes,
        "links": links,
        "drop_reasons": dict(drop_reasons),
        "stage_drops": drops,
        "summary": {
            "total_discovered": total_discovered,
            "total_written": total_written,
            "overall_pass_rate": total_written / total_discovered if total_discovered > 0 else 0
        }
    }


# ============================================================================
# RIDGE PLOT AGGREGATION
# ============================================================================

def calculate_text_length_distribution(
    metrics: List[Dict[str, Any]],
    num_bins: int = 10
) -> Dict[str, Any]:
    """
    Calculate text length distribution data for Ridge plot visualization.

    Creates logarithmic bins for text lengths and calculates density
    for each data source.

    Args:
        metrics: List of consolidated metrics with text_length_stats
        num_bins: Number of logarithmic bins (default: 10)

    Returns:
        Dictionary with bins and densities per source

    Example:
        {
            "bins": [10, 100, 1000, 10000, 100000],
            "sources": {
                "BBC-Somali": {
                    "densities": [0.1, 0.3, 0.4, 0.15, 0.05],
                    "counts": [100, 300, 400, 150, 50],
                    "mean": 2500,
                    "median": 1800
                },
                "Wikipedia-Somali": {...}
            }
        }
    """
    # Define logarithmic bins (characters)
    min_log = 1  # 10^1 = 10 characters
    max_log = 6  # 10^6 = 1,000,000 characters

    bins = [10 ** (min_log + i * (max_log - min_log) / num_bins)
            for i in range(num_bins + 1)]
    bins = [int(b) for b in bins]

    # Organize by source
    sources_data = defaultdict(lambda: {
        "counts": [0] * num_bins,
        "text_lengths": [],
        "total_records": 0
    })

    for metric in metrics:
        source = metric.get("source", "Unknown")
        text_stats = metric.get("text_length_stats", {})

        # Try to reconstruct distribution from stats
        if text_stats:
            mean = text_stats.get("mean", 0)
            median = text_stats.get("median", 0)
            min_len = text_stats.get("min", 0)
            max_len = text_stats.get("max", 0)
            total_chars = text_stats.get("total_chars", 0)

            records_written = metric.get("records_written", 0)

            if records_written > 0:
                sources_data[source]["total_records"] += records_written

                # Estimate which bin this metric's data falls into
                # Use mean as representative value
                if mean > 0:
                    for i in range(num_bins):
                        if bins[i] <= mean < bins[i + 1]:
                            sources_data[source]["counts"][i] += records_written
                            break
                    else:
                        # If mean is outside bins, add to last bin
                        if mean >= bins[-1]:
                            sources_data[source]["counts"][-1] += records_written
                        else:
                            sources_data[source]["counts"][0] += records_written

                # Store representative lengths
                sources_data[source]["text_lengths"].extend([mean, median])

    # Calculate densities (normalize counts)
    result_sources = {}

    for source, data in sources_data.items():
        total = data["total_records"]
        if total > 0:
            densities = [count / total for count in data["counts"]]

            result_sources[source] = {
                "densities": densities,
                "counts": data["counts"],
                "mean": statistics.mean(data["text_lengths"]) if data["text_lengths"] else 0,
                "median": statistics.median(data["text_lengths"]) if data["text_lengths"] else 0,
                "total_records": total
            }

    return {
        "bins": bins,
        "bin_labels": [f"{bins[i]}-{bins[i+1]}" for i in range(num_bins)],
        "sources": result_sources,
        "metadata": {
            "num_bins": num_bins,
            "bin_scale": "logarithmic",
            "unit": "characters"
        }
    }


# ============================================================================
# TIME-SERIES AGGREGATION
# ============================================================================

def calculate_time_series(
    metrics: List[Dict[str, Any]],
    interval: str = "daily"
) -> Dict[str, Any]:
    """
    Calculate time-series data for trend visualization.

    Groups metrics by time interval and calculates aggregates.

    Args:
        metrics: List of consolidated metrics with timestamps
        interval: Time interval ('hourly', 'daily', 'weekly')

    Returns:
        Dictionary with time-series data

    Example:
        {
            "interval": "daily",
            "series": [
                {
                    "date": "2025-10-21",
                    "records_written": 10000,
                    "avg_success_rate": 0.95,
                    "sources": ["BBC-Somali", "Wikipedia-Somali"]
                }
            ]
        }
    """
    # Group by time interval
    time_groups = defaultdict(lambda: {
        "records_written": 0,
        "success_rates": [],
        "quality_pass_rates": [],
        "sources": set(),
        "runs": 0
    })

    for metric in metrics:
        timestamp_str = metric.get("timestamp", "")
        if not timestamp_str:
            continue

        try:
            # Parse ISO timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            # Determine grouping key based on interval
            if interval == "hourly":
                key = timestamp.strftime("%Y-%m-%d %H:00")
            elif interval == "weekly":
                # ISO week
                key = timestamp.strftime("%Y-W%V")
            else:  # daily
                key = timestamp.strftime("%Y-%m-%d")

            # Aggregate data
            group = time_groups[key]
            group["records_written"] += metric.get("records_written", 0)

            success_rate = metric.get("http_request_success_rate",
                                     metric.get("file_extraction_success_rate",
                                               metric.get("stream_connection_success_rate", 0)))
            if success_rate > 0:
                group["success_rates"].append(success_rate)

            quality_rate = metric.get("quality_pass_rate", 0)
            if quality_rate > 0:
                group["quality_pass_rates"].append(quality_rate)

            source = metric.get("source", "Unknown")
            group["sources"].add(source)
            group["runs"] += 1

        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp: {timestamp_str}: {e}")
            continue

    # Build series
    series = []
    for date_key in sorted(time_groups.keys()):
        group = time_groups[date_key]

        series.append({
            "date": date_key,
            "records_written": group["records_written"],
            "avg_success_rate": statistics.mean(group["success_rates"]) if group["success_rates"] else 0,
            "avg_quality_pass_rate": statistics.mean(group["quality_pass_rates"]) if group["quality_pass_rates"] else 0,
            "sources": sorted(list(group["sources"])),
            "num_runs": group["runs"]
        })

    return {
        "interval": interval,
        "series": series,
        "metadata": {
            "total_periods": len(series),
            "date_range": {
                "start": series[0]["date"] if series else None,
                "end": series[-1]["date"] if series else None
            }
        }
    }


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_visualization_data(
    metrics: List[Dict[str, Any]],
    output_dir: Path
) -> None:
    """
    Export all visualization aggregations to JSON files.

    Creates separate JSON files for each visualization type:
    - sankey_flow.json
    - ridge_distribution.json
    - time_series_daily.json
    - time_series_weekly.json

    Args:
        metrics: List of consolidated metrics
        output_dir: Directory to save JSON files (e.g., _site/data)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate Sankey data
    logger.info("Generating Sankey flow data...")
    sankey_data = calculate_pipeline_flow(metrics)
    sankey_file = output_dir / "sankey_flow.json"
    with open(sankey_file, 'w', encoding='utf-8') as f:
        json.dump(sankey_data, f, indent=2)
    logger.info(f"✓ Wrote Sankey data to: {sankey_file}")

    # Generate Ridge plot data
    logger.info("Generating text length distribution data...")
    ridge_data = calculate_text_length_distribution(metrics, num_bins=10)
    ridge_file = output_dir / "ridge_distribution.json"
    with open(ridge_file, 'w', encoding='utf-8') as f:
        json.dump(ridge_data, f, indent=2)
    logger.info(f"✓ Wrote Ridge plot data to: {ridge_file}")

    # Generate time-series data (daily)
    logger.info("Generating daily time-series data...")
    daily_series = calculate_time_series(metrics, interval="daily")
    daily_file = output_dir / "time_series_daily.json"
    with open(daily_file, 'w', encoding='utf-8') as f:
        json.dump(daily_series, f, indent=2)
    logger.info(f"✓ Wrote daily time-series to: {daily_file}")

    # Generate time-series data (weekly)
    logger.info("Generating weekly time-series data...")
    weekly_series = calculate_time_series(metrics, interval="weekly")
    weekly_file = output_dir / "time_series_weekly.json"
    with open(weekly_file, 'w', encoding='utf-8') as f:
        json.dump(weekly_series, f, indent=2)
    logger.info(f"✓ Wrote weekly time-series to: {weekly_file}")

    logger.info("✓ All visualization data exported successfully")


def calculate_summary_stats(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary statistics for export and reporting.

    Args:
        metrics: List of consolidated metrics

    Returns:
        Dictionary with summary statistics
    """
    if not metrics:
        return {
            "total_records": 0,
            "total_sources": 0,
            "total_runs": 0,
            "avg_success_rate": 0,
            "avg_quality_pass_rate": 0
        }

    total_records = sum(m.get("records_written", 0) for m in metrics)
    sources = set(m.get("source", "Unknown") for m in metrics)

    success_rates = []
    quality_rates = []

    for m in metrics:
        sr = m.get("http_request_success_rate",
                  m.get("file_extraction_success_rate",
                       m.get("stream_connection_success_rate", 0)))
        if sr > 0:
            success_rates.append(sr)

        qr = m.get("quality_pass_rate", 0)
        if qr > 0:
            quality_rates.append(qr)

    return {
        "total_records": total_records,
        "total_sources": len(sources),
        "total_runs": len(metrics),
        "avg_success_rate": statistics.mean(success_rates) if success_rates else 0,
        "avg_quality_pass_rate": statistics.mean(quality_rates) if quality_rates else 0,
        "sources": sorted(list(sources))
    }
