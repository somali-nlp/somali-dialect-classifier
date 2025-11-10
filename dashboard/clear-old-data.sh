#!/bin/bash
# Clear old dashboard data files
# Use this to reset the dashboard when you want to remove old cached data

set -e

echo "============================================================"
echo "Dashboard Data Cleanup"
echo "============================================================"
echo ""

# Parse command line arguments
CLEAR_METRICS=false
CUTOFF_DATE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --clear-metrics)
            CLEAR_METRICS=true
            shift
            ;;
        --before)
            CUTOFF_DATE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--clear-metrics] [--before YYYY-MM-DD]"
            echo "  --clear-metrics: Also remove source metric files from data/metrics/"
            echo "  --before DATE: Only remove files before this date (format: YYYY-MM-DD)"
            exit 1
            ;;
    esac
done

# Remove cached JSON files from dashboard/data (except config files)
DATA_DIR="dashboard/data"
if [ -d "$DATA_DIR" ]; then
    echo "Removing old data files from $DATA_DIR..."
    rm -f "$DATA_DIR/all_metrics.json"
    rm -f "$DATA_DIR/pipeline_run_history.json"
    rm -f "$DATA_DIR/pipeline_alerts.json"
    rm -f "$DATA_DIR/pipeline_observations.json"
    rm -f "$DATA_DIR/cache_summary.json"
    echo "✓ Cleared dashboard/data files"
fi

# Remove cached JSON files from _site/data (except config files)
SITE_DATA_DIR="dashboard/_site/data"
if [ -d "$SITE_DATA_DIR" ]; then
    echo "Removing old data files from $SITE_DATA_DIR..."
    rm -f "$SITE_DATA_DIR/all_metrics.json"
    rm -f "$SITE_DATA_DIR/pipeline_run_history.json"
    rm -f "$SITE_DATA_DIR/pipeline_alerts.json"
    rm -f "$SITE_DATA_DIR/pipeline_observations.json"
    rm -f "$SITE_DATA_DIR/cache_summary.json"
    rm -f "$SITE_DATA_DIR/sankey_flow.json"
    rm -f "$SITE_DATA_DIR/text_distributions.json"
    rm -f "$SITE_DATA_DIR/comparison_metadata.json"
    echo "✓ Cleared _site/data files"
fi

# Optionally clear source metric files
if [ "$CLEAR_METRICS" = true ]; then
    METRICS_DIR="data/metrics"
    if [ -d "$METRICS_DIR" ]; then
        echo ""
        echo "Clearing source metric files from $METRICS_DIR..."

        if [ -n "$CUTOFF_DATE" ]; then
            # Convert date to format used in filenames (YYYYMMDD)
            CUTOFF_PREFIX=$(echo "$CUTOFF_DATE" | tr -d '-')
            echo "Removing metrics before date: $CUTOFF_DATE (prefix: $CUTOFF_PREFIX)"

            # Count files before deletion
            COUNT=$(find "$METRICS_DIR" -name "*.json" -type f | wc -l | tr -d ' ')
            echo "Found $COUNT metric files"

            # Delete files with dates before cutoff
            find "$METRICS_DIR" -name "*.json" -type f | while read file; do
                filename=$(basename "$file")
                # Extract date from filename (format: YYYYMMDD_HHMMSS_...)
                file_date_prefix="${filename:0:8}"

                if [ "$file_date_prefix" \< "$CUTOFF_PREFIX" ]; then
                    echo "  Removing: $filename (date: $file_date_prefix)"
                    rm -f "$file"
                fi
            done

            REMAINING=$(find "$METRICS_DIR" -name "*.json" -type f | wc -l | tr -d ' ')
            DELETED=$((COUNT - REMAINING))
            echo "✓ Removed $DELETED metric files, $REMAINING remaining"
        else
            # Remove all metric files
            COUNT=$(find "$METRICS_DIR" -name "*.json" -type f | wc -l | tr -d ' ')
            rm -f "$METRICS_DIR"/*.json
            echo "✓ Removed all $COUNT metric files"
        fi
    else
        echo "⚠ Warning: $METRICS_DIR not found"
    fi
fi

echo ""
echo "============================================================"
echo "✓ Dashboard data cleanup complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Run your data pipeline to generate new metrics"
echo "2. Run 'bash dashboard/build-site.sh' to rebuild the site"
echo "3. Clear your browser cache:"
echo "   - Chrome/Safari: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)"
echo "   - Or open DevTools > Application > Clear storage"
echo "4. If using GitHub Pages, commit and push to deploy"
echo ""
