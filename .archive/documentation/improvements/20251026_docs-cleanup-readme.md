# Documentation Cleanup Archive - 2025-10-26

This archive contains documentation that was removed from the public-facing docs directory during a comprehensive reorganization.

## Archive Date

**2025-10-26**

## Archived Items

### 1. docs/investigations/

**Location**: `docs/investigations/2025-10-26-quality-stats/`

**Archived Files**:
- `README.md` - Investigation summary
- `QUALITY_STATS_FIX_VERIFICATION.md` - Verification report
- `QUALITY_STATS_TECHNICAL_ANALYSIS.md` - Technical analysis

**Reason for Archival**: Internal investigation documents not intended for end users. These documented a bug investigation that concluded no bug existed (field was renamed from `quality_stats` to `text_length_stats`).

**Key Finding**: Feature is working correctly. No code changes were needed.

### 2. docs/guides/metrics-migration.md

**Reason for Archival**: Internal migration documentation describing a refactoring process. This was Phase 1 implementation documentation for the metrics system refactoring, introducing pipeline-specific metric names.

**User-Facing Content Extracted To**: `docs/reference/metrics.md`

**Key Content Preserved**:
- Pipeline-specific metric names (web scraping, file processing, stream processing)
- Metric semantics and descriptions
- Examples of how to access metrics
- Quality report structure
- Best practices for using metrics

**Internal Content Archived**:
- Migration timeline and deprecation warnings
- Backward compatibility notes
- Bug fix details (BBC test limit calculation)
- Phase 2/3 planned features
- Internal implementation notes

### 3. docs/reference/examples/

**Location**: `reference/examples/`

**Archived Files**:
- `backward_compat_example_web_scraping.json`
- `backward_compat_example_stream_processing.json`
- `backward_compat_example_file_processing.json`

**Reason for Archival**: Internal testing artifacts created during Phase 1/2 metrics refactoring to validate backward compatibility.

**Why These Are Internal**:
1. **Named as Migration Tests**: "backward_compat" prefix indicates these are migration validation artifacts, not user examples
2. **Extensive Disclaimers**: Each file contains warnings NOT to use values as expected results:
   - `"_EXAMPLE_DISCLAIMER": "BACKWARD COMPATIBILITY EXAMPLE - NOT PRODUCTION DATA"`
   - `"do_not_expect": ["187 URLs will always be discovered", ...]`
   - `"usage": "Use this to understand the JSON STRUCTURE, not as expected values"`
3. **Migration Metadata**: Files contain internal fields like `_migration_timestamp`, `_legacy_fetch_success_rate`, `_format_version`
4. **Test-Specific Values**: Values are from single test runs with artificial limits (e.g., `--max-bbc-articles=20`)
5. **Not Referenced**: Zero references found in any user-facing documentation

**Better Alternative for Users**: The `docs/reference/metrics.md` file provides comprehensive metric format examples without confusing migration metadata.

### 4. docs/reference/schemas/

**Location**: `reference/schemas/`

**Archived Files**:
- `all_metrics_schema_v2.json`

**Reason for Archival**: Despite the filename suggesting a formal schema, this is actually a snapshot from a specific test run on 2025-10-26, created during metrics refactoring.

**Why This Is Internal**:
1. **Snapshot, Not Schema**: Contains specific values from a test run:
   - `"total_records": 9662`
   - `"last_run": "2025-10-26T10:00:50.364857+00:00"`
   - `"_test_run_limited": true`
2. **Migration Artifact**: Created by `metrics_analysis.py` during Phase 2 to validate the new format
3. **Misleading Disclaimers**: Contains extensive warnings that this is NOT a requirements document:
   - `"type": "DYNAMIC SNAPSHOT - NOT HARDCODED REQUIREMENTS"`
   - `"do_not_assume": ["Total records will always be 9662", ...]`
4. **Not Referenced**: No references found in user-facing documentation
5. **Confusing for Users**: Users seeking a schema would be confused by this dynamic snapshot

**Better Alternative for Users**: The `docs/reference/metrics.md` file provides clear, structured metric format documentation with proper examples.

## Rationale

The documentation reorganization focused on:

1. **User-Facing vs Internal**: Separating documentation intended for end users/contributors from internal development artifacts
2. **Single Source of Truth**: Extracting user-facing content from migration guides and integrating it into permanent reference documentation
3. **Clean Structure**: Removing investigation artifacts and process documentation from the main docs tree
4. **Maintainability**: Ensuring the docs directory contains only current, relevant documentation

## Content Migration

### What Was Preserved

From `metrics-migration.md`, the following user-facing content was extracted and integrated into `docs/reference/metrics.md`:

- ✅ Complete metric reference tables for all pipeline types
- ✅ Metric descriptions and semantics
- ✅ Examples of accessing metrics programmatically
- ✅ Quality report structure and interpretation
- ✅ Best practices for monitoring and debugging
- ✅ Metric calculation details

### What Was Archived

Internal process documentation:
- Migration guide structure and timeline
- Deprecation warnings for old metric names
- Backward compatibility implementation details
- Bug fix specifics (test limit calculation)
- Future phase planning (hierarchical metrics, domain-specific classes)
- FAQs about migration process

## References

For current metrics documentation, see:
- [Metrics Reference](../../docs/reference/metrics.md) - Complete metrics documentation
- [Data Pipeline Guide](../../docs/guides/data-pipeline.md) - Using pipelines
- [API Reference](../../docs/reference/api.md) - MetricsCollector API

## Archive Retention

These files should be retained for historical reference but are not part of the active documentation set.

---

**Archived By**: Documentation reorganization process
**Archive Date**: 2025-10-26
**Retention**: Indefinite (historical reference)
