# Internal Archive

**Purpose:** Internal working documents for development team
**Status:** This directory is gitignored - for local use only
**Last Reorganized:** 2025-10-26

---

## What Goes Here

Internal working documents including:
- Bug fix summaries
- Implementation reports
- Code reviews
- Investigation findings
- Test reports
- Architecture decisions
- Deployment notes
- Verification scripts

**NOT for:** User-facing documentation (use `docs/` instead)

---

## Directory Structure

```
.archive/
├── fixes/              Bug fixes and issue resolutions
│   ├── critical/      P0 production issues
│   ├── bugs/          Standard bug fixes (25 files)
│   └── improvements/  Enhancement fixes (3 files)
│
├── implementations/   Feature implementations
│   ├── features/     New feature work (19 files)
│   ├── integrations/ System integrations (5 files)
│   └── refactoring/  Code refactoring (4 files)
│
├── reviews/          Code reviews and assessments
│   ├── design-reviews/ Architecture reviews (1 file)
│   ├── code-reviews/   Code reviews (3 files)
│   └── peer-reviews/   Peer feedback (2 files)
│
├── investigations/   Research and analysis
│   ├── analysis/     Data/metrics analysis (20 files)
│   ├── diagnostics/  Problem diagnosis (9 files)
│   └── research/     Technology research
│
├── planning/         Planning and architecture
│   ├── architecture/ Architecture decisions (3 files)
│   ├── roadmaps/     Project roadmaps (1 file)
│   └── strategies/   Strategic planning (3 files)
│
├── testing/          Testing documentation
│   ├── test-reports/ Test execution (2 files)
│   ├── test-plans/   Test planning (3 files)
│   └── verification/ Verification scripts (4 files)
│
├── deployments/      Deployment documentation
│   ├── releases/     Release notes
│   ├── rollbacks/    Rollback incidents
│   └── automation/   Deploy automation (8 files)
│
├── documentation/    Internal doc work
│   ├── cleanup/      Restructures (4 files)
│   ├── audits/       Audits
│   └── improvements/ Improvements (11 files)
│
└── artifacts/        Code artifacts
    ├── scripts/      Utility scripts
    ├── prototypes/   Prototype code (1 file)
    └── patches/      Temporary patches (1 file)
```

**Total:** 132 files organized by work type

---

## File Naming Convention

**Format:** `YYYYMMDD_descriptive-label.md`

**Examples:**
```
✅ Good:
20251026_dashboard-consolidation-fix.md
20251026_metrics-phase1-implementation.md
20251026_architecture-design-review.md

❌ Bad:
2025-10-26_DASHBOARD_FIX.md    # Wrong format
DashboardFix.md                 # No date
fix-summary.md                  # No date
```

---

## Quick Commands

### Create New Document

```bash
# Bug fix
DATE=$(date +%Y%m%d)
touch .archive/fixes/bugs/${DATE}_my-bug-fix.md

# Feature implementation
touch .archive/implementations/features/${DATE}_my-feature.md

# Test report
touch .archive/testing/test-reports/${DATE}_my-test-report.md
```

### Search Archives

```bash
# Search by keyword
grep -r "keyword" .archive/

# Find by date
find .archive/ -name "20251026*.md"

# List category
ls .archive/fixes/bugs/

# View structure
tree .archive/ -L 2
```

### Count Files

```bash
# Total files
find .archive/ -name "*.md" | wc -l

# By category
for cat in fixes implementations reviews investigations planning testing deployments documentation artifacts; do
  count=$(find ".archive/$cat" -name "*.md" 2>/dev/null | wc -l)
  printf "%-20s %3d\n" "$cat:" "$count"
done
```

---

## Categorization Guide

**Where does my document go?**

| I did... | Goes in... |
|----------|------------|
| Fixed a bug | `fixes/bugs/` |
| Fixed critical issue | `fixes/critical/` |
| Built a feature | `implementations/features/` |
| Integrated system | `implementations/integrations/` |
| Reviewed code | `reviews/code-reviews/` |
| Analyzed data | `investigations/analysis/` |
| Diagnosed problem | `investigations/diagnostics/` |
| Designed architecture | `planning/architecture/` |
| Ran tests | `testing/test-reports/` |
| Deployed release | `deployments/automation/` |
| Cleaned up docs | `documentation/cleanup/` |
| Wrote verification script | `artifacts/scripts/` |

**Need more help?** See `../ARCHIVE_QUICK_REFERENCE.md`

---

## Full Documentation

Located in project root:
- **Quick Reference:** `ARCHIVE_QUICK_REFERENCE.md`
- **Full Design:** `ARCHIVE_ORGANIZATION_DESIGN.md`
- **Executive Summary:** `ARCHIVE_SUMMARY.md`
- **Migration Script:** `migrate_archives.py`

---

## Migration Status

**Date:** 2025-10-26
**Status:** Not yet migrated (files still in flat structure)

**To migrate:**
```bash
# Preview migration
python ../migrate_archives.py --dry-run

# Execute migration
python ../migrate_archives.py

# Verify results
tree .archive/ -L 2
```

After migration, this structure will be populated with 132 organized files.

---

## Maintenance

**Archive within 24 hours after:**
- PR merged
- Feature deployed
- Test cycle complete
- Review concluded

**Quarterly cleanup:**
- Review documents >6 months old
- Consolidate duplicates
- Remove obsolete docs

---

## Historical Notes

### Pre-2025-10-26 (Before Reorganization)
Files were stored in flat structure with mixed naming conventions:
- `2025-10-13_` format (with hyphens)
- `20251021_` format (without hyphens)
- Mixed case: `UPPERCASE_LABELS` vs `lowercase`

### 2025-10-26 Reorganization
Implemented scalable 8-category structure:
- Consistent naming: `YYYYMMDD_kebab-case.md`
- 2-level hierarchy (category/subcategory)
- Clear categorization rules
- Migration automation

**Migration planned for:** 2025-10-26
**Expected result:** 132 files organized into 27 subcategories
