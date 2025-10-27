"""
Filter analysis utilities for quality control insights.

This module provides tools to analyze filter behavior, generate stratified
datasets, and compute filter breakdown statistics. Useful for understanding
what data is being dropped and why.

Usage:
    from somali_dialect_classifier.utils.filter_analysis import FilterAnalyzer

    analyzer = FilterAnalyzer(source="BBC-Somali")
    analyzer.enable_sampling(rate=0.01)  # Sample 1% of filtered records

    # During processing
    analyzer.record_passed(record)
    analyzer.record_filtered(record, "min_length_filter", reason="too short")

    # After processing
    report = analyzer.generate_report()
    analyzer.export_stratified_dataset("data/reports/bbc_filtered_samples.jsonl")
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from collections import defaultdict, Counter
import json
import random
from datetime import datetime


class FilteredSample:
    """Represents a sample of a filtered record."""

    def __init__(
        self,
        record_id: str,
        title: str,
        text_preview: str,
        filter_name: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize filtered sample.

        Args:
            record_id: Unique identifier for the record
            title: Record title
            text_preview: Preview of text (first 200 chars)
            filter_name: Name of filter that rejected record
            reason: Optional human-readable reason
            metadata: Optional additional metadata
        """
        self.record_id = record_id
        self.title = title
        self.text_preview = text_preview
        self.filter_name = filter_name
        self.reason = reason
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "record_id": self.record_id,
            "title": self.title,
            "text_preview": self.text_preview,
            "filter_name": self.filter_name,
            "reason": self.reason,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class FilterAnalyzer:
    """
    Analyzer for filter behavior and quality control insights.

    Tracks which filters are dropping records, samples rejected records,
    and generates detailed reports for debugging and optimization.
    """

    def __init__(
        self,
        source: str,
        sampling_rate: float = 0.0,
        max_samples_per_filter: int = 100
    ):
        """
        Initialize filter analyzer.

        Args:
            source: Source name (e.g., "BBC-Somali")
            sampling_rate: Fraction of filtered records to sample (0.0-1.0)
            max_samples_per_filter: Maximum samples to retain per filter
        """
        self.source = source
        self.sampling_rate = sampling_rate
        self.max_samples_per_filter = max_samples_per_filter

        # Statistics
        self.filter_counts: Counter = Counter()
        self.total_processed = 0
        self.total_passed = 0
        self.total_filtered = 0

        # Sampled records
        self.filtered_samples: Dict[str, List[FilteredSample]] = defaultdict(list)

        # Per-filter detailed stats
        self.filter_details: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "percentage": 0.0,
                "reasons": Counter()
            }
        )

    def enable_sampling(self, rate: float = 0.01):
        """
        Enable sampling of filtered records.

        Args:
            rate: Sampling rate (0.0-1.0), default 0.01 (1%)
        """
        self.sampling_rate = max(0.0, min(1.0, rate))

    def record_processed(self):
        """Record that a record was processed."""
        self.total_processed += 1

    def record_passed(self, record_data: Optional[Dict[str, Any]] = None):
        """
        Record that a record passed all filters.

        Args:
            record_data: Optional record metadata for analysis
        """
        self.total_passed += 1

    def record_filtered(
        self,
        record_id: str,
        title: str,
        text: str,
        filter_name: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record that a record was filtered.

        Args:
            record_id: Unique identifier for the record
            title: Record title
            text: Record text (will be previewed)
            filter_name: Name of filter that rejected record
            reason: Optional human-readable reason
            metadata: Optional additional metadata
        """
        self.total_filtered += 1
        self.filter_counts[filter_name] += 1

        # Track reason if provided
        if reason:
            self.filter_details[filter_name]["reasons"][reason] += 1

        # Sample if enabled
        if self.sampling_rate > 0 and random.random() < self.sampling_rate:
            # Check if we've reached max samples for this filter
            if len(self.filtered_samples[filter_name]) < self.max_samples_per_filter:
                sample = FilteredSample(
                    record_id=record_id,
                    title=title,
                    text_preview=text[:200] + "..." if len(text) > 200 else text,
                    filter_name=filter_name,
                    reason=reason,
                    metadata=metadata
                )
                self.filtered_samples[filter_name].append(sample)

    def get_filter_breakdown(self) -> Dict[str, int]:
        """
        Get filter breakdown for metrics reporting.

        Returns:
            Dictionary mapping filter names to counts
        """
        return dict(self.filter_counts)

    def compute_filter_percentages(self) -> Dict[str, float]:
        """
        Compute percentage of records dropped by each filter.

        Returns:
            Dictionary mapping filter names to percentages
        """
        if self.total_processed == 0:
            return {}

        return {
            filter_name: (count / self.total_processed) * 100
            for filter_name, count in self.filter_counts.items()
        }

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive filter analysis report.

        Returns:
            Report dictionary with statistics and insights
        """
        percentages = self.compute_filter_percentages()

        report = {
            "source": self.source,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_processed": self.total_processed,
                "total_passed": self.total_passed,
                "total_filtered": self.total_filtered,
                "pass_rate": (self.total_passed / self.total_processed) if self.total_processed > 0 else 0.0,
                "filter_rate": (self.total_filtered / self.total_processed) if self.total_processed > 0 else 0.0,
            },
            "filter_breakdown": {
                filter_name: {
                    "count": count,
                    "percentage": percentages.get(filter_name, 0.0),
                    "top_reasons": dict(self.filter_details[filter_name]["reasons"].most_common(5))
                }
                for filter_name, count in self.filter_counts.most_common()
            },
            "sampling": {
                "enabled": self.sampling_rate > 0,
                "rate": self.sampling_rate,
                "total_samples": sum(len(samples) for samples in self.filtered_samples.values()),
                "samples_per_filter": {
                    filter_name: len(samples)
                    for filter_name, samples in self.filtered_samples.items()
                }
            }
        }

        return report

    def export_stratified_dataset(self, output_path: Path) -> int:
        """
        Export stratified dataset of filtered samples to JSONL.

        Each line contains a sampled record with filter information.

        Args:
            output_path: Path to output JSONL file

        Returns:
            Number of samples exported
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        total_exported = 0

        with open(output_path, 'w', encoding='utf-8') as f:
            for filter_name, samples in sorted(self.filtered_samples.items()):
                for sample in samples:
                    f.write(json.dumps(sample.to_dict()) + "\n")
                    total_exported += 1

        return total_exported

    def export_report(self, output_path: Path):
        """
        Export detailed report to JSON.

        Args:
            output_path: Path to output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = self.generate_report()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

    def print_summary(self):
        """Print human-readable summary to console."""
        report = self.generate_report()
        summary = report["summary"]

        print("\n" + "=" * 60)
        print(f"FILTER ANALYSIS SUMMARY: {self.source}")
        print("=" * 60)
        print(f"Total Processed:  {summary['total_processed']:,}")
        print(f"Total Passed:     {summary['total_passed']:,} ({summary['pass_rate']:.1%})")
        print(f"Total Filtered:   {summary['total_filtered']:,} ({summary['filter_rate']:.1%})")
        print("\nFilter Breakdown:")
        print("-" * 60)

        for filter_name, stats in report["filter_breakdown"].items():
            print(f"  {filter_name:30} {stats['count']:>6,} ({stats['percentage']:>5.1f}%)")

            # Print top reasons if available
            if stats["top_reasons"]:
                for reason, count in list(stats["top_reasons"].items())[:3]:
                    print(f"    - {reason}: {count}")

        if report["sampling"]["enabled"]:
            print("\nSampling:")
            print(f"  Rate: {report['sampling']['rate']:.1%}")
            print(f"  Total Samples: {report['sampling']['total_samples']}")

        print("=" * 60 + "\n")


def create_filter_analyzer(
    source: str,
    enable_sampling: bool = False,
    sampling_rate: float = 0.01
) -> FilterAnalyzer:
    """
    Factory function to create FilterAnalyzer with common settings.

    Args:
        source: Source name
        enable_sampling: Whether to enable sampling of filtered records
        sampling_rate: Sampling rate if enabled

    Returns:
        Configured FilterAnalyzer instance
    """
    analyzer = FilterAnalyzer(
        source=source,
        sampling_rate=sampling_rate if enable_sampling else 0.0
    )
    return analyzer


def analyze_filter_impact(
    filter_breakdown: Dict[str, int],
    total_records: int
) -> Dict[str, Any]:
    """
    Analyze impact of filters on dataset quality.

    Args:
        filter_breakdown: Filter counts from metrics
        total_records: Total records processed

    Returns:
        Analysis results with recommendations
    """
    if not filter_breakdown or total_records == 0:
        return {
            "total_filtered": 0,
            "filter_rate": 0.0,
            "top_filters": [],
            "recommendations": []
        }

    total_filtered = sum(filter_breakdown.values())
    filter_rate = total_filtered / total_records

    # Sort filters by impact
    sorted_filters = sorted(
        filter_breakdown.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Generate recommendations
    recommendations = []

    # High filter rate warning
    if filter_rate > 0.5:
        recommendations.append(
            "WARNING: Over 50% of records are being filtered. "
            "Consider reviewing filter thresholds."
        )

    # Single filter dominating
    if sorted_filters and sorted_filters[0][1] / total_filtered > 0.7:
        dominant_filter = sorted_filters[0][0]
        recommendations.append(
            f"Filter '{dominant_filter}' is responsible for >70% of drops. "
            f"Consider adjusting its parameters or examining input data quality."
        )

    # Low filter rate
    if filter_rate < 0.05:
        recommendations.append(
            "Very few records are being filtered (<5%). "
            "Filters may be too permissive."
        )

    return {
        "total_filtered": total_filtered,
        "filter_rate": filter_rate,
        "top_filters": sorted_filters[:5],
        "recommendations": recommendations
    }
