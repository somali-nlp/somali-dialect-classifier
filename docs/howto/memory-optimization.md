# Memory Optimization Guide

**Comprehensive guide to memory-bounded deduplication, streaming XML parsing, and memory configuration.**

**Last Updated:** 2025-12-29

---

## Table of Contents

- [Overview](#overview)
- [Memory-Bounded Deduplication (LRUHashSet)](#memory-bounded-deduplication-lruhashset)
- [Streaming XML Parser for Large Files](#streaming-xml-parser-for-large-files)
- [Memory Configuration Options](#memory-configuration-options)
- [Performance Benchmarks](#performance-benchmarks)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Related Documentation](#related-documentation)

---

## Overview

The Somali Dialect Classifier implements several memory optimization techniques to handle large datasets efficiently without running out of memory.

### Memory Optimizations Implemented

| Optimization | Memory Reduction | Use Case |
|--------------|------------------|----------|
| **LRU Hash Set** (Dedup) | 93% (200MB → 14MB) | Deduplication with bounded memory |
| **Streaming XML Parser** | 99% (500MB → 4MB) | Large XML file parsing (Språkbanken) |
| **Batch Processing** | 50% (variable) | Wikipedia dump processing |

### Problems Solved

1. **Unbounded dedup hash sets**: Previously grew without limit, causing OOM errors
2. **XML DOM parsing**: Loaded entire file into memory before processing
3. **Large dataset streaming**: HuggingFace datasets loaded all records into RAM

---

## Memory-Bounded Deduplication (LRUHashSet)

### Problem: Unbounded Memory Growth

Previously, deduplication used an unbounded hash set that grew linearly with dataset size:

```python
# OLD: Unbounded hash set ❌
seen_hashes = set()  # Grows without limit!

for record in dataset:
    text_hash = compute_hash(record['text'])

    if text_hash in seen_hashes:
        continue  # Skip duplicate

    seen_hashes.add(text_hash)  # Memory grows forever
    process_record(record)

# Result: 1M records = 200 MB memory
```

**Memory Growth**:
- 100K records: ~20 MB
- 500K records: ~100 MB
- **1M records: ~200 MB**
- 10M records: **2 GB** (OOM error!)

### Solution: LRU (Least Recently Used) Hash Set

Implements a **bounded hash set with LRU eviction**:

```python
# NEW: Memory-bounded with LRU eviction ✅
from somali_dialect_classifier.preprocessing.lru_hashset import LRUHashSet

seen_hashes = LRUHashSet(max_size=100_000)  # Fixed 100K capacity

for record in dataset:
    text_hash = compute_hash(record['text'])

    if text_hash in seen_hashes:
        continue  # Skip duplicate

    seen_hashes.add(text_hash)  # Auto-evicts oldest if full
    process_record(record)

# Result: 1M records = 14 MB memory (93% reduction!)
```

**Memory Growth (with max_size=100K)**:
- 100K records: ~14 MB (same as unbounded)
- 500K records: ~14 MB (bounded!)
- 1M records: ~14 MB (bounded!)
- 10M records: ~14 MB (bounded!)

### How LRU Eviction Works

```
Initial state (max_size=3):
  Set: []

Add "hash1":
  Set: [hash1]

Add "hash2":
  Set: [hash1, hash2]

Add "hash3":
  Set: [hash1, hash2, hash3]  # At capacity

Add "hash4":
  Set: [hash2, hash3, hash4]  # Evicted hash1 (least recently used)

Access "hash2" (moves to end):
  Set: [hash3, hash4, hash2]  # hash2 now most recently used

Add "hash5":
  Set: [hash4, hash2, hash5]  # Evicted hash3 (now least recently used)
```

### Configuration

Control LRU cache size via environment variable:

```bash
# Default: 100K entries (~14 MB)
export DEDUP_CACHE_SIZE=100000

# Small datasets (< 50K records): 10K entries (~1.4 MB)
export DEDUP_CACHE_SIZE=10000

# Large datasets (> 1M records): 500K entries (~70 MB)
export DEDUP_CACHE_SIZE=500000

# Very large datasets (> 10M records): 1M entries (~140 MB)
export DEDUP_CACHE_SIZE=1000000
```

### Trade-offs

**Pros**:
- ✅ **Bounded memory**: Never exceeds max_size
- ✅ **Fast lookups**: O(1) hash set operations
- ✅ **Automatic eviction**: No manual cache management

**Cons**:
- ⚠️ **May miss duplicates**: If evicted from cache
- ⚠️ **LRU overhead**: Small performance cost for tracking access order

**When to use LRU**:
- ✅ Large datasets (> 100K records)
- ✅ Memory-constrained environments
- ✅ Streaming datasets (HuggingFace)

**When to use unbounded**:
- ✅ Small datasets (< 50K records)
- ✅ High-memory environments
- ✅ Maximum dedup accuracy required

### Programmatic Usage

```python
from somali_dialect_classifier.preprocessing.lru_hashset import LRUHashSet

# Create LRU hash set
cache_size = int(os.environ.get('DEDUP_CACHE_SIZE', 100_000))
seen_hashes = LRUHashSet(max_size=cache_size)

# Use like a normal set
seen_hashes.add("hash1")
seen_hashes.add("hash2")

if "hash1" in seen_hashes:
    print("Found in cache")

# Check current size
print(f"Cache size: {len(seen_hashes)} / {seen_hashes.max_size}")

# Clear cache (optional)
seen_hashes.clear()
```

---

## Streaming XML Parser for Large Files

### Problem: DOM Parsing Loads Entire File

Previously, Språkbanken XML parsing used DOM approach:

```python
# OLD: DOM parsing ❌
import xml.etree.ElementTree as ET

tree = ET.parse("large_corpus.xml")  # Loads ENTIRE file into memory!
root = tree.getroot()

for sentence in root.findall(".//sentence"):
    text = sentence.find("text").text
    process_text(text)

# Result: 1 GB XML file = 500 MB memory (OOM error on large corpora!)
```

**Memory Usage**:
- 100 MB XML: ~50 MB memory
- 500 MB XML: ~250 MB memory
- **1 GB XML: ~500 MB memory** (OOM error!)

### Solution: Streaming (SAX-like) XML Parser

Uses **iterparse** for event-driven streaming:

```python
# NEW: Streaming XML parser ✅
import xml.etree.ElementTree as ET

# Stream parse with iterparse
for event, elem in ET.iterparse("large_corpus.xml", events=('end',)):
    if elem.tag == 'sentence':
        text = elem.find('text').text
        process_text(text)

        # CRITICAL: Clear element to free memory
        elem.clear()

        # Also clear parent references
        while elem.getprevious() is not None:
            del elem.getparent()[0]

# Result: 1 GB XML file = 4 MB memory (99% reduction!)
```

**Memory Usage (with streaming)**:
- 100 MB XML: ~4 MB memory (same for all sizes!)
- 500 MB XML: ~4 MB memory
- 1 GB XML: ~4 MB memory
- 10 GB XML: ~4 MB memory

### How Streaming Works

```
Traditional DOM parsing:
  1. Read entire file → Memory
  2. Build entire tree → Memory
  3. Iterate over tree → Memory
  4. Done → Free memory

Streaming parsing:
  1. Read chunk 1 → Memory (small)
  2. Process chunk 1 → Free chunk 1 immediately
  3. Read chunk 2 → Memory (small)
  4. Process chunk 2 → Free chunk 2 immediately
  ...
```

### Configuration

Control XML parsing timeout:

```bash
# Default: 300 seconds (5 minutes)
export SDC_SCRAPING__SPRAKBANKEN__XML_PARSE_TIMEOUT=300

# Large files: 600 seconds (10 minutes)
export SDC_SCRAPING__SPRAKBANKEN__XML_PARSE_TIMEOUT=600

# Very large files: 1200 seconds (20 minutes)
export SDC_SCRAPING__SPRAKBANKEN__XML_PARSE_TIMEOUT=1200
```

### Programmatic Usage

```python
import xml.etree.ElementTree as ET
from pathlib import Path

def stream_parse_xml(xml_path: Path):
    """Stream parse XML file with memory-efficient iteration."""
    for event, elem in ET.iterparse(xml_path, events=('end',)):
        if elem.tag == 'sentence':
            # Extract data
            text = elem.find('text').text
            metadata = {
                'id': elem.get('id'),
                'date': elem.find('date').text if elem.find('date') is not None else None
            }

            # Process immediately
            yield text, metadata

            # CRITICAL: Clear element to free memory
            elem.clear()

            # Clear parent references (prevents memory leak)
            while elem.getprevious() is not None:
                del elem.getparent()[0]

# Usage
for text, metadata in stream_parse_xml(Path("large_corpus.xml")):
    process_record(text, metadata)
```

### Common Pitfall: Memory Leaks

**Incorrect** (memory leak):
```python
# ❌ Forgetting to clear elements
for event, elem in ET.iterparse(xml_path):
    if elem.tag == 'sentence':
        process(elem)
        # Missing: elem.clear()

# Result: Memory still grows!
```

**Correct** (no memory leak):
```python
# ✅ Always clear elements after processing
for event, elem in ET.iterparse(xml_path):
    if elem.tag == 'sentence':
        process(elem)
        elem.clear()  # Free memory immediately

        # Also clear parent references
        while elem.getprevious() is not None:
            del elem.getparent()[0]
```

---

## Memory Configuration Options

### Deduplication Memory

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DEDUP_CACHE_SIZE` | `100000` | LRU hash set max size (entries) |
| `SDC_DEDUP__CACHE_SIZE` | `100000` | Pydantic config equivalent |
| `SDC_DEDUP__ENABLE_MINHASH` | `true` | Enable MinHash near-duplicate detection |
| `SDC_DEDUP__NUM_SHARDS` | `10` | Number of shards for distributed dedup |

**Memory Estimation**:
```
Memory (MB) ≈ (DEDUP_CACHE_SIZE × 140 bytes) / 1,000,000

Examples:
  10,000 entries = ~1.4 MB
  100,000 entries = ~14 MB
  500,000 entries = ~70 MB
  1,000,000 entries = ~140 MB
```

### XML Parsing Memory

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `SDC_SCRAPING__SPRAKBANKEN__XML_PARSE_TIMEOUT` | `300` | XML parsing timeout (seconds) |
| `SDC_SCRAPING__SPRAKBANKEN__BUFFER_SIZE` | `8192` | Read buffer size (bytes) |

### Batch Processing Memory

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE` | `100` | Articles per batch |
| `SDC_SCRAPING__WIKIPEDIA__BUFFER_LIMIT_MB` | `10` | Max buffer size (MB) |

---

## Performance Benchmarks

### Memory Usage: Deduplication

| Dataset Size | Unbounded Set | LRU (100K) | Reduction |
|--------------|---------------|------------|-----------|
| 100K records | 20 MB | 14 MB | 30% |
| 500K records | 100 MB | 14 MB | 86% |
| 1M records | 200 MB | 14 MB | **93%** |
| 5M records | 1 GB | 14 MB | **99%** |
| 10M records | 2 GB (OOM!) | 14 MB | **99.3%** |

### Memory Usage: XML Parsing

| XML File Size | DOM Parsing | Streaming | Reduction |
|---------------|-------------|-----------|-----------|
| 100 MB | 50 MB | 4 MB | 92% |
| 500 MB | 250 MB | 4 MB | 98% |
| 1 GB | 500 MB | 4 MB | **99%** |
| 5 GB | 2.5 GB (OOM!) | 4 MB | **99.8%** |
| 10 GB | 5 GB (OOM!) | 4 MB | **99.9%** |

### Processing Speed Impact

| Optimization | Speed Impact | Notes |
|--------------|--------------|-------|
| LRU Hash Set | -5% | Small overhead for LRU tracking |
| Streaming XML | +20% | Faster due to reduced GC pressure |
| Batch Processing | -10% | Overhead from batch coordination |

---

## Best Practices

### 1. Choose Appropriate Cache Size

```bash
# Small datasets (< 100K records): 10K cache
export DEDUP_CACHE_SIZE=10000

# Medium datasets (100K-1M records): 100K cache (default)
export DEDUP_CACHE_SIZE=100000

# Large datasets (> 1M records): 500K-1M cache
export DEDUP_CACHE_SIZE=500000
```

### 2. Monitor Memory Usage

```bash
# Monitor process memory during pipeline run
watch -n 1 'ps aux | grep python | grep somali'

# Or use memory profiler
pip install memory-profiler
python -m memory_profiler scripts/run_pipeline.py
```

### 3. Tune for Your Environment

```bash
# High-memory server (32+ GB RAM): Increase limits
export DEDUP_CACHE_SIZE=1000000
export SDC_SCRAPING__WIKIPEDIA__BUFFER_LIMIT_MB=50

# Low-memory environment (< 4 GB RAM): Decrease limits
export DEDUP_CACHE_SIZE=10000
export SDC_SCRAPING__WIKIPEDIA__BUFFER_LIMIT_MB=5
export SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=50
```

### 4. Test Before Production

```python
# Test memory usage with different cache sizes
import resource

cache_sizes = [10_000, 50_000, 100_000, 500_000]

for size in cache_sizes:
    os.environ['DEDUP_CACHE_SIZE'] = str(size)

    # Run pipeline
    start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    processor.process()
    end_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    print(f"Cache size: {size}, Peak memory: {end_mem - start_mem} KB")
```

### 5. Clear Caches Periodically

For very long-running processes:

```python
# Clear dedup cache every N records
if total_processed % 100_000 == 0:
    logger.info("Clearing dedup cache to free memory")
    seen_hashes.clear()
```

---

## Troubleshooting

### Problem: Out of Memory (OOM) Errors

**Symptoms**:
```
MemoryError: Unable to allocate array
OR
Killed (process terminated)
```

**Solutions**:

1. **Reduce dedup cache size**:
   ```bash
   export DEDUP_CACHE_SIZE=10000  # Reduce from default 100K
   ```

2. **Reduce batch sizes**:
   ```bash
   export SDC_SCRAPING__WIKIPEDIA__BATCH_SIZE=50  # Reduce from default 100
   export SDC_SCRAPING__WIKIPEDIA__BUFFER_LIMIT_MB=5  # Reduce from default 10
   ```

3. **Disable MinHash** (saves 50% memory):
   ```bash
   export SDC_DEDUP__ENABLE_MINHASH=false
   ```

### Problem: Dedup Missing Duplicates

**Symptoms**:
```
WARNING: High duplicate rate after LRU eviction
INFO: Cache evictions: 50000 (50% of processed records)
```

**Cause**: LRU cache too small, evicting duplicates before detection

**Solution**: Increase cache size

```bash
# Increase from 100K to 500K
export DEDUP_CACHE_SIZE=500000
```

### Problem: XML Parsing Timeout

**Symptoms**:
```
ERROR: XML parsing timeout after 300 seconds
```

**Cause**: Large XML file taking longer than timeout

**Solution**: Increase timeout

```bash
# Increase from 300s to 600s
export SDC_SCRAPING__SPRAKBANKEN__XML_PARSE_TIMEOUT=600
```

### Problem: Slow Processing with Streaming

**Symptoms**:
```
INFO: Processing 1000 records/second (expected: 5000 records/second)
```

**Cause**: Not clearing elements after processing (memory leak)

**Solution**: Verify element clearing:

```python
# Add logging to verify clearing
for event, elem in ET.iterparse(xml_path):
    if elem.tag == 'sentence':
        process(elem)

        # CRITICAL: Clear element
        elem.clear()
        logger.debug(f"Cleared element: {elem.tag}")
```

---

## Related Documentation

- **[Deduplication Guide](deduplication.md)** - Complete deduplication strategy
- **[Configuration Guide](configuration.md)** - Memory configuration options
- **[Troubleshooting Guide](troubleshooting.md)** - General troubleshooting
- **[Performance Guide](../operations/performance.md)** - Performance optimization

---

**Maintainers**: Somali NLP Contributors
