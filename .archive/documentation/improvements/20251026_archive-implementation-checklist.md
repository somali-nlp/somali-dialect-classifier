# Archive Organization - Implementation Checklist

**Date:** 2025-10-26
**Estimated Time:** 10-15 minutes
**Risk Level:** Low (non-destructive, can rollback via git)

---

## Pre-Migration Checklist

### 1. Review Design Documents

- [ ] Read `ARCHIVE_SUMMARY.md` (high-level overview)
- [ ] Review `ARCHIVE_ORGANIZATION_DESIGN.md` (full specification)
- [ ] Check `ARCHIVE_QUICK_REFERENCE.md` (usage guide)
- [ ] Understand directory structure (8 categories, 27 subcategories)
- [ ] Understand naming convention (`YYYYMMDD_kebab-case.md`)

### 2. Backup Current State

```bash
# Create git commit to preserve current state
cd /Users/ilyas/Desktop/Computer\ Programming/somali-nlp-projects/somali-dialect-classifier

git add .archive/ archive/ 2>/dev/null
git commit -m "chore(archive): backup before reorganization"
```

**Status:** [ ] Complete

### 3. Verify Tools

```bash
# Check Python is available
python3 --version  # Should be 3.7+

# Check migration script exists
ls migrate_archives.py

# Check script is executable
chmod +x migrate_archives.py
```

**Status:** [ ] Complete

### 4. Preview Migration

```bash
# Run in dry-run mode to see what will happen
python migrate_archives.py --dry-run | less

# Check statistics
python migrate_archives.py --stats
```

**Expected Output:**
- Total files: 132
- Categories: 8 (fixes, implementations, reviews, etc.)
- Subcategories: 27

**Status:** [ ] Complete

---

## Migration Execution

### Step 1: Run Migration

```bash
# Execute migration
python migrate_archives.py

# Save output to log (optional)
python migrate_archives.py 2>&1 | tee migration.log
```

**Expected:**
- Creates directory structure (27 subdirectories)
- Moves 132 files
- Renames files to standard format
- Removes empty `archive/` directory

**Status:** [ ] Complete

### Step 2: Verify Results

```bash
# Check directory structure
tree .archive/ -L 2

# Count files (should be 132)
find .archive/ -name "*.md" | wc -l

# Verify no files at root
ls .archive/*.md 2>&1 | grep "No such file"

# Check archive/ removed
ls archive/ 2>&1 | grep "No such file"
```

**Expected:**
- 132 files in organized structure
- Zero files at `.archive/` root
- `archive/` directory gone

**Status:** [ ] Complete

### Step 3: Spot Check Files

```bash
# Check a few files to verify correct placement
ls .archive/fixes/bugs/20251026_*.md
ls .archive/implementations/features/20251019_*.md
ls .archive/planning/architecture/20251019_*.md
ls .archive/investigations/analysis/20251020_*.md
```

**Status:** [ ] Complete

### Step 4: Verify Naming Convention

```bash
# All files should start with YYYYMMDD_
find .archive/ -name "*.md" | head -20

# Check for any old naming format
find .archive/ -name "????-??-??_*.md" | wc -l  # Should be 0
```

**Status:** [ ] Complete

---

## Post-Migration Tasks

### Step 1: Archive Design Documents

```bash
# Move design docs to archive
DATE=$(date +%Y%m%d)

# Archive full design
mv ARCHIVE_ORGANIZATION_DESIGN.md \
   .archive/documentation/improvements/${DATE}_archive-organization-design.md

# Archive quick reference
mv ARCHIVE_QUICK_REFERENCE.md \
   .archive/documentation/improvements/${DATE}_archive-quick-reference.md

# Archive summary
mv ARCHIVE_SUMMARY.md \
   .archive/documentation/improvements/${DATE}_archive-summary.md

# Archive migration script
mv migrate_archives.py \
   .archive/artifacts/scripts/${DATE}_migrate-archives.py

# Archive this checklist
mv ARCHIVE_IMPLEMENTATION_CHECKLIST.md \
   .archive/documentation/improvements/${DATE}_archive-implementation-checklist.md

# Archive migration log (if created)
if [ -f migration.log ]; then
  mv migration.log .archive/documentation/improvements/${DATE}_migration.log
fi
```

**Status:** [ ] Complete

### Step 2: Commit Changes

```bash
# Stage all changes
git add .archive/ archive/

# Commit with descriptive message
git commit -m "chore(archive): reorganize internal documents into scalable structure

- Migrated 132 files from flat structure to 8-category hierarchy
- Standardized naming: YYYYMMDD_kebab-case.md
- Created 27 subcategories for better organization
- Consolidated archive/ directory into .archive/
- Added README and categorization guide

See .archive/documentation/improvements/20251026_archive-organization-design.md
for full specification."
```

**Status:** [ ] Complete

### Step 3: Verify Git Status

```bash
# Check git status
git status

# Should show clean working tree
```

**Status:** [ ] Complete

---

## Validation Checklist

### Directory Structure

- [ ] `.archive/` exists and is gitignored
- [ ] 8 top-level categories exist (fixes, implementations, reviews, etc.)
- [ ] 27 subcategories exist
- [ ] All directories have proper structure (2 levels max)
- [ ] `archive/` directory removed

### Files

- [ ] 132 total files accounted for
- [ ] All files follow `YYYYMMDD_kebab-case.md` naming
- [ ] No files at `.archive/` root level
- [ ] Files correctly categorized (spot check 10-15 files)
- [ ] Code artifacts (.js, .py) in `artifacts/` subdirectories

### Documentation

- [ ] `.archive/README.md` updated with new structure
- [ ] Design documents archived
- [ ] Migration script archived
- [ ] This checklist archived

### Git

- [ ] Changes committed
- [ ] Clean working tree
- [ ] Can rollback if needed (`git revert HEAD`)

---

## Testing New Workflow

### Test 1: Create New Archive Document

```bash
# Create a test fix summary
DATE=$(date +%Y%m%d)
cat > .archive/fixes/bugs/${DATE}_test-document.md <<EOF
# Test Document

**Date:** $(date +%Y-%m-%d)
**Status:** Test

This is a test document to verify the new archive structure works.
EOF

# Verify file created
ls .archive/fixes/bugs/${DATE}_test-document.md
```

**Status:** [ ] Complete

### Test 2: Search Archives

```bash
# Search by keyword
grep -r "dashboard" .archive/ | head -5

# Find by date
find .archive/ -name "20251026*.md" | head -5

# List category
ls .archive/implementations/features/ | head -5
```

**Status:** [ ] Complete

### Test 3: Navigate Structure

```bash
# View structure
tree .archive/ -L 2

# Count by category
for cat in fixes implementations reviews investigations planning testing deployments documentation artifacts; do
  count=$(find ".archive/$cat" -name "*.md" 2>/dev/null | wc -l)
  printf "%-20s %3d\n" "$cat:" "$count"
done
```

**Status:** [ ] Complete

### Test 4: Cleanup Test Document

```bash
# Remove test document
DATE=$(date +%Y%m%d)
rm .archive/fixes/bugs/${DATE}_test-document.md
```

**Status:** [ ] Complete

---

## Rollback Procedure (If Needed)

**Only if something went wrong:**

```bash
# Rollback to pre-migration state
git log --oneline | head -5  # Find commit hash before migration
git revert <commit-hash>     # Revert the migration commit

# Or hard reset (DESTRUCTIVE)
git reset --hard HEAD~1

# Restore from backup commit
git checkout <backup-commit-hash> -- .archive/ archive/
```

**Note:** Migration is non-destructive. All files are moved, not deleted.

---

## Success Criteria

### Quantitative

- [x] 132 files migrated successfully
- [x] 100% consistent naming convention
- [x] Zero files at `.archive/` root level
- [x] Single archive location (`.archive/`)
- [x] 8 categories, 27 subcategories created

### Qualitative

- [ ] Easy to find historical documents
- [ ] Clear where new documents should go
- [ ] Team can navigate without training
- [ ] Search functionality works well
- [ ] Structure scales to future growth

---

## Known Issues & Workarounds

### Issue: File Already Exists

**Problem:** Migration fails because destination file already exists

**Solution:**
```bash
# The script should handle this, but if manual fix needed:
mv .archive/category/conflicting-file.md \
   .archive/category/conflicting-file-old.md
```

### Issue: Permission Denied

**Problem:** Cannot create directories or move files

**Solution:**
```bash
# Fix permissions
chmod -R u+w .archive/
chmod -R u+w archive/
```

### Issue: Python Script Error

**Problem:** Migration script encounters error

**Solution:**
```bash
# Check Python version
python3 --version  # Must be 3.7+

# Run with verbose output
python migrate_archives.py --verbose

# Check error logs
python migrate_archives.py 2>&1 | tee error.log
```

---

## Timeline

| Step | Estimated Time | Actual Time |
|------|----------------|-------------|
| Pre-migration review | 5 min | ___ min |
| Backup & preview | 2 min | ___ min |
| Execute migration | 1 min | ___ min |
| Verify results | 2 min | ___ min |
| Post-migration tasks | 3 min | ___ min |
| Testing | 2 min | ___ min |
| **TOTAL** | **15 min** | **___ min** |

---

## Sign-Off

### Implementation Team

- [ ] **Implementer:** _________________ Date: _________
- [ ] **Reviewer:** _________________ Date: _________
- [ ] **Approver:** _________________ Date: _________

### Verification

- [ ] All files migrated successfully
- [ ] No data loss
- [ ] Structure as designed
- [ ] Documentation updated
- [ ] Team notified

---

## Next Steps After Migration

1. **Update Team**
   - Share `ARCHIVE_QUICK_REFERENCE.md` (now archived)
   - Brief team on new categorization rules
   - Answer questions

2. **Monitor Usage**
   - Track if team follows new process
   - Collect feedback
   - Adjust if needed

3. **Quarterly Review**
   - Review after 3 months
   - Assess if categories are appropriate
   - Refine process based on usage

4. **Documentation**
   - Keep `.archive/README.md` updated
   - Document any process changes
   - Update this checklist if needed

---

## Support

**Questions?**
- Quick Reference: `.archive/documentation/improvements/20251026_archive-quick-reference.md`
- Full Design: `.archive/documentation/improvements/20251026_archive-organization-design.md`
- Migration Script: `.archive/artifacts/scripts/20251026_migrate-archives.py`

**Issues?**
- Check "Known Issues & Workarounds" section above
- Review migration log: `migration.log`
- Can always rollback via git

---

**Status:** [ ] Not Started | [ ] In Progress | [ ] Complete

**Completion Date:** _______________

**Notes:**
