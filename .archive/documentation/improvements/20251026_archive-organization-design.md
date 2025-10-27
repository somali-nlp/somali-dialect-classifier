# Internal Archive Organization Design

**Date:** 2025-10-26
**Purpose:** Scalable organization structure for internal working documents
**Scope:** `.archive/` directory only (gitignored, developer-internal)

---

## Executive Summary

This design consolidates 131 files from `.archive/` and 5 files from `archive/` into a unified, scalable structure with clear categorization rules and a consistent naming convention.

**Key Decisions:**
- **Single Location:** `.archive/` (gitignored)
- **Naming Convention:** `YYYYMMDD_descriptive-label.md` (8-digit dates, kebab-case)
- **Structure:** 2-level hierarchy (category/subcategory)
- **Philosophy:** Simple, pragmatic, easily navigable

---

## Current State Analysis

### Existing Files Breakdown

**`.archive/` - 131 files:**
- **Document Types:**
  - Summaries: 16 files (implementation, integration, fix summaries)
  - Reports: 7 files (analysis, audit, review reports)
  - Guides: 6 files (setup, implementation, quick start)
  - Analysis: 4 files (architecture, metrics, data viz)
  - Status Updates: 3 files
  - Checklists: 2 files
  - Plans: 2 files
  - Code Artifacts: 7 files (.js, .py, .html)

- **Topics:**
  - Dashboard: 15 files
  - Metrics: 11 files
  - Deployment: 6 files
  - Visualization: 5 files
  - Documentation: 4 files
  - Architecture: 2 files

- **Date Range:** October 13-26, 2025 (heavy activity on Oct 20-21, 23, 26)

**`archive/` - 5 files (not gitignored):**
- `dashboard-consolidation-fix-20251026/` - Fix implementation docs
- `fix-docs/` - General fix summaries
- `fixes/` - Ledger source fix
- `verification_scripts/` - Test verification scripts

### Issues with Current Structure

1. **Flat structure in `.archive/`** - Hard to navigate 131 files
2. **Inconsistent naming** - Mix of `YYYY-MM-DD_` and `YYYYMMDD_` formats
3. **Split locations** - Documents in both `.archive/` and `archive/`
4. **No categorization** - All files at root level
5. **Missing conventions** - No clear rules for where new docs go

---

## Proposed Structure

### Directory Hierarchy

```
.archive/
├── fixes/                    # Bug fixes and issue resolutions
│   ├── critical/            # P0/Critical production issues
│   ├── bugs/                # Standard bug fixes
│   └── improvements/        # Enhancement fixes
│
├── implementations/         # Feature implementations and integrations
│   ├── features/           # New feature implementations
│   ├── integrations/       # System integrations (APIs, data sources)
│   └── refactoring/        # Code refactoring work
│
├── reviews/                # Code reviews and assessments
│   ├── design-reviews/     # Architecture and design reviews
│   ├── code-reviews/       # Code quality reviews
│   └── peer-reviews/       # Peer review feedback
│
├── investigations/         # Research and analysis work
│   ├── analysis/           # Data analysis, metrics analysis
│   ├── diagnostics/        # Problem diagnosis, root cause analysis
│   └── research/           # Technology research, spike work
│
├── planning/              # Planning and strategy documents
│   ├── architecture/      # Architecture decisions and specs
│   ├── roadmaps/          # Project roadmaps and phases
│   └── strategies/        # Strategic planning docs
│
├── testing/              # Testing documentation
│   ├── test-reports/     # Test execution reports
│   ├── test-plans/       # Test planning and strategy
│   └── verification/     # Verification scripts and results
│
├── deployments/          # Deployment documentation
│   ├── releases/         # Release notes and summaries
│   ├── rollbacks/        # Rollback procedures and incidents
│   └── automation/       # Deployment automation docs
│
├── documentation/        # Documentation work (internal)
│   ├── cleanup/          # Documentation cleanup/restructure
│   ├── audits/           # Documentation audits
│   └── improvements/     # Documentation improvements
│
└── artifacts/           # Code artifacts and prototypes
    ├── scripts/         # Verification/utility scripts
    ├── prototypes/      # Prototype code (.js, .html, .css)
    └── patches/         # Temporary patches and workarounds
```

### Rationale for Structure

**8 Top-Level Categories:**
- Covers all major types of internal work
- Easy to remember and navigate
- Aligned with software development lifecycle
- Scales to hundreds of documents

**Subcategories:**
- Max 3-4 subcategories per category (avoids over-nesting)
- Based on priority/type rather than date
- Allows future expansion without restructuring

---

## Naming Convention

### Standard Format

```
YYYYMMDD_descriptive-label.md
```

**Rules:**
1. **Date:** 8 digits, no separators (20251026)
2. **Separator:** Single underscore after date
3. **Label:** Lowercase, kebab-case (hyphens between words)
4. **Extension:** `.md` for documents, preserve `.js/.py/.html` for code

**Examples:**
```
✅ GOOD:
20251026_dashboard-consolidation-fix.md
20251023_visualization-diagnostic-report.md
20251020_metrics-analysis-summary.md
20251019_phase-0-architecture.md

❌ BAD:
2025-10-26_DASHBOARD_CONSOLIDATION_FIX.md  # Wrong date format, uppercase
20251026_Dashboard_Fix.md                   # Snake_case instead of kebab-case
dashboard-fix-20251026.md                   # Date at end, not beginning
```

### Special Cases

**Multi-word Topics:**
```
20251026_bbc-somali-implementation.md
20251026_huggingface-integration-summary.md
20251026_sprakbanken-corpus-analysis.md
```

**Code Artifacts:**
```
20251025_pipeline-performance-charts.js
20251023_verification-script.py
20251025_demo-page.html
```

**Versions/Iterations:**
```
20251026_metrics-refactoring-v1.md
20251027_metrics-refactoring-v2.md
```

---

## Categorization Rules

### Decision Tree

```
START: What is this document?

│
├─ Did I fix a bug or resolve an issue?
│  └─ YES → fixes/
│      ├─ Production outage? → fixes/critical/
│      ├─ Standard bug? → fixes/bugs/
│      └─ Enhancement/improvement? → fixes/improvements/
│
├─ Did I implement or build something?
│  └─ YES → implementations/
│      ├─ New feature? → implementations/features/
│      ├─ System integration? → implementations/integrations/
│      └─ Code refactoring? → implementations/refactoring/
│
├─ Is this a code review or assessment?
│  └─ YES → reviews/
│      ├─ Architecture review? → reviews/design-reviews/
│      ├─ Code quality review? → reviews/code-reviews/
│      └─ Peer feedback? → reviews/peer-reviews/
│
├─ Did I investigate, analyze, or research something?
│  └─ YES → investigations/
│      ├─ Data/metrics analysis? → investigations/analysis/
│      ├─ Problem diagnosis? → investigations/diagnostics/
│      └─ Technology research? → investigations/research/
│
├─ Is this planning or architecture work?
│  └─ YES → planning/
│      ├─ Architecture decision? → planning/architecture/
│      ├─ Project roadmap? → planning/roadmaps/
│      └─ Strategic plan? → planning/strategies/
│
├─ Is this testing-related?
│  └─ YES → testing/
│      ├─ Test results? → testing/test-reports/
│      ├─ Test planning? → testing/test-plans/
│      └─ Verification script/result? → testing/verification/
│
├─ Is this deployment-related?
│  └─ YES → deployments/
│      ├─ Release notes? → deployments/releases/
│      ├─ Rollback incident? → deployments/rollbacks/
│      └─ Deployment automation? → deployments/automation/
│
├─ Did I work on internal documentation?
│  └─ YES → documentation/
│      ├─ Cleanup/restructure? → documentation/cleanup/
│      ├─ Audit? → documentation/audits/
│      └─ Improvements? → documentation/improvements/
│
└─ Is this code (script/prototype/patch)?
   └─ YES → artifacts/
       ├─ Utility script? → artifacts/scripts/
       ├─ Prototype code? → artifacts/prototypes/
       └─ Temporary patch? → artifacts/patches/
```

### Example Mappings

| Current Name | New Path | Rationale |
|--------------|----------|-----------|
| `2025-10-26_DASHBOARD_CONSOLIDATION_FIX.md` | `.archive/fixes/bugs/20251026_dashboard-consolidation-fix.md` | Bug fix |
| `2025-10-23_DESIGN_REVIEW_REPORT.md` | `.archive/reviews/design-reviews/20251023_design-review-report.md` | Design review |
| `2025-10-19_PHASE_0_ARCHITECTURE.md` | `.archive/planning/architecture/20251019_phase-0-architecture.md` | Architecture doc |
| `2025-10-20_METRICS_ANALYSIS_REPORT.md` | `.archive/investigations/analysis/20251020_metrics-analysis-report.md` | Analysis work |
| `2025-10-16_HUGGINGFACE_INTEGRATION_SUMMARY.md` | `.archive/implementations/integrations/20251016_huggingface-integration-summary.md` | Integration |
| `20251026_TEST_EXECUTION_REPORT.md` | `.archive/testing/test-reports/20251026_test-execution-report.md` | Test report |
| `verify_ledger_source_fix.py` | `.archive/artifacts/scripts/20251026_verify-ledger-source-fix.py` | Verification script |

---

## Migration Plan

### Phase 1: Prepare Directory Structure

```bash
# Create directory structure
cd .archive
mkdir -p fixes/{critical,bugs,improvements}
mkdir -p implementations/{features,integrations,refactoring}
mkdir -p reviews/{design-reviews,code-reviews,peer-reviews}
mkdir -p investigations/{analysis,diagnostics,research}
mkdir -p planning/{architecture,roadmaps,strategies}
mkdir -p testing/{test-reports,test-plans,verification}
mkdir -p deployments/{releases,rollbacks,automation}
mkdir -p documentation/{cleanup,audits,improvements}
mkdir -p artifacts/{scripts,prototypes,patches}
```

### Phase 2: Move Files from `archive/` to `.archive/`

```bash
# Move dashboard-consolidation-fix
mv ../archive/dashboard-consolidation-fix-20251026/*.md \
   fixes/bugs/

# Move fix-docs
mv ../archive/fix-docs/*.md \
   fixes/bugs/

# Move fixes
mv ../archive/fixes/*.md \
   fixes/bugs/

# Move verification scripts
mv ../archive/verification_scripts/*.py \
   artifacts/scripts/
```

### Phase 3: Categorize and Rename `.archive/` Files

**Automated Script Approach:**

```python
#!/usr/bin/env python3
"""
Migrate .archive/ files to new structure.
"""

import re
from pathlib import Path
from datetime import datetime

# Mapping rules (keyword → category)
CATEGORY_MAP = {
    'fix': 'fixes/bugs',
    'bug': 'fixes/bugs',
    'critical': 'fixes/critical',
    'implementation': 'implementations/features',
    'integration': 'implementations/integrations',
    'refactoring': 'implementations/refactoring',
    'design-review': 'reviews/design-reviews',
    'code-review': 'reviews/code-reviews',
    'peer-review': 'reviews/peer-reviews',
    'analysis': 'investigations/analysis',
    'diagnostic': 'investigations/diagnostics',
    'research': 'investigations/research',
    'architecture': 'planning/architecture',
    'roadmap': 'planning/roadmaps',
    'strategic-plan': 'planning/strategies',
    'phase': 'planning/roadmaps',
    'test-report': 'testing/test-reports',
    'test-execution': 'testing/test-reports',
    'testing-guide': 'testing/test-plans',
    'verification': 'testing/verification',
    'deployment': 'deployments/releases',
    'release': 'deployments/releases',
    'rollback': 'deployments/rollbacks',
    'documentation': 'documentation/cleanup',
    'audit': 'documentation/audits',
}

def normalize_filename(filename: str) -> str:
    """Convert to YYYYMMDD_kebab-case.ext format."""
    # Extract date (YYYY-MM-DD or YYYYMMDD)
    date_match = re.match(r'(\d{4})-?(\d{2})-?(\d{2})_', filename)
    if not date_match:
        return filename  # Keep as-is if no date

    date = f"{date_match.group(1)}{date_match.group(2)}{date_match.group(3)}"

    # Extract rest of filename
    rest = filename[date_match.end():]

    # Convert to lowercase kebab-case
    rest = rest.lower()
    rest = re.sub(r'[_\s]+', '-', rest)
    rest = re.sub(r'-+', '-', rest)

    return f"{date}_{rest}"

def categorize_file(filename: str) -> str:
    """Determine category path for file."""
    lower = filename.lower()

    # Check each keyword
    for keyword, category in CATEGORY_MAP.items():
        if keyword in lower:
            return category

    # Default fallback
    return 'investigations/diagnostics'

# Example usage
def migrate_file(src: Path, dest_base: Path):
    """Migrate a single file."""
    new_name = normalize_filename(src.name)
    category = categorize_file(new_name)
    dest = dest_base / category / new_name

    print(f"{src.name} → {category}/{new_name}")
    # Uncomment to perform actual move:
    # src.rename(dest)
```

### Phase 4: Remove Empty `archive/` Directory

```bash
# After all files moved
rmdir archive/dashboard-consolidation-fix-20251026
rmdir archive/fix-docs
rmdir archive/fixes
rmdir archive/verification_scripts
rmdir archive

# Update .gitignore (remove 'archive/' if present)
```

### Phase 5: Validation

```bash
# Verify structure
tree .archive/ -L 2

# Check for files at root (should be none after migration)
ls .archive/*.md 2>/dev/null && echo "WARNING: Files still at root"

# Verify naming convention
find .archive/ -name "*.md" | grep -E "^[0-9]{8}_" || echo "Some files don't follow naming convention"
```

---

## Process Guide for Future Documents

### When Creating a New Internal Document

**Step 1: Choose Document Type**
- What am I documenting? (fix, implementation, review, investigation, etc.)

**Step 2: Determine Category**
- Use the Decision Tree above
- If unsure, default to `investigations/diagnostics/`

**Step 3: Name the File**
```bash
# Format: YYYYMMDD_descriptive-label.md
DATE=$(date +%Y%m%d)
LABEL="your-descriptive-label"
FILE="${DATE}_${LABEL}.md"
```

**Step 4: Create File in Correct Location**
```bash
# Example: Bug fix summary
touch .archive/fixes/bugs/20251026_your-bug-fix.md

# Example: Architecture decision
touch .archive/planning/architecture/20251026_your-architecture-decision.md

# Example: Test report
touch .archive/testing/test-reports/20251026_your-test-report.md
```

**Step 5: Use Template (Optional)**

```markdown
# [Title]

**Date:** YYYY-MM-DD
**Category:** [Fix/Implementation/Review/Investigation/etc.]
**Status:** [In Progress/Complete/Archived]

---

## Summary
Brief overview of the work.

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
- Link to PR/issue
- Related docs
```

### Archiving Rules

**When to Archive:**
- Fix completed and verified
- Implementation merged to main
- Review feedback addressed
- Investigation concluded
- Testing phase complete

**What NOT to Archive:**
- User-facing documentation (goes in `docs/`)
- Active work-in-progress (keep in working directory)
- Temporary scratch notes (delete instead)

**Archive Within 24 Hours:**
- After PR merge
- After hotfix deployment
- After test cycle completion
- After review meeting conclusion

---

## Maintenance Guidelines

### Quarterly Cleanup (Every 3 Months)

1. **Review old documents** (>6 months)
   - Archive to compressed format if needed
   - Delete truly obsolete docs

2. **Consolidate duplicates**
   - Merge similar fix summaries
   - Remove redundant reports

3. **Update index** (optional)
   - Generate README.md with file listing
   - Update category descriptions

### Search and Navigation

**Finding Documents:**

```bash
# By date range
find .archive/ -name "202510*.md"  # October 2025

# By category
ls .archive/fixes/bugs/

# By keyword (full-text search)
grep -r "dashboard" .archive/

# By file type
find .archive/ -name "*.py"  # All Python scripts
```

**Tree View:**
```bash
tree .archive/ -L 2  # 2-level overview
tree .archive/fixes/  # Full fixes tree
```

### Git Integration

**Keep `.archive/` gitignored:**
- These are internal working documents
- Not needed by other developers
- Reduces repository bloat
- Personal development notes

**If team wants shared history:**
- Consider separate internal-docs repository
- Or move to team wiki/Confluence
- NOT recommended in main codebase

---

## Tool Support (Optional Future Enhancement)

### Archive Helper Script

```bash
# .archive/archive.sh - Helper script for common tasks

#!/bin/bash
# Archive helper for internal documents

case "$1" in
  new)
    # Create new archive document
    category="$2"
    label="$3"
    date=$(date +%Y%m%d)
    file=".archive/${category}/${date}_${label}.md"
    mkdir -p "$(dirname "$file")"
    touch "$file"
    echo "Created: $file"
    ;;

  find)
    # Search archives
    grep -r "$2" .archive/
    ;;

  list)
    # List by category
    tree ".archive/$2"
    ;;

  stats)
    # Show statistics
    echo "Total documents: $(find .archive/ -name "*.md" | wc -l)"
    echo "By category:"
    for cat in fixes implementations reviews investigations planning testing deployments documentation artifacts; do
      count=$(find ".archive/$cat" -name "*.md" 2>/dev/null | wc -l)
      echo "  $cat: $count"
    done
    ;;

  *)
    echo "Usage: archive.sh {new|find|list|stats} [args]"
    ;;
esac
```

Usage:
```bash
# Create new fix document
./archive.sh new fixes/bugs dashboard-data-fix

# Search archives
./archive.sh find "metrics"

# List category
./archive.sh list fixes/bugs

# Show stats
./archive.sh stats
```

---

## Benefits of This Design

### Immediate Benefits

1. **Easy Navigation** - Clear categories, no more 131-file flat structure
2. **Consistent Naming** - Single format, easy to sort chronologically
3. **Scalability** - Handles hundreds of documents without restructure
4. **Clear Rules** - Decision tree makes categorization obvious
5. **Searchability** - Both hierarchical browsing and grep-friendly

### Long-Term Benefits

1. **Knowledge Management** - Easy to find historical decisions
2. **Onboarding** - New developers can explore past work
3. **Audit Trail** - Clear record of fixes and implementations
4. **Quality Improvement** - Review past mistakes/successes
5. **Team Coordination** - Shared understanding of internal processes

### Maintenance Benefits

1. **Low Overhead** - Simple structure, minimal upkeep
2. **Self-Documenting** - Directory names explain purpose
3. **Tool-Friendly** - Works with standard Unix tools (find, grep, tree)
4. **Future-Proof** - Easy to extend with new categories

---

## Success Metrics

**After Migration:**
- [ ] All 131+ files categorized and renamed
- [ ] Zero files at `.archive/` root level
- [ ] All filenames follow `YYYYMMDD_kebab-case.md` format
- [ ] `archive/` directory removed
- [ ] Documentation updated (this file archived)

**After 1 Month:**
- [ ] All new documents follow process guide
- [ ] No confusion about where to put new docs
- [ ] Easy to find historical documents

**After 3 Months:**
- [ ] First quarterly cleanup completed
- [ ] Team feedback incorporated
- [ ] Process refinements documented

---

## Appendix: Quick Reference

### Cheat Sheet

| I did... | Category | Path |
|----------|----------|------|
| Fixed a bug | Fixes | `.archive/fixes/bugs/` |
| Built a feature | Implementation | `.archive/implementations/features/` |
| Integrated system | Implementation | `.archive/implementations/integrations/` |
| Reviewed code | Review | `.archive/reviews/code-reviews/` |
| Analyzed data | Investigation | `.archive/investigations/analysis/` |
| Diagnosed problem | Investigation | `.archive/investigations/diagnostics/` |
| Designed architecture | Planning | `.archive/planning/architecture/` |
| Ran tests | Testing | `.archive/testing/test-reports/` |
| Deployed release | Deployment | `.archive/deployments/releases/` |
| Cleaned up docs | Documentation | `.archive/documentation/cleanup/` |
| Wrote script | Artifact | `.archive/artifacts/scripts/` |

### File Naming Examples

```bash
# Good filenames
20251026_dashboard-consolidation-fix.md
20251026_metrics-phase1-implementation.md
20251026_architecture-design-review.md
20251026_ledger-source-preservation-fix.md
20251026_test-execution-report.md

# Bad filenames (DON'T DO THIS)
2025-10-26_DASHBOARD_FIX.md           # Wrong date format, uppercase
DashboardFix.md                        # No date, PascalCase
fix-summary.md                         # No date
20251026_Fix_For_Dashboard_Bug.md      # Snake_case instead of kebab-case
```

### Command Examples

```bash
# Create new document
DATE=$(date +%Y%m%d)
touch .archive/fixes/bugs/${DATE}_my-new-fix.md

# Find documents from today
find .archive/ -name "$(date +%Y%m%d)*.md"

# List all fixes
ls .archive/fixes/*/*.md

# Search for keyword
grep -r "metrics" .archive/ | cut -d: -f1 | sort -u

# Count documents by category
for dir in .archive/*/; do
  count=$(find "$dir" -name "*.md" | wc -l)
  echo "$(basename "$dir"): $count"
done
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-26 | Initial design |

---

**Author:** System Architect
**Reviewers:** Pending
**Status:** Awaiting Approval
**Next Steps:** Review → Approve → Migrate
