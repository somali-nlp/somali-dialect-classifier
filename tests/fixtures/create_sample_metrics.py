#!/usr/bin/env python3
"""
Create sample metrics for testing dashboard

This script generates realistic test metrics when no real data is available.
Used primarily in CI/CD environments and local testing.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import random


def create_sample_metric(
    source: str,
    pipeline_type: str,
    records_written: int,
    quality_rate: float,
    dedup_rate: float,
    timestamp_offset_days: int = 0
) -> dict:
    """Create a sample v3.0 metrics file"""

    timestamp = (datetime.utcnow() - timedelta(days=timestamp_offset_days)).isoformat() + "Z"
    run_id = f"test_{source.lower().replace('-', '_')}_{timestamp[:10].replace('-', '')}"

    # Calculate derived values
    http_success = quality_rate + random.uniform(-0.05, 0.05)
    http_success = max(0.0, min(1.0, http_success))

    urls_processed = int(records_written / (quality_rate or 0.5))
    urls_attempted = int(urls_processed / (http_success or 0.9))

    return {
        "_schema_version": "3.0",
        "_pipeline_type": pipeline_type,
        "_timestamp": timestamp,
        "_run_id": run_id,
        "_source": source,
        "layered_metrics": {
            "connectivity": {
                "connection_attempted": True,
                "connection_successful": True,
                "connection_duration_ms": random.uniform(1000, 5000)
            },
            "extraction": {
                "http_requests_attempted": urls_attempted if pipeline_type == "web_scraping" else 0,
                "http_requests_successful": urls_processed if pipeline_type == "web_scraping" else 0,
                "http_status_distribution": {"200": urls_processed} if pipeline_type == "web_scraping" else {},
                "pages_parsed": urls_processed if pipeline_type == "web_scraping" else 0,
                "content_extracted": urls_processed if pipeline_type == "web_scraping" else 0,
                "files_discovered": urls_processed if pipeline_type == "file_processing" else 0,
                "files_extracted": urls_processed if pipeline_type == "file_processing" else 0,
                "records_parsed": records_written if pipeline_type == "file_processing" else 0,
                "records_fetched": records_written if pipeline_type == "stream_processing" else 0,
                "records_retrieved": records_written if pipeline_type == "stream_processing" else 0
            },
            "quality": {
                "records_received": int(records_written / (1 - dedup_rate)) if dedup_rate < 1 else records_written,
                "records_passed_filters": records_written,
                "filter_breakdown": {}
            },
            "volume": {
                "records_written": records_written,
                "bytes_downloaded": records_written * random.randint(3000, 8000),
                "total_chars": records_written * random.randint(3500, 7000)
            }
        },
        "legacy_metrics": {
            "snapshot": {
                "timestamp": timestamp,
                "run_id": run_id,
                "source": source,
                "duration_seconds": random.uniform(300, 3600),
                "pipeline_type": pipeline_type,
                "urls_discovered": urls_attempted if pipeline_type == "web_scraping" else 0,
                "urls_fetched": urls_processed if pipeline_type == "web_scraping" else 0,
                "urls_processed": urls_processed if pipeline_type == "web_scraping" else 0,
                "files_discovered": urls_processed if pipeline_type == "file_processing" else 0,
                "files_processed": urls_processed if pipeline_type == "file_processing" else 0,
                "records_fetched": records_written if pipeline_type == "stream_processing" else 0,
                "records_written": records_written,
                "bytes_downloaded": records_written * random.randint(3000, 8000),
            },
            "statistics": {
                "http_request_success_rate": http_success if pipeline_type == "web_scraping" else 0,
                "content_extraction_success_rate": quality_rate if pipeline_type == "web_scraping" else 0,
                "file_extraction_success_rate": quality_rate if pipeline_type == "file_processing" else 0,
                "record_parsing_success_rate": quality_rate if pipeline_type == "file_processing" else 0,
                "stream_connection_success_rate": quality_rate if pipeline_type == "stream_processing" else 0,
                "record_retrieval_success_rate": quality_rate if pipeline_type == "stream_processing" else 0,
                "quality_pass_rate": quality_rate,
                "deduplication_rate": dedup_rate,
                "fetch_success_rate": http_success,  # Deprecated
                "text_length_stats": {
                    "min": random.randint(200, 500),
                    "max": random.randint(8000, 15000),
                    "mean": random.randint(3500, 7000),
                    "median": random.randint(3000, 6500),
                    "total_chars": records_written * random.randint(3500, 7000)
                },
                "throughput": {
                    "urls_per_second": random.uniform(0.01, 0.05),
                    "bytes_per_second": random.uniform(1000, 5000),
                    "records_per_minute": random.uniform(0.5, 2.0)
                }
            }
        }
    }


def main():
    """Generate sample metrics for all sources"""

    output_dir = Path("data/metrics")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define sample sources
    sources = [
        {
            "name": "Wikipedia-Somali",
            "pipeline": "web_scraping",
            "records": 1250,
            "quality": 0.98,
            "dedup": 0.05
        },
        {
            "name": "BBC-Somali",
            "pipeline": "web_scraping",
            "records": 850,
            "quality": 0.96,
            "dedup": 0.08
        },
        {
            "name": "HuggingFace-Somali_c4-so",
            "pipeline": "stream_processing",
            "records": 2100,
            "quality": 0.92,
            "dedup": 0.15
        },
        {
            "name": "Sprakbanken-Somali",
            "pipeline": "file_processing",
            "records": 1600,
            "quality": 0.97,
            "dedup": 0.03
        }
    ]

    print("Generating sample metrics...")

    for source in sources:
        metric = create_sample_metric(
            source=source["name"],
            pipeline_type=source["pipeline"],
            records_written=source["records"],
            quality_rate=source["quality"],
            dedup_rate=source["dedup"],
            timestamp_offset_days=random.randint(0, 7)
        )

        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        source_slug = source["name"].lower().replace("-", "_").replace(" ", "_")
        filename = f"{timestamp}_{source_slug}_processing.json"

        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(metric, f, indent=2)

        print(f"  ✓ Created {filename}")

    print(f"\n✅ Generated {len(sources)} sample metrics in {output_dir}")
    print(f"Total records: {sum(s['records'] for s in sources):,}")


if __name__ == "__main__":
    main()
