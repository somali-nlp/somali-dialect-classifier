# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- **Comprehensive Test Suite**: 137 tests covering filters, pipelines, and integration scenarios

### Changed
- **Logger Naming**: Changed from `self.__class__.__name__` to `__name__` for module-level consistency
- **Config Alignment**: `silver_dir` path changed from `data/silver` to `data/processed/silver`
- **SilverDatasetWriter**: Now uses `config.data.silver_dir` by default instead of hardcoded path
- **WikipediaSomaliProcessor**: Retrofitted with `min_length_filter` + `langid_filter` (0.3 confidence)
- **BBCSomaliProcessor**: Retrofitted with length, language, and topic enrichment filters

### Fixed
- **HIGH PRIORITY**: Reprocessing blocked when prior files exist (resolved via `force` flag)
- **HIGH PRIORITY**: BBC max_articles caching ignores parameter changes (cache validation added)
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
