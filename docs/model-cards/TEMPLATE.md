# Model Card Template: Somali Dialect Classifier

**Format:** Model Card (Mitchell et al., 2019)  
**Template Version:** 1.0  
**Status:** Template — to be completed when Phase 3 training is complete  
**Instructions:** Replace all `[PLACEHOLDER]` values and example rows. Remove this instruction block before publishing.

---

## Model Details

| Field | Value |
|-------|-------|
| Model name | [PLACEHOLDER — e.g., `somnlp-dialect-xlmr-base`] |
| Model type | Fine-tuned transformer sequence classifier |
| Base model | [PLACEHOLDER — e.g., `xlm-roberta-base`] |
| Training framework | [PLACEHOLDER — e.g., HuggingFace Transformers, PyTorch] |
| Model version | [PLACEHOLDER — e.g., `v1.0.0`] |
| Release date | [PLACEHOLDER — e.g., 2026-QX] |
| License | [PLACEHOLDER — e.g., MIT (model weights); training data licenses vary by source — see datasheet] |
| Contact | Via GitHub Issues |

**Example (completed row format):**

| Field | Value |
|-------|-------|
| Model name | `somnlp-dialect-xlmr-base-v1` |
| Model type | Fine-tuned transformer, sequence classification |
| Base model | `xlm-roberta-base` (560M params) |
| Training framework | HuggingFace Transformers 4.x, PyTorch 2.x |
| Model version | v1.0.0 |
| Release date | 2026-Q3 |
| License | MIT (model weights); training corpus licenses mixed — see datasheet |

### Model Description

[PLACEHOLDER — 2–4 sentences. Describe what the model does, what it was trained on, and what problem it solves. Example:]

> `somnlp-dialect-xlmr-base` is a sequence classifier fine-tuned on XLM-RoBERTa-base to identify the dialect group of Somali text. It distinguishes three classes: Northern (Standard Somali), Southern (Af-Maay), and Central. The model was trained on the Somali Silver Dataset (Phase 1–2), a curated corpus of [N] annotated records from Wikipedia, BBC Somali, HuggingFace MC4, Språkbanken, and TikTok.

---

## Intended Use

### Primary Use Cases

- Dialect-aware text routing for downstream NLP pipelines
- Corpus analysis and dialect distribution studies
- Language learning tools requiring dialect identification
- Pre-processing step for dialect-specific fine-tuning

### Out-of-Scope Use Cases

- Any form of speaker/author identification
- Geo-location or ethnicity inference from text
- Sentiment analysis or toxicity detection (model is trained only for dialect classification)
- Languages other than Somali (ISO `so`)
- Commercial deployment without reviewing source data licenses (BBC Somali content has non-commercial restrictions)

---

## Factors

### Relevant Factors

The following factors may affect model behavior and should be evaluated:

| Factor | Description |
|--------|-------------|
| Dialect group | Northern (Standard Somali), Southern (Af-Maay), Central |
| Text register | Formal (encyclopedic, news) vs. informal (social media comments) |
| Text length | Short comments vs. long articles |
| Source domain | Wikipedia, news, social media, academic corpora |
| Orthographic variation | Somali spelling is not standardized across dialects |

### Evaluation Factors

[PLACEHOLDER — list which factor combinations were explicitly evaluated in the evaluation data. Example:]

> Evaluation was stratified by source (Wikipedia, BBC, TikTok) and text length quartile. Register distribution: [N]% formal, [N]% informal, [N]% colloquial. Dialect distribution in test set: [N]% Northern, [N]% Southern, [N]% Central.

---

## Metrics

### Performance Metrics

| Metric | Definition | Relevance |
|--------|------------|-----------|
| Macro F1 | Unweighted mean F1 across all 3 dialect classes | Primary metric; treats all classes equally regardless of frequency |
| Per-class F1 | F1 per dialect class | Detects per-dialect performance gaps |
| Accuracy | Fraction of correctly classified instances | Secondary; can mask class imbalance |
| Confidence calibration (ECE) | Expected Calibration Error | Measures whether confidence scores are reliable |

**Example (completed row format):**

| Metric | Corpus-wide | Northern | Southern (Af-Maay) | Central |
|--------|-------------|----------|---------------------|---------|
| Macro F1 | 0.78 | 0.82 | 0.74 | 0.77 |
| Accuracy | 0.81 | — | — | — |
| ECE | 0.06 | — | — | — |

---

## Evaluation Data

### Dataset

[PLACEHOLDER — describe the held-out test set. Example:]

> Test split: [N] records held out from the Phase 2 annotated dataset, stratified by source and dialect group. Split performed with fixed random seed [SEED]. Records in the test set were not seen during fine-tuning.

### Motivation

[PLACEHOLDER — why this test set reflects realistic deployment conditions.]

### Preprocessing Applied

[PLACEHOLDER — same preprocessing as training: `TextCleaningPipeline` (WikiMarkupCleaner, HTMLCleaner, WhitespaceCleaner), tokenization via `xlm-roberta-base` tokenizer, max sequence length [N].]

---

## Training Data

### Dataset

Training data: Somali Silver Dataset (Phase 1–2). See full datasheet at `docs/data-cards/silver-dataset-datasheet.md`.

| Field | Value |
|-------|-------|
| Training records | [PLACEHOLDER — e.g., ~200,000 annotated records] |
| Annotation method | [PLACEHOLDER — heuristic pre-labeling (Phase 2) + human spot-check] |
| Dialect distribution (train) | [PLACEHOLDER — N% Northern, N% Southern, N% Central] |
| Source distribution (train) | [PLACEHOLDER — N% Wikipedia, N% BBC, N% MC4, N% Språkbanken, N% TikTok] |

**Example (completed row format):**

| Field | Value |
|-------|-------|
| Training records | 180,000 annotated records |
| Annotation method | Heuristic pre-labeling + 2,000 human-verified spot checks |
| Dialect distribution (train) | 65% Northern, 25% Southern (Af-Maay), 10% Central |
| Source distribution (train) | 45% MC4, 30% Wikipedia, 15% BBC, 7% Språkbanken, 3% TikTok |

### Preprocessing

[PLACEHOLDER — tokenization, max sequence length, any data augmentation.]

---

## Quantitative Analyses

### Unitary Results

[PLACEHOLDER — performance on each dialect class in isolation, from the evaluation data section.]

| Dialect | Precision | Recall | F1 | Support |
|---------|-----------|--------|----|---------|
| Northern | [N] | [N] | [N] | [N] |
| Southern (Af-Maay) | [N] | [N] | [N] | [N] |
| Central | [N] | [N] | [N] | [N] |

**Example (completed row format):**

| Dialect | Precision | Recall | F1 | Support |
|---------|-----------|--------|----|---------|
| Northern | 0.83 | 0.81 | 0.82 | 1,240 |
| Southern (Af-Maay) | 0.72 | 0.76 | 0.74 | 480 |
| Central | 0.79 | 0.75 | 0.77 | 280 |

### Intersectional Results

[PLACEHOLDER — performance by source × dialect combinations. Flag any combinations with poor coverage or degraded performance.]

| Source | Northern F1 | Southern F1 | Central F1 |
|--------|-------------|-------------|------------|
| Wikipedia | [N] | [N] | [N] |
| BBC | [N] | [N] | [N] |
| TikTok (social) | [N] | [N] | [N] |

---

## Ethical Considerations

- **No PII:** Training data contains no usernames, emails, or identifiable author information. The pipeline explicitly avoids collecting PII (see data collection pipeline and `docs/data-cards/silver-dataset-datasheet.md`).
- **Dialect imbalance:** Northern (Standard Somali) is significantly over-represented in text corpora compared to Southern and Central dialects. The model may perform worse on under-represented dialects. See quantitative analyses for per-dialect F1 scores.
- **Proxy for sensitive attributes:** Dialect can correlate with geographic origin and ethnicity. This model should not be used for any purpose that infers demographic characteristics of individuals.
- **Orthographic instability:** Written Somali lacks a standardized orthography across dialectal contexts. Evaluation on informal text (TikTok) may differ substantially from formal text (Wikipedia, BBC).
- **Data provenance caveats:** The HuggingFace MC4 source (web crawl) may contain machine-translated or low-quality text that passed quality filters. The BBC source is limited to recent articles (quota-capped). See the Phase 1 audit for full provenance limitations.

---

## Caveats and Recommendations

- This model targets three broad dialect groups. It does not distinguish sub-dialects within each group.
- Users deploying on informal text (e.g., social media, SMS) should validate against their own domain before relying on confidence scores.
- The `register` field in training data is heuristically assigned per-source, not per-document. Users who need register-controlled evaluation should filter by `source` rather than `register`.
- For academic use: cite both this model card and the Silver Dataset datasheet (`docs/data-cards/silver-dataset-datasheet.md`).
- Known Phase 1 corpus limitations apply to this model's training data — see the datasheet and `audits/2026-03-10-phase1-audit/audit-report-final.md`.

---

## References

- Mitchell, M. et al. (2019). Model Cards for Model Reporting. *FAccT 2019*.
- Conneau, A. et al. (2020). Unsupervised Cross-lingual Representation Learning at Scale (XLM-RoBERTa). *ACL 2020*.
- Silver Dataset Datasheet: `docs/data-cards/silver-dataset-datasheet.md`
- Phase 1 Audit: `audits/2026-03-10-phase1-audit/audit-report-final.md`

---

**Maintainers**: Somali NLP Contributors
