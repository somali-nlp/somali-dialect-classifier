#!/bin/bash
# Local Development Runner
# Makes it easy to run pipelines locally with SQLite instead of PostgreSQL

set -e  # Exit on error

# Load local environment variables
export SDC_LEDGER_BACKEND=sqlite
export SDC_LEDGER_SQLITE_PATH=data/ledger/crawl_ledger.db
export ENV=development
export LOG_LEVEL=INFO

# Load additional variables from .env.local if it exists
if [ -f .env.local ]; then
    echo "Loading environment from .env.local..."
    set -a  # Export all variables
    source .env.local
    set +a
fi

echo "================================================"
echo "Running locally with SQLite backend"
echo "Ledger: $SDC_LEDGER_SQLITE_PATH"
echo "Environment: $ENV"
echo "================================================"
echo ""

# Run the command passed as arguments
# Usage: ./run-local.sh python -m somali_dialect_classifier.orchestration.flows --pipeline wikipedia
exec "$@"
