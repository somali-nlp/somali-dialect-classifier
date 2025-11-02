#!/usr/bin/env python3
"""
Query examples for filter history Parquet data.

Demonstrates common analytics queries using DuckDB and Pandas for
historical filter metrics analysis.

Features:
- 5 pre-built query types (effectiveness, trends, quality, anomalies, top filters)
- Console output as formatted tables
- Optional CSV export
- DuckDB SQL and Pandas approaches

Usage:
    # Run all queries
    python scripts/query_filter_history.py

    # Run specific query
    python scripts/query_filter_history.py --query trends

    # Export results to CSV
    python scripts/query_filter_history.py --query effectiveness --output results.csv

Requirements:
    pip install duckdb pandas pyarrow tabulate
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    import duckdb
    import pandas as pd
    from tabulate import tabulate
except ImportError as e:
    print(f"ERROR: Missing required dependencies: {e}")
    print("Install with: pip install duckdb pandas pyarrow tabulate")
    sys.exit(1)


PARQUET_PATH = Path("data/warehouse/filter_history.parquet")


def query_filter_effectiveness(parquet_path: Path, days: int = 90) -> pd.DataFrame:
    """
    Query 1: Filter effectiveness by total records filtered.

    Shows which filters remove the most content across all sources.

    Args:
        parquet_path: Path to Parquet dataset
        days: Number of days to analyze (default: 90)

    Returns:
        DataFrame with filter effectiveness metrics
    """
    con = duckdb.connect()

    query = f"""
    SELECT
        filter_label,
        filter_category,
        COUNT(DISTINCT run_id) AS run_count,
        SUM(records_filtered) AS total_filtered,
        AVG(records_filtered) AS avg_per_run,
        AVG(filter_rate) AS avg_filter_rate,
        MIN(filter_rate) AS min_rate,
        MAX(filter_rate) AS max_rate
    FROM read_parquet('{parquet_path}/**/*.parquet')
    WHERE timestamp >= CURRENT_DATE - INTERVAL '{days} days'
    GROUP BY filter_label, filter_category
    ORDER BY total_filtered DESC
    """

    df = con.execute(query).df()

    # Format percentages
    df["avg_filter_rate"] = (df["avg_filter_rate"] * 100).round(2)
    df["min_rate"] = (df["min_rate"] * 100).round(2)
    df["max_rate"] = (df["max_rate"] * 100).round(2)

    return df


def query_trends_over_time(parquet_path: Path, days: int = 30) -> pd.DataFrame:
    """
    Query 2: Filter trends over time (weekly aggregation).

    Shows how filter usage changes over time.

    Args:
        parquet_path: Path to Parquet dataset
        days: Number of days to analyze (default: 30)

    Returns:
        DataFrame with weekly filter trends
    """
    con = duckdb.connect()

    query = f"""
    SELECT
        DATE_TRUNC('week', timestamp) AS week,
        source,
        filter_label,
        COUNT(*) AS run_count,
        AVG(records_filtered) AS avg_filtered,
        SUM(records_filtered) AS total_filtered,
        AVG(filter_rate) AS avg_rate
    FROM read_parquet('{parquet_path}/**/*.parquet')
    WHERE timestamp >= CURRENT_DATE - INTERVAL '{days} days'
    GROUP BY week, source, filter_label
    ORDER BY week DESC, total_filtered DESC
    LIMIT 50
    """

    df = con.execute(query).df()

    # Format percentages
    df["avg_rate"] = (df["avg_rate"] * 100).round(2)

    return df


def query_top_filters_by_source(parquet_path: Path, days: int = 90) -> pd.DataFrame:
    """
    Query 3: Top filters by rejection count per source.

    Shows the most impactful filters for each data source.

    Args:
        parquet_path: Path to Parquet dataset
        days: Number of days to analyze (default: 90)

    Returns:
        DataFrame with top filters per source
    """
    con = duckdb.connect()

    query = f"""
    WITH RankedFilters AS (
        SELECT
            source,
            filter_label,
            SUM(records_filtered) AS total_filtered,
            AVG(filter_rate) AS avg_rate,
            ROW_NUMBER() OVER (PARTITION BY source ORDER BY SUM(records_filtered) DESC) AS rank
        FROM read_parquet('{parquet_path}/**/*.parquet')
        WHERE timestamp >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY source, filter_label
    )
    SELECT
        source,
        filter_label,
        total_filtered,
        avg_rate,
        rank
    FROM RankedFilters
    WHERE rank <= 5
    ORDER BY source, rank
    """

    df = con.execute(query).df()

    # Format percentages
    df["avg_rate"] = (df["avg_rate"] * 100).round(2)

    return df


def query_quality_correlation(parquet_path: Path) -> pd.DataFrame:
    """
    Query 4: Quality pass rate correlation with filter activity.

    Analyzes relationship between filtering activity and quality pass rate.

    Args:
        parquet_path: Path to Parquet dataset

    Returns:
        DataFrame with quality correlation metrics
    """
    con = duckdb.connect()

    query = f"""
    SELECT
        source,
        COUNT(DISTINCT run_id) AS total_runs,
        AVG(records_filtered::FLOAT / NULLIF(records_received, 0)) AS avg_filter_rate,
        AVG(records_passed::FLOAT / NULLIF(records_received, 0)) AS avg_pass_rate,
        SUM(records_filtered) AS total_filtered,
        SUM(records_passed) AS total_passed,
        SUM(records_received) AS total_received
    FROM (
        SELECT DISTINCT
            run_id,
            source,
            records_filtered,
            records_passed,
            records_received
        FROM read_parquet('{parquet_path}/**/*.parquet')
    )
    GROUP BY source
    ORDER BY total_received DESC
    """

    df = con.execute(query).df()

    # Format percentages
    df["avg_filter_rate"] = (df["avg_filter_rate"] * 100).round(2)
    df["avg_pass_rate"] = (df["avg_pass_rate"] * 100).round(2)

    return df


def query_anomaly_detection(parquet_path: Path, threshold: float = 2.0) -> pd.DataFrame:
    """
    Query 5: Anomaly detection - sudden changes in filter rates.

    Detects runs where filter rates deviate significantly from average.

    Args:
        parquet_path: Path to Parquet dataset
        threshold: Standard deviation multiplier for anomaly detection (default: 2.0)

    Returns:
        DataFrame with detected anomalies
    """
    # Use Pandas for this query as it's more complex
    df = pd.read_parquet(parquet_path)

    # Calculate stats per filter and source
    stats = df.groupby(["source", "filter_type"])["filter_rate"].agg(["mean", "std"]).reset_index()

    # Merge stats back to original data
    df = df.merge(stats, on=["source", "filter_type"], how="left")

    # Detect anomalies (filter_rate outside mean ± threshold*std)
    df["z_score"] = (df["filter_rate"] - df["mean"]) / df["std"].replace(0, 1)
    anomalies = df[abs(df["z_score"]) > threshold].copy()

    # Select relevant columns
    result = anomalies[[
        "timestamp", "source", "filter_type", "filter_label",
        "filter_rate", "mean", "std", "z_score"
    ]].sort_values("z_score", ascending=False)

    # Format percentages
    result["filter_rate"] = (result["filter_rate"] * 100).round(2)
    result["mean"] = (result["mean"] * 100).round(2)
    result["std"] = (result["std"] * 100).round(2)
    result["z_score"] = result["z_score"].round(2)

    return result.head(20)  # Top 20 anomalies


def print_query_result(title: str, df: pd.DataFrame, output_csv: Optional[Path] = None):
    """
    Print query result as formatted table and optionally export to CSV.

    Args:
        title: Query title
        df: DataFrame to display
        output_csv: Optional CSV output path
    """
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")

    if df.empty:
        print("  No results found.")
        return

    # Print as table
    print(tabulate(df, headers="keys", tablefmt="grid", showindex=False))

    print(f"\n  Total rows: {len(df)}")

    # Export to CSV if requested
    if output_csv:
        df.to_csv(output_csv, index=False)
        print(f"  Exported to: {output_csv}")


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Query filter history Parquet data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Query types:
  effectiveness  - Which filters remove the most content
  trends         - Filter usage trends over time
  top-filters    - Top filters by source
  quality        - Quality pass rate correlation
  anomalies      - Detect sudden filter rate changes

Examples:
  # Run all queries
  python scripts/query_filter_history.py

  # Run specific query
  python scripts/query_filter_history.py --query trends

  # Export results
  python scripts/query_filter_history.py --query effectiveness --output results.csv
        """
    )

    parser.add_argument(
        "--parquet-path",
        type=Path,
        default=PARQUET_PATH,
        help=f"Path to Parquet dataset (default: {PARQUET_PATH})"
    )

    parser.add_argument(
        "--query",
        choices=["effectiveness", "trends", "top-filters", "quality", "anomalies", "all"],
        default="all",
        help="Query type to run (default: all)"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days to analyze (default: 90)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Export results to CSV file"
    )

    args = parser.parse_args()

    # Validate Parquet path
    if not args.parquet_path.exists():
        print(f"❌ Parquet dataset not found: {args.parquet_path}")
        print(f"   Run: python scripts/export_filters_to_parquet.py")
        sys.exit(1)

    print(f"🔍 Querying filter history from: {args.parquet_path}")
    print(f"   Analysis period: Last {args.days} days")

    # Execute queries
    queries = {
        "effectiveness": (
            "Query 1: Filter Effectiveness (Last 90 Days)",
            lambda: query_filter_effectiveness(args.parquet_path, args.days)
        ),
        "trends": (
            "Query 2: Filter Trends Over Time (Weekly Aggregation)",
            lambda: query_trends_over_time(args.parquet_path, args.days)
        ),
        "top-filters": (
            "Query 3: Top 5 Filters per Source",
            lambda: query_top_filters_by_source(args.parquet_path, args.days)
        ),
        "quality": (
            "Query 4: Quality Pass Rate Correlation",
            lambda: query_quality_correlation(args.parquet_path)
        ),
        "anomalies": (
            "Query 5: Anomaly Detection (Filter Rate Deviations)",
            lambda: query_anomaly_detection(args.parquet_path)
        )
    }

    # Run selected query or all queries
    if args.query == "all":
        for query_name, (title, query_func) in queries.items():
            try:
                df = query_func()
                output = args.output.with_stem(f"{args.output.stem}_{query_name}") if args.output else None
                print_query_result(title, df, output)
            except Exception as e:
                print(f"\n❌ Error running {query_name}: {e}")
    else:
        title, query_func = queries[args.query]
        try:
            df = query_func()
            print_query_result(title, df, args.output)
        except Exception as e:
            print(f"\n❌ Error running query: {e}")
            sys.exit(1)

    print(f"\n{'=' * 80}")
    print("  Query execution complete!")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
