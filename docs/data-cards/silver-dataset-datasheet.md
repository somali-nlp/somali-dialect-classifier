# Datasheet for the Somali Silver Dataset

**Format:** Datasheet for Datasets (Gebru et al., 2021)  
**Dataset Name:** Somali Silver Dataset  
**Version:** Phase 1 (v2.1 schema)  
**Date:** 2026-04-20  
**Maintainer:** ilyasibrahim  
**Contact:** Via GitHub Issues at the project repository

---

## Motivation

### Why was this dataset created?

Somali (ISO 639-1: `so`) is spoken by approximately 25 million people across Somalia, Ethiopia, Kenya, Djibouti, and diaspora communities worldwide. It is severely under-resourced for NLP: no publicly available dialect classifier exists, and curated training corpora are scarce. This dataset was created to:

1. Provide a reproducible, ethically-sourced Somali text corpus for downstream NLP tasks — particularly dialect classification across Northern (Standard Somali), Southern (Af-Maay), and Central dialect groups.
2. Demonstrate production-quality data engineering practices for low-resource language NLP.

### Who created this dataset?

ilyasibrahim, operating as a solo open-source maintainer. No institutional funding or organizational affiliation.

### Who funded the creation?

No institutional funding. TikTok comment collection is paid via Apify (approximately $1 per 1,000 comments). All other sources are free/open access.

---

## Composition

### What do the instances represent?

Each instance is a single text document in the Somali language, sourced from one of five origins (see source breakdown below). Documents range from encyclopedic articles to news articles, academic corpora, and social media comments.

### How many instances are there in total?

The Phase 1 collection objective is 130,000–300,000 deduplicated records. The May 2026 validation run (pipeline end-to-end validation, not the production collection campaign) produced **16,767 records / ~4.66M tokens** (partition date_accessed=2026-05-29). The production collection campaign (campaign_init_001) has not yet run as of 2026-06-11. Exact counts by source are logged in `data/metrics/` and surfaced by `somali-tools metrics consolidate`; precise per-run totals should be retrieved from the metrics pipeline (`somali-tools metrics consolidate`).

### Source Breakdown

| Source | Source Name in Dataset | Source Type | License | Dedup Strategy | Approx. Records |
|--------|------------------------|-------------|---------|----------------|-----------------|
| Somali Wikipedia | `Wikipedia-Somali` | `wiki` | CC-BY-SA-3.0 | 5-level: HTTP 304, URL filter, text hash, namespace filter, incremental timestamp | ~50,000 |
| BBC Somali | `BBC-Somali` | `news` | BBC Terms of Use (non-commercial research) | RSS + conditional HTTP requests + parameter cache | ~5,000–10,000 (350/day quota) |
| HuggingFace MC4 | `HuggingFace-MC4` | `web_corpus` | ODC-By (allenai/c4) | Streaming checkpoints + manifest-based dedup; MinHash LSH active | ~100,000–200,000 |
| Språkbanken | `Sprakbanken-Somali` | `corpus` | CC BY 4.0 (per corpus; see metadata) | File-level hash + cross-dataset persistent LSH | TBD — fill from metrics pipeline |
| TikTok (via Apify) | `TikTok-Somali` | `social` | TikTok Terms of Service (research use) | Exact SHA256 only; MinHash intentionally disabled | TBD — fill from metrics pipeline |

**Note on TikTok deduplication:** MinHash LSH is intentionally disabled for TikTok data (`enable_minhash=False`, `similarity_threshold=1.0`). TikTok comments contain deliberate dialectal and orthographic variation that near-duplicate detection would incorrectly suppress. This is a documented design decision, not a bug.

### Does the dataset contain all possible instances or a sample?

A sample. Wikipedia and Språkbanken represent the full available Somali corpora from those sources. BBC Somali is quota-limited (350 articles/day; no historical archive). HuggingFace MC4 is streamed with an optional `--max-records` cap. TikTok data is sourced from a pre-configured URL list (`data/tiktok_urls.txt`).

### Is there a label or target associated with each instance?

Not in Phase 1. Phase 1 is dialect-agnostic: no dialect labels are assigned. Topic enrichment metadata is attached via the `topic_lexicon_enrichment_filter` (field: `primary_dialect` in `source_metadata` — this field name is legacy; it stores a topic category, not a linguistic dialect label). True dialect labels are planned for Phase 2.

### Are there recommended data splits (train/validation/test)?

No splits are defined in Phase 1. Splitting is deferred to Phase 2 annotation work.

### Is any information missing from individual instances?

- `embedding` field is present in schema but always null (placeholder for Phase 3).
- `date_published` may be absent for some sources where publication date is not available.
- `source_id` may be null where no external identifier exists.
- `register` field is populated with heuristic values (`formal`, `informal`, `colloquial`) — not human-verified.

### Are relationships between instances captured?

No explicit cross-document relationships. Deduplication removes near-duplicates, but no citation graph or threading is preserved.

### Are there any errors, sources of noise, or redundancies?

- Language detection (`langid_filter`) uses heuristic Somali-specific patterns, not a trained classifier. False positives (non-Somali text passing) may occur, particularly for Afroasiatic languages with lexical overlap.
- BBC data excludes historical articles (quota and recency limits apply).
- HuggingFace MC4 is a web crawl and may contain boilerplate, navigation text, or low-quality passages not caught by `min_length_filter`.
- As of Phase 1 audit (2026-03-12): file-level deduplication for Wikipedia and Språkbanken has a confirmed bug (`dedup.py:931,971` — `self.ledger` not initialized). Duplicate large downloads may be reprocessed. This is tracked as F-003 (HIGH severity) in the audit report.

### Is the dataset self-contained?

No. The pipeline must be re-run to regenerate data. Raw source files are downloaded to `data/raw/`; silver Parquet files are in `data/processed/silver/`. Neither is committed to the repository.

---

## Collection Process

### How was the data associated with each instance acquired?

Data collection is fully automated via source-specific processor classes extending `BasePipeline`:

- **Wikipedia:** XML dump downloaded from `dumps.wikimedia.org/sowiki/latest/`; parsed with streaming SAX parser; WikiMarkup stripped.
- **BBC Somali:** RSS feed discovery (`https://feeds.bbci.co.uk/somali/rss.xml`) followed by article scraping with `AdaptiveRateLimiter` (3–6s delays, token-bucket algorithm); `robots.txt` compliance enforced.
- **HuggingFace MC4:** Streamed via `datasets` library (`allenai/c4`, config `so`); streaming batch checkpointing with manifest-based resume for interrupted runs.
- **Språkbanken:** Downloaded from University of Gothenburg's Korp API; 23 corpora across news, literature, science, health, radio, and historical domains.
- **TikTok:** Apify Actor API (`tiktok-comment-scraper`); input URL list from `data/tiktok_urls.txt`.

### What mechanisms or procedures were used to collect the data?

Collection scripts use:
- `AdaptiveRateLimiter` (token-bucket) for rate limiting
- `TimeoutHTTPSession` with SSRF blocking (`is_safe_url()`)
- `defusedxml` for XXE-safe XML parsing
- `CrawlLedger` (SQLite/PostgreSQL) for state tracking and quota enforcement
- `DedupEngine` with `ShardedLSH` and `LRUHashSet` for extraction-stage deduplication

### Who collected the data?

Automated pipeline only, operated by ilyasibrahim. No crowdsourced or human collectors.

### Over what timeframe was the data collected?

Phase 1 data collection began October 2025. The `date_accessed` partition field in each Parquet file records the exact collection date per run.

### Were any ethical review processes conducted?

No formal IRB process (not an institution-affiliated project). Ethical scraping practices applied:
- `robots.txt` compliance for BBC Somali
- Research-identifying User-Agent header
- Rate limiting to avoid server impact
- No PII collection (text-only; no usernames, emails, or identifiable author data collected)
- TikTok comments are public-facing; no private messages scraped

---

## Preprocessing, Cleaning, and Labeling

### Was any preprocessing or cleaning done?

Yes. Each record passes through a `TextCleaningPipeline` before quality filtering:

1. **WikiMarkupCleaner** (Wikipedia only): Strips `[[links]]`, `{{templates}}`, `<ref>` tags, section headings, list markers.
2. **HTMLCleaner** (BBC, TikTok): Strips HTML tags and entities.
3. **WhitespaceCleaner** (all sources): Normalizes multiple spaces and newlines.

### Was any labeling done?

Phase 1: No human labeling. Automated enrichment only:
- `topic_lexicon_enrichment_filter`: Attaches a heuristic topic category to `source_metadata.primary_dialect` (field name is a legacy artifact; the value is a topic, not a dialect label).
- `langid_filter`: Attaches `detected_lang` and `lang_confidence` to `source_metadata`.
- `namespace_filter` (Wikipedia): Attaches `namespace` to rejected records' metadata.

### Was the raw data saved?

Yes. Raw downloads are stored in `data/raw/source=*/date_accessed=YYYY-MM-DD/` (partitioned by source and date). Staging files in `data/staging/`. Neither is committed to the repository.

### Deduplication — Three-Phase System

The pipeline implements three distinct dedup phases:

| Phase | Stage | Mechanism | Notes |
|-------|-------|-----------|-------|
| 1 | Discovery | Ledger-based URL tracking | Prevents re-crawling known URLs |
| 2 | Extraction | SHA256 exact hash + MinHash LSH (`ShardedLSH` + `LRUHashSet`) | Near-duplicate suppression; TikTok disables MinHash |
| 3 | Processing | Cross-dataset persistent LSH index | Catches cross-source duplicates at silver write time |

**Known issue (Phase 1 audit F-003):** File-level dedup (`check_file_duplicate()` in `dedup.py`) has a bug where `self.ledger` is referenced but never initialized. Large-file dedup for Wikipedia and Språkbanken silently fails. Fix is pending.

---

## Uses

### What tasks has the dataset been used for?

Phase 1: Not yet used for model training. Intended as pre-training / fine-tuning corpus for Somali dialect classification.

### What tasks should this dataset not be used for?

- **Dialect classification** without Phase 2 annotation: Phase 1 records carry no verified dialect labels.
- **PII research or author identification:** No author metadata is preserved; the pipeline explicitly avoids collecting it.
- **Speech synthesis or ASR:** Text-only dataset.
- **Sentiment analysis:** No sentiment labels; the corpus is not balanced for sentiment.
- **Commercial applications** using BBC data: BBC Somali content is covered by BBC Terms of Use; commercial use requires separate licensing.

### Is there anything about the composition, collection, or preprocessing that might affect future uses?

- The `langid_filter` is heuristic, not trained. For tasks requiring high-precision language identification, additional filtering is recommended.
- MC4 data (the largest source) is a web crawl and may exhibit web-corpus distribution biases.
- TikTok comments reflect informal, colloquial register and social media-specific orthography. They are not representative of formal written Somali.
- The `register` field is assigned heuristically per source (e.g., Wikipedia = "formal"), not per-document. Records with atypical register for their source will be mislabeled.

---

## Distribution

### How will the dataset be distributed?

The pipeline code and processing scripts are distributed as open-source under MIT license. Raw and silver data files are not committed to the repository; end users must re-run the pipeline to generate the dataset locally.

A processed snapshot may be published to HuggingFace Hub in Phase 4.

### What license applies to the dataset?

Licenses vary by source. Each silver record's `license` field carries the applicable license string:

| Source | License |
|--------|---------|
| Wikipedia-Somali | CC-BY-SA-3.0 |
| BBC-Somali | BBC Terms of Use (research/non-commercial) |
| HuggingFace-MC4 | ODC-By (allenai/c4) |
| Sprakbanken-Somali | CC BY 4.0 (per-corpus; verify `source_metadata`) |
| TikTok-Somali | TikTok Terms of Service |

Pipeline code: MIT.

### How should this dataset be cited?

TBD — citation format will be established at Phase 4 open-source release. See `README.md` for the current citation block.

---

## Maintenance

### Who maintains the dataset?

ilyasibrahim. The pipeline is designed for reproducibility: re-running the pipeline regenerates the dataset from upstream sources.

### How will updates be communicated?

Via GitHub releases and the project's CHANGELOG.

### Will the dataset be updated in response to upstream changes?

Source data (Wikipedia dumps, BBC articles, HuggingFace MC4) changes over time. The pipeline uses `date_accessed` partitioning and ledger-based dedup to allow incremental updates without reprocessing historical data. New pipeline runs append to the silver layer; they do not overwrite existing partitions.

### Will older versions be supported?

The silver schema is versioned via `pipeline_version` in each record. Schema migrations are documented in `docs/reference/metrics-schema.md` and enforced by `SilverDatasetWriter`.

### Is there any mechanism for dataset consumers to flag issues?

Yes — GitHub Issues at the project repository.

---

## References

- Gebru, T. et al. (2021). Datasheets for Datasets. *Communications of the ACM*, 64(12), 86–92.
- Wang, A. et al. (2019). allenai/c4 (MC4). HuggingFace Hub.
- Somali Wikipedia dump: https://dumps.wikimedia.org/sowiki/
- Språkbanken corpora: https://spraakbanken.gu.se/ (23 Somali corpora)
- Phase 1 audit: `audits/2026-03-10-phase1-audit/audit-report-final.md`

---

**Maintainers**: Somali NLP Contributors
