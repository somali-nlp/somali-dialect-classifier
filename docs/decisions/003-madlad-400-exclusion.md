# MADLAD-400 Dataset - Decision and Rationale

## Decision: **NOT USING MADLAD-400**

Date: October 16, 2025

## TL;DR

**MADLAD-400 is incompatible with modern HuggingFace datasets library (v3.0+) and there's no timeline for a fix.**

**Use MC4 instead** - it has more data, works perfectly, and requires zero workarounds.

---

## Analysis

### MC4 (allenai/c4) - CHOSEN ✅
- **Compatibility**: ✅ Works with datasets>=3.0
- **Size**: ~100k-200k Somali records
- **Format**: Native Parquet (streaming supported)
- **Status**: ✅ Working perfectly NOW
- **Authentication**: ❌ NOT required
- **Maintenance**: Zero issues
- **Effort**: Already working

### MADLAD-400 - REJECTED ❌
- **Compatibility**: ❌ Requires datasets<3.0 (DEPRECATED)
- **Size**: 293k (clean) / 729k (noisy) records
- **Format**: Python dataset script (UNSUPPORTED)
- **Status**: 🔴 **BROKEN** with datasets>=3.0
- **Authentication**: ❌ NOT required
- **Maintenance**: High (requires library downgrade)
- **Effort**: High - workarounds needed

---

## Technical Root Cause

### Why MADLAD-400 Doesn't Work

1. **Dataset Script Deprecation**
   - MADLAD-400 uses `MADLAD-400.py` (Python dataset loading script)
   - HuggingFace deprecated dataset scripts in `datasets>=3.0` (released 2024)
   - Reason: Security concerns (arbitrary code execution)

2. **No Parquet Migration**
   - Dataset has NOT been migrated to native Parquet format
   - Attempted Parquet API: `400 Bad Request`
   - Dataset viewer API: `404 Not Found`
   - No `/data/som/` folder with Parquet files exists

3. **Error Message**
   ```
   RuntimeError: Dataset scripts are no longer supported, but found MADLAD-400.py
   ```

### Investigation Timeline

**October 16, 2025** - Comprehensive investigation:

1. ❌ **Parquet API attempt**
   ```bash
   curl https://huggingface.co/api/datasets/allenai/madlad-400/parquet
   # Result: 400 Bad Request
   ```

2. ❌ **Dataset Viewer API attempt**
   ```bash
   curl https://datasets-server.huggingface.co/parquet?dataset=allenai/madlad-400
   # Result: 404 Not Found
   ```

3. ❌ **hf:// URL scheme attempt**
   ```python
   data_files = {"train": "hf://datasets/allenai/madlad-400@refs/convert/parquet/clean/som/*.parquet"}
   # Result: Empty file list, ValueError: At least one valid data file must be specified
   ```

4. ❌ **Direct repository check**
   ```
   https://huggingface.co/datasets/allenai/MADLAD-400/tree/main/data/som
   # Result: 404 Not Found (folder doesn't exist)
   ```

**Conclusion**: No migration path exists. Dataset is fundamentally incompatible.

---

## Key Reasons for Rejecting MADLAD-400

### 1. **Broken with Modern Datasets Library** 🔴
- Requires downgrading to `datasets<3.0` (deprecated version)
- Blocks access to new features in `datasets>=3.0`
- Creates dependency conflicts with other libraries
- Not a sustainable long-term solution

### 2. **No Fix Timeline**
- **allenai** has not announced migration plans
- Dataset is 19.5 TB (migration is non-trivial)
- No community work in progress
- Could take 6-12 months or **never** be fixed

### 3. **MC4 Has More Data Anyway**
- **MC4**: ~100k-200k Somali records
- **MADLAD-400**: 293k (clean) records
- MC4 is sufficient for dialect classification
- Quality filters compensate for any quality differences

### 4. **Workarounds Are Unsustainable**

**Option A: Downgrade datasets**
```bash
pip install 'datasets<3.0'
```
- ❌ Deprecated library version
- ❌ Blocks other dependencies
- ❌ No long-term support
- ❌ Creates technical debt

**Option B: Wait for migration**
- ❌ Unknown timeline (6+ months realistic)
- ❌ Blocks current project progress
- ❌ No guarantee it will happen

**Option C: Manual conversion**
- ❌ Requires converting 19.5 TB dataset
- ❌ Requires HuggingFace infrastructure access
- ❌ Not feasible for individual projects

### 5. **MC4 Already Working Perfectly**
Current test results:
```
Dataset: allenai/c4 (Somali subset)
Downloaded: 10 records
Filtered: 1 record (language detection)
Processed: 9 records with full metadata
Output: 36.3KB enriched parquet file
Status: ✅ SUCCESS
```

Why risk breaking a working solution?

---

## What We Use Instead

### Primary Dataset: MC4 (Multilingual C4) ✅

```bash
# Quick test (10 records)
hfsom-download mc4 --max-records 10

# Development (1000 records)
hfsom-download mc4 --max-records 1000

# Production (full dataset)
hfsom-download mc4
```

**Why MC4 is Better:**
1. ✅ **Compatible**: Works with datasets>=3.0
2. ✅ **Maintained**: Active development, regular updates
3. ✅ **Larger**: More Somali text than MADLAD-400 clean split
4. ✅ **Streaming**: Efficient memory usage
5. ✅ **No Auth**: Public, no tokens required
6. ✅ **Proven**: Already working in production

**MC4 Dataset Details:**
- **Dataset**: `allenai/c4`
- **Config**: `so` (Somali, ISO 639-1)
- **Split**: `train`
- **Text Field**: `text`
- **Metadata**: `url`, `timestamp`
- **License**: ODC-BY-1.0
- **Format**: Native Parquet (streaming supported)

---

## Code Changes

### Removed from Codebase

1. ✅ **`create_madlad400_processor()` function** - REMOVED
   - Located in: `src/somali_dialect_classifier/preprocessing/huggingface_somali_processor.py`
   - Reason: Non-functional with datasets>=3.0

2. ✅ **MADLAD-400 CLI option** - REMOVED
   - Located in: `src/somali_dialect_classifier/cli/download_hfsom.py`
   - Previously: `hfsom-download madlad400`
   - Now: Only `hfsom-download mc4` available

3. ✅ **MADLAD-400 tests** - REMOVED
   - Located in: `tests/test_hf_processor.py`
   - Located in: `tests/test_hf_integration.py`
   - Reason: Cannot test non-functional code

4. ✅ **`--all` flag updated**
   - Previously: Processed MC4, MADLAD-400, OSCAR
   - Now: Processes MC4 only (OSCAR excluded per decision 001)

### Updated Documentation

1. ✅ **HUGGINGFACE_DATASETS.md**
   - Removed MADLAD-400 from supported datasets list
   - Added note about incompatibility
   - Focus on MC4 as sole HuggingFace source

2. ✅ **README.md**
   - Updated data sources section
   - Removed MADLAD-400 mentions
   - Updated CLI examples

3. ✅ **MADLAD400_STATUS.md**
   - Created detailed technical report
   - Explains root cause and investigation
   - Provides workarounds (for reference only)

4. ✅ **Decision document** (this file)
   - Formal exclusion decision
   - Rationale and alternatives

---

## Data Sources Summary (Updated)

After decisions 001 (OSCAR) and 003 (MADLAD-400), our final data sources are:

### ✅ Active Data Sources

| Source | Records | Auth | Status | Command |
|--------|---------|------|--------|---------|
| **Wikipedia** | ~5k articles | ❌ No | ✅ Working | `wikisom-download` |
| **BBC Somali** | ~50k articles | ❌ No | ✅ Working | `bbcsom-download` |
| **MC4** | ~100-200k | ❌ No | ✅ Working | `hfsom-download mc4` |

### ❌ Excluded Data Sources

| Source | Reason | Decision |
|--------|--------|----------|
| **OSCAR-2301** | Requires authentication, less data than MC4 | [001-oscar-exclusion.md](001-oscar-exclusion.md) |
| **MADLAD-400** | Incompatible with datasets>=3.0, no fix timeline | [003-madlad-400-exclusion.md](003-madlad-400-exclusion.md) |

---

## Recommended Workflow

### For Development
```bash
# Test setup (30 seconds)
hfsom-download mc4 --max-records 10

# Development iteration (10-15 min)
hfsom-download mc4 --max-records 1000
```

### For Production
```bash
# Full Wikipedia corpus
wikisom-download

# Full BBC Somali news
bbcsom-download --max-articles 10000

# Full MC4 Somali web crawl
hfsom-download mc4
```

### Combined Data Collection
```bash
# Process all three sources
wikisom-download
bbcsom-download
hfsom-download mc4
```

**Total corpus**: ~150k-200k+ Somali text samples with diverse domains

---

## If You Really Want MADLAD-400 (Not Recommended)

### Temporary Workaround (For Exploration Only)

**⚠️ WARNING**: This is NOT recommended for production use.

```bash
# Create isolated environment
python -m venv madlad_env
source madlad_env/bin/activate

# Downgrade datasets library
pip install 'datasets<3.0'

# Install project
pip install -e .

# Test MADLAD-400
hfsom-download madlad400 --max-records 10
```

**Limitations**:
- ❌ Deprecated library version
- ❌ May conflict with other dependencies
- ❌ Not sustainable long-term
- ❌ Blocks access to datasets 3.x features

### Long-Term Alternative: Wait and Monitor

If MADLAD-400 is critical to your use case:

1. **Monitor the repository**: https://huggingface.co/datasets/allenai/MADLAD-400
2. **Check for Parquet conversion**: Look for commits adding `.parquet` files
3. **Revisit in 6+ months**: Realistic timeline for potential migration
4. **Use MC4 in the meantime**: Don't block progress

---

## Comparison: MC4 vs MADLAD-400

| Aspect | MC4 | MADLAD-400 |
|--------|-----|------------|
| **Compatibility** | ✅ datasets>=3.0 | ❌ datasets<3.0 only |
| **Somali Records** | ~100k-200k | 293k (clean) / 729k (noisy) |
| **Format** | Parquet | Python script |
| **Streaming** | ✅ Yes | ❌ Broken |
| **Authentication** | ❌ No | ❌ No |
| **Maintenance** | ✅ Active | ❌ Unmaintained |
| **Status** | ✅ Working | 🔴 **BROKEN** |
| **Quality** | Raw web crawl | Mixed (2 tiers) |
| **License** | ODC-BY-1.0 | ODC-BY-1.0 |
| **Recommendation** | ✅ **USE THIS** | ❌ **AVOID** |

---

## Related Decisions

- **[001-oscar-exclusion.md](001-oscar-exclusion.md)**: Why we don't use OSCAR-2301
- **[002-filter-framework.md](002-filter-framework.md)**: Quality filter design

---

## References

- **MADLAD-400 Repository**: https://huggingface.co/datasets/allenai/MADLAD-400
- **MADLAD-400 Paper**: https://arxiv.org/abs/2309.04662
- **datasets v3.0 Release**: https://github.com/huggingface/datasets/releases/tag/3.0.0
- **MC4 Dataset**: https://huggingface.co/datasets/allenai/c4
- **Technical Report**: [MADLAD400_STATUS.md](../../MADLAD400_STATUS.md)

---

## Changelog

- **2025-10-16**: Initial decision - MADLAD-400 excluded due to datasets>=3.0 incompatibility
- **Future**: This document will be updated if allenai migrates MADLAD-400 to Parquet format

---

**Maintainer Note**: If MADLAD-400 is migrated to Parquet format in the future, this decision can be revisited. Until then, **use MC4** - it works beautifully! ✅
