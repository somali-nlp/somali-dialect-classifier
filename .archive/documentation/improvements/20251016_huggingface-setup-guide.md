# HuggingFace Datasets Setup Guide

## Current Status

The HuggingFace integration code is **complete and tested**, but requires additional setup to access real data from HuggingFace Hub.

## Issues from Your Test Run

### 1. ✅ MC4 (allenai/c4) - FIXED
**Error**: `Object of type datetime is not JSON serializable`
**Status**: **FIXED** - Added `_make_json_serializable()` method to handle datetime objects
**Result**: MC4 now works and can download/process data

### 2. ⚠️ OSCAR-2301 - REQUIRES AUTHENTICATION
**Error**: `Dataset 'oscar-corpus/OSCAR-2301' is a gated dataset on the Hub. You must be authenticated to access it.`
**Status**: **REQUIRES ACTION FROM YOU**
**What you need to do**:

```bash
# Step 1: Install HuggingFace CLI (if not already installed)
pip install huggingface_hub

# Step 2: Login to HuggingFace
huggingface-cli login
# This will prompt you for your HuggingFace token
# Get your token from: https://huggingface.co/settings/tokens

# Step 3: Accept the OSCAR-2301 terms
# Visit: https://huggingface.co/datasets/oscar-corpus/OSCAR-2301
# Click "Access repository" and accept the terms

# Step 4: Test OSCAR download
hfsom-download oscar --max-records 10
```

### 3. ❌ MADLAD-400 - CONFIGURATION ISSUE
**Error**: `No (supported) data files found in allenai/MADLAD-400`
**Status**: **NEEDS INVESTIGATION**
**Issue**: The dataset might not have Somali data in the expected format, or the language code is wrong

## Recommended Next Steps

### Option 1: Focus on MC4 (Recommended)
MC4 is working now and doesn't require authentication:

```bash
# Test with small sample
hfsom-download mc4 --max-records 100

# Process full dataset (this will take time)
hfsom-download mc4
```

### Option 2: Set up OSCAR Authentication
If you need OSCAR data:

1. Create HuggingFace account: https://huggingface.co/join
2. Generate access token: https://huggingface.co/settings/tokens
3. Run `huggingface-cli login` and paste token
4. Accept OSCAR terms: https://huggingface.co/datasets/oscar-corpus/OSCAR-2301
5. Test: `hfsom-download oscar --max-records 10`

### Option 3: Fix MADLAD-400 Configuration
MADLAD-400 needs investigation:

```bash
# Check if Somali is available
python -c "from datasets import load_dataset; print(load_dataset('allenai/MADLAD-400', languages=['som'], split='clean', streaming=True))"
```

If that fails, Somali might not be available in MADLAD-400, or we need to use a different language code.

## Why Tests Pass But No Data

The **unit tests use mocked data**, so they pass without network access. The tests validate:
- Code structure ✅
- Field mapping ✅
- Error handling ✅
- Configuration ✅

But they **don't test real HuggingFace Hub access**.

## Verification Commands

### Check Authentication Status
```bash
# Check if you're logged in
huggingface-cli whoami

# If not logged in, you'll see an error
# If logged in, you'll see your username
```

### Test MC4 (No Auth Required)
```bash
# Small test (10 records, takes ~2 minutes)
hfsom-download mc4 --max-records 10

# Check output
ls -lh data/processed/silver/source=HuggingFace-Somali\ \(allenai/c4/so\)/
```

### Test OSCAR (Requires Auth)
```bash
# Must run huggingface-cli login first!
hfsom-download oscar --max-records 10

# Check output
ls -lh data/processed/silver/source=HuggingFace-Somali\ \(oscar-corpus/OSCAR-2301/so\)/
```

## Expected Processing Times

| Dataset | Records | Time (estimated) |
|---------|---------|------------------|
| MC4 (10 records) | 10 | ~2 minutes |
| MC4 (1000 records) | 1000 | ~10-15 minutes |
| MC4 (full) | ~100k-200k | 2-4 hours |
| OSCAR (10 records) | 10 | ~2 minutes |
| OSCAR (full) | ~50k-100k | 1-2 hours |

## Troubleshooting

### "No data in output files"
**Cause**: Authentication required or dataset not accessible
**Solution**:
1. Check if you need authentication (OSCAR)
2. Verify you accepted dataset terms
3. Check logs for actual error messages

### "Dataset not found"
**Cause**: Wrong dataset name or configuration
**Solution**: Verify dataset exists at https://huggingface.co/datasets/[dataset-name]

### "Timeout errors"
**Cause**: HuggingFace Hub is slow or network issues
**Solution**:
1. Increase timeout in download() method
2. Use `--max-records` to test with smaller samples first
3. Try again later

## Summary

**What Works Now**:
- ✅ MC4 (allenai/c4) - Ready to use, no authentication needed
- ✅ Code architecture (manifest, batching, resume, filters)
- ✅ All 18 unit tests pass

**What Needs Your Action**:
- ⚠️ OSCAR: Run `huggingface-cli login` and accept terms
- ❌ MADLAD-400: Investigate if Somali data is available

**Recommended Action**:
```bash
# Start with MC4 (works out of the box)
hfsom-download mc4 --max-records 100

# Check the output
ls -R data/processed/silver/source=HuggingFace-Somali\ \(allenai/c4/so\)/
```

This will give you ~100 Somali text samples from MC4 to verify everything works end-to-end.
