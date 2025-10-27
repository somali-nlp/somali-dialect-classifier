# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-10-27

### Added
- **Orchestration Enhancement**: Advanced pipeline control and automation features
  - **--skip-sources flag**: Skip specific data sources when running all pipelines (e.g., `--skip-sources bbc huggingface`)
  - **--sprakbanken-corpus flag**: Choose specific Språkbanken corpus instead of processing all 23 (e.g., `--sprakbanken-corpus cilmi`)
  - **--auto-deploy flag**: Automatically deploy metrics to GitHub Pages dashboard after successful pipeline runs
  - **--max-bbc-articles flag**: Limit BBC articles fetched for testing purposes
  - **--max-hf-records flag**: Limit HuggingFace records processed for testing purposes
  - **Proper exit codes**: Orchestrator now exits with code 1 on failures (critical for CI/CD integration)
  - Enables flexible testing workflows and incremental data collection
- **Documentation Reorganization (Phase 1)**: Production-ready documentation structure
  - Archived 9 internal planning documents to `docs/archive/` with timestamped naming (`YYYYMMDD_HHMM_<filename>.md`)
  - Consolidated 4 dashboard docs into single comprehensive guide at `docs/guides/dashboard.md` (1,000+ lines)
  - Updated `dashboard/README.md` as technical reference pointing to main guide
  - Removed duplicate content (~700 lines) while preserving all information
  - Established clear documentation hierarchy: guides, howtos, reference, operations
- **Interactive Dashboard System**: ✅ **PRODUCTION-READY** - Professional data quality monitoring with zero hosting costs
  - **GitHub Pages deployment**: Static dashboard auto-deploys via GitHub Actions on every push to main
  - **Local Streamlit dashboard**: Interactive charts with filtering, zoom, and real-time updates
  - **Metrics visualization**: 15+ KPIs tracked (success rates, throughput, deduplication, P95 latency)
  - **Quality reports viewer**: Markdown rendering of automated quality reports with source/date filters
  - **Time series analysis**: Records over time, success rate trends, performance benchmarks
  - **Source comparison**: Side-by-side metrics across Wikipedia, BBC, HuggingFace, Språkbanken
  - **Portfolio-ready**: Professional visualizations with Plotly, responsive mobile design
  - **Zero cost**: Free hosting on GitHub Pages, no external services required
  - **Automated quality reporting**: Per-run extraction reports and final quality summaries
- **Metrics System Enhancement**: Three-tier pipeline metrics architecture
  - **Pipeline-level metrics**: Overall run statistics (extraction, final reports)
  - **Component metrics**: Per-component tracking (download, extract, process phases)
  - **Quality metrics**: Filter statistics, deduplication rates, data quality scores
  - **Structured JSON logging**: Machine-parsable logs with context injection and nested fields
  - **Context managers**: Automatic timing and status tracking for pipeline phases
  - **Metrics export**: JSON serialization for dashboard consumption and historical analysis
- **Improved File Naming Conventions (Phase 1)**: Data engineering best practices implemented
  - **run_id in all filenames**: `{source_slug}_{run_id}_{layer}_{descriptive_name}.{ext}` pattern
  - **Unique run_id generation**: Format `YYYYMMDD_HHMMSS` for traceability (e.g., `20251020_143045`)
  - **Source-specific silver filenames**: `{source_slug}_{run_id}_silver_part-{num}.parquet` (replaces generic `part-0000.parquet`)
  - **Metadata JSON sidecars**: `{source_slug}_{run_id}_silver_metadata.json` with checksums (SHA256), record counts, and statistics
  - **Wikipedia**: `wikipedia-somali_{run_id}_staging_extracted.txt`, `wikipedia-somali_{run_id}_processed_cleaned.txt`
  - **BBC**: `bbc-somali_{run_id}_raw_article-links.json`, `bbc-somali_{run_id}_staging_articles.jsonl`, `bbc-somali_{run_id}_raw_article-{num}.json`
  - **HuggingFace**: `{dataset}_{run_id}_raw_manifest.json`, `{dataset}_{run_id}_staging_batch-{num}.jsonl`
  - **Språkbanken**: `sprakbanken-{corpus_id}_{run_id}_raw_manifest.json`, `sprakbanken-{corpus_id}_{run_id}_staging_extracted.jsonl`
  - **Benefits**: Prevents overwrites, enables lineage tracking, supports incremental processing, MLOps-ready
- **Silver Dataset Schema v2.1**: Added `register` field for linguistic formality classification
  - New field: `register` (string) - Values: "formal", "informal", "colloquial"
  - All 4 processors now implement `_get_register()` abstract method
  - Wikipedia, BBC, HuggingFace MC4, Språkbanken all return "formal" (current sources are predominantly formal)
  - Future sources (TikTok, conversational data) will use "informal" and "colloquial"
  - Schema validation via `VALID_REGISTERS = {"formal", "informal", "colloquial"}` in `SilverDatasetWriter`
  - Backward compatible: v2.0 and v1.0 datasets automatically upgraded on read with inferred register values
  - Purpose: Enable filtering by linguistic formality level, train register-aware models, analyze stylistic variation
- **Comprehensive Integration Guides**: ✅ **PRODUCTION-READY** - Dedicated documentation for all four data sources
  - Created `docs/howto/wikipedia-integration.md` (800+ lines) - Complete guide to Wikipedia dumps, MediaWiki XML parsing, namespace filtering, performance optimization
  - Created `docs/howto/bbc-integration.md` (850+ lines) - Ethical web scraping guide with topic enrichment, rate limiting, robots.txt compliance
  - Enhanced `docs/howto/processing-pipelines.md` - Added Språkbanken section and comparison table for all four sources
  - All four sources now have equal, comprehensive, professional documentation
- **API Reference Completeness**: ✅ **COMPLETE** - Added missing processor documentation
  - Added `HuggingFaceSomaliProcessor` API reference with factory functions and streaming architecture
  - Added `SprakbankenSomaliProcessor` API reference with all 23 corpora and helper functions
  - Updated table of contents to include all four processors
  - All processors now equally documented in API reference
- **Documentation System**: ✅ **PRODUCTION-READY** - Comprehensive documentation framework
  - Created `DOCUMENTATION_GUIDE.md` - Complete style guide and writing guidelines for contributors
  - Added documentation templates in `docs/templates/`:
    - `adr-template.md` - Template for Architecture Decision Records
    - `howto-template.md` - Template for task-oriented guides
  - Consolidated HuggingFace documentation into single comprehensive guide
  - Created `.archive/` for temporary development documents (excluded from git)
  - Established clear documentation maintenance process and review checklist
- **Documentation Restructure**: ✅ **COMPLETE** - Hierarchical organization implemented
  - Created `overview/`, `howto/`, `reference/`, `operations/`, `decisions/`, `roadmap/` directories
  - Migrated all docs to lowercase kebab-case naming (`architecture.md` not `ARCHITECTURE.md`)
  - New comprehensive guides: `processing-pipelines.md` (3 sources walkthrough), `custom-filters.md` (6 examples with tests)
  - Roadmap documents: `lifecycle.md` (5-phase project plan), `future-work.md` (19 backlog items)
  - Updated `docs/index.md` with role-based navigation (5 personas: New Users, Developers, Data Engineers, DevOps, ML Engineers)
  - MkDocs/Sphinx-ready structure for future automated deployment
- **Silver Dataset Schema v2.1 Enhancement**: Added `register` field for linguistic formality classification
  - Extended schema with `register` field (values: "formal", "informal", "colloquial")
  - All 4 processors implement register classification (currently all return "formal" for academic/news sources)
  - Future-ready for informal sources (social media, conversational data)
  - Backward compatible with v2.0 and v1.0 datasets (auto-upgrade with inferred values)
  - Enables filtering by linguistic formality and training register-aware models
- **Deduplication Engine**: Two-tier deduplication system for silver dataset quality
  - **Exact deduplication**: SHA256 hash-based detection of identical texts
  - **Near-duplicate detection**: Simhash-based fuzzy matching for similar content (configurable threshold)
  - **Cross-source deduplication**: Detect duplicates across different data sources
  - **Statistics tracking**: Deduplication rates per source and overall
  - **Configurable**: Threshold tuning via environment variables
  - **Performance optimized**: Memory-efficient streaming processing
- **HuggingFace Datasets Integration**: Streaming processor for large-scale datasets
  - `HuggingFaceSomaliProcessor`: Streaming support for HF Hub datasets
  - **Manifest-based versioning**: Track dataset/config/split/revision
  - **JSONL batching**: Resume-capable extraction (5k records/batch)
  - **Field mapping**: Handle heterogeneous schemas
  - **Factory functions**: Pre-configured for MC4, OSCAR-2301, MADLAD-400
  - **CLI**: `hfsom-download` command for easy dataset processing
  - **Configuration**: Externalized thresholds via environment variables
  - **28 new tests**: Comprehensive coverage with mocked datasets for CI
  - **Documentation**: 800-line guide (docs/HUGGINGFACE_DATASETS.md)
- **Filter Framework**: Pluggable quality control system for silver data pipelines
  - `min_length_filter`: Reject records below character threshold (default: 50)
  - `langid_filter`: Heuristic-based Somali language detection (120+ word vocabulary)
  - `dialect_heuristic_filter`: Topic/dialect marker enrichment for downstream scoring
  - `namespace_filter`: Wikipedia namespace validation (Talk, User, etc.)
  - `custom_filter`: Arbitrary predicate functions
- **Hook Interface**: `BasePipeline._register_filters()` for subclass filter registration
- **Filter Statistics**: Counter-based logging of per-filter rejection counts
- **Metadata Enrichment**: Filters can add metadata fields without rejecting records
- **Force Reprocessing**: `force=True` parameter to rebuild existing silver datasets
- **BBC Cache Invalidation**: Automatic cache invalidation on `max_articles` parameter changes
- **Memory-Safe Wikipedia Extraction**: 10MB buffer threshold with streaming writes
- **Comprehensive Test Suite**: 165+ tests covering filters, pipelines, and integration scenarios
  - Added `test_hf_processor.py` for processed_file validation
- **Documentation Suite**: 10 comprehensive technical documents
  - **NEW**: `docs/HUGGINGFACE_DATA_FLOW.md` - 400-line guide explaining directory structure, data flow, and debugging
  - Includes "Inspecting Staged Batches" section with `jq`, `head`, `python -m json.tool` examples

### Changed
- **Partition Key Consistency**: Fixed `date_processed` → `date_accessed` in processed layer
  - **Previously**: Raw/Staging used `date_accessed`, Processed used `date_processed`, Silver used `date_accessed` (INCONSISTENT)
  - **Now**: All layers use `date_accessed` consistently for Hive-style partitioning
  - **Impact**: Simplifies queries, enables consistent lakehouse integration, aligns with data engineering best practices
- **run_id Propagation**: BasePipeline now generates run_id at initialization and passes to silver_writer
  - Ensures consistent run_id across raw → staging → processed → silver
  - Enables end-to-end lineage tracking from source to silver dataset
- **Silver Writer API**: Updated `write()` method to require `run_id` parameter
  - Signature: `write(records, source, date_accessed, run_id, partition_num=None)`
  - Generates source-specific filenames instead of generic `part-XXXX.parquet`
  - Auto-increments partition numbers per run_id to prevent collisions
- **Documentation Consistency**: ✅ **COMPLETE** - All four data sources now equally documented
  - Updated `docs/index.md` - Added all four integration guides to How-To section, updated project status to mention all sources
  - Updated `docs/howto/processing-pipelines.md` - Header now lists all four sources, added Språkbanken section, added comparison table
  - Updated `docs/reference/api.md` - All four processors (Wikipedia, BBC, HuggingFace, Språkbanken) now in table of contents and fully documented
  - Silver dataset schema updated across all docs to include all four source types and licenses
  - Established consistent documentation structure: each source has dedicated integration guide + API reference coverage + quick-start in processing-pipelines.md
- **Documentation Organization**: Major restructure for production-readiness
  - Moved `DOCUMENTATION_GUIDE.md` → `docs/guides/documentation-guide.md` (root cleanup)
  - Deleted `DOCUMENTATION_AUDIT_REPORT.md` (temporary working document)
  - Deleted `docs/DOCUMENTATION_BEST_PRACTICES.md` (superseded by documentation-guide.md)
  - Moved temporary documents to `.archive/` (IMPLEMENTATION_SUMMARY.md, MADLAD400_STATUS.md, HUGGINGFACE_SETUP_GUIDE.md)
  - Standardized all filenames to kebab-case for consistency
- **HuggingFace Documentation**: Complete consolidation
  - Deleted `docs/HUGGINGFACE_DATASETS.md` (719 lines) - merged into howto guide
  - Deleted `docs/HUGGINGFACE_DATA_FLOW.md` (413 lines) - merged into howto guide
  - Deleted `docs/DOCUMENTATION_RESTRUCTURE_PLAN.md` - planning doc (obsolete)
  - Created single comprehensive guide at `docs/howto/huggingface-integration.md` (435 lines)
  - Updated README.md and docs/index.md with corrected references
  - Total redundant content removed: ~1,482 lines
- **Logger Naming**: Changed from `self.__class__.__name__` to `__name__` for module-level consistency
- **Config Alignment**: `silver_dir` path changed from `data/silver` to `data/processed/silver`
- **SilverDatasetWriter**: Now uses `config.data.silver_dir` by default instead of hardcoded path
- **WikipediaSomaliProcessor**: Retrofitted with `min_length_filter` + `langid_filter` (0.3 confidence)
- **BBCSomaliProcessor**: Retrofitted with length, language, and topic enrichment filters

### Changed
- **Dashboard Documentation Consolidation**: Streamlined documentation for better usability
  - Merged 4 overlapping dashboard docs into single authoritative guide
  - Archived superseded docs: `DASHBOARD_SETUP.md`, `DASHBOARD_SUMMARY.md`, `QUICK_START_DASHBOARD.md`
  - Created comprehensive `docs/guides/dashboard.md` (1,000+ lines) covering setup, features, troubleshooting, portfolio tips
  - Updated `dashboard/README.md` as technical reference with API documentation
  - Eliminated ~700 lines of duplicate content while improving organization

### Fixed
- **CRITICAL: BasePipeline Output Format**: BasePipeline now returns Parquet silver datasets (not .txt files)
  - All processors now consistently write to unified silver dataset schema
  - Fixes inconsistency where some pipelines returned text files instead of structured Parquet
  - Ensures consistent downstream data processing and analysis
- **CRITICAL: Orchestrator Exit Codes**: Orchestrator exits with code 1 on pipeline failures (was always 0)
  - Enables proper CI/CD integration and error detection
  - Failed pipelines now properly signal errors to automation systems
  - Critical for production deployment reliability
- **CRITICAL: Dashboard Deployment v3.0 Compatibility**: Dashboard deployment now works with v3.0 metrics schema
  - Fixed metric field mapping for new schema structure
  - Dashboard properly renders discovery, extraction, and processing metrics
  - Resolves deployment failures after metrics schema migration
- **HIGH: CLI Rate Limit Flags**: Rate-limit flags now work correctly for BBC scraping
  - Fixed --max-articles parameter handling in orchestrator
  - Ensures testing limits are properly applied
  - Prevents accidental over-scraping during development
- **HIGH: Crawl Ledger Source Identifier**: Crawl ledger now preserves source identifier
  - Fixed source field consistency in ledger tracking
  - Enables accurate resume capability across runs
  - Improves deduplication accuracy
- **Språkbanken CLI Logging**: Fixed structured logging format in `download_sprakbanken.py`
  - Changed from generic file logger to source-specific `sprakbanken-somali` logger for consistency
  - Ensures structured JSON logs include correct source identifier
  - Aligns with logging standards across all CLI modules
- **HuggingFace Extraction Reports**: Fixed missing extraction report generation
  - Added `processed_file` generation to `HuggingFaceSomaliProcessor.extract()`
  - Now writes human-readable JSONL samples to `data/processed/.../date_processed=.../` directory
  - Aligns with BBC and Wikipedia pipeline report generation patterns
  - Enables quality auditing and debugging for HuggingFace datasets
- **BUG (Principal MLE Review)**: `HuggingFaceSomaliProcessor.process()` returned `None` when all records filtered - Now raises `ValueError` with clear message (never returns None)
- **HIGH RISK (Principal MLE Review)**: `BasePipeline.process()` memory issue - Changed default `batch_size` from `None` to `5000` to prevent OOM on large sources like Wikipedia dumps
- **RISK (Principal MLE Review)**: HF source slug contained spaces/parentheses - Changed to filesystem-friendly format (`HuggingFace-Somali_c4-so` instead of `HuggingFace-Somali (allenai/c4)`), added `display_name` to metadata for pretty display
- **RISK (Principal MLE Review)**: Contract tests failed without optional `datasets` library - Made HuggingFaceSomaliProcessor import conditional in test suite
- **RISK (Principal MLE Review)**: BBC scraper used transient CSS class `bbc-1y32vyc` - Replaced with semantic selectors (`<main>`, `role="main"`, `<article>`, `data-component`) with multi-level fallback strategy
- **RISK (Principal MLE Review)**: BBC scraper could silently return empty bodies - Added warning log when text extraction returns empty content
- **CRITICAL (Principal MLE Review)**: HuggingFaceSomaliProcessor missing `self.processed_file` - Now writes human-readable text dump to `data/processed/.../date_processed=.../` (aligns with BBC/Wikipedia pipelines)
- **CRITICAL (Principal MLE Review)**: MADLAD-400 "Dataset scripts no longer supported" - Switched to `revision="refs/convert/parquet"` branch workaround (removed `trust_remote_code`)
- **CRITICAL**: MADLAD-400 "Dataset scripts no longer supported" error - Added `trust_remote_code=True` for datasets with custom loading scripts
- **HIGH PRIORITY (Principal MLE Review)**: Progress bars still leaking through - Added `datasets.utils.logging.disable_progress_bar()` + `DownloadConfig(disable_tqdm=True)` to all `load_dataset()` calls
- **HIGH PRIORITY (Principal MLE Review)**: Manifest missing audit metadata - Added `total_records_extracted`, `total_batches`, `manifest_version` fields for Ops auditing
- **HIGH PRIORITY**: Reprocessing blocked when prior files exist (resolved via `force` flag)
- **HIGH PRIORITY**: BBC max_articles caching ignores parameter changes (cache validation added)
- **HIGH PRIORITY**: MADLAD-400 loading failure - Fixed incorrect dataset configuration (now uses `"so"` as config parameter instead of `pushdown_filters`)
- **HIGH PRIORITY**: HuggingFace progress bars cluttering logs - Suppressed via `HF_DATASETS_DISABLE_PROGRESS_BARS` environment variable
- **MEDIUM PRIORITY (Principal MLE Review)**: Manifest file naming collision - Changed from generic `hf_manifest.json` to `{dataset_slug}_manifest.json` (e.g., `c4_manifest.json`, `madlad-400_manifest.json`)
- **MEDIUM PRIORITY**: CLI naming inconsistency - Renamed `download_hf.py` to `download_hfsom.py` (following `wikisom`/`bbcsom` pattern)
- **MEDIUM PRIORITY**: Log file naming - Updated from `download_hf.log` to `download_hfsom.log`
- **MEDIUM PRIORITY**: Logger naming mismatch between implementation and tests
- **MEDIUM PRIORITY**: Config/silver directory path drift
- **LOW PRIORITY**: Wikipedia extraction memory scalability (streaming implementation)

### Technical Details
- **Filter Signature**: `(cleaned_text: str, **kwargs) -> (passes: bool, metadata_updates: dict)`
- **Opt-in Design**: Base `_register_filters()` returns empty list (zero breaking changes)
- **Graceful Error Handling**: Filter exceptions logged as warnings, pipeline continues
- **Backward Compatible**: All existing processors work without modification

## [0.1.0] - 2025-01-XX (Initial Release)

### Added
- Wikipedia Somali article extraction pipeline
- BBC Somali news article scraping pipeline
- Silver dataset schema with Parquet serialization
- Text cleaning pipeline (HTML, Wiki markup, whitespace)
- CLI interfaces for both processors
- Base pipeline contract with standardized interfaces
- Comprehensive test suite with fixtures

---

## Release Notes Guidelines

### Version Numbers
- **MAJOR**: Breaking API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Categories
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

### Commit Message Convention
Use conventional commits for automated changelog generation:
- `feat:` → Added
- `fix:` → Fixed
- `refactor:` → Changed
- `docs:` → Documentation
- `test:` → Test changes
- `chore:` → Maintenance

### Example
```bash
git commit -m "feat(filters): add langid_filter with Somali word vocabulary"
git commit -m "fix(bbc): invalidate cache when max_articles changes"
```
