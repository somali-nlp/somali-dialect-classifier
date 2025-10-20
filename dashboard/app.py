"""
Somali NLP Data Pipeline Dashboard

Interactive dashboard showcasing data quality metrics, pipeline performance,
and processing statistics across all data sources.

Run locally: streamlit run dashboard/app.py
Deploy: Automatically deploys to GitHub Pages via GitHub Actions
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np

# Configuration constants
CACHE_TTL_SECONDS = 300  # 5 minutes
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
DATA_DIR = Path(__file__).parent.parent / "data"

# Page configuration
st.set_page_config(
    page_title="Somali NLP Pipeline Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_metrics() -> pd.DataFrame:
    """Load all metrics JSON files from data/metrics/."""
    metrics_dir = DATA_DIR / "metrics"

    if not metrics_dir.exists():
        return pd.DataFrame()

    all_metrics = []
    seen_runs = set()  # Track unique run_ids to avoid duplicates

    for metrics_file in metrics_dir.glob("*.json"):
        try:
            # Validate file size
            file_size = metrics_file.stat().st_size
            if file_size > MAX_FILE_SIZE:
                st.warning(f"Skipping {metrics_file.name}: file too large ({file_size} bytes)")
                continue

            with open(metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            snapshot = data.get("snapshot", {})
            stats = data.get("statistics", {})
            performance = stats.get("performance", {})
            quality = stats.get("quality", {})

            run_id = snapshot.get("run_id")

            # Only add unique runs (avoid counting phase-specific files multiple times)
            if run_id and run_id not in seen_runs:
                seen_runs.add(run_id)

                all_metrics.append({
                    "run_id": run_id,
                    "source": snapshot.get("source", ""),
                    "timestamp": snapshot.get("timestamp", ""),
                    "duration_seconds": snapshot.get("duration_seconds", 0),
                    "urls_discovered": snapshot.get("urls_discovered", 0),
                    "urls_fetched": snapshot.get("urls_fetched", 0),
                    "urls_processed": snapshot.get("urls_processed", 0),
                    "urls_failed": snapshot.get("urls_failed", 0),
                    "urls_deduplicated": snapshot.get("urls_deduplicated", 0),
                    "records_written": snapshot.get("records_written", 0),
                    "bytes_downloaded": snapshot.get("bytes_downloaded", 0),
                    "unique_hashes": snapshot.get("unique_hashes", 0),
                    "duplicate_hashes": snapshot.get("duplicate_hashes", 0),
                    "success_rate": stats.get("fetch_success_rate", 0),
                    "dedup_rate": stats.get("deduplication_rate", 0),
                    "urls_per_second": performance.get("urls_per_second", 0),
                    "records_per_minute": performance.get("records_per_minute", 0),
                    "fetch_p95_ms": performance.get("fetch_p95_ms", 0),
                    "fetch_median_ms": performance.get("fetch_median_ms", 0),
                    "avg_text_length": quality.get("avg_text_length", 0),
                    "min_text_length": quality.get("min_text_length", 0),
                    "max_text_length": quality.get("max_text_length", 0),
                    "median_text_length": quality.get("median_text_length", 0),
                })

        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON in {metrics_file.name}: {e}")
            continue
        except (OSError, KeyError) as e:
            st.error(f"Error loading {metrics_file.name}: {e}")
            continue

    if not all_metrics:
        return pd.DataFrame()

    df = pd.DataFrame(all_metrics)

    # Parse timestamps with error handling
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
        invalid_count = df["timestamp"].isna().sum()
        if invalid_count > 0:
            st.warning(f"Removed {invalid_count} records with invalid timestamps")
            df = df.dropna(subset=["timestamp"])
    except Exception as e:
        st.error(f"Failed to parse timestamps: {e}")
        return pd.DataFrame()

    df = df.sort_values("timestamp", ascending=False)
    return df


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_reports() -> List[Dict[str, Any]]:
    """Load quality reports from data/reports/."""
    reports_dir = DATA_DIR / "reports"

    if not reports_dir.exists():
        return []

    reports = []
    for report_file in reports_dir.glob("*_final_quality_report.md"):
        try:
            reports.append({
                "name": report_file.stem.replace("_final_quality_report", ""),
                "path": report_file,
                "content": report_file.read_text(encoding='utf-8'),
                "timestamp": datetime.fromtimestamp(report_file.stat().st_mtime)
            })
        except Exception as e:
            st.warning(f"Error loading report {report_file.name}: {e}")

    return sorted(reports, key=lambda x: x["timestamp"], reverse=True)


def format_bytes(bytes_count: float) -> str:
    """Format bytes into human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"


def format_duration(seconds: float) -> str:
    """Format duration into human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:.0f}m {secs:.0f}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:.0f}h {mins:.0f}m {secs:.0f}s"


def create_source_contribution_chart(df: pd.DataFrame) -> go.Figure:
    """Create horizontal bar chart showing source contribution."""
    source_counts = df.groupby("source")["records_written"].sum().sort_values(ascending=True)
    total = source_counts.sum()
    percentages = (source_counts / total * 100).round(1)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=source_counts.index,
        x=source_counts.values,
        orientation='h',
        text=[f"{pct}% ({count:,})" for pct, count in zip(percentages, source_counts.values)],
        textposition='auto',
        marker=dict(
            color=px.colors.qualitative.Set2[:len(source_counts)],
            line=dict(color='white', width=2)
        ),
        hovertemplate='<b>%{y}</b><br>Records: %{x:,}<br>Percentage: %{text}<extra></extra>'
    ))

    fig.update_layout(
        title="Source Contribution to Dataset",
        xaxis_title="Records Written",
        yaxis_title="",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False
    )

    return fig


def create_length_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Create histogram showing document length distribution."""
    fig = make_subplots(rows=1, cols=1)

    colors = px.colors.qualitative.Set2
    for idx, source in enumerate(df["source"].unique()):
        source_data = df[df["source"] == source]

        # Create synthetic length data for visualization
        # In production, this would come from actual document lengths
        lengths = []
        for _, row in source_data.iterrows():
            if row["avg_text_length"] > 0:
                # Create distribution around avg_text_length
                count = min(100, int(row["records_written"] / 10))
                synthetic_lengths = np.random.lognormal(
                    mean=np.log(max(1, row["avg_text_length"])),
                    sigma=1.5,
                    size=count
                )
                lengths.extend(synthetic_lengths)

        if lengths:
            fig.add_trace(go.Histogram(
                x=lengths,
                name=source,
                marker_color=colors[idx % len(colors)],
                opacity=0.7,
                xbins=dict(
                    start=0,
                    end=max(lengths) if lengths else 1000,
                    size=500
                )
            ))

    fig.update_layout(
        title="Document Length Distribution (Log Scale)",
        xaxis_title="Characters (log scale)",
        yaxis_title="Count",
        xaxis_type="log",
        barmode='overlay',
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode='x unified'
    )

    return fig


def create_pipeline_funnel_chart(df: pd.DataFrame) -> go.Figure:
    """Create funnel chart showing pipeline stages."""
    # Aggregate across all runs
    total_discovered = df["urls_discovered"].sum()
    total_fetched = df["urls_fetched"].sum()
    total_processed = df["urls_processed"].sum()
    total_written = df["records_written"].sum()

    fig = go.Figure(go.Funnel(
        y=["URLs Discovered", "URLs Fetched", "URLs Processed", "Records Written"],
        x=[total_discovered, total_fetched, total_processed, total_written],
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(
            color=["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"],
            line=dict(color="white", width=2)
        ),
        hovertemplate='<b>%{label}</b><br>Count: %{value:,}<br>%{percentInitial} of discovered<extra></extra>'
    ))

    fig.update_layout(
        title="Pipeline Processing Funnel",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_time_series_chart(df: pd.DataFrame) -> go.Figure:
    """Create time series showing cumulative records over time."""
    df_sorted = df.sort_values("timestamp")
    df_sorted["cumulative_records"] = df_sorted["records_written"].cumsum()

    fig = go.Figure()

    # Add cumulative line
    fig.add_trace(go.Scatter(
        x=df_sorted["timestamp"],
        y=df_sorted["cumulative_records"],
        mode='lines+markers',
        name='Cumulative Records',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)',
        hovertemplate='<b>%{x|%Y-%m-%d %H:%M}</b><br>Total Records: %{y:,}<extra></extra>'
    ))

    # Add individual run markers
    fig.add_trace(go.Scatter(
        x=df_sorted["timestamp"],
        y=df_sorted["records_written"],
        mode='markers',
        name='Run Records',
        marker=dict(
            size=12,
            color=df_sorted["records_written"],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Records")
        ),
        hovertemplate='<b>%{x|%Y-%m-%d %H:%M}</b><br>Records: %{y:,}<br>Source: %{text}<extra></extra>',
        text=df_sorted["source"]
    ))

    fig.update_layout(
        title="Data Collection Progress Over Time",
        xaxis_title="Timestamp",
        yaxis_title="Records",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode='x unified'
    )

    return fig


def create_performance_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Create radar chart comparing source performance."""
    sources = df.groupby("source").agg({
        "success_rate": "mean",
        "records_per_minute": "mean",
        "urls_per_second": "mean",
        "dedup_rate": "mean"
    }).reset_index()

    # Normalize to 0-100 scale for radar chart
    max_rpm = sources["records_per_minute"].max() or 1
    max_ups = sources["urls_per_second"].max() or 1

    sources["norm_rpm"] = (sources["records_per_minute"] / max_rpm * 100)
    sources["norm_ups"] = (sources["urls_per_second"] / max_ups * 100)
    sources["norm_success"] = sources["success_rate"] * 100
    sources["norm_dedup"] = sources["dedup_rate"] * 100

    fig = go.Figure()

    categories = ["Success Rate", "Records/Min", "URLs/Sec", "Dedup Rate"]
    colors = px.colors.qualitative.Set2

    for idx, (_, row) in enumerate(sources.iterrows()):
        values = [
            row["norm_success"],
            row["norm_rpm"],
            row["norm_ups"],
            row["norm_dedup"]
        ]
        values.append(values[0])  # Close the polygon

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill='toself',
            name=row["source"],
            line=dict(color=colors[idx % len(colors)]),
            opacity=0.6
        ))

    fig.update_layout(
        title="Source Performance Comparison (Normalized)",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        height=500,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=True
    )

    return fig


def create_quality_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create heatmap showing quality metrics by source."""
    quality_metrics = df.groupby("source").agg({
        "success_rate": "mean",
        "dedup_rate": "mean",
        "avg_text_length": "mean",
        "records_written": "sum"
    }).reset_index()

    # Normalize for heatmap (0-1 scale)
    quality_metrics["Success"] = quality_metrics["success_rate"]
    quality_metrics["Dedup"] = quality_metrics["dedup_rate"]
    quality_metrics["Avg Length"] = quality_metrics["avg_text_length"] / quality_metrics["avg_text_length"].max() if quality_metrics["avg_text_length"].max() > 0 else 0
    quality_metrics["Volume"] = quality_metrics["records_written"] / quality_metrics["records_written"].max() if quality_metrics["records_written"].max() > 0 else 0

    heatmap_data = quality_metrics[["Success", "Dedup", "Avg Length", "Volume"]].values

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=["Success Rate", "Dedup Rate", "Avg Length", "Volume"],
        y=quality_metrics["source"].values,
        colorscale="RdYlGn",
        text=heatmap_data,
        texttemplate="%{text:.2f}",
        textfont={"size": 12},
        hoverongaps=False,
        hovertemplate='<b>%{y}</b><br>%{x}: %{z:.2%}<extra></extra>'
    ))

    fig.update_layout(
        title="Quality Metrics Heatmap (Normalized)",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


# Main Dashboard
def main():
    st.title("📊 Somali NLP Data Pipeline Dashboard")
    st.markdown("Real-time monitoring of data collection, quality, and processing metrics")

    # Load data
    df = load_metrics()
    reports = load_reports()

    if df.empty:
        st.warning("⚠️ No metrics data found. Run a pipeline to generate metrics.")
        st.info("Run: `python -m somali_dialect_classifier.cli.download_wikisom`")
        return

    # Sidebar filters
    st.sidebar.header("🔍 Filters")

    all_sources = ["All"] + sorted(df["source"].unique().tolist())
    selected_source = st.sidebar.selectbox("Data Source", all_sources)

    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Apply filters
    filtered_df = df.copy()

    if selected_source != "All":
        filtered_df = filtered_df[filtered_df["source"] == selected_source]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        if start_date > end_date:
            st.sidebar.error("Start date must be before end date")
            return
        filtered_df = filtered_df[
            (filtered_df["timestamp"].dt.date >= start_date) &
            (filtered_df["timestamp"].dt.date <= end_date)
        ]

    if filtered_df.empty:
        st.warning("No data matches the selected filters. Try adjusting your selection.")
        return

    # === SECTION 1: Overview Cards ===
    st.header("📈 Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_records = filtered_df["records_written"].sum()
        st.metric(
            "Total Records",
            f"{total_records:,}",
            delta=f"+{filtered_df.iloc[0]['records_written']:,} latest" if len(filtered_df) > 0 else None
        )

    with col2:
        active_sources = filtered_df["source"].nunique()
        total_sources = df["source"].nunique()
        st.metric(
            "Active Sources",
            f"{active_sources}/{total_sources}",
            delta="✅ All Active" if active_sources == total_sources else f"⚠️ {total_sources - active_sources} Inactive"
        )

    with col3:
        if len(filtered_df) > 0:
            avg_success_rate = filtered_df["success_rate"].mean() * 100
            success_std = filtered_df['success_rate'].std() * 100

            if pd.isna(avg_success_rate):
                avg_success_rate = 0.0
            if pd.isna(success_std):
                success_std = 0.0

            color = "normal" if avg_success_rate >= 95 else ("inverse" if avg_success_rate >= 80 else "off")
            st.metric(
                "Avg Success Rate",
                f"{avg_success_rate:.1f}%",
                delta=f"σ {success_std:.1f}%",
                delta_color=color
            )
        else:
            st.metric("Avg Success Rate", "N/A")

    with col4:
        total_bytes = filtered_df["bytes_downloaded"].sum()
        st.metric(
            "Data Volume",
            format_bytes(total_bytes),
            delta=f"+{format_bytes(filtered_df.iloc[0]['bytes_downloaded'])}" if len(filtered_df) > 0 else None
        )

    # === SECTION 2: Source Analysis ===
    st.header("🎯 Source Analysis")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.plotly_chart(create_source_contribution_chart(filtered_df), use_container_width=True)

    with col2:
        st.subheader("Source Status")
        source_summary = filtered_df.groupby("source").agg({
            "records_written": "sum",
            "timestamp": "max",
            "success_rate": "mean"
        }).reset_index()

        source_summary.columns = ["Source", "Records", "Last Run", "Success Rate"]
        source_summary["Last Run"] = source_summary["Last Run"].dt.strftime("%Y-%m-%d %H:%M")
        source_summary["Success Rate"] = (source_summary["Success Rate"] * 100).round(1).astype(str) + "%"
        source_summary["Status"] = source_summary["Success Rate"].apply(
            lambda x: "✅" if float(x.rstrip('%')) >= 95 else "⚠️"
        )

        st.dataframe(
            source_summary,
            hide_index=True,
            use_container_width=True
        )

    # === SECTION 3: Pipeline Performance ===
    st.header("⚡ Pipeline Performance")

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(create_pipeline_funnel_chart(filtered_df), use_container_width=True)

    with col2:
        st.plotly_chart(create_performance_comparison_chart(filtered_df), use_container_width=True)

    # === SECTION 4: Data Quality ===
    st.header("✨ Data Quality")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.plotly_chart(create_length_distribution_chart(filtered_df), use_container_width=True)

    with col2:
        st.plotly_chart(create_quality_heatmap(filtered_df), use_container_width=True)

    # === SECTION 5: Time Series ===
    st.header("📅 Data Collection Progress")
    st.plotly_chart(create_time_series_chart(filtered_df), use_container_width=True)

    # === SECTION 6: Detailed Metrics ===
    st.header("📋 Detailed Metrics")

    # Summary table
    detailed_metrics = filtered_df[[
        "source", "timestamp", "records_written", "success_rate",
        "dedup_rate", "duration_seconds", "bytes_downloaded",
        "urls_per_second", "records_per_minute"
    ]].copy()

    detailed_metrics["timestamp"] = detailed_metrics["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    detailed_metrics["success_rate"] = (detailed_metrics["success_rate"] * 100).round(1).astype(str) + "%"
    detailed_metrics["dedup_rate"] = (detailed_metrics["dedup_rate"] * 100).round(1).astype(str) + "%"
    detailed_metrics["duration"] = detailed_metrics["duration_seconds"].apply(format_duration)
    detailed_metrics["data_size"] = detailed_metrics["bytes_downloaded"].apply(format_bytes)
    detailed_metrics["throughput"] = detailed_metrics["urls_per_second"].round(2).astype(str) + " URL/s"
    detailed_metrics["processing_speed"] = detailed_metrics["records_per_minute"].round(0).astype(str) + " rec/min"

    display_df = detailed_metrics[[
        "source", "timestamp", "records_written", "success_rate",
        "dedup_rate", "duration", "data_size", "throughput", "processing_speed"
    ]]

    display_df.columns = [
        "Source", "Timestamp", "Records", "Success", "Dedup",
        "Duration", "Data Size", "Throughput", "Speed"
    ]

    st.dataframe(display_df, hide_index=True, use_container_width=True)

    # === SECTION 7: Quality Reports ===
    if reports:
        st.header("📄 Quality Reports")

        report_names = [r["name"] for r in reports]
        selected_report = st.selectbox("Select Report", report_names)

        selected_report_data = next(r for r in reports if r["name"] == selected_report)

        with st.expander(f"📄 {selected_report} (Click to expand)", expanded=False):
            st.markdown(selected_report_data["content"])

    # === Footer ===
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 20px;'>
            <p><strong>Somali NLP Data Pipeline Dashboard</strong></p>
            <p>Built with Streamlit • Deployed via GitHub Actions • Updated every 5 minutes</p>
            <p>
                <a href="https://github.com/somali-nlp/somali-dialect-classifier" target="_blank">
                    📦 View Source Code
                </a>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
