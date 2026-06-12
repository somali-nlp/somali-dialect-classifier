# Codebase Tour

**The authoritative repository map for the Somali Dialect Classifier project.**

**This document is the single source of truth for paths, package layout, and structural conventions.
All other instruction files (CLAUDE.md, AGENTS.md, CONTRIBUTING.md, architecture.md) point here
for path and tree information rather than duplicating it.**

**Last Updated:** 2026-06-12

---

## Quick Navigation

### If you want to...

#### Work on data ingestion
- **Location:** `src/somdialc/ingestion/`
- **Entry point:** `ingestion/base_pipeline.py`
- **Source processors:** `ingestion/processors/*.py`
- **Key files:**
  - `base_pipeline.py` — Abstract pipeline orchestrator; run registration is lazy at stage entry (`run()` and `process()`)
  - `crawl_ledger.py` — URL tracking, quotas, campaign state, provenance
  - `dedup/` — Deduplication engine (exact hash + LSH shards)
  - `apify_tiktok_client.py` — TikTok Apify client with idempotency guard
  - `processors/` — Source processors (`wikipedia_somali_processor.py`, `bbc_somali_processor.py`, `huggingface_somali_processor.py`, `sprakbanken_somali_processor.py`, `tiktok_somali_processor.py`)
- **Tests:** `tests/test_base_pipeline_contract.py`, `tests/test_*_integration.py`
- **Docs:** `docs/howto/processing-pipelines.md`, `docs/howto/adding-sources.md`

#### Work on filters and data quality
- **Location:** `src/somdialc/quality/`
- **Key files:**
  - `filter_functions.py` — Filter implementations (min_length, langid, topic_lexicon, min_token_floor, etc.)
  - `filter_engine.py` — Filter orchestration and pipeline
  - `filters/catalog.py` — Dynamic filter registry (dashboard discovery)
  - `record_builder.py` — Schema enforcement and validation
  - `silver_writer.py` — Silver dataset Parquet writer (21-field schema, `tokens` as int64)
  - `text_cleaners.py` — Text cleaning pipelines (HTML, Wiki markup)
  - `schema_mappers.py` — Schema version mapping
- **Tests:** `tests/test_filters.py`, `tests/quality/`
- **Docs:** `docs/reference/filters.md`, `docs/howto/custom-filters.md`

#### Work on metrics and observability
- **Location:** `src/somdialc/infra/`
- **Key files:**
  - `metrics.py`, `metrics_schema.py` — Metrics collection and schema
  - `metrics_aggregation.py` — Consolidation utilities
  - `config.py` — Configuration management (Pydantic)
  - `profiles/` — Runtime YAML profiles (`production.yaml`, `development.yaml`)
  - `data_manager.py` — Data path management
  - `logging_utils.py` — Structured logging
  - `manifest_writer.py` — Run manifest output to `data/manifests/<run_id>.json`
- **CLI:** `somali-tools metrics`
- **Tests:** `tests/infra/`, `tests/utils/test_metrics_aggregation.py`
- **Docs:** `docs/guides/metrics.md`, `docs/reference/metrics-schema.md`

#### Work on the dashboard
- **Location:** `src/dashboard/`
- **Key files:**
  - `src/dashboard/src/` — TypeScript/JS source
  - `src/dashboard/build-site.sh` — Build script → `_site/`
  - `_site/` — Built artifacts (gitignored)
- **Config:** `playwright.config.js` at repository root (Playwright auto-discovers it)
- **Build:** `somali-tools dashboard build` or `src/dashboard/build-site.sh`
- **Deploy:** `somali-tools dashboard deploy` or `deploy-dashboard.yml` workflow
- **Tests:** Playwright visual regression via `dashboard-tests.yml`
- **Docs:** `docs/guides/dashboard.md`

#### Work on CLI tools
- **Location:** `src/somdialc/tools/`
- **Key files:**
  - `cli.py` — `somali-tools` Click group (metrics, ledger, data, dashboard subcommands)
- **Source download CLIs:** `src/somdialc/cli/download_*.py` (thin entry points delegating to processors)
- **Entry point:** `somali-tools` command
- **Tests:** `tests/tools/`
- **Docs:** `docs/reference/cli-reference.md`

#### Work on orchestration flows
- **Location:** `src/somdialc/orchestration/`
- **Key files:**
  - `flows.py` — Multi-source pipeline coordination
- **CLI:** `somali-orchestrate` command
- **Tests:** `tests/orchestration/`
- **Docs:** `docs/howto/orchestration.md`

#### Work on the schema/contracts boundary
- **Location:** `src/somdialc/schema/`, `src/somdialc/contracts/`
- **Key files:**
  - `schema/registry.py` — Schema version registry (`CURRENT_SCHEMA_VERSION`)
  - `schema/validation_service.py` — Schema version mapping
  - `contracts/ingestion_output.py` — TypedDict contract at the ingestion→quality boundary

#### Work on the database / ledger backends
- **Location:** `src/somdialc/database/`
- **Key files:**
  - `ledger_backend.py` — Abstract ledger interface (`CrawlState`, `LedgerBackend`)
  - `postgres_backend.py` — PostgreSQL implementation (incomplete quota methods; SQLite is production)
- **Docs:** `docs/decisions/005-sqlite-vs-postgres-ledger.md`

#### Work on ML models (Stage 2 — upcoming)
- **Location:** `src/somdialc/ml/` (scaffolded stub, `__all__ = []`)
- **Status:** Awaiting gold datasets with dialect labels
- **Docs:** See roadmap in `docs/roadmap/`

---

## Package Tree (Post-2026-06-12 Cleanup)

```
somali-dialect-classifier/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── Makefile
├── docker-compose.yml
├── playwright.config.js          # Playwright root config (tool default location)
│
├── docs/
│   ├── overview/
│   │   ├── codebase-tour.md      # THIS FILE — canonical map
│   │   └── architecture.md       # Layer descriptions + design patterns
│   ├── decisions/                # ADRs 001-008
│   ├── reference/
│   │   └── metrics_schema.json   # JSON-Schema contract for dashboard metrics
│   ├── howto/
│   ├── guides/
│   ├── operations/
│   ├── roadmap/
│   └── templates/
│
├── src/
│   ├── somdialc/                 # Main package (canonical name per ADR-004)
│   │   ├── ingestion/
│   │   │   ├── base_pipeline.py
│   │   │   ├── crawl_ledger.py
│   │   │   ├── sqlite_ledger_mixins.py
│   │   │   ├── pipeline_setup.py
│   │   │   ├── raw_record.py
│   │   │   ├── apify_tiktok_client.py
│   │   │   ├── source_names.py   # CANONICAL_SOURCES constant (lowercase-kebab)
│   │   │   ├── dedup/            # Exact hash + LSH shards
│   │   │   └── processors/
│   │   │       ├── wikipedia_somali_processor.py
│   │   │       ├── bbc_somali_processor.py
│   │   │       ├── huggingface_somali_processor.py
│   │   │       ├── sprakbanken_somali_processor.py
│   │   │       └── tiktok_somali_processor.py
│   │   ├── quality/
│   │   │   ├── filter_functions.py
│   │   │   ├── filter_engine.py
│   │   │   ├── record_builder.py
│   │   │   ├── record_utils.py
│   │   │   ├── silver_writer.py
│   │   │   ├── text_cleaners.py
│   │   │   ├── schema_mappers.py
│   │   │   └── filters/catalog.py
│   │   ├── infra/
│   │   │   ├── config.py
│   │   │   ├── profiles/         # production.yaml, development.yaml (importlib.resources)
│   │   │   ├── data_manager.py
│   │   │   ├── metrics.py
│   │   │   ├── metrics_schema.py
│   │   │   ├── metrics_aggregation.py
│   │   │   ├── manifest_writer.py
│   │   │   ├── logging_utils.py
│   │   │   ├── http.py
│   │   │   ├── rate_limiter.py
│   │   │   ├── security.py
│   │   │   └── tracking.py
│   │   ├── schema/
│   │   │   ├── registry.py
│   │   │   └── validation_service.py
│   │   ├── contracts/
│   │   │   └── ingestion_output.py
│   │   ├── database/
│   │   │   ├── ledger_backend.py
│   │   │   └── postgres_backend.py
│   │   ├── orchestration/
│   │   │   └── flows.py
│   │   ├── preprocessing/
│   │   │   └── validator.py
│   │   ├── cli/
│   │   │   ├── download_wikisom.py
│   │   │   ├── download_bbcsom.py
│   │   │   ├── download_hfsom.py
│   │   │   ├── download_spraksom.py
│   │   │   ├── download_tiktoksom.py
│   │   │   └── lock_status.py
│   │   ├── tools/
│   │   │   └── cli.py            # somali-tools Click group
│   │   ├── deployment/
│   │   │   └── deploy.py
│   │   ├── ml/                   # Scaffolded stub (Stage 2 landing zone)
│   │   │   └── __init__.py
│   │   └── version.py
│   └── dashboard/                # Static JS dashboard source
│       ├── src/
│       ├── build-site.sh
│       └── _site/                # Built artifacts (gitignored)
│
├── tests/                        # 1,200+ tests across 73 files
│   ├── fixtures/
│   ├── regression/
│   ├── test_base_pipeline_contract.py
│   ├── test_*_integration.py
│   └── conftest.py
│
├── .github/workflows/            # 7 workflows (ci, dashboard-tests, dashboard-validation,
│                                 #   deploy-dashboard, deployment-health-check,
│                                 #   scheduled-backup, secret-scan)
├── migrations/                   # Alembic + docker init SQL
├── scripts/
│   ├── dev/
│   └── ops/
├── audits/
│   └── 2026-03-10-phase1-audit/
│       ├── *-final.md            # Authoritative
│       └── drafts/               # v1/v2 drafts archived here
└── data/  logs/  mlruns/         # Gitignored runtime trees
```

> **Removed in June 2026 cleanup:** `src/somdialc/pipeline/` (vestigial shim), root `config/` (now `playwright.config.js` at root), root `schemas/` (now `docs/reference/metrics_schema.json`), `src/somdialc/config/` YAML-only dir (now `src/somdialc/infra/profiles/`).

---

## Silver Dataset Schema

The authoritative schema is defined in `src/somdialc/quality/silver_writer.py` (`SilverDatasetWriter.SCHEMA`). The 21 fields are:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | SHA-256 hash |
| `text` | string | Cleaned text |
| `title` | string | Document title |
| `source` | string | Lowercase-kebab, e.g. `wikipedia-somali` |
| `source_type` | string | e.g. `wiki`, `news`, `corpus` |
| `url` | string | Source URL |
| `source_id` | string | Source-internal identifier |
| `date_published` | string | ISO date string |
| `date_accessed` | string | ISO date string (partition key) |
| `language` | string | ISO 639-1, e.g. `so` |
| `license` | string | e.g. `CC-BY-SA-3.0` |
| `topic` | string | Topic enrichment from lexicon |
| `tokens` | **int64** | Whitespace token count |
| `text_hash` | string | SHA-256 of text (dedup key) |
| `pipeline_version` | string | `__pipeline_version__` at write time |
| `source_metadata` | string | JSON-serialized extra fields |
| `domain` | string | Content domain (news, encyclopedia, etc.) |
| `embedding` | string | Reserved; null in silver |
| `register` | string | Linguistic register |
| `run_id` | string | Links record to pipeline_runs + manifests |
| `schema_version` | string | Schema version from `schema/registry.py` |

**Partition key:** `source=<lowercase-kebab>/date_accessed=YYYY-MM-DD/`

```
data/processed/silver/
├── source=wikipedia-somali/date_accessed=2026-06-01/
├── source=bbc-somali/date_accessed=2026-06-01/
├── source=huggingface-somali_c4-so/date_accessed=2026-06-01/
├── source=sprakbanken-somali/date_accessed=2026-06-01/
└── source=tiktok-somali/date_accessed=2026-06-01/
```

The canonical source name constants live in `src/somdialc/ingestion/source_names.py` (`CANONICAL_SOURCES`). Use those constants; do not hardcode string literals.

---

## Campaign and Run Provenance

Run registration in `BasePipeline` is **lazy**: `_ensure_pipeline_run_registered()` fires at the top of `run()` and `process()`, not at construction. This is the single hook for campaign and provenance logic.

- **Production-purpose runs** (`SDC_RUN__PURPOSE=production`, the default): automatically start `campaign_init_001` (6-day window) on first entry and auto-complete it on expiry.
- **Validation/test-purpose runs** (`SDC_RUN__PURPOSE=validation|test`): never create campaigns.
- `run_purpose` and `campaign_id` are stamped into the `pipeline_runs` ledger row, every silver `source_metadata` field, and `data/manifests/<run_id>.json`.

See `docs/guides/data-pipeline.md` §Campaigns and `docs/operations/runbook.md` §Campaigns for operational details.

---

## CLI Commands

```bash
# Ingestion (source download)
wikisom-download [--force]
bbcsom-download [--max-articles N] [--force]
hfsom-download mc4 [--max-records N]
spraksom-download [--corpus <name>]
tiktoksom-download --video-urls data/tiktok_urls.txt

# Orchestration
somali-orchestrate --pipeline all [--skip-sources bbc huggingface]
somali-orchestrate --pipeline all --auto-deploy

# Unified tools (somali-tools subcommands)
somali-tools metrics consolidate
somali-tools metrics validate
somali-tools ledger status
somali-tools data validate-silver
somali-tools dashboard build
somali-tools dashboard deploy
```

For deploy-dashboard: the canonical workflow is `deploy-dashboard.yml` (renamed from `deploy-dashboard-v2.yml` in June 2026). The old name is no longer present.

---

## Configuration

Config is managed by `src/somdialc/infra/config.py` (`get_config()`).

```python
from somdialc.infra.config import get_config

config = get_config()
config.data.raw_dir
config.scraping.bbc.max_articles
```

Environment variables use double-underscore notation: `SDC_DATA__RAW_DIR`, `SDC_SCRAPING__BBC__MAX_ARTICLES`.

Runtime YAML profiles live at `src/somdialc/infra/profiles/production.yaml` and `development.yaml` (accessible via `importlib.resources`).

---

## Testing

```bash
pytest                                          # All tests
pytest --cov --cov-report=term-missing          # With coverage
pytest tests/test_bbc_integration.py           # Single file
pytest tests/regression/test_filter_telemetry.py -v  # Regression suite
```

The `isolated_pipeline_env` session fixture in `tests/conftest.py` sets `SDC_DATA__METRICS_DIR` and `SDC_DATA__SILVER_DIR` to temp paths, ensuring test runs never write to production data.

---

## Development Workflow

```bash
pip install -e ".[dev]"

# Quality gates (must pass before PR)
ruff format src/ tests/
ruff check --fix src/ tests/
mypy src/somdialc/contracts src/somdialc/schema src/somdialc/quality \
     src/somdialc/infra src/somdialc/orchestration
pytest
```

See `CONTRIBUTING.md` for the full contributing guide. Paths in that file reference this document.

---

## Decisions

ADRs live in `docs/decisions/`:

| ADR | Decision |
|-----|----------|
| 001 | OSCAR corpus exclusion |
| 002 | Filter framework design |
| 003 | MADLAD-400 exclusion |
| 004 | Package renamed `somdialc` |
| 005 | SQLite vs PostgreSQL for ledger |
| 006 | Parquet/medallion silver storage |
| 007 | Apify TikTok dependency (cost + alternatives) |
| 008 | Vanilla JS dashboard stack |

---

**Maintainers:** Somali NLP Contributors
