#!/bin/bash
# Build script for generating the static GitHub Pages site
# This replaces the inline heredoc in the GitHub Action workflow

set -e

echo "Building static site..."

# Create _site directory
mkdir -p _site

# Copy the enhanced template
cp dashboard/templates/index.html _site/index.html

# Copy data files
mkdir -p _site/data
if [ -f "data/all_metrics.json" ]; then
    cp data/all_metrics.json _site/data/
    echo "✓ Copied all_metrics.json"
else
    echo "⚠ Warning: all_metrics.json not found"
fi

if [ -f "data/summary.json" ]; then
    cp data/summary.json _site/data/
    echo "✓ Copied summary.json"
fi

# Copy favicon
if [ -f "dashboard/favicon.svg" ]; then
    cp dashboard/favicon.svg _site/favicon.svg
    echo "✓ Copied favicon"
elif [ -f "data/favicon.svg" ]; then
    cp data/favicon.svg _site/favicon.svg
    echo "✓ Copied favicon from data/"
fi

# Copy any metric files
if [ -d "data/metrics" ]; then
    cp -r data/metrics _site/data/ 2>/dev/null || true
fi

if [ -d "data/reports" ]; then
    cp -r data/reports _site/data/ 2>/dev/null || true
fi

echo "✓ Site built successfully in _site/"
ls -lh _site/
