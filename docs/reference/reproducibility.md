# ML Reproducibility Checklist

**Project:** Somali Dialect Classifier  
**Phase covered:** Phase 1 — Data Curation (complete)  
**Schema:** Aligned with NeurIPS ML Reproducibility Checklist (2023 edition)  
**Last updated:** 2026-04-20

---

## How to Read This Document

Each item carries a status badge:

| Badge | Meaning |
|-------|---------|
| `✓ Met` | Fully satisfied; pointer to evidence included |
| `◐ Partial` | Partially satisfied; gap described |
| `○ Not yet` | Not yet addressed; target phase noted |
| `N/A` | Not applicable to this project |

---

## 1. Models and Algorithms

> Phase 3 (training) has not started. Items marked `○ Not yet` will be populated once experiments begin. Phase 1 items (pipeline algorithms) are assessed against the current codebase.

| # | Checklist Item | Status | Where / Notes |
|---|---------------|--------|---------------|
| 1.1 | Clear description of the algorithm / model | `◐ Partial` | Pipeline algorithms documented in `docs/guides/data-pipeline.md` and `docs/overview/data-pipeline-architecture.md`. Dialect classifier model architecture (XLM-RoBERTa-base) described in `README.md` §Future Work. Formal model card does not yet exist. |
| 1.2 | Link to code implementing the model | `○ Not yet` | Training code not yet written. Entry point will be `src/somali_dialect_classifier/training/` once Phase 3 begins. |
| 1.3 | All model parameter settings that affect results | `○ Not yet` | Hyperparameter grid to be logged to MLflow (dependency already in `pyproject.toml` `[mlops]` group). Stub in `mlruns/`. |
| 1.4 | Reference to the method (paper, book, etc.) | `◐ Partial` | XLM-RoBERTa cited in `README.md`. Deduplication uses MinHash LSH (Leskovec et al.); not formally cited in code. |
| 1.5 | Number of runs to compute averaged results | `○ Not yet` | Target: ≥3 seeds per experiment (seeds 42, 123, 456). Protocol defined in `governance/evaluation-protocol.md`. |
| 1.6 | Exact hyperparameter values for each run | `○ Not yet` | Will be stored as MLflow run parameters; exported to `mlruns/<experiment_id>/params/`. |

---

## 2. Datasets

| # | Checklist Item | Status | Where / Notes |
|---|---------------|--------|---------------|
| 2.1 | Relevant statistics for each dataset | `◐ Partial` | Per-source record counts tracked in `data/metrics/*_processing.json` and aggregated to `_site/data/all_metrics.json`. Estimated totals: Wikipedia ~50k articles, BBC ~350 articles/day cap, HuggingFace MC4 ~100k–200k docs, Språkbanken 66 corpora, TikTok (paid, volume variable). Global dedup target: 130k–300k unique silver records. Character/token distributions not yet computed. |
| 2.2 | Details of train/dev/test splits | `○ Not yet` | Splits are Phase 2 work. Stratification strategy documented in `governance/evaluation-protocol.md` §Splits. |
| 2.3 | Explanation of any data that was excluded | `✓ Met` | Filter telemetry records every rejection with reason. See `docs/reference/filters.md` and per-run `*_processing.json` metrics. Regression tests in `tests/regression/test_filter_telemetry.py` prevent silent coverage drops. |
| 2.4 | Link to dataset or instructions to create it | `◐ Partial` | Pipeline commands documented in §"How to Reproduce Phase 1 Dataset" below. Raw data not redistributed (license constraints). Wikipedia and HuggingFace MC4 are public; BBC is scraped under fair-use research exemption; TikTok requires paid Apify token. |
| 2.5 | Information about dataset creation (collection, annotation, etc.) | `✓ Met` | Collection methodology in `docs/guides/data-pipeline.md`. Source licenses tracked in silver schema field `license`. No human annotation in Phase 1; dialectal labels are Phase 3 work. |
| 2.6 | Preprocessing steps | `◐ Partial` | Text cleaning pipeline documented in `src/somali_dialect_classifier/quality/text_cleaners.py` docstrings (WikiMarkup → HTML → whitespace normalization). Phase 2 normalization steps (Unicode NFC, diacritic handling) not yet specified. |

---

## 3. Experiments

> Phase 3 experiments have not run. All items below are `○ Not yet` unless a Phase 1 analogue exists.

| # | Checklist Item | Status | Where / Notes |
|---|---------------|--------|---------------|
| 3.1 | Relevant hyperparameters and method to select them | `○ Not yet` | Search strategy (Bayesian via Optuna or grid) TBD. All hyperparameters will be logged to MLflow before training starts (see `governance/evaluation-protocol.md` §Pre-registration). |
| 3.2 | Exact number of training and evaluation runs | `○ Not yet` | Minimum 3 seeds × 4 baselines = 12 runs. Final model: 3 seeds minimum. |
| 3.3 | Clear definition of the evaluation metric | `◐ Partial` | Macro-F1 chosen as primary metric for class-imbalance robustness; rationale in `governance/evaluation-protocol.md` §Primary Metrics. Exact sklearn call (`f1_score(average='macro')`) specified there. |
| 3.4 | Description of results with error bars | `○ Not yet` | 95% bootstrap confidence intervals (n=1000 resamples) required. Reporting template in `governance/evaluation-protocol.md` §Reporting Template. |
| 3.5 | Average runtime and compute used | `○ Not yet` | To be logged per MLflow run: wall-clock seconds, GPU hours, hardware spec. |
| 3.6 | Description of the computing infrastructure | `○ Not yet` | Will be documented in `governance/evaluation-protocol.md §Compute` once hardware is allocated. |

---

## 4. Code

| # | Checklist Item | Status | Where / Notes |
|---|---------------|--------|---------------|
| 4.1 | Specification of dependencies | `✓ Met` | `pyproject.toml` pins all dependencies. Optional groups: `dev`, `config`, `mlops`, `ml`. `pip install -e ".[all]"` installs everything. Python 3.9+ required. |
| 4.2 | Training code | `○ Not yet` | Will live in `src/somali_dialect_classifier/training/`. Entry point `somali-train` to be added to `pyproject.toml` `[scripts]`. |
| 4.3 | Evaluation code | `○ Not yet` | Will live in `src/somali_dialect_classifier/evaluation/`. Protocol in `governance/evaluation-protocol.md`. |
| 4.4 | Pre-trained model weights or link | `○ Not yet` | Phase 3 output. Will be versioned and uploaded to HuggingFace Hub or equivalent. |
| 4.5 | README covering setup, training, and evaluation | `◐ Partial` | `README.md` (446 lines) covers Phase 1 setup and pipeline execution. Phase 2/3 sections are stubs. |

---

## 5. Theoretical Results

| # | Checklist Item | Status | Where / Notes |
|---|---------------|--------|---------------|
| 5.1 | Statement and proof of theoretical results | `N/A` | This project does not present novel theoretical results. Empirical ML work only. |

---

## Known Reproducibility Gaps (Prioritised)

These gaps are blockers for Phase 2 consumption of Phase 1 output. Address before splitting data.

1. **Silver read-back broken (CRITICAL)** — JSON sidecars in Parquet partition directories cause `ArrowInvalid` on `pq.read_table()`. Any downstream consumer of `data/processed/silver/` will fail. See audit finding F-002.
2. **HuggingFace processor bypasses shared contract (CRITICAL)** — Largest single source does not flow through `RecordBuilder` / `ValidationService`. Schema evolution will not apply to HuggingFace records. See audit finding F-001.
3. **Provenance is not end-to-end traceable (HIGH)** — Run IDs diverge across orchestration, processors, metrics JSON, and silver sidecars. Only Wikipedia registers pipeline runs in the ledger. See audit finding F-004.
4. **Character/token distribution statistics not computed** — Required for split stratification and for reporting dataset statistics in any publication.

---

## How to Reproduce Phase 1 Dataset

### Prerequisites

```bash
# Python 3.9 or later required
python --version

# Install with all optional dependencies
git clone https://github.com/somali-nlp/somali-dialect-classifier.git
cd somali-dialect-classifier
pip install -e ".[all]"

# Copy and populate environment file
cp .env.example .env
# Edit .env — set SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN for TikTok source
# All other sources run without API keys
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `SDC_DATA__RAW_DIR` | Bronze layer root | `data/raw/` |
| `SDC_DATA__SILVER_DIR` | Silver Parquet root | `data/processed/silver/` |
| `SDC_SCRAPING__BBC__MAX_ARTICLES` | BBC article cap | `350` |
| `SDC_SCRAPING__HUGGINGFACE__MAX_RECORDS` | HuggingFace record cap | `200000` |
| `SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN` | Required for TikTok | *(no default)* |
| `SDC_LOGGING__LEVEL` | Log verbosity | `INFO` |

### Reproduction Steps

```bash
# Option A: Orchestrated (recommended)
# Runs all sources sequentially; skips TikTok if no Apify token
somali-orchestrate --pipeline all \
  --max-bbc-articles 350 \
  --max-hf-records 200000

# Option B: Individual sources (useful for debugging)
wikisom-download                                   # ~50k articles
bbcsom-download --max-articles 350                 # ~350 articles
hfsom-download mc4 --max-records 200000            # ~100k–200k docs
spraksom-download --corpus all                     # 66 corpora
tiktoksom-download --video-urls data/tiktok_urls.txt  # requires Apify token

# Force full reprocessing (bypasses resume caches)
somali-orchestrate --pipeline all --force
```

### Expected Output Paths

```
data/raw/                          # Bronze: original downloads
  source=Wikipedia-Somali/
  source=BBC-Somali/
  source=HuggingFace-MC4/
  source=Sprakbanken-Somali/
  source=TikTok-Somali/

data/processed/silver/             # Silver: unified Parquet
  source=Wikipedia-Somali/date_accessed=YYYY-MM-DD/
  source=BBC-Somali/date_accessed=YYYY-MM-DD/
  ...

data/metrics/                      # Per-run processing metrics
  *_processing.json

_site/data/all_metrics.json        # Aggregated dashboard metrics
```

### Expected Row Counts (approximate, after deduplication)

| Source | Raw Records | Expected Silver Records |
|--------|------------|------------------------|
| Wikipedia | ~50,000 articles | ~45,000–50,000 |
| BBC Somali | ~1,000–5,000 articles | ~900–4,500 |
| HuggingFace MC4 | ~200,000 docs | ~80,000–150,000 |
| Språkbanken | 66 corpora | ~10,000–30,000 |
| TikTok | Variable (paid) | ~1,000–10,000 |
| **Total (deduplicated)** | | **Collection objective: 130,000–300,000; validation run (2026-05-29): 16,767** |

Counts vary with network conditions, Apify quota, and BBC availability. Filter rejection rates are logged to `data/metrics/` for auditability.

### Verifying the Output

```bash
# Validate silver schema compliance
somali-tools data validate-silver

# Check record counts and statistics
somali-tools data stats

# Validate metrics schema
somali-tools metrics validate

# Run regression tests (filter telemetry coverage)
pytest tests/regression/test_filter_telemetry.py -v
```

### Known Reproduction Issue

**Silver read-back is currently broken** (audit finding F-002): JSON metadata sidecars stored inside Parquet partition directories cause `ArrowInvalid` when calling `pq.read_table("data/processed/silver/")`. Workaround until fixed:

```python
import pyarrow.parquet as pq
import glob

# Read individual Parquet files, skipping sidecars
files = glob.glob("data/processed/silver/**/*.parquet", recursive=True)
tables = [pq.read_table(f) for f in files]
import pyarrow as pa
combined = pa.concat_tables(tables)
```

---

*See `governance/evaluation-protocol.md` for Phase 3 evaluation procedures.*
