#!/usr/bin/env python3
"""
Enhanced consolidated metrics generator with advanced visualizations.

This script extends generate_consolidated_metrics.py to include:
- Sankey diagram data (pipeline flow)
- Ridge plot data (text length distributions)
- Time-series data (daily/weekly trends)
- Comparison data (deltas between runs)
- Performance optimizations (caching, compression)

Usage:
    python scripts/generate_enhanced_metrics.py
    python scripts/generate_enhanced_metrics.py --skip-visualizations
    python scripts/generate_enhanced_metrics.py --force-refresh
"""

import json
import sys
import gzip
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from somali_dialect_classifier.utils.metrics_schema import (
        validate_processing_json,
        ConsolidatedMetric,
        ConsolidatedMetricsOutput,
        DashboardSummary,
        AdvancedVisualizationData,
        EnhancedDashboardMetadata
    )
    from somali_dialect_classifier.utils.visualization_aggregator import (
        export_visualization_data,
        calculate_summary_stats
    )
    from somali_dialect_classifier.utils.metrics_comparison import (
        compare_multiple_runs,
        export_comparison_data,
        export_trend_analysis
    )
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Advanced features not available: {e}", file=sys.stderr)
    SCHEMA_VALIDATION_AVAILABLE = False


def load_metrics_from_processing_files(metrics_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all metrics from *_processing.json files.

    Args:
        metrics_dir: Path to data/metrics directory

    Returns:
        List of consolidated metrics
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

            metric = extract_consolidated_metric(data, metrics_file.name)

            if metric:
                all_metrics.append(metric)
            else:
                print(f"Skipped {metrics_file.name} (failed extraction)", file=sys.stderr)

        except json.JSONDecodeError as e:
            print(f"Error parsing {metrics_file.name}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {metrics_file.name}: {e}", file=sys.stderr)

    return all_metrics


def extract_consolidated_metric(data: Dict[str, Any], source_file: str) -> Optional[Dict[str, Any]]:
    """
    Extract consolidated metric from Phase 3 *_processing.json.

    This is imported from generate_consolidated_metrics.py logic.
    """
    try:
        if SCHEMA_VALIDATION_AVAILABLE:
            validated = validate_processing_json(data)

            source = validated.source
            run_id = validated.run_id

            layered = validated.layered_metrics
            legacy = validated.legacy_metrics
            snapshot = legacy.snapshot
            stats = legacy.statistics

            connectivity = layered.connectivity
            extraction = layered.extraction
            quality = layered.quality
            volume = layered.volume

            metric = {
                "run_id": run_id,
                "source": source,
                "timestamp": validated.timestamp,
                "duration_seconds": snapshot.duration_seconds,
                "pipeline_type": validated.pipeline_type,

                # Discovery metrics
                "urls_discovered": snapshot.urls_discovered,
                "urls_fetched": snapshot.urls_fetched,
                "urls_processed": snapshot.urls_processed,

                # Volume metrics
                "records_written": volume.records_written,
                "bytes_downloaded": volume.bytes_downloaded,
                "total_chars": volume.total_chars,

                # Quality metrics
                "http_request_success_rate": stats.http_request_success_rate or 0,
                "content_extraction_success_rate": stats.content_extraction_success_rate or 0,
                "quality_pass_rate": stats.quality_pass_rate or 0,
                "deduplication_rate": stats.deduplication_rate or 0,

                # Throughput metrics
                "urls_per_second": stats.throughput.urls_per_second or 0,
                "bytes_per_second": stats.throughput.bytes_per_second or 0,
                "records_per_minute": stats.throughput.records_per_minute or 0,
            }

            # Optional stats
            if stats.text_length_stats:
                metric["text_length_stats"] = stats.text_length_stats.model_dump()

            if stats.fetch_duration_stats:
                metric["fetch_duration_stats"] = stats.fetch_duration_stats.model_dump()

            if quality.filter_breakdown:
                metric["filter_breakdown"] = quality.filter_breakdown

            # Validate consolidated metric
            try:
                ConsolidatedMetric.model_validate(metric)
            except Exception as e:
                print(f"Warning: Consolidated metric validation failed for {source_file}: {e}", file=sys.stderr)

            return metric

        else:
            # Fallback without validation
            layered = data.get("layered_metrics", {})
            legacy = data.get("legacy_metrics", {})
            snapshot = legacy.get("snapshot", {})
            stats = legacy.get("statistics", {})

            source = data.get("_source") or snapshot.get("source")
            if not source:
                print(f"Warning: No source found in {source_file}, skipping", file=sys.stderr)
                return None

            run_id = data.get("_run_id") or snapshot.get("run_id")
            if not run_id:
                print(f"Warning: No run_id found in {source_file}, skipping", file=sys.stderr)
                return None

            volume = layered.get("volume", {})
            quality = layered.get("quality", {})

            metric = {
                "run_id": run_id,
                "source": source,
                "timestamp": data.get("_timestamp") or snapshot.get("timestamp", ""),
                "duration_seconds": snapshot.get("duration_seconds", 0),
                "pipeline_type": data.get("_pipeline_type", "web_scraping"),

                "urls_discovered": snapshot.get("urls_discovered", 0),
                "urls_fetched": snapshot.get("urls_fetched", 0),
                "urls_processed": snapshot.get("urls_processed", 0),

                "records_written": volume.get("records_written", 0),
                "bytes_downloaded": volume.get("bytes_downloaded", 0),
                "total_chars": volume.get("total_chars", 0),

                "http_request_success_rate": stats.get("http_request_success_rate", 0),
                "content_extraction_success_rate": stats.get("content_extraction_success_rate", 0),
                "quality_pass_rate": stats.get("quality_pass_rate", 0),
                "deduplication_rate": stats.get("deduplication_rate", 0),

                "urls_per_second": stats.get("throughput", {}).get("urls_per_second", 0),
                "bytes_per_second": stats.get("throughput", {}).get("bytes_per_second", 0),
                "records_per_minute": stats.get("throughput", {}).get("records_per_minute", 0),
            }

            if "text_length_stats" in stats and stats["text_length_stats"]:
                metric["text_length_stats"] = stats["text_length_stats"]

            if "fetch_duration_stats" in stats and stats["fetch_duration_stats"]:
                metric["fetch_duration_stats"] = stats["fetch_duration_stats"]

            filter_breakdown = quality.get("filter_breakdown", {})
            if filter_breakdown:
                metric["filter_breakdown"] = filter_breakdown

            return metric

    except KeyError as e:
        print(f"Error: Missing required field in {source_file}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error processing {source_file}: {e}", file=sys.stderr)
        return None


def generate_cache_key(metrics: List[Dict[str, Any]]) -> str:
    """
    Generate cache key based on metrics content.

    Args:
        metrics: List of consolidated metrics

    Returns:
        MD5 hash of metrics data
    """
    # Create deterministic string representation
    content = json.dumps(metrics, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()


def check_cache_validity(
    cache_file: Path,
    current_key: str,
    ttl_seconds: int = 3600
) -> bool:
    """
    Check if cached data is still valid.

    Args:
        cache_file: Path to cache metadata file
        current_key: Current cache key
        ttl_seconds: Time-to-live in seconds

    Returns:
        True if cache is valid, False otherwise
    """
    if not cache_file.exists():
        return False

    try:
        with open(cache_file, 'r') as f:
            cache_meta = json.load(f)

        cached_key = cache_meta.get("cache_key", "")
        cached_time = datetime.fromisoformat(cache_meta.get("cached_at", ""))

        # Check if key matches
        if cached_key != current_key:
            return False

        # Check if TTL expired
        age_seconds = (datetime.now() - cached_time).total_seconds()
        if age_seconds > ttl_seconds:
            return False

        return True

    except (json.JSONDecodeError, ValueError, KeyError):
        return False


def compress_json_file(input_file: Path, output_file: Path) -> None:
    """
    Compress JSON file with gzip.

    Args:
        input_file: Path to uncompressed JSON file
        output_file: Path to compressed .json.gz file
    """
    with open(input_file, 'rb') as f_in:
        with gzip.open(output_file, 'wb') as f_out:
            f_out.writelines(f_in)

    # Log compression ratio
    original_size = input_file.stat().st_size
    compressed_size = output_file.stat().st_size
    ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

    print(f"  Compressed {input_file.name}: {original_size:,} → {compressed_size:,} bytes ({ratio:.1f}% reduction)")


def export_filter_catalog(output_dir: Path) -> None:
    """
    Export filter catalog to JSON for dashboard consumption.

    Args:
        output_dir: Directory where filter_catalog.json should be written
    """
    try:
        from somali_dialect_classifier.pipeline.filters.catalog import (
            FILTER_CATALOG,
            get_all_categories
        )

        # Build filters dictionary
        filters = {}
        for key, (label, description, category) in FILTER_CATALOG.items():
            filters[key] = {
                "label": label,
                "description": description,
                "category": category
            }

        # Get categories
        categories = get_all_categories()

        # Calculate semantic version
        version = f"1.{len(FILTER_CATALOG)}.0"

        # Build output structure
        catalog_export = {
            "filters": filters,
            "categories": categories,
            "metadata": {
                "version": version,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "filter_count": len(filters),
                "category_count": len(categories),
                "schema_version": "1.0"
            }
        }

        # Write to file
        output_file = output_dir / "filter_catalog.json"
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(catalog_export, f, indent=2, ensure_ascii=False)

        print(f"✓ Exported filter catalog: {len(filters)} filters, {len(categories)} categories")

    except ImportError as e:
        print(f"⚠ Warning: Could not export filter catalog: {e}", file=sys.stderr)
        print("  Filter catalog will not be available to dashboard", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Warning: Failed to export filter catalog: {e}", file=sys.stderr)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Generate enhanced consolidated metrics with visualizations")
    parser.add_argument("--skip-visualizations", action="store_true", help="Skip visualization data generation")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh cache (ignore TTL)")
    parser.add_argument("--compress", action="store_true", help="Generate compressed .json.gz files")
    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    metrics_dir = project_root / "data" / "metrics"
    output_dir = project_root / "_site" / "data"

    # Load metrics
    print(f"Loading metrics from: {metrics_dir}")
    metrics = load_metrics_from_processing_files(metrics_dir)

    if not metrics:
        print("No valid metrics found. Creating empty consolidated file.")
    else:
        print(f"Successfully loaded {len(metrics)} metric records")

    # Generate cache key
    cache_key = generate_cache_key(metrics)
    cache_meta_file = output_dir / ".cache_metadata.json"

    # Check cache validity
    if not args.force_refresh and check_cache_validity(cache_meta_file, cache_key):
        print("✓ Cache is valid. Skipping generation. Use --force-refresh to regenerate.")
        return

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export filter catalog for dashboard
    print("\n=== Exporting Filter Catalog ===")
    export_filter_catalog(output_dir)

    # Generate basic summary (backward compatible)
    print("\n=== Generating Summary Statistics ===")
    if SCHEMA_VALIDATION_AVAILABLE:
        summary_stats = calculate_summary_stats(metrics)
    else:
        # Fallback summary
        summary_stats = {
            "total_records": sum(m.get("records_written", 0) for m in metrics),
            "total_sources": len(set(m.get("source", "") for m in metrics)),
            "total_runs": len(metrics)
        }

    # Load source mix targets (Stage 1 planning)
    source_mix_share = {}
    source_mix_volumes = {}
    source_mix_config = {}
    targets_path = project_root / "dashboard" / "data" / "source_mix_targets.json"
    if targets_path.exists():
        try:
            with open(targets_path, 'r', encoding='utf-8') as f:
                source_mix_config = json.load(f)
                if isinstance(source_mix_config, dict):
                    candidate_volumes = source_mix_config.get("volumes")
                    if isinstance(candidate_volumes, dict):
                        source_mix_volumes = candidate_volumes
                        total_volume = sum(
                            value for value in candidate_volumes.values()
                            if isinstance(value, (int, float)) and value > 0
                        )
                        if total_volume > 0:
                            source_mix_share = {
                                key: float(value) / total_volume
                                for key, value in candidate_volumes.items()
                                if isinstance(value, (int, float)) and value >= 0
                            }
        except Exception as exc:
            print(f"⚠ Warning: Failed to load source mix targets from {targets_path}: {exc}", file=sys.stderr)

    # Build dashboard summary
    sources = sorted(set(m.get("source", "") for m in metrics if m.get("source")))
    source_breakdown = {}

    for source in sources:
        source_metrics = [m for m in metrics if m.get("source") == source]
        source_breakdown[source] = {
            "records": sum(m.get("records_written", 0) for m in source_metrics),
            "runs": len(source_metrics),
            "avg_success_rate": sum(m.get("http_request_success_rate", 0) for m in source_metrics) / len(source_metrics) if source_metrics else 0,
            "avg_quality_pass_rate": sum(m.get("quality_pass_rate", 0) for m in source_metrics) / len(source_metrics) if source_metrics else 0,
            "total_chars": sum(m.get("total_chars", 0) for m in source_metrics),
            "last_run": max((m.get("timestamp", "") for m in source_metrics), default="")
        }

    summary = {
        "total_records": summary_stats.get("total_records", 0),
        "total_urls_processed": sum(m.get("urls_processed", 0) for m in metrics),
        "avg_success_rate": summary_stats.get("avg_success_rate", 0),
        "total_data_downloaded_bytes": sum(m.get("bytes_downloaded", 0) for m in metrics),
        "sources": sources,
        "total_runs": len(metrics),
        "last_update": datetime.utcnow().isoformat() + "Z",
        "source_breakdown": source_breakdown
    }

    # Write summary
    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Wrote summary to: {summary_file}")

    # Write consolidated metrics
    all_metrics_file = output_dir / "all_metrics.json"
    consolidated_output = {
        "count": len(metrics),
        "records": summary["total_records"],
        "sources": sources,
        "metrics": metrics
    }

    with open(all_metrics_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated_output, f, indent=2)
    print(f"✓ Wrote consolidated metrics to: {all_metrics_file}")

    # Generate advanced visualizations
    viz_data = AdvancedVisualizationData()

    if not args.skip_visualizations and SCHEMA_VALIDATION_AVAILABLE:
        print("\n=== Generating Advanced Visualizations ===")

        try:
            # Export visualization data
            export_visualization_data(metrics, output_dir)

            viz_data.sankey_available = True
            viz_data.sankey_last_updated = datetime.utcnow().isoformat() + "Z"
            viz_data.ridge_available = True
            viz_data.ridge_last_updated = datetime.utcnow().isoformat() + "Z"
            viz_data.timeseries_available = True
            viz_data.timeseries_last_updated = datetime.utcnow().isoformat() + "Z"

            print("✓ All visualization data generated")

        except Exception as e:
            print(f"✗ Failed to generate visualizations: {e}", file=sys.stderr)

        # Generate comparison data
        try:
            print("\nGenerating comparison and trend data...")

            # Export trend analysis
            trend_file = output_dir / "trend_analysis.json"
            export_trend_analysis(metrics, trend_file)

            viz_data.comparison_available = True
            viz_data.comparison_last_updated = datetime.utcnow().isoformat() + "Z"

            print("✓ Comparison data generated")

        except Exception as e:
            print(f"✗ Failed to generate comparison data: {e}", file=sys.stderr)

    # Generate metadata with visualization flags
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "schema_version": "4.0",
        "metrics_count": len(metrics),
        "sources_count": len(sources),
        "source_mix_targets": {
            "volumes": source_mix_volumes,
            "share": source_mix_share
        },
        "source_mix_targets_version": source_mix_config.get("version") if isinstance(source_mix_config, dict) else None,
        "visualizations": viz_data.model_dump() if SCHEMA_VALIDATION_AVAILABLE else {},
        "cache_key": cache_key,
        "cache_ttl_seconds": 3600
    }

    metadata_file = output_dir / "dashboard_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Wrote metadata to: {metadata_file}")

    # Save cache metadata
    cache_meta = {
        "cache_key": cache_key,
        "cached_at": datetime.now().isoformat(),
        "metrics_count": len(metrics),
        "sources_count": len(sources)
    }

    with open(cache_meta_file, 'w', encoding='utf-8') as f:
        json.dump(cache_meta, f, indent=2)

    # Optional: Compress large files
    if args.compress:
        print("\n=== Compressing JSON Files ===")
        large_files = [
            all_metrics_file,
            output_dir / "time_series_daily.json",
            output_dir / "ridge_distribution.json"
        ]

        for file in large_files:
            if file.exists():
                compressed_file = file.with_suffix(file.suffix + ".gz")
                compress_json_file(file, compressed_file)

    # Print summary
    print(f"\n=== Generation Complete ===")
    print(f"Total Records: {summary['total_records']:,}")
    print(f"Total URLs Processed: {summary['total_urls_processed']:,}")
    print(f"Avg Success Rate: {summary['avg_success_rate']:.1%}")
    print(f"Total Data Downloaded: {summary['total_data_downloaded_bytes']:,} bytes")
    print(f"Sources: {', '.join(sources)}")
    print(f"Total Runs: {summary['total_runs']}")

    if SCHEMA_VALIDATION_AVAILABLE:
        print(f"\n✓ All schema validations passed")
        print(f"✓ Advanced visualizations: {'Enabled' if not args.skip_visualizations else 'Skipped'}")
        print(f"✓ Compression: {'Enabled' if args.compress else 'Disabled'}")
    else:
        print(f"\n⚠ Schema validation skipped (pydantic not installed)")


if __name__ == "__main__":
    main()
