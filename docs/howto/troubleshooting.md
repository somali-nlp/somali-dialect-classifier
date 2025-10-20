# Troubleshooting Guide

**Common issues and solutions for the Somali Dialect Classifier project.**

**Last Updated**: 2025-10-20

---

## Table of Contents

- [Installation Issues](#installation-issues)
- [Pipeline Execution Problems](#pipeline-execution-problems)
- [Data Quality Issues](#data-quality-issues)
- [Dashboard Problems](#dashboard-problems)
- [Performance Issues](#performance-issues)
- [Testing Failures](#testing-failures)
- [Configuration Errors](#configuration-errors)
- [Development Environment](#development-environment)

---

## Installation Issues

### Problem: pip install fails with dependency conflicts

**Symptoms**:
```
ERROR: Cannot install somali-dialect-classifier because these package versions have conflicts:
  - pandas>=2.0.0 conflicts with pyarrow<13.0.0
```

**Solutions**:

1. **Use a fresh virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install --upgrade pip
   pip install -e ".[config]"
   ```

2. **Specify compatible versions explicitly**:
   ```bash
   pip install pandas==2.0.3 pyarrow==13.0.0
   pip install -e ".[config]"
   ```

3. **Use pip's dependency resolver**:
   ```bash
   pip install -e ".[config]" --use-feature=fast-deps
   ```

### Problem: ModuleNotFoundError after installation

**Symptoms**:
```
ModuleNotFoundError: No module named 'somali_dialect_classifier'
```

**Solutions**:

1. **Verify installation**:
   ```bash
   pip list | grep somali
   # Should show: somali-dialect-classifier  0.1.0
   ```

2. **Reinstall in editable mode**:
   ```bash
   pip uninstall somali-dialect-classifier
   pip install -e .
   ```

3. **Check Python path**:
   ```python
   import sys
   print(sys.path)
   # Ensure your project directory is included
   ```

4. **Activate correct virtual environment**:
   ```bash
   which python  # Should point to venv/bin/python
   ```

### Problem: Optional dependencies missing

**Symptoms**:
```
ModuleNotFoundError: No module named 'datasets'
```

**Solutions**:

Install optional dependency groups:

```bash
# HuggingFace datasets support
pip install -e ".[datasets]"

# Configuration management
pip install -e ".[config]"

# All optional dependencies
pip install -e ".[all]"

# Development dependencies (testing, linting)
pip install -e ".[dev]"
```

---

## Pipeline Execution Problems

### Problem: Pipeline fails with "Permission denied" when writing files

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: 'data/bronze/...'
```

**Solutions**:

1. **Check directory permissions**:
   ```bash
   ls -ld data/bronze data/staging data/processed data/silver
   chmod 755 data data/bronze data/staging data/processed data/silver
   ```

2. **Ensure directories exist**:
   ```bash
   mkdir -p data/bronze data/staging data/processed data/silver
   mkdir -p data/metrics data/reports logs
   ```

3. **Check disk space**:
   ```bash
   df -h .
   # Ensure sufficient space (at least 5GB free)
   ```

### Problem: Wikipedia download fails with "HTTP 404"

**Symptoms**:
```
FileNotFoundError: Wikipedia dump not found at https://dumps.wikimedia.org/...
```

**Solutions**:

1. **Check dump availability**:
   - Visit https://dumps.wikimedia.org/sowiki/
   - Note the latest available date
   - Update config or use explicit date

2. **Specify valid dump date**:
   ```bash
   # Check available dumps
   curl -s https://dumps.wikimedia.org/sowiki/ | grep -o '[0-9]\{8\}' | sort -u | tail -5

   # Use valid date (format: YYYYMMDD)
   wikisom-download --dump-date 20241015
   ```

3. **Use backup mirrors**:
   ```bash
   # Set environment variable for mirror
   export WIKI_MIRROR="https://dumps.wikimedia.your_country.org"
   ```

### Problem: BBC scraping blocked or returns empty content

**Symptoms**:
```
WARNING: Fetched empty body for https://www.bbc.com/somali/...
```

**Solutions**:

1. **Check robots.txt compliance**:
   ```bash
   curl https://www.bbc.com/robots.txt
   # Ensure /somali is not disallowed
   ```

2. **Increase rate limiting delay**:
   ```python
   # In config.py or via environment variable
   SDC_BBC_RATE_LIMIT_DELAY=2.0  # Increase from 1.0 to 2.0 seconds
   ```

3. **Update CSS selectors** (if website changed):
   ```bash
   # Check if selectors are outdated
   python -c "
   from somali_dialect_classifier.preprocessing.bbc_somali_processor import BBCSomaliProcessor
   processor = BBCSomaliProcessor()
   # Manual debugging of selector logic
   "
   ```

4. **Use User-Agent header**:
   ```python
   # Already implemented, but verify:
   # In bbc_somali_processor.py, requests should include:
   # headers={"User-Agent": "Mozilla/5.0 ..."}
   ```

### Problem: HuggingFace dataset loading fails

**Symptoms**:
```
ConnectionError: Couldn't reach https://huggingface.co
```

**Solutions**:

1. **Check network connectivity**:
   ```bash
   ping huggingface.co
   curl -I https://huggingface.co
   ```

2. **Use offline mode** (if dataset cached):
   ```bash
   export HF_DATASETS_OFFLINE=1
   hfsom-download mc4 --max-records 1000
   ```

3. **Specify cache directory**:
   ```bash
   export HF_DATASETS_CACHE="/path/to/cache"
   hfsom-download mc4
   ```

4. **Use revision parameter** for datasets with script issues:
   ```bash
   # For MADLAD-400 "dataset scripts no longer supported" error
   hfsom-download madlad-400 --revision refs/convert/parquet
   ```

### Problem: Pipeline crashes with "Out of Memory"

**Symptoms**:
```
MemoryError: Unable to allocate array
OR
Killed (process terminated)
```

**Solutions**:

1. **Reduce batch size**:
   ```python
   # In processor initialization or via config
   processor = WikipediaSomaliProcessor(batch_size=1000)  # Default: 5000
   ```

2. **Enable streaming for large files**:
   ```python
   # For Wikipedia, already implemented with 10MB buffer
   # For HuggingFace, uses streaming by default
   ```

3. **Increase system memory**:
   ```bash
   # Check current memory
   free -h  # Linux
   vm_stat  # macOS

   # Close other applications
   # Or increase Docker memory limit (if using containers)
   ```

4. **Process in chunks**:
   ```bash
   # Wikipedia: Process smaller dump
   # BBC: Use --max-articles to limit
   bbcsom-download --max-articles 1000

   # HuggingFace: Use --max-records
   hfsom-download mc4 --max-records 10000
   ```

### Problem: Deduplication is too slow

**Symptoms**:
```
INFO: Deduplication stage taking >10 minutes for 10K records
```

**Solutions**:

1. **Adjust deduplication threshold**:
   ```bash
   # Increase threshold to reduce fuzzy matching
   export SDC_DEDUP_SIMHASH_THRESHOLD=0.95  # Default: 0.90
   ```

2. **Disable near-duplicate detection**:
   ```python
   # In deduplication module, set threshold to 1.0 (exact only)
   export SDC_DEDUP_SIMHASH_THRESHOLD=1.0
   ```

3. **Use faster hashing**:
   ```python
   # Already using SHA256, which is fast
   # Consider MD5 for non-cryptographic use (modify code)
   ```

---

## Data Quality Issues

### Problem: Many records rejected by filters

**Symptoms**:
```
INFO: Filtered 80% of records (8000/10000 rejected)
```

**Solutions**:

1. **Review filter statistics**:
   ```bash
   # Check quality report
   cat data/reports/latest_quality_report.md
   # Look for "Filter Rejections" section
   ```

2. **Adjust filter thresholds**:
   ```python
   # Lower minimum length
   min_length_filter(cleaned_text, threshold=30)  # Default: 50

   # Lower language confidence
   langid_filter(cleaned_text, confidence_threshold=0.3)  # Default: 0.5
   ```

3. **Inspect rejected samples**:
   ```python
   # Add logging to see rejected content
   # In BasePipeline.process(), add:
   if not passes:
       logger.warning(f"Rejected by {filter_name}: {cleaned_text[:100]}")
   ```

4. **Disable specific filters temporarily**:
   ```python
   # In processor._register_filters(), comment out problematic filter
   return [
       (min_length_filter, {"threshold": 50}),
       # (langid_filter, {"allowed_langs": {"so"}}),  # Disabled for debugging
   ]
   ```

### Problem: Language detection is inaccurate

**Symptoms**:
```
Somali text incorrectly detected as English or vice versa
```

**Solutions**:

1. **Review detected language metadata**:
   ```python
   # Check silver dataset
   import pandas as pd
   df = pd.read_parquet("data/silver/latest.parquet")
   print(df["source_metadata"].apply(lambda x: x.get("detected_lang")).value_counts())
   ```

2. **Expand Somali word vocabulary**:
   ```python
   # In filters.py, add domain-specific words to somali_words set
   somali_words.update(["your", "custom", "words"])
   ```

3. **Use external library** (advanced):
   ```bash
   pip install fasttext
   # Download language model
   wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin

   # Modify langid_filter to use fasttext
   ```

4. **Lower confidence threshold**:
   ```python
   langid_filter(cleaned_text, confidence_threshold=0.3)
   ```

### Problem: High duplicate rate

**Symptoms**:
```
INFO: Deduplication removed 30% of records
```

**Solutions**:

1. **Check if expected**:
   - Cross-source duplicates are normal (e.g., Wikipedia article also on BBC)
   - Within-source duplicates suggest data quality issues

2. **Review duplicate patterns**:
   ```bash
   # Check quality report for duplicate analysis
   cat data/reports/latest_quality_report.md | grep -A 10 "Deduplication"
   ```

3. **Investigate source**:
   ```python
   # If BBC has high duplicates, check scraping logic
   # If Wikipedia, may be redirect pages (already handled by namespace_filter)
   ```

4. **Adjust simhash threshold**:
   ```bash
   # Higher threshold = stricter (fewer duplicates detected)
   export SDC_DEDUP_SIMHASH_THRESHOLD=0.95  # Default: 0.90
   ```

---

## Dashboard Problems

### Problem: Dashboard shows "No data available"

**Symptoms**:
- Dashboard loads but displays empty charts
- Metrics cards show 0 or "N/A"

**Solutions**:

1. **Verify metrics files exist**:
   ```bash
   ls -lh data/metrics/
   # Should show .json files like: 20251020_143000_wikipedia-somali_metrics.json
   ```

2. **Check JSON format**:
   ```bash
   python -m json.tool data/metrics/latest_metrics.json
   # Should pretty-print valid JSON
   ```

3. **Run a pipeline to generate metrics**:
   ```bash
   wikisom-download
   # Wait for completion, then refresh dashboard
   ```

4. **Check dashboard data loading**:
   ```python
   streamlit run dashboard/app.py --logger.level=debug
   # Review console output for loading errors
   ```

### Problem: Dashboard not deploying to GitHub Pages

**Symptoms**:
- GitHub Actions workflow fails
- 404 error on dashboard URL

**Solutions**:

1. **Check workflow logs**:
   - Go to GitHub repository > Actions tab
   - Click on latest "Deploy Dashboard" workflow
   - Review error messages

2. **Enable GitHub Pages**:
   - Go to Settings > Pages
   - Ensure Source is set to "GitHub Actions"
   - Save

3. **Verify workflow permissions**:
   - Go to Settings > Actions > General
   - Enable "Read and write permissions"

4. **Check for workflow file**:
   ```bash
   cat .github/workflows/deploy-dashboard.yml
   # Ensure file exists and is valid YAML
   ```

5. **Wait for propagation**:
   - First deployment can take 5-10 minutes
   - Check back after waiting

### Problem: Dashboard charts not rendering

**Symptoms**:
- Dashboard loads but charts are blank
- Console errors about Plotly

**Solutions**:

1. **Update dependencies**:
   ```bash
   pip install --upgrade streamlit plotly pandas pyarrow
   ```

2. **Clear Streamlit cache**:
   ```bash
   rm -rf ~/.streamlit/cache/
   streamlit cache clear
   ```

3. **Check browser console**:
   - Open browser DevTools (F12)
   - Look for JavaScript errors
   - May need to hard refresh (Ctrl+Shift+R)

4. **Verify data format**:
   ```python
   # In dashboard/app.py, add debug output
   st.write("Data shape:", df.shape)
   st.write("Columns:", df.columns.tolist())
   st.dataframe(df.head())
   ```

---

## Performance Issues

### Problem: Pipeline is very slow

**Symptoms**:
```
Processing 10K records takes >30 minutes
```

**Solutions**:

1. **Enable batch processing**:
   ```python
   # Already enabled by default with batch_size=5000
   # Verify in logs:
   # "Processing batch 1/3 (5000 records)"
   ```

2. **Profile pipeline**:
   ```python
   import cProfile
   import pstats

   profiler = cProfile.Profile()
   profiler.enable()

   processor.download()
   processor.extract()
   processor.process()

   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative')
   stats.print_stats(20)  # Top 20 functions
   ```

3. **Identify bottleneck**:
   - **Download**: Network speed, rate limiting
   - **Extract**: XML parsing, HTML parsing
   - **Process**: Text cleaning, filter evaluation, deduplication

4. **Optimize specific stages**:
   ```bash
   # For BBC, reduce rate limit delay (be respectful)
   export SDC_BBC_RATE_LIMIT_DELAY=0.5  # Default: 1.0

   # For Wikipedia, increase buffer size
   export SDC_WIKI_BUFFER_SIZE_MB=20  # Default: 10

   # For HuggingFace, increase batch size
   export SDC_HF_BATCH_SIZE=10000  # Default: 5000
   ```

### Problem: High memory usage

**Symptoms**:
```
Process using >4GB RAM for small datasets
```

**Solutions**:

1. **Check memory profile**:
   ```python
   from memory_profiler import profile

   @profile
   def process_pipeline():
       processor.process()

   # Run and review memory increments
   ```

2. **Reduce batch size**:
   ```python
   processor = WikipediaSomaliProcessor(batch_size=1000)
   ```

3. **Clear intermediate data**:
   ```python
   # After processing, explicitly delete large variables
   del large_dataframe
   import gc
   gc.collect()
   ```

4. **Use generators** (already implemented):
   ```python
   # Verify streaming is used for large files
   # Check logs for "Streaming processing enabled"
   ```

### Problem: Disk space filling up

**Symptoms**:
```
OSError: [Errno 28] No space left on device
```

**Solutions**:

1. **Check disk usage**:
   ```bash
   du -sh data/*
   du -sh logs/*
   ```

2. **Clean old logs**:
   ```bash
   rm logs/*.log
   # Or keep only recent logs
   find logs/ -name "*.log" -mtime +7 -delete
   ```

3. **Remove bronze/staging data** (if not needed):
   ```bash
   # Warning: Only remove if silver data is generated
   rm -rf data/bronze/ data/staging/ data/processed/
   ```

4. **Compress old data**:
   ```bash
   tar -czf data/bronze_backup.tar.gz data/bronze/
   rm -rf data/bronze/
   ```

5. **Use external storage**:
   ```bash
   # Mount external drive or cloud storage
   export SDC_DATA_DIR=/mnt/external/somali-nlp-data
   ```

---

## Testing Failures

### Problem: Tests fail with "fixtures not found"

**Symptoms**:
```
FileNotFoundError: tests/fixtures/mini_wiki_dump.xml not found
```

**Solutions**:

1. **Verify fixtures exist**:
   ```bash
   ls tests/fixtures/
   # Should show: mini_wiki_dump.xml, bbc_articles.json, etc.
   ```

2. **Run tests from project root**:
   ```bash
   cd /path/to/somali-dialect-classifier
   pytest
   # NOT: cd tests && pytest (wrong directory)
   ```

3. **Check test paths**:
   ```python
   # In test files, use absolute paths or Path(__file__).parent
   from pathlib import Path
   fixture_path = Path(__file__).parent / "fixtures" / "mini_wiki_dump.xml"
   ```

### Problem: Integration tests fail in CI

**Symptoms**:
```
ERROR: Test failed: ConnectionError (network request)
```

**Solutions**:

1. **Skip integration tests in CI**:
   ```bash
   # In .github/workflows/ci.yml
   pytest -m "not integration"
   ```

2. **Mark integration tests**:
   ```python
   import pytest

   @pytest.mark.integration
   def test_bbc_scraping():
       # Test that hits real BBC website
       ...
   ```

3. **Use VCR.py for recording**:
   ```bash
   pip install vcrpy
   ```

   ```python
   import vcr

   @vcr.use_cassette('tests/vcr_cassettes/bbc_homepage.yaml')
   def test_bbc_scraping():
       # First run records, subsequent runs replay
       ...
   ```

### Problem: Tests pass locally but fail in CI

**Symptoms**:
- All tests pass on local machine
- Same tests fail in GitHub Actions

**Solutions**:

1. **Check Python version**:
   ```yaml
   # In .github/workflows/ci.yml
   - uses: actions/setup-python@v4
     with:
       python-version: '3.11'  # Match local version
   ```

2. **Install all dependencies**:
   ```yaml
   - name: Install dependencies
     run: |
       pip install -e ".[dev,all]"
   ```

3. **Check environment differences**:
   - File paths (Windows vs. Linux)
   - Timezone differences
   - Available resources (memory, CPU)

4. **Add debug output**:
   ```yaml
   - name: Debug
     run: |
       python --version
       pip list
       env | sort
   ```

---

## Configuration Errors

### Problem: Configuration not loading

**Symptoms**:
```
AttributeError: 'Config' object has no attribute 'data'
```

**Solutions**:

1. **Verify config module**:
   ```python
   from somali_dialect_classifier.config import config
   print(config.data.bronze_dir)
   # Should print path, not error
   ```

2. **Check environment variables**:
   ```bash
   env | grep SDC_
   # Should show SDC_* variables if set
   ```

3. **Reinstall with config extras**:
   ```bash
   pip install -e ".[config]"
   ```

4. **Use explicit config file**:
   ```python
   # Create config.yaml
   data:
     bronze_dir: data/bronze
     silver_dir: data/silver

   # Load in code
   from omegaconf import OmegaConf
   config = OmegaConf.load("config.yaml")
   ```

### Problem: Environment variables not recognized

**Symptoms**:
```
Using default values instead of environment variable overrides
```

**Solutions**:

1. **Check variable naming**:
   ```bash
   # Correct format: SDC_<SECTION>_<KEY>
   export SDC_DATA_BRONZE_DIR=/custom/path
   export SDC_BBC_RATE_LIMIT_DELAY=2.0
   ```

2. **Verify export**:
   ```bash
   echo $SDC_DATA_BRONZE_DIR
   # Should print value, not blank
   ```

3. **Use .env file**:
   ```bash
   # Create .env in project root
   SDC_DATA_BRONZE_DIR=/custom/path
   SDC_BBC_RATE_LIMIT_DELAY=2.0

   # Load with python-dotenv
   pip install python-dotenv
   ```

   ```python
   from dotenv import load_dotenv
   load_dotenv()  # Loads .env variables
   ```

---

## Development Environment

### Problem: Pre-commit hooks fail

**Symptoms**:
```
git commit fails with "black", "flake8", or "mypy" errors
```

**Solutions**:

1. **Install pre-commit**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

2. **Run hooks manually**:
   ```bash
   pre-commit run --all-files
   # Fix errors shown
   ```

3. **Format code**:
   ```bash
   black src/ tests/
   isort src/ tests/
   ```

4. **Fix linting errors**:
   ```bash
   flake8 src/ tests/
   # Address warnings shown
   ```

5. **Skip hooks temporarily** (not recommended):
   ```bash
   git commit --no-verify -m "message"
   ```

### Problem: IDE not recognizing imports

**Symptoms**:
- VS Code / PyCharm shows "import not found"
- Autocomplete doesn't work

**Solutions**:

1. **Select correct interpreter**:
   - VS Code: Ctrl+Shift+P > "Python: Select Interpreter" > Choose venv
   - PyCharm: Settings > Project > Python Interpreter > Add > Existing environment

2. **Reload window**:
   - VS Code: Ctrl+Shift+P > "Developer: Reload Window"
   - PyCharm: File > Invalidate Caches > Restart

3. **Install in editable mode**:
   ```bash
   pip install -e .
   ```

4. **Add to PYTHONPATH**:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:/path/to/somali-dialect-classifier/src"
   ```

### Problem: Jupyter notebook kernel crashes

**Symptoms**:
```
Kernel died unexpectedly
```

**Solutions**:

1. **Reinstall ipykernel**:
   ```bash
   pip install --upgrade ipykernel
   python -m ipykernel install --user --name=somali-nlp
   ```

2. **Increase memory limit**:
   ```bash
   # Check available memory
   free -h

   # Reduce batch sizes in notebook
   processor = WikipediaSomaliProcessor(batch_size=1000)
   ```

3. **Check for infinite loops**:
   - Review code for while loops without exit conditions
   - Add debug print statements

4. **Clear output**:
   - Jupyter: Cell > All Output > Clear
   - Restart kernel: Kernel > Restart & Clear Output

---

## Getting Additional Help

### Search Documentation

1. **Search docs/index.md** for relevant guides
2. **Check API reference** at docs/reference/api.md
3. **Review ADRs** in docs/decisions/ for design rationale

### Check Logs

```bash
# View latest log
tail -f logs/$(ls -t logs/ | head -1)

# Search for errors
grep -i error logs/*.log

# Check structured logs
cat logs/*.log | jq 'select(.level == "ERROR")'
```

### Enable Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export SDC_LOG_LEVEL=DEBUG
```

### Community Support

- **GitHub Issues**: https://github.com/YOUR-USERNAME/somali-dialect-classifier/issues
- **GitHub Discussions**: https://github.com/YOUR-USERNAME/somali-dialect-classifier/discussions

### Report Bugs

When reporting issues, include:

1. **Environment**:
   - OS and version
   - Python version
   - Installed packages: `pip list`

2. **Error Message**:
   - Full traceback
   - Relevant log excerpts

3. **Steps to Reproduce**:
   - Commands run
   - Configuration used

4. **Expected vs. Actual**:
   - What you expected to happen
   - What actually happened

---

## Related Documentation

- **[Installation Guide](../../README.md#installation)** - Setup instructions
- **[Configuration Guide](configuration.md)** - Environment and config setup
- **[Testing Guide](../operations/testing.md)** - Running and writing tests
- **[Dashboard Guide](../guides/dashboard.md)** - Dashboard troubleshooting
- **[Data Pipeline Guide](../guides/data-pipeline.md)** - Pipeline execution details

---

**Last Updated**: 2025-10-20
**Maintained By**: Somali NLP Team
**License**: MIT License
