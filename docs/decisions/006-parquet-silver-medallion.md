# ADR 006 — Parquet / Medallion Silver Storage

**Date:** 2025-11-01 (decision made during Phase 1 design; recorded retrospectively 2026-06-12)
**Status:** Accepted (retrospective)
**Deciders:** Project principal

---

## Context

The pipeline collects Somali text from five heterogeneous sources (Wikipedia XML dump, BBC HTML scrape, HuggingFace streaming dataset, Språkbanken corpus files, TikTok comments via API). A unified storage format is needed that:

- Enforces a common schema across all sources
- Enables efficient partial reads by source or date
- Is readable by downstream ML training code without a dedicated data service
- Can version the schema as the project moves from Phase 1 to Phase 2 modelling

---

## Decision

Use **Apache Parquet** with a **medallion (Bronze → Silver → Gold) layered architecture**:

- **Bronze (raw/):** Immutable, source-native files (XML, JSON, HTML, JSONL)
- **Silver (processed/silver/):** Schema-enforced, deduplicated Parquet files with a 21-field schema; partitioned by `source=<lowercase-kebab>/date_accessed=YYYY-MM-DD/`
- **Gold (future):** Dialect-labelled, model-ready datasets (not yet implemented)

The silver schema is authoritative in `SilverDatasetWriter.SCHEMA` in `src/somdialc/quality/silver_writer.py`.

---

## Rationale

1. **Schema enforcement:** PyArrow schema validation at write time prevents silent type drift. The `tokens` field is `int64` (not `int32`) to avoid overflow on large corpora without casting.
2. **Partitioning:** Hive-compatible `source=*/date_accessed=*` partitioning enables source-filtered reads in Spark, DuckDB, and pandas without loading all data.
3. **Incremental updates:** New partitions can be added without reprocessing previous dates.
4. **Interoperability:** Parquet is readable by every major ML framework (Hugging Face Datasets, PyTorch DataPipes, TensorFlow, Ray) without a custom reader.
5. **Atomic writes:** Parquet fragments are written atomically (temp file + rename) to prevent partial reads on crash.
6. **Source-name canonicalisation:** All source values are lowercase-kebab (e.g. `wikipedia-somali`, not `Wikipedia-Somali`) to prevent case-sensitivity mismatches in partition paths across macOS and Linux. Constants live in `src/somdialc/ingestion/source_names.py`.

---

## Consequences

- `silver_writer.py` is the sole authoritative write path; processors must not write Parquet directly.
- Any schema change requires a version bump in `schema/registry.py` and a corresponding migration note.
- The Bronze layer is append-only; reprocessing always re-derives Silver from Bronze.
- A Gold layer will be added when dialect labels exist; its schema and storage decision will require a new ADR.

---

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|-----------------|
| JSON/JSONL for silver | No schema enforcement; large files; slow columnar access |
| CSV | No type information; schema drift inevitable |
| HuggingFace Datasets arrow cache | Introduces dependency on HF tooling; harder to inspect without Python |
| Delta Lake / Iceberg | Adds significant operational overhead for single-node pipeline; reconsider if distributed processing is adopted |
