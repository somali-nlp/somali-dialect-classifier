#!/usr/bin/env bash
# Reproduce Phase 1 data curation at sample scale (100 Wikipedia articles).
# Usage:  bash scripts/reproduce_phase1.sh
# Requirements: Python >=3.9 with somali-dialect-classifier installed

set -euo pipefail

PASS=0
FAIL=0

check() { local label="$1"; local ok="$2"
  if [ "$ok" = "0" ]; then printf "  PASS  %s\n" "$label"; PASS=$((PASS+1))
  else printf "  FAIL  %s\n" "$label"; FAIL=$((FAIL+1)); fi
}

echo "==============================="
echo " Somali Dialect Classifier"
echo " Phase 1 Reproducibility Check"
echo "==============================="

# 1 — Python version
PY_VER=$(python --version 2>&1 | awk '{print $2}')
MAJOR=$(echo "$PY_VER" | cut -d. -f1)
MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
  check "Python >= 3.9 (found $PY_VER)" 0
else
  check "Python >= 3.9 (found $PY_VER)" 1
fi

# 2 — Package installed
python -c "import somali_dialect_classifier" 2>/dev/null
check "somali_dialect_classifier importable" $?

# 3 — Core CLI entry points present
command -v wikisom-download >/dev/null 2>&1
check "wikisom-download CLI available" $?

# 4 — Run Wikipedia pipeline at sample scale
echo
echo "Running wikipedia pipeline (--max-articles 100) ..."
wikisom-download --max-articles 100 2>&1 | tail -5 || true

SILVER_DIR="data/processed/silver"
SILVER_FILES=$(find "$SILVER_DIR" -name "*_silver_part-*.parquet" 2>/dev/null | wc -l | tr -d ' ')
if [ "$SILVER_FILES" -gt 0 ]; then
  check "Silver Parquet files written ($SILVER_FILES files found)" 0
else
  check "Silver Parquet files written (none found in $SILVER_DIR)" 1
fi

# 5 — Validate silver schema
python - <<'PYEOF'
import sys, pathlib
silver_dir = pathlib.Path("data/processed/silver")
files = list(silver_dir.glob("**/*_silver_part-*.parquet"))
if not files:
    sys.exit(0)   # no files = earlier check caught it
import pyarrow.parquet as pq
t = pq.read_table(str(files[0]))
required = {"id", "text", "source", "tokens", "register"}
missing = required - set(t.schema.names)
sys.exit(1 if missing else 0)
PYEOF
check "Silver schema contains required columns" $?

echo
echo "==============================="
printf "Result: %d passed, %d failed\n" "$PASS" "$FAIL"
echo "==============================="
[ "$FAIL" -eq 0 ]
