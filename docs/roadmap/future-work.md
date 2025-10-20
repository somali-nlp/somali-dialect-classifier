# Future Work & Backlog

**Last Updated**: 2025-10-16

This document tracks enhancement ideas, technical debt, and future improvements for the Somali Dialect Classifier project.

---

## High Priority

### 1. MLflow Integration

**Status**: Design Complete, Implementation Pending
**Effort**: 2-3 days
**Owner**: ML Engineering

**Description**: Hook up filter statistics and model metrics to MLflow for experiment tracking.

**Tasks**:
- [ ] Add MLflow to dependencies (`pip install mlflow`)
- [ ] Instrument `BasePipeline.process()` to log metrics
- [ ] Create MLflow experiment for each data source
- [ ] Log filter statistics as metrics
- [ ] Log silver dataset size and quality metrics
- [ ] Set up MLflow UI deployment

**Code Sketch**:
```python
# In process() method
if mlflow.active_run():
    mlflow.log_metrics({
        "records_processed": records_processed,
        "records_filtered": records_filtered,
        "filter_rate": records_filtered / (records_processed + records_filtered)
    })

    for filter_reason, count in filter_stats.items():
        mlflow.log_metric(f"filter/{filter_reason}", count)
```

**Benefits**:
- Track filter drift over time
- Compare data quality across sources
- Debugging: Identify when filters become too aggressive

---

### 2. Orchestration with Prefect/Dagster

**Status**: Not Started
**Effort**: 1 week
**Owner**: Data Engineering

**Description**: Add workflow orchestration for scheduled pipeline runs.

**Options**:
1. **Prefect** (recommended): Python-native, easy learning curve
2. **Dagster**: Asset-based, better for complex pipelines
3. **Airflow**: Industry standard, but heavier

**Tasks**:
- [ ] Choose orchestration framework (Prefect recommended)
- [ ] Wrap each processor in a task/op
- [ ] Define DAG for full pipeline (all sources)
- [ ] Add retry logic and error handling
- [ ] Schedule daily/weekly runs
- [ ] Set up alerting for failures

**Example (Prefect)**:
```python
from prefect import flow, task

@task
def process_wikipedia():
    from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor
    processor = WikipediaSomaliProcessor()
    return processor.run()

@task
def process_bbc():
    from somali_dialect_classifier.preprocessing import BBCSomaliProcessor
    processor = BBCSomaliProcessor(max_articles=100)
    return processor.run()

@flow(name="daily-data-pipeline")
def daily_pipeline():
    wiki_path = process_wikipedia()
    bbc_path = process_bbc()
    # Add quality checks
    # Trigger downstream tasks
```

**Benefits**:
- Automated data refresh
- Dependency management
- Failure recovery
- Monitoring and observability

---

### 3. Precision/Recall Evaluation of Filters

**Status**: Not Started
**Effort**: 1-2 weeks
**Owner**: Research + ML Engineering

**Description**: Benchmark heuristic filter accuracy against manually labeled test set.

**Motivation**: Current filters (langid, dialect_heuristic) use hand-crafted rules. We need to measure:
- False positive rate (good records filtered out)
- False negative rate (bad records kept)
- Per-filter performance

**Tasks**:
- [ ] Create gold-standard test set (500-1K samples)
- [ ] Manually label: Somali/non-Somali, topic, quality
- [ ] Run filters on test set
- [ ] Calculate precision, recall, F1 for each filter
- [ ] Identify worst-performing filters
- [ ] Refine lexicons and thresholds
- [ ] Re-evaluate

**Evaluation Framework**:
```python
# tests/test_filter_evaluation.py
import pandas as pd
from sklearn.metrics import classification_report

def evaluate_filter(filter_func, test_data: pd.DataFrame):
    """
    test_data must have columns:
    - text: str
    - ground_truth: bool (True = should keep, False = should filter)
    """
    predictions = []
    for text in test_data['text']:
        passes, _ = filter_func(text, **kwargs)
        predictions.append(passes)

    report = classification_report(
        test_data['ground_truth'],
        predictions,
        target_names=['Filter', 'Keep']
    )
    return report
```

**Benefits**:
- Quantify filter quality
- Identify high-error filters
- Data-driven threshold tuning

---

## Medium Priority

### 4. Great Expectations Data Quality

**Status**: Not Started
**Effort**: 3-4 days
**Owner**: Data Engineering

**Description**: Add automated data quality assertions for silver dataset.

**Tasks**:
- [ ] Install Great Expectations
- [ ] Define expectation suite for silver schema
- [ ] Add expectations for:
  - Schema validation (all required columns present)
  - Value ranges (e.g., tokens > 0)
  - Null checks (e.g., text not null)
  - Distributions (e.g., source distribution stable)
- [ ] Run expectations after each pipeline
- [ ] Generate data quality reports

**Example**:
```python
import great_expectations as ge

df = ge.read_parquet(silver_path)

# Schema validation
df.expect_column_to_exist("text")
df.expect_column_to_exist("detected_lang")

# Quality checks
df.expect_column_values_to_be_in_set("language", ["so"])
df.expect_column_values_to_not_be_null("text")
df.expect_column_values_to_match_regex("text", r".{50,}")  # Min 50 chars

# Save results
df.save_expectation_suite("silver_dataset_expectations.json")
```

**Benefits**:
- Catch data quality regressions early
- Automated smoke tests for pipelines
- Documentation of data expectations

---

### 5. Deduplication Pipeline

**Status**: Partial (script exists: `scripts/deduplicate_silver.py`)
**Effort**: 2-3 days
**Owner**: Data Engineering

**Description**: Automated deduplication across silver dataset partitions.

**Current State**: Manual script exists, needs integration into pipeline.

**Tasks**:
- [ ] Review existing `deduplicate_silver.py` script
- [ ] Integrate into `BasePipeline` or post-processing step
- [ ] Add cross-source deduplication (Wikipedia + BBC)
- [ ] Implement MinHash or SimHash for near-duplicate detection
- [ ] Log duplicate statistics
- [ ] Schedule periodic deduplication runs

**Deduplication Strategy**:
1. **Exact duplicates**: text_hash matching (already in schema)
2. **Near-duplicates**: SimHash with Hamming distance threshold
3. **Cross-source**: Prefer newer/higher-quality sources

**Benefits**:
- Reduce training data redundancy
- Improve model generalization
- Save storage costs

---

### 6. Additional Data Sources

**Status**: Ideas Only
**Effort**: 1-2 weeks per source
**Owner**: Data Engineering

**Potential Sources**:
1. **Voice of America (VOA) Somali** - News articles
2. **SomaliNet Forums** - Conversational text
3. **Somali Government Websites** - Official documents
4. **Social Media** (Twitter/X, Facebook) - Short-form, informal text
5. **Somali Literature** (Project Gutenberg, etc.) - Books, poetry

**Considerations**:
- Licensing and copyright
- Scraping ethics and robots.txt compliance
- Data quality (social media very noisy)
- Bias (certain sources over-represent certain dialects)

---

## Low Priority / Nice-to-Have

### 7. Incremental Updates

**Description**: Support incremental pipeline runs (only process new data).

**Current State**: Pipelines reprocess entire sources.

**Enhancement**:
- Track last_processed timestamp
- Only download/extract new articles since last run
- Append to existing silver dataset

**Benefits**:
- Faster pipeline runs
- Reduced compute costs

---

### 8. Data Versioning with DVC

**Description**: Version control for datasets using Data Version Control (DVC).

**Tasks**:
- [ ] Initialize DVC in repo
- [ ] Track raw, staging, silver directories
- [ ] Push to S3/GCS remote
- [ ] Document DVC workflow

**Benefits**:
- Reproducibility
- Rollback to previous data versions
- Collaboration on datasets

---

### 9. Streaming Processing

**Description**: Real-time processing for incoming articles (e.g., BBC RSS feed).

**Architecture**:
- Kafka/RabbitMQ for message queue
- Continuous consumer polling RSS feeds
- Incremental silver dataset updates

**Benefits**:
- Near-real-time data availability
- Lower latency for downstream applications

---

### 10. Multi-language Support

**Description**: Extend pipeline to support other African languages (Amharic, Swahili, Hausa).

**Effort**: High (refactor language-specific components)

**Tasks**:
- [ ] Abstract language-specific logic (lexicons, filters)
- [ ] Create language-agnostic base classes
- [ ] Add language-specific subclasses

**Benefits**:
- Reuse codebase for other languages
- Cross-lingual model training

---

## Technical Debt

### 11. Refactor BasePipeline.process()

**Issue**: `process()` method is 140+ lines, does too much.

**Proposal**: Extract helper methods:
- `_apply_filters(record) -> (bool, metadata)`
- `_build_silver_record(raw_record) -> Dict`
- `_write_batch(records) -> None`

**Benefit**: Improved readability and testability.

---

### 12. Improve Error Messages

**Issue**: Some errors lack context (e.g., "Manifest not found").

**Proposal**: Add actionable error messages:
```python
raise FileNotFoundError(
    f"Manifest not found: {manifest_path}. "
    f"Run processor.download() first to create the manifest."
)
```

**Benefit**: Better developer experience.

---

### 13. Logging Levels

**Issue**: Some DEBUG logs are too verbose, some INFO logs insufficient.

**Proposal**: Review all log statements and adjust levels appropriately.

**Benefit**: Cleaner logs in production.

---

## Research & Experimentation

### 14. Dialect Taxonomy Research

**Description**: Formal linguistic research on Somali dialect classification.

**Questions**:
- How many major dialects exist?
- What are the distinguishing features?
- Can we detect dialects from text alone (vs. audio)?

**Tasks**:
- [ ] Literature review
- [ ] Consult Somali linguists
- [ ] Define annotation schema based on research

---

### 15. Active Learning Strategy

**Description**: Model-assisted labeling to reduce annotation costs.

**Approaches**:
1. **Uncertainty Sampling**: Label examples the model is least confident about
2. **Diversity Sampling**: Label examples that represent under-represented regions of feature space
3. **Query-by-Committee**: Train multiple models, label examples they disagree on

**Tasks**:
- [ ] Implement uncertainty scoring
- [ ] Build active learning loop
- [ ] Measure labeling efficiency gains

---

### 16. Multilingual Model Fine-tuning

**Description**: Experiment with pre-trained multilingual models (mBERT, XLM-R) for dialect classification.

**Tasks**:
- [ ] Download pre-trained models
- [ ] Fine-tune on labeled Somali data
- [ ] Compare to baseline (TF-IDF + LR)
- [ ] Evaluate on test set

---

## Documentation Improvements

### 17. Video Tutorials

**Description**: Create screencasts/video walkthroughs for common tasks.

**Topics**:
- Setting up the environment
- Running your first pipeline
- Writing custom filters
- Troubleshooting common errors

---

### 18. API Reference Generation

**Description**: Auto-generate API docs from docstrings.

**Tools**:
- Sphinx with autodoc
- MkDocs with mkdocstrings

**Benefit**: Always up-to-date API reference.

---

### 19. Contribution Guide

**Description**: Detailed guide for external contributors.

**Sections**:
- Setting up development environment
- Running tests
- Submitting pull requests
- Code style guide

---

## See Also

- [Lifecycle & Roadmap](lifecycle.md) - Project phases and milestones
- [Architecture](../overview/architecture.md) - System design
- [Filter Framework Decision](../decisions/002-filter-framework.md) - Filter system design rationale
