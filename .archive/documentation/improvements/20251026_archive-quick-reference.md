# Archive Quick Reference Guide

**Last Updated:** 2025-10-26

Quick guide for saving internal working documents to `.archive/`.

---

## TL;DR

```bash
# Format: YYYYMMDD_descriptive-label.md
DATE=$(date +%Y%m%d)

# Bug fix → fixes/bugs/
touch .archive/fixes/bugs/${DATE}_my-bug-fix.md

# Feature implementation → implementations/features/
touch .archive/implementations/features/${DATE}_my-feature.md

# Code review → reviews/code-reviews/
touch .archive/reviews/code-reviews/${DATE}_my-code-review.md

# Analysis work → investigations/analysis/
touch .archive/investigations/analysis/${DATE}_my-analysis.md

# Test report → testing/test-reports/
touch .archive/testing/test-reports/${DATE}_my-test-report.md
```

---

## File Naming

**Format:** `YYYYMMDD_descriptive-label.md`

**Good:**
```
20251026_dashboard-consolidation-fix.md
20251026_metrics-phase1-implementation.md
20251026_architecture-design-review.md
```

**Bad:**
```
2025-10-26_DASHBOARD_FIX.md    # Wrong date format, uppercase
DashboardFix.md                 # No date
fix-summary.md                  # No date
```

---

## Categories

| I did... | Goes in... |
|----------|------------|
| Fixed a bug | `.archive/fixes/bugs/` |
| Fixed critical issue | `.archive/fixes/critical/` |
| Made improvement | `.archive/fixes/improvements/` |
| Built feature | `.archive/implementations/features/` |
| Integrated system | `.archive/implementations/integrations/` |
| Refactored code | `.archive/implementations/refactoring/` |
| Design review | `.archive/reviews/design-reviews/` |
| Code review | `.archive/reviews/code-reviews/` |
| Peer review | `.archive/reviews/peer-reviews/` |
| Data analysis | `.archive/investigations/analysis/` |
| Problem diagnosis | `.archive/investigations/diagnostics/` |
| Technology research | `.archive/investigations/research/` |
| Architecture design | `.archive/planning/architecture/` |
| Project roadmap | `.archive/planning/roadmaps/` |
| Strategic planning | `.archive/planning/strategies/` |
| Test execution | `.archive/testing/test-reports/` |
| Test planning | `.archive/testing/test-plans/` |
| Verification script | `.archive/testing/verification/` |
| Release notes | `.archive/deployments/releases/` |
| Rollback incident | `.archive/deployments/rollbacks/` |
| Deploy automation | `.archive/deployments/automation/` |
| Docs cleanup | `.archive/documentation/cleanup/` |
| Docs audit | `.archive/documentation/audits/` |
| Docs improvements | `.archive/documentation/improvements/` |
| Utility script | `.archive/artifacts/scripts/` |
| Prototype code | `.archive/artifacts/prototypes/` |
| Temporary patch | `.archive/artifacts/patches/` |

---

## Common Scenarios

### After Fixing a Bug

```bash
DATE=$(date +%Y%m%d)
cat > .archive/fixes/bugs/${DATE}_dashboard-data-fix.md <<EOF
# Dashboard Data Fix

**Date:** $(date +%Y-%m-%d)
**Status:** Fixed

## Problem
Dashboard showed zero data.

## Solution
Added consolidation step to deployment.

## Files Modified
- dashboard_deployer.py
- generate_consolidated_metrics.py
EOF
```

### After Implementing a Feature

```bash
DATE=$(date +%Y%m%d)
touch .archive/implementations/features/${DATE}_sprakbanken-integration.md
# Edit file with implementation details
```

### After Code Review

```bash
DATE=$(date +%Y%m%d)
touch .archive/reviews/code-reviews/${DATE}_metrics-refactoring-review.md
# Document review findings
```

### After Running Tests

```bash
DATE=$(date +%Y%m%d)
touch .archive/testing/test-reports/${DATE}_full-pipeline-test.md
# Document test results
```

---

## Searching Archives

### By Date

```bash
# Today's documents
find .archive/ -name "$(date +%Y%m%d)*.md"

# October 2025
find .archive/ -name "202510*.md"

# Date range (Oct 20-26)
find .archive/ -name "202510[2][0-6]*.md"
```

### By Category

```bash
# All fixes
ls .archive/fixes/*/*.md

# All implementations
ls .archive/implementations/*/*.md

# All test reports
ls .archive/testing/test-reports/*.md
```

### By Keyword

```bash
# Search filenames
find .archive/ -name "*dashboard*.md"

# Search file contents
grep -r "metrics" .archive/ | cut -d: -f1 | sort -u

# Search with context
grep -r -C 3 "bug fix" .archive/
```

### Tree View

```bash
# Overview
tree .archive/ -L 2

# Specific category
tree .archive/fixes/

# With file sizes
tree .archive/ -L 2 -h
```

---

## Document Template

```markdown
# [Title]

**Date:** YYYY-MM-DD
**Category:** [Fix/Implementation/Review/Investigation/etc.]
**Status:** [In Progress/Complete/Archived]

---

## Summary
Brief overview.

## Problem Statement
What was the issue/task?

## Solution/Findings
What was done?

## Impact
What changed?

## Files Modified
- File 1
- File 2

## Related Work
- PR #123
- Related doc
```

---

## Migration Tool

### Preview Migration

```bash
# See what would happen (no changes)
python migrate_archives.py --dry-run
```

### Execute Migration

```bash
# Migrate all files
python migrate_archives.py

# With verbose output
python migrate_archives.py --verbose
```

### Show Statistics

```bash
# Just show stats
python migrate_archives.py --stats
```

---

## Helper Commands

### Create New Document

```bash
# Helper function (add to ~/.bashrc or ~/.zshrc)
archive() {
  local category="$1"
  local label="$2"
  local date=$(date +%Y%m%d)
  local file=".archive/${category}/${date}_${label}.md"

  mkdir -p "$(dirname "$file")"
  cat > "$file" <<EOF
# $(echo "$label" | tr '-' ' ' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')

**Date:** $(date +%Y-%m-%d)
**Category:** $(basename "$category")
**Status:** In Progress

---

## Summary


## Details

EOF

  echo "Created: $file"
  echo "$file"
}

# Usage:
archive fixes/bugs my-bug-fix
archive implementations/features my-new-feature
archive testing/test-reports my-test-report
```

### List Recent Documents

```bash
# Last 10 documents
find .archive/ -name "*.md" -type f -print0 | xargs -0 ls -lt | head -10

# Last 10 from specific category
find .archive/fixes/ -name "*.md" -type f -print0 | xargs -0 ls -lt | head -10
```

### Count Documents

```bash
# Total
find .archive/ -name "*.md" | wc -l

# By category
for cat in fixes implementations reviews investigations planning testing deployments documentation artifacts; do
  count=$(find ".archive/$cat" -name "*.md" 2>/dev/null | wc -l)
  printf "%-20s %3d\n" "$cat:" "$count"
done
```

---

## What NOT to Archive

- ❌ User-facing documentation (goes in `docs/`)
- ❌ Active work-in-progress (keep in working directory)
- ❌ Temporary scratch notes (delete instead)
- ❌ Generated files (logs, build artifacts)
- ❌ Secrets or credentials (NEVER!)

## What TO Archive

- ✅ Bug fix summaries (after PR merged)
- ✅ Implementation reports (after feature complete)
- ✅ Code review notes (after review done)
- ✅ Investigation findings (after investigation complete)
- ✅ Test reports (after test cycle)
- ✅ Architecture decisions (after design finalized)

---

## Rules of Thumb

1. **Archive within 24 hours** after work complete
2. **Use descriptive labels** (5-7 words)
3. **Follow naming convention** (`YYYYMMDD_kebab-case.md`)
4. **Choose specific category** (use Decision Tree if unsure)
5. **Keep it concise** (1-3 pages max)
6. **Link to related work** (PRs, issues, docs)

---

## Getting Help

**Can't decide on category?**
→ Use Decision Tree in `ARCHIVE_ORGANIZATION_DESIGN.md`

**Unsure about naming?**
→ Follow examples above, use kebab-case

**Need to find old document?**
→ Use grep: `grep -r "keyword" .archive/`

**Want to reorganize?**
→ Run migration tool with `--dry-run` first

---

## Maintenance

**Quarterly Cleanup (Every 3 Months):**
- Review documents >6 months old
- Consolidate duplicates
- Delete truly obsolete docs
- Update this guide if needed

**Annual Review:**
- Archive old documents (>1 year) to compressed format
- Review category structure
- Update process based on team feedback

---

## Examples from Real Usage

### Example 1: Bug Fix

```
File: .archive/fixes/bugs/20251026_dashboard-consolidation-fix.md
Category: Bug fix
Content: Fixed dashboard zero data by adding consolidation step
Status: Complete
```

### Example 2: Integration

```
File: .archive/implementations/integrations/20251016_huggingface-integration.md
Category: System integration
Content: Integrated HuggingFace Somali_c4-so dataset
Status: Complete
```

### Example 3: Code Review

```
File: .archive/reviews/code-reviews/20251026_metrics-refactoring-review.md
Category: Code review
Content: Review of Phase 1 metrics refactoring
Status: Complete
```

### Example 4: Test Report

```
File: .archive/testing/test-reports/20251026_full-pipeline-test.md
Category: Test execution
Content: Results from running full pipeline test suite
Status: Complete
```

---

## Troubleshooting

**Problem:** File already exists with same name
**Solution:** Add version suffix: `20251026_my-fix-v2.md`

**Problem:** Don't know which category to use
**Solution:** Default to `investigations/diagnostics/`, refine later

**Problem:** Filename too long
**Solution:** Use abbreviations, max 50 chars total

**Problem:** Need to move file to different category
**Solution:** `mv .archive/old/category/file.md .archive/new/category/`

---

## Quick Links

- Full Design: `ARCHIVE_ORGANIZATION_DESIGN.md`
- Migration Tool: `migrate_archives.py`
- Decision Tree: See "Categorization Rules" in design doc
- Template: See "Document Template" above

---

**Remember:** Keep it simple. The goal is to find documents later, not perfect organization.
