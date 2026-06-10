"""
End-to-end silver verification script.
Confirms fix correctness for:
  Fix 1 — Wikipedia + HF cleaner outputs (pipe-cell, category, HTML entity, table block residue)
  Fix 2 — TikTok title synthesis (@handle(video) pattern, title != text)
  Fix 3 — HF MIME pre-screen (mime-rejected records caught, none in silver)
"""

import json
import re
import sys
import glob
import time
from pathlib import Path

import pyarrow.parquet as pq
import pyarrow as pa

PROJECT_ROOT = Path("/Users/ilyas/Desktop/Computer Programming/somali-nlp-projects/somali-dialect-classifier")
SILVER_ROOT = PROJECT_ROOT / "data/processed/silver"
METRICS_ROOT = PROJECT_ROOT / "data/metrics"

report_lines = []

def rpt(*args, **kwargs):
    line = " ".join(str(a) for a in args)
    print(line, **kwargs)
    report_lines.append(line)

def section(title):
    rpt()
    rpt("=" * 70)
    rpt(title)
    rpt("=" * 70)

def subsection(title):
    rpt()
    rpt("-" * 50)
    rpt(title)
    rpt("-" * 50)


# ─── Load all silver tables ────────────────────────────────────────────────
section("SILVER DATASET INVENTORY")

source_tables = {}
for source_dir in sorted(SILVER_ROOT.glob("source=*")):
    source_name = source_dir.name.replace("source=", "")
    parquet_files = list(source_dir.rglob("*.parquet"))
    if not parquet_files:
        rpt(f"  {source_name}: NO PARQUET FILES FOUND")
        continue
    # Read individual files using ParquetFile to bypass schema inference issues
    tables = []
    for pf in parquet_files:
        pfile = pq.ParquetFile(str(pf))
        t = pfile.read()
        # Cast dictionary columns to plain strings
        new_cols = {}
        for col_name in t.schema.names:
            col = t.column(col_name)
            if pa.types.is_dictionary(col.type):
                col = col.cast(pa.string())
            new_cols[col_name] = col
        t = pa.table(new_cols)
        tables.append(t)
    if len(tables) == 1:
        table = tables[0]
    else:
        table = pa.concat_tables(tables, promote_options="default")
    source_tables[source_name] = table
    rpt(f"  {source_name}: {table.num_rows} rows, {len(table.schema)} columns")

rpt()
rpt(f"Total silver rows (all sources): {sum(t.num_rows for t in source_tables.values())}")


# ─── Schema dump ──────────────────────────────────────────────────────────
section("SCHEMA (first source as reference)")
if source_tables:
    first_name = next(iter(source_tables))
    rpt(str(source_tables[first_name].schema))


# ─── 10-row samples per source ────────────────────────────────────────────
section("10-ROW SAMPLES (title, source, source_type, language, tokens, text[:200])")
for source_name, table in source_tables.items():
    subsection(f"Source: {source_name}")
    df = table.to_pandas()
    sample = df.head(10)
    cols = ["title", "source", "source_type", "language", "tokens"]
    for i, row in sample.iterrows():
        rpt(f"  [{i}] title     : {str(row.get('title',''))[:80]}")
        rpt(f"       source    : {row.get('source','')}")
        rpt(f"       src_type  : {row.get('source_type','')}")
        rpt(f"       language  : {row.get('language','')}")
        rpt(f"       tokens    : {row.get('tokens','')}")
        rpt(f"       text[:200]: {str(row.get('text',''))[:200]}")
        rpt()


# ─── FIX 1: Wikipedia + HF cleaner output checks ─────────────────────────
section("FIX 1 — CLEANER OUTPUT CHECKS (Wikipedia + HuggingFace)")

PIPE_CELL_RE   = re.compile(r"^\s*\|", re.MULTILINE)
CATEGORY_RE    = re.compile(r"\bCategory[A-Za-z]")
HTML_ENTITY_RE = re.compile(r"&(?:lt|gt|amp|quot|nbsp);")
TABLE_OPEN_RE  = re.compile(r"\{\|")
TABLE_CLOSE_RE = re.compile(r"\|\}")

for source_name in ["wikipedia-somali", "huggingface-somali_c4-so"]:
    if source_name not in source_tables:
        rpt(f"  {source_name}: NOT FOUND - skipping")
        continue
    subsection(f"Fix 1 checks — {source_name}")
    df = source_tables[source_name].to_pandas()
    n = len(df)

    pipe_hits   = df[df['text'].apply(lambda t: bool(PIPE_CELL_RE.search(str(t))))]
    cat_hits    = df[df['text'].apply(lambda t: bool(CATEGORY_RE.search(str(t))))]
    entity_hits = df[df['text'].apply(lambda t: bool(HTML_ENTITY_RE.search(str(t))))]
    topen_hits  = df[df['text'].apply(lambda t: bool(TABLE_OPEN_RE.search(str(t))))]
    tclose_hits = df[df['text'].apply(lambda t: bool(TABLE_CLOSE_RE.search(str(t))))]

    rpt(f"  Total rows          : {n}")
    rpt(f"  Pipe-cell residue   : {len(pipe_hits)} ({100*len(pipe_hits)/n:.1f}%)  [PASS if 0 or near-zero]")
    rpt(f"  Category residue    : {len(cat_hits)} ({100*len(cat_hits)/n:.1f}%)  [judge hits below]")
    rpt(f"  HTML entity leak    : {len(entity_hits)} ({100*len(entity_hits)/n:.1f}%)  [PASS if 0]")
    rpt(f"  Table open {{|       : {len(topen_hits)} ({100*len(topen_hits)/n:.1f}%)  [PASS if 0]")
    rpt(f"  Table close |}}      : {len(tclose_hits)} ({100*len(tclose_hits)/n:.1f}%)  [PASS if 0]")

    # Stop-and-report: pipe_cell > 5%
    if len(pipe_hits) / n > 0.05:
        rpt(f"  *** REGRESSION: pipe-cell rate {100*len(pipe_hits)/n:.1f}% > 5% threshold ***")

    # Samples for non-zero categories
    for label, hits in [
        ("Pipe-cell",    pipe_hits),
        ("Category",     cat_hits),
        ("HTML entity",  entity_hits),
        ("Table open",   topen_hits),
        ("Table close",  tclose_hits),
    ]:
        if len(hits) > 0:
            rpt(f"\n  --- {label} samples (up to 3) ---")
            for _, row in hits.head(3).iterrows():
                rpt(f"    id   : {row.get('id','')[:16]}...")
                rpt(f"    title: {str(row.get('title',''))[:80]}")
                rpt(f"    text : {str(row.get('text',''))[:300]}")
                rpt()


# ─── FIX 2: TikTok title synthesis ────────────────────────────────────────
section("FIX 2 — TIKTOK TITLE SYNTHESIS")

if "tiktok-somali" not in source_tables:
    rpt("  tiktok-somali: NOT FOUND - skipping Fix 2")
else:
    df = source_tables["tiktok-somali"].to_pandas()
    n = len(df)
    rpt(f"  Total TikTok silver rows: {n}")

    # title == text (must be 0)
    title_eq_text = df[df['title'] == df['text']]
    rpt(f"  title == text count     : {len(title_eq_text)}  [PASS if 0]")
    if len(title_eq_text) > 0:
        rpt("  *** REGRESSION: title == text found ***")
        for _, row in title_eq_text.head(3).iterrows():
            rpt(f"    title/text: {str(row.get('title',''))[:120]}")

    # title matches @handle(video) pattern
    HANDLE_RE = re.compile(r"^@.+\(.+\)$")
    handle_matches = df[df['title'].apply(lambda t: bool(HANDLE_RE.match(str(t))))]
    rpt(f"  @handle(video) matches  : {len(handle_matches)} / {n}  [should equal total]")
    if len(handle_matches) < n:
        rpt(f"  *** WARNING: {n - len(handle_matches)} rows do NOT match @handle(video) pattern ***")

    # 10 sample (title, text[:80]) pairs
    subsection("10 sample (title, text[:80]) pairs")
    for i, (_, row) in enumerate(df.head(10).iterrows()):
        rpt(f"  [{i}] title: {str(row.get('title',''))[:100]}")
        rpt(f"       text : {str(row.get('text',''))[:80]}")
        rpt()

    # 3 sample source_metadata JSON values
    subsection("3 sample source_metadata (pretty-printed)")
    for i, (_, row) in enumerate(df.head(3).iterrows()):
        raw_meta = row.get('source_metadata', '{}')
        try:
            meta = json.loads(raw_meta)
        except Exception:
            meta = {"raw": str(raw_meta)}
        rpt(f"  [{i}] " + json.dumps(meta, indent=4, ensure_ascii=False))
        rpt()


# ─── FIX 3: HF MIME pre-screen ────────────────────────────────────────────
section("FIX 3 — HF MIME PRE-SCREEN")

# Find HF processing metrics file
hf_proc_files = list(METRICS_ROOT.glob("*huggingface*_processing.json"))
if not hf_proc_files:
    rpt("  No HF processing metrics file found.")
else:
    for mf in hf_proc_files:
        rpt(f"  Metrics file: {mf.name}")
        data = json.loads(mf.read_text())
        rpt(f"  Full metrics keys: {list(data.keys())}")

        # Look for langid_filter counters and mime
        total_processed = data.get("total_processed", data.get("records_processed", "N/A"))
        total_rejected  = data.get("total_rejected",  data.get("records_filtered",  "N/A"))
        rpt(f"  total_processed : {total_processed}")
        rpt(f"  total_rejected  : {total_rejected}")

        # Drill into filter stats
        filter_stats = data.get("filter_stats", data.get("filters", {}))
        rpt(f"  filter_stats    : {json.dumps(filter_stats, indent=4)}")

        # Count mime detections in silver source_metadata
        if "huggingface-somali_c4-so" in source_tables:
            df_hf = source_tables["huggingface-somali_c4-so"].to_pandas()
            mime_in_silver = 0
            for _, row in df_hf.iterrows():
                try:
                    meta = json.loads(row.get('source_metadata', '{}'))
                    if meta.get('detected_lang') == 'mime':
                        mime_in_silver += 1
                except Exception:
                    pass
            rpt(f"  detected_lang=='mime' in silver HF: {mime_in_silver}  [PASS if 0]")
            if mime_in_silver > 0:
                rpt("  *** REGRESSION: mime records leaked into silver ***")

# Check staging for rejected mime records
hf_staging = list(Path(PROJECT_ROOT / "data/staging").rglob("*huggingface*staging*.jsonl"))
rpt()
rpt(f"  HF staging JSONL files: {[f.name for f in hf_staging]}")
if hf_staging:
    # We can't tell which were rejected vs kept from staging alone, but we can look for mime in raw
    hf_raw = list(Path(PROJECT_ROOT / "data/raw").rglob("*huggingface*.jsonl"))
    rpt(f"  HF raw JSONL files: {[f.name for f in hf_raw]}")
    if hf_raw:
        mime_raw_samples = []
        for rf in hf_raw:
            with open(rf) as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                        text = rec.get("text", rec.get("content", ""))
                        # MIME records are typically binary content or content with no Somali chars
                        if text and all(ord(c) < 128 for c in text[:100]) and len(text) > 20:
                            mime_raw_samples.append(text)
                            if len(mime_raw_samples) >= 3:
                                break
                    except Exception:
                        pass
        if mime_raw_samples:
            rpt("  Raw records with ASCII-only content (likely MIME-screened candidates):")
            for i, s in enumerate(mime_raw_samples[:3]):
                rpt(f"    [{i}] {s[:200]}")


# ─── ALL-SOURCE ROLLUP ────────────────────────────────────────────────────
section("ALL-SOURCE ROLLUP")

subsection("Silver row counts by source")
total = 0
for source_name, table in source_tables.items():
    rpt(f"  {source_name:40s}: {table.num_rows:6d} rows")
    total += table.num_rows
rpt(f"  {'TOTAL':40s}: {total:6d} rows")

subsection("Processing metrics by source")
for mf in sorted(METRICS_ROOT.glob("*_processing.json")):
    data = json.loads(mf.read_text())
    processed = data.get("total_processed", data.get("records_processed", "?"))
    rejected  = data.get("total_rejected",  data.get("records_filtered", "?"))
    rpt(f"  {mf.name[:60]:60s}  processed={processed}  rejected={rejected}")

subsection("Rejection counts by filter name (all sources)")
filter_totals = {}
for mf in sorted(METRICS_ROOT.glob("*_processing.json")):
    data = json.loads(mf.read_text())
    # Try multiple key patterns the pipeline may use
    for key in ("filter_stats", "filters", "filter_counts", "filter_rejections"):
        fs = data.get(key, {})
        if isinstance(fs, dict):
            for fname, count in fs.items():
                if isinstance(count, (int, float)):
                    filter_totals[fname] = filter_totals.get(fname, 0) + int(count)
                elif isinstance(count, dict):
                    # nested: {filter_name: {rejected: N, ...}}
                    rejected_val = count.get("rejected", count.get("filtered", count.get("count", 0)))
                    if isinstance(rejected_val, (int, float)):
                        filter_totals[fname] = filter_totals.get(fname, 0) + int(rejected_val)

for fname, count in sorted(filter_totals.items(), key=lambda x: -x[1]):
    rpt(f"  {fname:45s}: {count:6d}")

subsection("Runtime summary (from metrics files)")
for mf in sorted(METRICS_ROOT.glob("*_processing.json")):
    data = json.loads(mf.read_text())
    duration = data.get("duration_seconds", data.get("runtime_seconds", data.get("elapsed_seconds", "?")))
    rpt(f"  {mf.name[:60]:60s}  duration={duration}s")


# ─── Write report ─────────────────────────────────────────────────────────
section("VERIFICATION COMPLETE")
rpt(f"Run timestamp: 2026-05-29")
rpt(f"Sources verified: {list(source_tables.keys())}")

report_path = PROJECT_ROOT / "reports/audit/silver_e2e_verification_20260529.md"
report_path.parent.mkdir(parents=True, exist_ok=True)
with open(report_path, "w") as f:
    f.write("# Silver E2E Verification — 2026-05-29\n\n")
    f.write("```\n")
    f.write("\n".join(report_lines))
    f.write("\n```\n")

rpt(f"\nFull report written to: {report_path}")
