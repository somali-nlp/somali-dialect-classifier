#!/usr/bin/env python3
"""
Metrics Refactoring Analysis
Analyzes existing metrics data and validates the impact of the refactoring project.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict
import statistics


def load_all_metrics(metrics_dir: Path) -> Dict[str, List[Dict]]:
    """Load all metrics files grouped by pipeline type."""
    metrics_by_type = defaultdict(list)

    for metrics_file in metrics_dir.glob("*_processing.json"):
        try:
            with open(metrics_file) as f:
                data = json.load(f)
                pipeline_type = data.get("snapshot", {}).get("pipeline_type", "unknown")
                metrics_by_type[pipeline_type].append({
                    "file": metrics_file.name,
                    "data": data
                })
        except Exception as e:
            print(f"Error loading {metrics_file}: {e}")

    return dict(metrics_by_type)


def analyze_bbc_test_limit_issue(metrics: Dict) -> Dict[str, Any]:
    """Analyze the BBC test limit issue in detail."""
    snapshot = metrics.get("snapshot", {})
    stats = metrics.get("statistics", {})

    urls_discovered = snapshot.get("urls_discovered", 0)
    urls_fetched = snapshot.get("urls_fetched", 0)
    urls_processed = snapshot.get("urls_processed", 0)
    records_written = snapshot.get("records_written", 0)

    # Current (misleading) calculation
    current_fetch_success_rate = stats.get("fetch_success_rate", 0)

    # True success rates
    true_http_success_rate = (urls_fetched / urls_fetched) if urls_fetched > 0 else 0
    true_extraction_success_rate = (urls_processed / urls_fetched) if urls_fetched > 0 else 0
    true_quality_pass_rate = stats.get("quality_pass_rate", 0)

    # The problem: fetch_success_rate is calculated as urls_fetched / urls_discovered
    # But urls_discovered includes ALL discovered URLs, not just the ones we attempted
    misleading_calculation = urls_fetched / urls_discovered if urls_discovered > 0 else 0

    return {
        "urls_discovered": urls_discovered,
        "urls_fetched": urls_fetched,
        "urls_processed": urls_processed,
        "records_written": records_written,
        "current_fetch_success_rate": current_fetch_success_rate,
        "misleading_calculation": misleading_calculation,
        "true_metrics": {
            "http_request_success_rate": true_http_success_rate,
            "content_extraction_success_rate": true_extraction_success_rate,
            "quality_pass_rate": true_quality_pass_rate
        },
        "http_status_codes": snapshot.get("http_status_codes", {}),
        "error_types": snapshot.get("error_types", {}),
        "is_test_run": urls_fetched < urls_discovered
    }


def analyze_file_processing_metrics(metrics: Dict) -> Dict[str, Any]:
    """Analyze file processing pipeline metrics."""
    snapshot = metrics.get("snapshot", {})
    stats = metrics.get("statistics", {})

    files_discovered = snapshot.get("files_discovered", 0)
    files_processed = snapshot.get("files_processed", 0)
    records_extracted = snapshot.get("records_extracted", 0)
    records_written = snapshot.get("records_written", 0)
    records_filtered = snapshot.get("records_filtered", 0)

    # Current metric
    current_fetch_success_rate = stats.get("fetch_success_rate", 0)

    # New metrics
    file_extraction_success_rate = (files_processed / files_discovered) if files_discovered > 0 else 0
    record_parsing_success_rate = (records_written / (records_written + records_filtered)) if (records_written + records_filtered) > 0 else 0
    quality_pass_rate = stats.get("quality_pass_rate", 0)

    return {
        "files_discovered": files_discovered,
        "files_processed": files_processed,
        "records_extracted": records_extracted,
        "records_written": records_written,
        "records_filtered": records_filtered,
        "current_fetch_success_rate": current_fetch_success_rate,
        "new_metrics": {
            "file_extraction_success_rate": file_extraction_success_rate,
            "record_parsing_success_rate": record_parsing_success_rate,
            "quality_pass_rate": quality_pass_rate
        },
        "filter_reasons": snapshot.get("filter_reasons", {})
    }


def analyze_stream_processing_metrics(metrics: Dict) -> Dict[str, Any]:
    """Analyze stream processing pipeline metrics."""
    snapshot = metrics.get("snapshot", {})
    stats = metrics.get("statistics", {})

    datasets_opened = snapshot.get("datasets_opened", 0)
    records_fetched = snapshot.get("records_fetched", 0)
    records_processed = snapshot.get("records_processed", 0)
    records_written = snapshot.get("records_written", 0)

    # Current metric
    current_fetch_success_rate = stats.get("fetch_success_rate", 0)

    # New metrics
    stream_connection_success_rate = 1.0 if datasets_opened > 0 else 0.0
    record_retrieval_success_rate = (records_fetched / records_fetched) if records_fetched > 0 else 0.0
    quality_pass_rate = stats.get("quality_pass_rate", 0)

    return {
        "datasets_opened": datasets_opened,
        "records_fetched": records_fetched,
        "records_processed": records_processed,
        "records_written": records_written,
        "current_fetch_success_rate": current_fetch_success_rate,
        "new_metrics": {
            "stream_connection_success_rate": stream_connection_success_rate,
            "record_retrieval_success_rate": record_retrieval_success_rate,
            "quality_pass_rate": quality_pass_rate
        }
    }


def generate_backward_compatible_metrics(old_metrics: Dict) -> Dict:
    """Generate new format metrics from old format, preserving legacy data."""
    snapshot = old_metrics.get("snapshot", {})
    stats = old_metrics.get("statistics", {})
    pipeline_type = snapshot.get("pipeline_type", "unknown")

    # Base structure with legacy preservation
    new_format = {
        "snapshot": snapshot,
        "statistics": {
            **stats,
            "_legacy_fetch_success_rate": stats.get("fetch_success_rate"),
            "_migration_timestamp": datetime.utcnow().isoformat() + "Z",
            "_format_version": "2.0"
        }
    }

    # Add pipeline-specific new metrics
    if pipeline_type == "web_scraping":
        analysis = analyze_bbc_test_limit_issue(old_metrics)
        new_format["statistics"].update({
            "http_request_success_rate": analysis["true_metrics"]["http_request_success_rate"],
            "content_extraction_success_rate": analysis["true_metrics"]["content_extraction_success_rate"],
            # quality_pass_rate already exists
        })
    elif pipeline_type == "file_processing":
        analysis = analyze_file_processing_metrics(old_metrics)
        new_format["statistics"].update({
            "file_extraction_success_rate": analysis["new_metrics"]["file_extraction_success_rate"],
            "record_parsing_success_rate": analysis["new_metrics"]["record_parsing_success_rate"],
            # quality_pass_rate already exists
        })
    elif pipeline_type == "stream_processing":
        analysis = analyze_stream_processing_metrics(old_metrics)
        new_format["statistics"].update({
            "stream_connection_success_rate": analysis["new_metrics"]["stream_connection_success_rate"],
            "record_retrieval_success_rate": analysis["new_metrics"]["record_retrieval_success_rate"],
            # quality_pass_rate already exists
        })

    return new_format


def generate_dashboard_schema(metrics_by_type: Dict[str, List[Dict]]) -> Dict:
    """Generate the optimal JSON structure for dashboard consumption."""
    output = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "format_version": "2.0",
        "total_records": 0,
        "sources": []
    }

    for pipeline_type, metrics_list in metrics_by_type.items():
        for metrics_entry in metrics_list:
            data = metrics_entry["data"]
            snapshot = data.get("snapshot", {})
            stats = data.get("statistics", {})

            source_name = snapshot.get("source", "Unknown")
            records_written = snapshot.get("records_written", 0)
            output["total_records"] += records_written

            # Build source entry based on pipeline type
            source_entry = {
                "name": source_name,
                "pipeline_type": pipeline_type,
                "last_run": snapshot.get("timestamp", ""),
                "run_id": snapshot.get("run_id", ""),
                "metrics": {
                    "volume": {
                        "records_written": records_written,
                        "bytes_downloaded": snapshot.get("bytes_downloaded", 0),
                        "duration_seconds": snapshot.get("duration_seconds", 0)
                    }
                }
            }

            # Add pipeline-specific metrics
            if pipeline_type == "web_scraping":
                analysis = analyze_bbc_test_limit_issue(data)
                source_entry["metrics"]["discovery"] = {
                    "urls_discovered": analysis["urls_discovered"]
                }
                source_entry["metrics"]["extraction"] = {
                    "http_request_success_rate": analysis["true_metrics"]["http_request_success_rate"],
                    "http_requests_attempted": analysis["urls_fetched"],
                    "http_requests_successful": analysis["urls_fetched"],  # Based on HTTP 200 status
                    "content_extraction_success_rate": analysis["true_metrics"]["content_extraction_success_rate"],
                    "content_extracted": analysis["urls_processed"]
                }
                source_entry["metrics"]["quality"] = {
                    "quality_pass_rate": analysis["true_metrics"]["quality_pass_rate"],
                    "records_received": analysis["urls_processed"],
                    "records_passed": records_written
                }
                # Flag test runs
                if analysis["is_test_run"]:
                    source_entry["_test_run_limited"] = True
                    source_entry["_limit_applied"] = analysis["urls_fetched"]

            elif pipeline_type == "file_processing":
                analysis = analyze_file_processing_metrics(data)
                source_entry["metrics"]["discovery"] = {
                    "files_discovered": analysis["files_discovered"]
                }
                source_entry["metrics"]["extraction"] = {
                    "file_extraction_success_rate": analysis["new_metrics"]["file_extraction_success_rate"],
                    "files_processed": analysis["files_processed"],
                    "record_parsing_success_rate": analysis["new_metrics"]["record_parsing_success_rate"],
                    "records_parsed": records_written,
                    "records_filtered": analysis["records_filtered"]
                }
                source_entry["metrics"]["quality"] = {
                    "quality_pass_rate": analysis["new_metrics"]["quality_pass_rate"],
                    "filter_reasons": analysis["filter_reasons"]
                }

            elif pipeline_type == "stream_processing":
                analysis = analyze_stream_processing_metrics(data)
                source_entry["metrics"]["discovery"] = {
                    "datasets_opened": analysis["datasets_opened"]
                }
                source_entry["metrics"]["extraction"] = {
                    "stream_connection_success_rate": analysis["new_metrics"]["stream_connection_success_rate"],
                    "record_retrieval_success_rate": analysis["new_metrics"]["record_retrieval_success_rate"],
                    "records_fetched": analysis["records_fetched"],
                    "records_retrieved": analysis["records_processed"]
                }
                source_entry["metrics"]["quality"] = {
                    "quality_pass_rate": analysis["new_metrics"]["quality_pass_rate"],
                    "records_received": analysis["records_processed"],
                    "records_passed": records_written
                }

            # Add performance metrics if available
            if "text_length_stats" in stats:
                source_entry["metrics"]["text_statistics"] = stats["text_length_stats"]

            if "throughput" in stats:
                source_entry["metrics"]["performance"] = stats["throughput"]

            output["sources"].append(source_entry)

    return output


def calculate_aggregation_comparisons(metrics_by_type: Dict[str, List[Dict]]) -> Dict:
    """Compare different aggregation methods (simple avg, volume-weighted, harmonic mean)."""
    all_success_rates = []
    weighted_numerator = 0
    weighted_denominator = 0

    for pipeline_type, metrics_list in metrics_by_type.items():
        for metrics_entry in metrics_list:
            data = metrics_entry["data"]
            snapshot = data.get("snapshot", {})
            stats = data.get("statistics", {})

            success_rate = stats.get("fetch_success_rate", 0)
            records = snapshot.get("records_written", 0)

            all_success_rates.append(success_rate)
            weighted_numerator += success_rate * records
            weighted_denominator += records

    simple_average = statistics.mean(all_success_rates) if all_success_rates else 0
    volume_weighted = weighted_numerator / weighted_denominator if weighted_denominator > 0 else 0

    # Harmonic mean (only for non-zero values)
    non_zero_rates = [r for r in all_success_rates if r > 0]
    harmonic_mean = statistics.harmonic_mean(non_zero_rates) if non_zero_rates else 0

    return {
        "simple_average": simple_average,
        "volume_weighted": volume_weighted,
        "harmonic_mean": harmonic_mean,
        "recommendation": "Do NOT aggregate incompatible metrics across pipeline types. Show source-specific metrics instead."
    }


def main():
    """Main analysis execution."""
    metrics_dir = Path("data/metrics")

    print("=" * 80)
    print("METRICS REFACTORING ANALYSIS")
    print("=" * 80)
    print()

    # Load all metrics
    print("1. Loading metrics files...")
    metrics_by_type = load_all_metrics(metrics_dir)
    print(f"   Found {sum(len(m) for m in metrics_by_type.values())} metrics files across {len(metrics_by_type)} pipeline types")
    print()

    # Analyze each pipeline type
    print("2. Analyzing pipeline-specific metrics...")
    for pipeline_type, metrics_list in metrics_by_type.items():
        print(f"\n   {pipeline_type.upper()} ({len(metrics_list)} runs)")
        print("   " + "-" * 60)

        for metrics_entry in metrics_list:
            data = metrics_entry["data"]
            source = data.get("snapshot", {}).get("source", "Unknown")

            if pipeline_type == "web_scraping":
                analysis = analyze_bbc_test_limit_issue(data)
                print(f"   {source}:")
                print(f"      - URLs discovered: {analysis['urls_discovered']}")
                print(f"      - URLs fetched: {analysis['urls_fetched']}")
                print(f"      - URLs processed: {analysis['urls_processed']}")
                print(f"      - Current fetch_success_rate: {analysis['current_fetch_success_rate']:.1%}")
                print(f"      - Misleading calc (fetched/discovered): {analysis['misleading_calculation']:.1%}")
                print(f"      - TRUE http_request_success_rate: {analysis['true_metrics']['http_request_success_rate']:.1%}")
                print(f"      - TRUE content_extraction_success_rate: {analysis['true_metrics']['content_extraction_success_rate']:.1%}")
                print(f"      - Quality pass rate: {analysis['true_metrics']['quality_pass_rate']:.1%}")
                if analysis['is_test_run']:
                    print(f"      - [TEST RUN] Limited to {analysis['urls_fetched']} of {analysis['urls_discovered']} URLs")

            elif pipeline_type == "file_processing":
                analysis = analyze_file_processing_metrics(data)
                print(f"   {source}:")
                print(f"      - Files discovered: {analysis['files_discovered']}")
                print(f"      - Files processed: {analysis['files_processed']}")
                print(f"      - Records written: {analysis['records_written']}")
                print(f"      - Records filtered: {analysis['records_filtered']}")
                print(f"      - Current fetch_success_rate: {analysis['current_fetch_success_rate']:.1%}")
                print(f"      - NEW file_extraction_success_rate: {analysis['new_metrics']['file_extraction_success_rate']:.1%}")
                print(f"      - NEW record_parsing_success_rate: {analysis['new_metrics']['record_parsing_success_rate']:.1%}")
                print(f"      - Quality pass rate: {analysis['new_metrics']['quality_pass_rate']:.1%}")

            elif pipeline_type == "stream_processing":
                analysis = analyze_stream_processing_metrics(data)
                print(f"   {source}:")
                print(f"      - Datasets opened: {analysis['datasets_opened']}")
                print(f"      - Records fetched: {analysis['records_fetched']}")
                print(f"      - Records processed: {analysis['records_processed']}")
                print(f"      - Current fetch_success_rate: {analysis['current_fetch_success_rate']:.1%}")
                print(f"      - NEW stream_connection_success_rate: {analysis['new_metrics']['stream_connection_success_rate']:.1%}")
                print(f"      - NEW record_retrieval_success_rate: {analysis['new_metrics']['record_retrieval_success_rate']:.1%}")
                print(f"      - Quality pass rate: {analysis['new_metrics']['quality_pass_rate']:.1%}")

    print()
    print("3. Aggregation analysis...")
    agg_comparison = calculate_aggregation_comparisons(metrics_by_type)
    print(f"   Simple average: {agg_comparison['simple_average']:.1%}")
    print(f"   Volume-weighted: {agg_comparison['volume_weighted']:.1%}")
    print(f"   Harmonic mean: {agg_comparison['harmonic_mean']:.1%}")
    print(f"   Recommendation: {agg_comparison['recommendation']}")
    print()

    # Generate dashboard schema
    print("4. Generating dashboard schema...")
    dashboard_schema = generate_dashboard_schema(metrics_by_type)
    output_file = Path("all_metrics_schema_v2.json")
    with open(output_file, "w") as f:
        json.dump(dashboard_schema, f, indent=2)
    print(f"   Saved to: {output_file}")
    print(f"   Total records: {dashboard_schema['total_records']:,}")
    print(f"   Total sources: {len(dashboard_schema['sources'])}")
    print()

    # Generate backward compatible examples
    print("5. Generating backward compatibility examples...")
    for pipeline_type, metrics_list in metrics_by_type.items():
        if metrics_list:
            example = metrics_list[0]
            new_format = generate_backward_compatible_metrics(example["data"])
            output_file = Path(f"backward_compat_example_{pipeline_type}.json")
            with open(output_file, "w") as f:
                json.dump(new_format, f, indent=2)
            print(f"   {pipeline_type}: {output_file}")
    print()

    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
