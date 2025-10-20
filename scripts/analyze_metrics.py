#!/usr/bin/env python3
"""
Metrics Analysis Script
Analyzes pipeline metrics and generates insights for dashboard improvements.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import statistics


class MetricsAnalyzer:
    """Analyzes pipeline metrics and generates insights."""

    def __init__(self, metrics_dir: Path):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_files = list(self.metrics_dir.glob("*.json"))
        self.runs = {}
        self.load_metrics()

    def load_metrics(self):
        """Load all metrics files and organize by run."""
        for mf in self.metrics_files:
            with open(mf) as f:
                data = json.load(f)
                run_id = data['snapshot']['run_id']
                if run_id not in self.runs:
                    self.runs[run_id] = {
                        'run_id': run_id,
                        'source': data['snapshot']['source'],
                        'metrics': []
                    }
                self.runs[run_id]['metrics'].append(data)

    def get_final_metrics(self, run_id: str) -> Dict:
        """Get the final (processing) metrics for a run."""
        run = self.runs[run_id]
        # Find the metric with the highest records_written
        final = max(run['metrics'],
                   key=lambda x: x['snapshot'].get('records_written', 0))
        return final

    def calculate_aggregate_stats(self) -> Dict[str, Any]:
        """Calculate aggregate statistics across all runs."""
        total_records = 0
        total_chars = 0
        all_lengths = []
        sources = {}

        for run_id, run in self.runs.items():
            final = self.get_final_metrics(run_id)
            snapshot = final['snapshot']
            stats = final.get('statistics', {})

            records = snapshot.get('records_written', 0)
            total_records += records

            source = snapshot['source']
            if source not in sources:
                sources[source] = {
                    'records': 0,
                    'chars': 0,
                    'runs': 0,
                    'avg_length': 0,
                    'status': 'incomplete'
                }

            sources[source]['records'] += records
            sources[source]['runs'] += 1

            if records > 0:
                sources[source]['status'] = 'complete'

            # Get text lengths
            if 'text_lengths' in snapshot and snapshot['text_lengths']:
                lengths = snapshot['text_lengths']
                all_lengths.extend(lengths)
                total_chars += sum(lengths)
                sources[source]['chars'] += sum(lengths)
                if records > 0:
                    sources[source]['avg_length'] = sources[source]['chars'] / sources[source]['records']

        return {
            'total_records': total_records,
            'total_chars': total_chars,
            'total_sources': len(sources),
            'active_sources': len([s for s in sources.values() if s['status'] == 'complete']),
            'sources': sources,
            'text_stats': self._calculate_text_stats(all_lengths) if all_lengths else {},
            'total_runs': len(self.runs)
        }

    def _calculate_text_stats(self, lengths: List[int]) -> Dict:
        """Calculate text length statistics."""
        if not lengths:
            return {}

        sorted_lengths = sorted(lengths)
        return {
            'min': min(lengths),
            'max': max(lengths),
            'mean': statistics.mean(lengths),
            'median': statistics.median(lengths),
            'stdev': statistics.stdev(lengths) if len(lengths) > 1 else 0,
            'q1': sorted_lengths[len(lengths) // 4],
            'q3': sorted_lengths[3 * len(lengths) // 4],
            'total_docs': len(lengths),
            'very_short': len([l for l in lengths if l < 20]),
            'short': len([l for l in lengths if 20 <= l < 100]),
            'medium': len([l for l in lengths if 100 <= l < 1000]),
            'long': len([l for l in lengths if 1000 <= l < 10000]),
            'very_long': len([l for l in lengths if l >= 10000])
        }

    def identify_quality_issues(self) -> List[Dict]:
        """Identify data quality issues."""
        issues = []

        for run_id, run in self.runs.items():
            final = self.get_final_metrics(run_id)
            snapshot = final['snapshot']
            stats = final.get('statistics', {})

            # Check for ultra-short documents
            if 'text_lengths' in snapshot:
                ultra_short = [l for l in snapshot['text_lengths'] if l < 10]
                if ultra_short:
                    issues.append({
                        'severity': 'warning',
                        'run_id': run_id,
                        'source': snapshot['source'],
                        'issue': 'ultra_short_documents',
                        'count': len(ultra_short),
                        'description': f"Found {len(ultra_short)} documents shorter than 10 characters"
                    })

            # Check for missing deduplication
            if snapshot.get('unique_hashes', 0) == 0 and snapshot.get('records_written', 0) > 0:
                issues.append({
                    'severity': 'critical',
                    'run_id': run_id,
                    'source': snapshot['source'],
                    'issue': 'no_deduplication',
                    'description': "Deduplication metrics are all zero - may not be functioning"
                })

            # Check for incomplete pipelines
            if snapshot.get('urls_discovered', 0) > 0 and snapshot.get('urls_fetched', 0) == 0:
                issues.append({
                    'severity': 'critical',
                    'run_id': run_id,
                    'source': snapshot['source'],
                    'issue': 'incomplete_pipeline',
                    'urls_discovered': snapshot['urls_discovered'],
                    'description': f"Pipeline stopped after discovery: {snapshot['urls_discovered']} URLs found but not fetched"
                })

            # Check for high filter rate
            extracted = snapshot.get('records_extracted', 0)
            written = snapshot.get('records_written', 0)
            if extracted > 0 and written > 0:
                filter_rate = (extracted - written) / extracted
                if filter_rate > 0.15:  # More than 15% filtered
                    issues.append({
                        'severity': 'warning',
                        'run_id': run_id,
                        'source': snapshot['source'],
                        'issue': 'high_filter_rate',
                        'filter_rate': filter_rate,
                        'filtered_count': extracted - written,
                        'description': f"High filter rate: {filter_rate:.1%} of records filtered ({extracted - written} records)"
                    })

        return sorted(issues, key=lambda x: {'critical': 0, 'warning': 1}.get(x['severity'], 2))

    def generate_recommendations(self) -> Dict[str, List[str]]:
        """Generate recommendations based on analysis."""
        agg_stats = self.calculate_aggregate_stats()
        issues = self.identify_quality_issues()

        recommendations = {
            'immediate': [],
            'short_term': [],
            'long_term': []
        }

        # Check data volume
        if agg_stats['total_records'] < 20000:
            recommendations['immediate'].append(
                f"Increase data volume: Current {agg_stats['total_records']:,} records is below recommended 20,000 minimum"
            )

        # Check source diversity
        if agg_stats['active_sources'] < 3:
            recommendations['immediate'].append(
                f"Add more data sources: Only {agg_stats['active_sources']} active sources. Target: 4-5 diverse sources"
            )

        # Check for critical issues
        critical_issues = [i for i in issues if i['severity'] == 'critical']
        if critical_issues:
            for issue in critical_issues:
                if issue['issue'] == 'no_deduplication':
                    recommendations['immediate'].append(
                        f"Fix deduplication tracking for {issue['source']}: All metrics show zero"
                    )
                elif issue['issue'] == 'incomplete_pipeline':
                    recommendations['immediate'].append(
                        f"Complete {issue['source']} pipeline: {issue['urls_discovered']} URLs discovered but not processed"
                    )

        # Check for warning issues
        warning_issues = [i for i in issues if i['severity'] == 'warning']
        if warning_issues:
            for issue in warning_issues:
                if issue['issue'] == 'ultra_short_documents':
                    recommendations['short_term'].append(
                        f"Filter ultra-short documents in {issue['source']}: {issue['count']} docs < 10 chars"
                    )
                elif issue['issue'] == 'high_filter_rate':
                    recommendations['short_term'].append(
                        f"Investigate high filter rate in {issue['source']}: {issue['filter_rate']:.1%} filtered"
                    )

        # Long-term recommendations
        recommendations['long_term'].extend([
            "Add vocabulary richness metrics (unique words, type-token ratio)",
            "Implement content type classification (article, sentence, paragraph)",
            "Add dialect/regional indicator tracking",
            "Implement language detection and track non-Somali percentage",
            "Add temporal metadata for articles with timestamps"
        ])

        return recommendations

    def generate_dashboard_config(self) -> Dict:
        """Generate recommended dashboard configuration."""
        agg_stats = self.calculate_aggregate_stats()

        return {
            'visualizations': [
                {
                    'type': 'bar_chart',
                    'title': 'Records by Source',
                    'data_source': 'sources.*.records',
                    'priority': 1
                },
                {
                    'type': 'histogram',
                    'title': 'Document Length Distribution',
                    'data_source': 'text_lengths',
                    'config': {
                        'bins': 50,
                        'x_scale': 'log',
                        'overlay_by_source': True
                    },
                    'priority': 1
                },
                {
                    'type': 'gauge',
                    'title': 'Overall Success Rate',
                    'data_source': 'success_rate',
                    'config': {
                        'green_threshold': 0.95,
                        'yellow_threshold': 0.80
                    },
                    'priority': 1
                },
                {
                    'type': 'box_plot',
                    'title': 'Text Length by Source',
                    'data_source': 'text_lengths',
                    'group_by': 'source',
                    'priority': 2
                },
                {
                    'type': 'funnel',
                    'title': 'Pipeline Stage Funnel',
                    'data_source': 'pipeline_stages',
                    'stages': ['discovered', 'fetched', 'extracted', 'filtered', 'written'],
                    'priority': 2
                },
                {
                    'type': 'line_chart',
                    'title': 'Cumulative Records Over Time',
                    'data_source': 'timestamp',
                    'y_axis': 'cumulative_records',
                    'priority': 2
                },
                {
                    'type': 'heatmap',
                    'title': 'Character Distribution by Source',
                    'x_axis': 'source',
                    'y_axis': 'length_bucket',
                    'priority': 3
                },
                {
                    'type': 'scorecard',
                    'title': 'Data Quality Scorecard',
                    'metrics': [
                        'success_rate',
                        'deduplication_rate',
                        'avg_document_length',
                        'filter_rate'
                    ],
                    'priority': 1
                }
            ],
            'metrics_to_add': [
                'filter_reasons',
                'language_distribution',
                'content_type_distribution',
                'vocabulary_stats',
                'error_details'
            ]
        }

    def export_analysis(self, output_dir: Path) -> Path:
        """Export complete analysis as JSON."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        analysis = {
            'generated_at': datetime.now().isoformat(),
            'total_runs': len(self.runs),
            'aggregate_statistics': self.calculate_aggregate_stats(),
            'quality_issues': self.identify_quality_issues(),
            'recommendations': self.generate_recommendations(),
            'dashboard_config': self.generate_dashboard_config()
        }

        output_file = output_dir / f"metrics_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)

        return output_file

    def print_summary(self):
        """Print a summary of the analysis."""
        agg = self.calculate_aggregate_stats()
        issues = self.identify_quality_issues()
        recs = self.generate_recommendations()

        print("=" * 80)
        print("PIPELINE METRICS ANALYSIS SUMMARY")
        print("=" * 80)
        print(f"\nTotal Runs: {len(self.runs)}")
        print(f"Total Records: {agg['total_records']:,}")
        print(f"Total Characters: {agg['total_chars']:,}")
        print(f"Active Sources: {agg['active_sources']}/{agg['total_sources']}")

        print("\n" + "-" * 80)
        print("SOURCE BREAKDOWN")
        print("-" * 80)
        for source, data in agg['sources'].items():
            print(f"\n{source}:")
            print(f"  Status: {data['status']}")
            print(f"  Records: {data['records']:,}")
            print(f"  Characters: {data['chars']:,}")
            print(f"  Avg Length: {data['avg_length']:.1f} chars")

        if agg['text_stats']:
            print("\n" + "-" * 80)
            print("TEXT STATISTICS")
            print("-" * 80)
            ts = agg['text_stats']
            print(f"  Min Length: {ts['min']} chars")
            print(f"  Max Length: {ts['max']:,} chars")
            print(f"  Mean Length: {ts['mean']:.1f} chars")
            print(f"  Median Length: {ts['median']:.1f} chars")
            print(f"  Std Dev: {ts['stdev']:.1f}")
            print(f"\n  Distribution:")
            print(f"    Very Short (<20):    {ts['very_short']:,} ({ts['very_short']/ts['total_docs']*100:.1f}%)")
            print(f"    Short (20-100):      {ts['short']:,} ({ts['short']/ts['total_docs']*100:.1f}%)")
            print(f"    Medium (100-1000):   {ts['medium']:,} ({ts['medium']/ts['total_docs']*100:.1f}%)")
            print(f"    Long (1000-10000):   {ts['long']:,} ({ts['long']/ts['total_docs']*100:.1f}%)")
            print(f"    Very Long (10000+):  {ts['very_long']:,} ({ts['very_long']/ts['total_docs']*100:.1f}%)")

        print("\n" + "-" * 80)
        print(f"QUALITY ISSUES ({len(issues)} found)")
        print("-" * 80)
        if issues:
            for issue in issues:
                print(f"\n  [{issue['severity'].upper()}] {issue['source']}")
                print(f"    {issue['description']}")
        else:
            print("  No issues found!")

        print("\n" + "-" * 80)
        print("RECOMMENDATIONS")
        print("-" * 80)

        if recs['immediate']:
            print("\n  IMMEDIATE:")
            for i, rec in enumerate(recs['immediate'], 1):
                print(f"    {i}. {rec}")

        if recs['short_term']:
            print("\n  SHORT-TERM:")
            for i, rec in enumerate(recs['short_term'], 1):
                print(f"    {i}. {rec}")

        if recs['long_term']:
            print("\n  LONG-TERM:")
            for i, rec in enumerate(recs['long_term'], 1):
                print(f"    {i}. {rec}")

        print("\n" + "=" * 80)


def main():
    """Main entry point."""
    import sys

    # Default to project metrics directory
    project_root = Path(__file__).parent.parent
    metrics_dir = project_root / "data" / "metrics"
    output_dir = project_root / "data" / "analysis"

    if not metrics_dir.exists():
        print(f"Error: Metrics directory not found: {metrics_dir}")
        sys.exit(1)

    analyzer = MetricsAnalyzer(metrics_dir)

    # Print summary
    analyzer.print_summary()

    # Export analysis
    output_file = analyzer.export_analysis(output_dir)
    print(f"\nFull analysis exported to: {output_file}")


if __name__ == "__main__":
    main()
