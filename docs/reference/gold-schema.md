# Gold Dataset Schema

**Version:** 1.0.0
**Last Updated:** 2025-11-15
**Status:** Specification (Not Yet Implemented)

---

## Overview

The **gold layer** contains ML-ready datasets with supervised labels for various NLP tasks. Gold datasets are distinct from the silver layer, which contains cleaned, deduplicated raw data.

### Purpose
- Provide annotated datasets for model training and evaluation
- Support multiple NLP tasks (dialect classification, code-switch detection, etc.)
- Enable reproducible research and benchmarking (e.g., SomaliGLUE)
- Track annotation quality and provenance

### Gold vs. Silver

| Aspect | Silver Layer | Gold Layer |
|--------|-------------|------------|
| **Purpose** | Cleaned raw data | ML-ready annotated data |
| **Labels** | None (or heuristic enrichment) | Supervised ground-truth labels |
| **Split** | No train/val/test split | Proper data splits for ML |
| **Annotation** | Automated only | Human/consensus/model-assisted |
| **Format** | JSONL | Parquet (with schema validation) |
| **Versioning** | By run_id | By dataset version + manifest |

---

## Dialect Classification Schema

### Overview
Dialect classification is a sentence-level or document-level task to predict the dialect category of Somali text.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `gold_id` | string (UUID) | ✅ Yes | Stable unique identifier for this gold record |
| `silver_id` | string | ✅ Yes | Foreign key to source silver record `id` |
| `text` | string | ✅ Yes | Text used for model training/evaluation (may be normalized vs. silver) |
| `dialect_label` | enum | ✅ Yes | Categorical dialect label (see values below) |
| `dialect_confidence` | float (0-1) | ❌ No | Confidence score for soft labels or consensus |
| `split` | enum | ✅ Yes | Dataset split: `train`, `validation`, `test` (optional `dev`) |
| `annotator_ids` | array[string] | ❌ No | List of annotator IDs who produced this label |
| `annotation_method` | enum | ✅ Yes | Method used to produce label (see values below) |
| `annotation_timestamp` | timestamp | ✅ Yes | ISO 8601 timestamp of when annotation occurred |
| `annotation_batch` | string | ❌ No | Batch identifier for tracking annotation campaigns |

**Preserved metadata from silver:**
- `source`: Data source (wikipedia, bbc-somali, etc.)
- `domain`: Content domain (news, social, government, etc.)
- `register`: Language register (formal, informal, colloquial)
- `created_at`: Original creation timestamp
- `url`: Source URL (if available)
- `title`: Title/heading (if available)

### Dialect Label Values

| Value | Description | Examples |
|-------|-------------|----------|
| `north` | Northern Somali dialect | Predominant in Somaliland, Puntland |
| `south` | Southern Somali dialect | Includes Mogadishu dialect, southern regions |
| `benadiri` | Benadiri (Coastal) dialect | Coastal cities, distinct phonology |
| `maay` | Maay/Maay Maay dialect | Inter-riverine regions, mutually intelligible |
| `diaspora` | Diaspora/mixed dialect | Code-switched, non-standard, mixed features |
| `unknown` | Cannot determine dialect | Use sparingly when truly ambiguous |

**Important Notes:**
- `diaspora` is a **first-class label** (not a fallback)
- Multi-dialect texts can use `dialect_confidence < 1.0` to indicate uncertainty
- For legitimately multi-dialect texts, consider creating separate records or using consensus method

### Annotation Method Values

| Value | Description | Use Case |
|-------|-------------|----------|
| `human` | Manually annotated by human expert | High-quality labels, gold standard |
| `model_assisted` | Human review of model prediction | Accelerated annotation with human validation |
| `consensus` | Multiple annotators with voting/consensus | High-quality labels, inter-annotator agreement tracked |
| `automatic` | Fully automated (heuristic, model, rule-based) | Use with caution, lower confidence |

**Recommendation:** Prefer `human` or `consensus` for high-quality datasets. Use `automatic` only when clearly documented and validated.

### Storage Format

**File Path:** `data/gold/dialect_classification/{version}/data.parquet`

**Partitioning:** By `split` (train/validation/test subdirectories)
- `data/gold/dialect_classification/v1.0.0/train/data.parquet`
- `data/gold/dialect_classification/v1.0.0/validation/data.parquet`
- `data/gold/dialect_classification/v1.0.0/test/data.parquet`

**Compression:** Snappy (default for Parquet)

**Schema Validation:** Enforced on read/write using Pydantic or Pandera

### Example Record

```json
{
  "gold_id": "550e8400-e29b-41d4-a716-446655440000",
  "silver_id": "wikipedia_so_12345",
  "text": "Waxaan ku noolahay magaalada Muqdisho.",
  "dialect_label": "south",
  "dialect_confidence": 0.95,
  "split": "train",
  "annotator_ids": ["annotator_001", "annotator_002"],
  "annotation_method": "consensus",
  "annotation_timestamp": "2025-11-15T10:30:00Z",
  "annotation_batch": "batch_001_mogadishu_news",
  "source": "bbc-somali",
  "domain": "news",
  "register": "formal",
  "created_at": "2025-11-10T08:15:00Z",
  "url": "https://www.bbc.com/somali/...",
  "title": "Warka Muqdisho"
}
```

---

## Code-Switch Detection Schema

### Overview
Code-switch detection is a token-level task to identify language boundaries in mixed-language text (primarily Somali-English switching).

### Approach Options

Two approaches are supported. Choose ONE for consistency:

1. **Token-Level Tagging** (RECOMMENDED for transformer models)
2. **Span-Based Annotation** (Alternative for span-based models)

### Token-Level Approach (Recommended)

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `gold_id` | string (UUID) | ✅ Yes | Stable unique identifier |
| `silver_id` | string | ✅ Yes | FK to silver record |
| `text` | string | ✅ Yes | Original text (untokenized) |
| `tokenized_text` | array[string] | ✅ Yes | Tokenized words/subwords (aligned 1:1 with tags) |
| `token_lang_tags` | array[enum] | ✅ Yes | Language tag per token: `so`, `en`, `ar`, `other` |
| `so_token_ratio` | float (0-1) | ❌ No | Percentage of Somali tokens (summary feature) |
| `en_token_ratio` | float (0-1) | ❌ No | Percentage of English tokens (summary feature) |
| `num_switch_points` | int | ❌ No | Count of language switches in text |
| `split` | enum | ✅ Yes | Dataset split: `train`, `validation`, `test` |

**Plus:** Same annotation metadata as dialect task (annotator_ids, annotation_method, timestamp, etc.)

#### Token Language Tag Values

| Value | Description |
|-------|-------------|
| `so` | Somali language token |
| `en` | English language token |
| `ar` | Arabic language token |
| `other` | Other language or unknown |

#### Example Record (Token-Level)

```json
{
  "gold_id": "660f8500-e29b-41d4-a716-556655440000",
  "silver_id": "tiktok_12345",
  "text": "Subax wanaagsan guys, how are you today?",
  "tokenized_text": ["Subax", "wanaagsan", "guys", ",", "how", "are", "you", "today", "?"],
  "token_lang_tags": ["so", "so", "en", "so", "en", "en", "en", "en", "en"],
  "so_token_ratio": 0.33,
  "en_token_ratio": 0.56,
  "num_switch_points": 2,
  "split": "train",
  "annotation_method": "human",
  "annotation_timestamp": "2025-11-15T11:00:00Z"
}
```

### Span-Based Approach (Alternative)

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language_spans` | array[object] | ✅ Yes | List of `{start: int, end: int, lang: str}` objects |

Each span object:
```json
{
  "start": 0,      // Character start index (inclusive)
  "end": 5,        // Character end index (exclusive)
  "lang": "so"     // Language code
}
```

#### Example Record (Span-Based)

```json
{
  "gold_id": "770f8600-e29b-41d4-a716-666655440000",
  "silver_id": "tiktok_67890",
  "text": "Subax wanaagsan guys, how are you today?",
  "language_spans": [
    {"start": 0, "end": 17, "lang": "so"},
    {"start": 18, "end": 41, "lang": "en"}
  ],
  "split": "train"
}
```

### Storage Format

**File Path:** `data/gold/code_switch/{version}/data.parquet`

**Partitioning:** By `split`

**Note:** Choose ONE approach (token-level OR span-based) for the entire dataset. Token-level is recommended for transformer-based models (BERT, RoBERTa, etc.).

---

## Task Metadata Schema

### Purpose
Support multiple NLP tasks and enable benchmark dataset releases (e.g., SomaliGLUE).

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | string | ✅ Yes | Unique task identifier (e.g., "somali_dialect_v1") |
| `task_name` | enum | ✅ Yes | Task type category (see values below) |
| `dataset_id` | string | ✅ Yes | Logical dataset grouping identifier |
| `dataset_version` | string | ✅ Yes | Semantic version (e.g., "1.0.0") |

### Task Name Values

| Value | Description | Future Use |
|-------|-------------|------------|
| `dialect_classification` | Dialect classification (sentence/doc level) | ✅ Stage 0 |
| `code_switch_detection` | Language ID (token level) | ✅ Stage 0 |
| `sentiment` | Sentiment analysis | ⏳ Future |
| `ner` | Named entity recognition | ⏳ Future |
| `qa` | Question answering | ⏳ Future |
| `nli` | Natural language inference | ⏳ Future |

**Extensibility:** Add new task types as needed. Follow naming convention: lowercase with underscores.

### Versioning Strategy

Use **semantic versioning**: `MAJOR.MINOR.PATCH`

- **MAJOR:** Breaking schema changes or incompatible data changes
- **MINOR:** New annotations, expanded dataset, backward-compatible changes
- **PATCH:** Bug fixes, corrections, no new data

**Examples:**
- `1.0.0` → Initial release
- `1.1.0` → Added 5,000 new annotated records (backward compatible)
- `2.0.0` → Changed dialect labels from 4 to 6 categories (breaking change)
- `1.0.1` → Fixed annotation errors in 50 records (patch)

---

## Dataset Versioning Manifests

### Purpose
Track reproducibility, provenance, and dataset statistics.

### Manifest File

**File Path:** `data/gold/{task}/{version}/manifest.json`

**Committed to Git:** Yes (for reproducibility)

### Manifest Schema

```json
{
  "manifest_version": "1.0",
  "dataset": {
    "dataset_id": "somali-dialect-v1",
    "dataset_version": "1.0.0",
    "task": "dialect_classification",
    "created_at": "2025-11-15T10:30:00Z",
    "created_by": "annotation-pipeline-v2"
  },
  "source_data": {
    "silver_commit": "3380cb2abc...",
    "silver_run_ids": ["run-20251101-001", "run-20251102-001"],
    "config_hash": "sha256:abc123..."
  },
  "schema": {
    "version": "1.0.0",
    "fields": ["gold_id", "silver_id", "text", "dialect_label", "split", ...]
  },
  "statistics": {
    "total_records": 10000,
    "train_records": 7000,
    "validation_records": 1500,
    "test_records": 1500,
    "dialect_distribution": {
      "north": 2500,
      "south": 2000,
      "benadiri": 1500,
      "maay": 1500,
      "diaspora": 2000,
      "unknown": 500
    }
  },
  "annotation": {
    "method": "consensus",
    "annotator_count": 3,
    "annotation_rounds": 2,
    "inter_annotator_agreement": 0.87
  },
  "quality": {
    "validation_checks": ["schema_compliance", "label_distribution", "split_ratios"],
    "validation_results": "PASS"
  }
}
```

### Manifest Fields

**dataset:**
- `dataset_id`: Unique dataset identifier
- `dataset_version`: Semantic version
- `task`: Task type
- `created_at`: Creation timestamp
- `created_by`: Creation pipeline/tool

**source_data:**
- `silver_commit`: Git commit hash of silver data used
- `silver_run_ids`: List of run_ids from silver layer
- `config_hash`: Hash of config used for reproducibility

**schema:**
- `version`: Schema version
- `fields`: List of all fields in dataset

**statistics:**
- `total_records`: Total record count
- `train_records`, `validation_records`, `test_records`: Per-split counts
- `dialect_distribution` (or task-specific distribution): Label distribution

**annotation:**
- `method`: Annotation method used
- `annotator_count`: Number of annotators
- `annotation_rounds`: Number of annotation passes
- `inter_annotator_agreement`: Kappa, F1, or other agreement metric

**quality:**
- `validation_checks`: List of quality checks performed
- `validation_results`: Overall result (PASS/FAIL)

---

## Data Splits

### Split Ratios

**Recommended ratios:**
- **Train:** 70% (used for model training)
- **Validation:** 15% (used for hyperparameter tuning)
- **Test:** 15% (used for final evaluation, held out)

**Optional:**
- **Dev:** Small subset of train for rapid iteration

### Split Assignment

**Requirements:**
- Stratified by dialect label (maintain label distribution across splits)
- Random assignment with fixed seed (for reproducibility)
- No data leakage between splits

**Code Example (Conceptual):**
```python
from sklearn.model_selection import train_test_split

# Split train vs. (val+test)
train, temp = train_test_split(
    data,
    test_size=0.30,
    stratify=data['dialect_label'],
    random_state=42
)

# Split val vs. test
val, test = train_test_split(
    temp,
    test_size=0.50,
    stratify=temp['dialect_label'],
    random_state=42
)
```

---

## Quality Assurance

### Schema Validation

**Tools:** Pydantic or Pandera

**Validation Checks:**
- All required fields present
- Enum values valid
- Confidence scores in range [0, 1]
- Timestamps in ISO 8601 format
- UUID format for gold_id

### Data Quality Checks

- **Label Distribution:** No extreme class imbalance (min 5% per class recommended)
- **Split Ratios:** Train/val/test ratios within 5% of target
- **Annotation Quality:** Inter-annotator agreement ≥ 0.70 (Kappa or F1)
- **Text Quality:** No empty texts, minimum length requirements
- **Duplicate Detection:** No duplicate gold_ids

### Documentation Requirements

For each gold dataset release:
1. **Manifest file** (full metadata)
2. **README.md** (dataset description, usage examples)
3. **CITATION.cff** (citation information for research)
4. **LICENSE** (data license, usually CC-BY-SA or CC-BY)

---

## Future Extensions

### Additional Tasks

As project expands, add schemas for:
- **Sentiment Analysis:** `{text, sentiment_label (positive/negative/neutral), confidence}`
- **Named Entity Recognition:** `{text, tokenized_text, ner_tags (PER/LOC/ORG/O)}`
- **Question Answering:** `{question, context, answer, answer_start}`
- **Natural Language Inference:** `{premise, hypothesis, label (entailment/contradiction/neutral)}`

### SomaliGLUE Benchmark

Design supports future SomaliGLUE benchmark:
- Multiple tasks packaged together
- Standardized evaluation protocols
- Leaderboard integration
- Versioned releases

---

## References

- **Audit Report:** `.claude/audit-implementation-plan-detailed.md` (§3.1, §6.1 #5)
- **Silver Schema:** `docs/reference/silver-schema.md`
- **Metrics Schema:** `docs/reference/metrics-schema.md`

---

## Change Log

- **2025-11-15:** Initial specification created (Stage 0.5)
