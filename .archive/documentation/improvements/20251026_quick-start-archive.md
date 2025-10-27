# Quick Start: Archive Phase 1 Documentation

**Time Required:** ~10 minutes (automated) + ~20 minutes (manual updates)

---

## TL;DR

```bash
# 1. Run the archive script
./archive_phase1_docs.sh

# 2. Update main README (copy from README_UPDATE.md)
# 3. Update .archive/README.md (copy from .archive/README_UPDATE.md)
# 4. Update docs/index.md (add metrics-migration.md to TOC)
# 5. Commit
git add .
git commit -m "docs(archive): organize Phase 1 metrics refactoring documentation"
```

---

## Step-by-Step

### 1. Run Archive Script (2 minutes)

```bash
cd /Users/ilyas/Desktop/Computer\ Programming/somali-nlp-projects/somali-dialect-classifier
./archive_phase1_docs.sh
```

**What it does:**
- Creates directory structure in docs/ and .archive/
- Moves user docs to docs/guides/
- Moves schemas to docs/reference/schemas/
- Moves examples to docs/reference/examples/
- Archives internal docs to .archive/2025-10-26-metrics-phase1/

**Expected result:**
```
✓ Moved METRICS_MIGRATION_GUIDE.md → docs/guides/metrics-migration.md
✓ Moved all_metrics_schema_v2.json → docs/reference/schemas/
✓ Archived 4 audit files
✓ Archived 4 investigation files
✓ Archived 3 verification files
```

### 2. Update README.md (5 minutes)

**Open:** `README.md`
**Copy content from:** `README_UPDATE.md`
**Location:** After project description, before "Features" section

**Verify:** README now has "Recent Updates" section mentioning Phase 1

### 3. Update .archive/README.md (5 minutes)

**Open:** `.archive/README.md`
**Copy content from:** `.archive/README_UPDATE.md`
**Location:** Under "Major Archive Collections" (after 2025-10-25 entry)

**Verify:** Archive README now has 2025-10-26 collection entry

### 4. Update docs/index.md (2 minutes)

**Open:** `docs/index.md`
**Add under "Guides" section:**
```markdown
- [Metrics Migration Guide](guides/metrics-migration.md) - Phase 1 metrics refactoring migration
```

### 5. Update docs/guides/dashboard.md (Optional, 3 minutes)

**Open:** `docs/guides/dashboard.md`
**Add under "Data Sources > Metrics Schema":**
```markdown
See [schema reference](../reference/schemas/all_metrics_schema_v2.json) for complete metrics structure.
```

### 6. Verify (3 minutes)

```bash
# User docs accessible?
ls docs/guides/metrics-migration.md
ls docs/reference/schemas/all_metrics_schema_v2.json
ls docs/reference/examples/*.json

# Archive organized?
ls .archive/2025-10-26-metrics-phase1/README.md
ls .archive/2025-10-26-metrics-phase1/audits/
ls .archive/2025-10-26-metrics-phase1/investigations/

# Root clean?
ls *.md  # Should see README, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT + temp files
```

### 7. Cleanup Temporary Files (1 minute)

```bash
rm DOCUMENTATION_ORGANIZATION_PLAN.md
rm DOCUMENTATION_CLEANUP_SUMMARY.md
rm QUICK_START_ARCHIVE.md
rm archive_phase1_docs.sh
rm README_UPDATE.md
rm .archive/README_UPDATE.md
```

### 8. Commit (2 minutes)

```bash
git add .
git status  # Review changes
git commit -m "docs(archive): organize Phase 1 metrics refactoring documentation

- Move metrics-migration.md to docs/guides/
- Move schemas and examples to docs/reference/
- Archive 13 internal docs to .archive/2025-10-26-metrics-phase1/
- Update README with Phase 1 summary
- Update archive index
- Clean up project root (22 → 4 markdown files)

Archive structure:
- audits/ (4 files): Verification of dynamic data usage
- investigations/ (4 files): BBC bug and success rate analysis
- verification/ (3 files): Dashboard and data flow verification

User-facing docs:
- docs/guides/metrics-migration.md: Complete migration guide
- docs/reference/schemas/: Schema examples
- docs/reference/examples/: Backward compatibility examples"
```

---

## Verification Checklist

After commit, verify:

- [ ] `docs/guides/metrics-migration.md` exists
- [ ] `docs/reference/schemas/all_metrics_schema_v2.json` exists
- [ ] `docs/reference/examples/` has 3 JSON files
- [ ] `.archive/2025-10-26-metrics-phase1/` exists with 3 subdirectories
- [ ] `.archive/2025-10-26-metrics-phase1/README.md` is comprehensive
- [ ] Main `README.md` mentions Phase 1
- [ ] `.archive/README.md` has 2025-10-26 entry
- [ ] `docs/index.md` links to metrics-migration.md
- [ ] Root has only 4-5 .md files (essential docs)
- [ ] All temporary files removed

---

## Troubleshooting

### Script fails with "file not found"
**Cause:** Some files already moved or don't exist
**Solution:** Check warnings in script output, manually verify file locations

### Git shows too many changes
**Cause:** Expected - you're moving ~18 files
**Solution:** Review with `git status` and `git diff --stat`

### Links broken after move
**Cause:** Relative paths changed
**Solution:** Update links in moved files to use correct relative paths

### Archive subdirectory empty
**Cause:** Script didn't run correctly
**Solution:** Re-run script or manually move files following DOCUMENTATION_ORGANIZATION_PLAN.md

---

## Quick Reference

### What Goes Where

| File Type | Location |
|-----------|----------|
| User guides | `docs/guides/` |
| Schemas | `docs/reference/schemas/` |
| Examples | `docs/reference/examples/` |
| Audits | `.archive/2025-10-26-metrics-phase1/audits/` |
| Investigations | `.archive/2025-10-26-metrics-phase1/investigations/` |
| Verification | `.archive/2025-10-26-metrics-phase1/verification/` |

### Key Files

| Purpose | File |
|---------|------|
| Comprehensive plan | `DOCUMENTATION_ORGANIZATION_PLAN.md` |
| This quick start | `QUICK_START_ARCHIVE.md` |
| Archive script | `archive_phase1_docs.sh` |
| README update content | `README_UPDATE.md` |
| Archive README content | `.archive/README_UPDATE.md` |
| Archive index | `.archive/2025-10-26-metrics-phase1/README.md` |
| Full summary | `DOCUMENTATION_CLEANUP_SUMMARY.md` |

---

**Total Time:** ~30-40 minutes
**Difficulty:** Easy (mostly automated)
**Risk:** Low (all changes tracked by git)
