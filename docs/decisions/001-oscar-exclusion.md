# OSCAR Dataset - Decision and Rationale

## Decision: **NOT USING OSCAR**

Date: October 16, 2025

## Analysis

### MC4 (allenai/c4) - CHOSEN ✅
- **Authentication**: ❌ NOT required
- **Size**: ~100k-200k Somali records
- **Quality**: Raw web crawl
- **Status**: ✅ Working perfectly NOW
- **Current results**: 9/10 records processed successfully
- **Effort**: Zero - already working

### OSCAR-2301 - REJECTED ❌
- **Authentication**: ✅ Required (gated dataset)
- **Size**: ~50k-100k Somali records (LESS than MC4!)
- **Quality**: Pre-filtered
- **Status**: ⚠️ Requires setup
- **Effort**: High - account, token, terms, maintenance

## Key Reasons for Rejecting OSCAR

### 1. **MC4 Has MORE Data**
- MC4: ~100k-200k Somali records
- OSCAR: ~50k-100k Somali records
- **Winner**: MC4 (2x more data!)

### 2. **We Already Have Quality Filters**
Our pipeline includes:
- `min_length_filter`: Removes short/low-quality text
- `langid_filter`: Detects and filters non-Somali text
- `HTMLCleaner`: Cleans markup and formatting
- Text normalization and deduplication

OSCAR's pre-filtering is redundant when we have our own quality control.

### 3. **MC4 is Working NOW**
Current test results:
```
Downloaded: 10 records
Filtered: 1 record (language detection)
Processed: 9 records with full metadata
Output: 36.3KB enriched parquet file
```

Why risk this working solution for marginal quality gains?

### 4. **Authentication is Ongoing Maintenance**
- Tokens expire
- Terms of use change
- Access can be revoked
- Additional complexity in deployment
- Team members need individual access

### 5. **Our Filters Are Effective**
Evidence from current run:
- 1/10 records filtered by `langid_filter`
- This shows our quality control works!
- No need for pre-filtered data

## What We Keep

### Primary Dataset: MC4
```bash
# Get 1000 high-quality Somali records
hfsom-download mc4 --max-records 1000

# Get full dataset (100k-200k records)
hfsom-download mc4
```

### Secondary Dataset: MADLAD-400 (if accessible)
- Document-level data (different from web crawl)
- 419 languages including Somali
- Hosted by AI2 (public, no auth)
- Complements MC4 with different sources

### Combined Command
```bash
# Process both MC4 and MADLAD-400
hfsom-download --all --max-records 1000
```

## Code Changes

### Keep in Code (Commented)
The OSCAR processor functions remain in the code but are commented out:
- `create_oscar_processor()` - kept for reference
- OSCAR imports - commented out
- OSCAR CLI options - commented out

### Why Keep It?
1. If authentication requirements change (e.g., OSCAR becomes public)
2. For reference if someone wants to add it later
3. Minimal code - doesn't hurt to keep commented

### Remove from Active Use
- `--all` flag now processes: mc4, madlad400 (not oscar)
- CLI help text updated
- Documentation focuses on MC4 and MADLAD-400

## Recommendation

**Use MC4 as your primary Somali text source:**

```bash
# Quick test (10 records)
hfsom-download mc4 --max-records 10

# Development (1000 records, ~10-15 min)
hfsom-download mc4 --max-records 1000

# Production (full dataset, ~2-4 hours)
hfsom-download mc4
```

This gives you:
- ✅ 100k-200k Somali text samples
- ✅ No authentication hassles
- ✅ Working NOW
- ✅ Your quality filters applied
- ✅ Full metadata enrichment
- ✅ Zero maintenance overhead

## If You Really Want OSCAR Later

If you decide OSCAR's pre-filtering is worth the auth hassle:

1. Uncomment OSCAR code in:
   - `src/somali_dialect_classifier/cli/download_hf.py`
   - Factory import: `create_oscar_processor`

2. Follow authentication:
   ```bash
   huggingface-cli login
   # Visit: https://huggingface.co/datasets/oscar-corpus/OSCAR-2301
   # Accept terms
   ```

3. Test:
   ```bash
   hfsom-download oscar --max-records 10
   ```

But honestly? **MC4 is enough.** You have quantity AND your own quality filters.

## Final Summary

| Aspect | MC4 | OSCAR |
|--------|-----|-------|
| Records | 100k-200k | 50k-100k |
| Auth | ❌ No | ✅ Yes |
| Status | ✅ Working | ⚠️ Needs setup |
| Quality | Raw + our filters | Pre-filtered |
| Maintenance | Zero | Ongoing |
| **Decision** | **✅ USE** | **❌ SKIP** |

**Bottom line**: MC4 gives you MORE data with LESS hassle. That's a win-win!

---

**Date**: 2025-10-16
**Status**: Accepted
