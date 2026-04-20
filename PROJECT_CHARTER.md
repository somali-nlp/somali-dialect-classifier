# Project Charter: Somali Dialect Classifier

**Version:** 1.0  
**Status:** Active  
**Date:** 2026-04-20  
**Owner:** ilyasibrahim  
**Governance Tier:** Solo Open-Source Project

---

## 1. Mission

Build a production-quality, reproducible pipeline for curating, classifying, and serving high-quality Somali language text — with particular focus on dialectal variation across Northern (Standard Somali / Af-Maay), Southern (Af-Maay), and Central dialect regions — to enable downstream NLP research on a critically under-resourced language.

---

## 2. Vision

A publicly documented, citable reference implementation demonstrating that rigorous ML data engineering (medallion architecture, structured quality filtering, ethical scraping, DI-based pipeline, dashboard observability) is achievable for low-resource languages by a solo maintainer. The project will produce a dialect-labeled corpus, a fine-tuned XLM-RoBERTa classifier, and a deployment-ready inference service — all open-source.

---

## 3. Scope

### In Scope

- Data curation from five sources: Somali Wikipedia, BBC Somali, HuggingFace MC4, Språkbanken corpora, TikTok via Apify
- Quality filtering, text cleaning, and deduplication using three-phase dedup (ledger, SHA256+MinHash LSH, cross-dataset persistent LSH)
- Silver-layer Parquet dataset with unified schema (ISO 639-1 language field, license tracking, provenance metadata)
- Dialect annotation pipeline (Phase 2: heuristic pre-labeling; Phase 3: supervised fine-tuning)
- XLM-RoBERTa fine-tuned dialect classifier for Northern / Southern / Central Somali (Phase 3)
- Static dashboard for pipeline observability and quality metrics
- RESTful inference API and containerized deployment (Phase 4)
- Open-source governance: MIT license, CONTRIBUTING guide, CODE_OF_CONDUCT, issue/PR templates, CI/CD

### Out of Scope

- Speech/audio processing or ASR
- Machine translation between Somali dialects
- PII collection of any kind (no usernames, emails, or identifiable author data)
- Commercial licensing or SaaS deployment
- Languages other than Somali (ISO `so`)

---

## 4. Phased Objectives and Key Results

### Phase 1 — Data Curation (COMPLETE)

**Objective:** Establish a reproducible, ethically-sourced corpus of 130k–300k deduplicated Somali-language records.

| Key Result | Target | Status |
|------------|--------|--------|
| Five data sources integrated and pipeline-tested | 5 sources | Done |
| Silver-layer Parquet schema enforced across all sources | Schema v2.1 | Done (F-006 naming drift pending fix) |
| Three-phase deduplication operational | Phase 1+2+3 dedup | Done (F-003 file-dedup bug pending fix) |
| CI/CD with 9 workflows including anomaly detection | 9 workflows | Done |
| Dashboard exposing filter telemetry and quality metrics | Live | Done |
| Phase 2 data readability | Silver read-back | Blocked by F-002 (JSON sidecar bug) |
| HuggingFace processor contract alignment | BasePipeline contract | Blocked by F-001 (bypass) |

**Phase 1 Audit Rating:** 6/10 (2026-03-12). Three CRITICAL findings block Phase 2 entry. See `audits/2026-03-10-phase1-audit/audit-report-final.md`.

---

### Phase 2 — Preprocessing and Annotation (NEXT)

**Objective:** Produce a dialect-annotated dataset ready for model training.

| Key Result | Target | Condition |
|------------|--------|-----------|
| Silver read-back fixed; preprocessing pipeline can consume Phase 1 output | 0 `ArrowInvalid` errors | Requires F-002 resolution |
| HuggingFace processor aligned with `BasePipeline` contract | 0 bypasses of `RecordBuilder` / `ValidationService` | Requires F-001 resolution |
| Heuristic dialect pre-labeling applied to ≥80% of silver records | ≥80% coverage | TBD |
| Human annotation protocol documented and piloted | Annotation guide + 500 spot-checked records | TBD |
| Preprocessing validator operates in true streaming mode | Memory-bounded at 1M records | Requires F-007 resolution |
| Provenance traceable end-to-end (run_id consistent across ledger, metrics, silver) | Single canonical run_id per task | Requires F-004 resolution |

---

### Phase 3 — Model Training (FUTURE)

**Objective:** Fine-tune and evaluate a XLM-RoBERTa-based Somali dialect classifier.

| Key Result | Target |
|------------|--------|
| XLM-RoBERTa-base fine-tuned on annotated dialect corpus | F1 ≥ 0.75 on held-out test split |
| Per-dialect evaluation: Northern, Southern (Af-Maay), Central | F1 ≥ 0.70 per class |
| Model card published per Mitchell et al. 2019 format | Published at `docs/model-cards/` |
| Bias and fairness analysis documented | In model card |
| Reproducible training script with fixed seed, logged hyperparameters | `experiments/` directory |

---

### Phase 4 — Deployment (FUTURE)

**Objective:** Package and deploy the classifier as a production-quality, citable inference service.

| Key Result | Target |
|------------|--------|
| REST inference API (FastAPI) containerized with Docker | Docker image published |
| GitHub Actions CI for model regression on API | No regression on reference test set |
| Academic citation format documented | BibTeX in README |
| Open-source release announcement | GitHub release + dataset card on HuggingFace Hub |

---

## 5. Stakeholder Register

| Stakeholder | Role | Interest | Influence |
|-------------|------|----------|-----------|
| ilyasibrahim | Owner / Solo Maintainer | Delivery, correctness, open-source reputation | Decision authority |
| Somali NLP research community | Primary beneficiary | Access to reproducible corpus and classifier | None (feedback via issues) |
| Open-source contributors | Potential contributors | Contribution experience, documentation quality | Low (PR review) |
| Academic institutions using corpus | External researchers | Data quality, license clarity, citability | None |
| BBC, Wikipedia, Språkbanken, HuggingFace | Data providers | Compliance with their terms of service | Indirect (data access) |
| Apify (TikTok data) | Paid API provider | API usage within quota | Indirect (billing) |

---

## 6. Governance Model

This project operates under a **solo maintainer** governance model with open-source community input.

**Decision authority:** All architectural and scope decisions rest with the owner.

**Contribution process:** Pull requests accepted from external contributors per `CONTRIBUTING.md`. Contract tests (`test_base_pipeline_contract.py`) and regression tests (`tests/regression/`) serve as automated gatekeepers.

**ADR process:** Significant technical decisions are documented as Architecture Decision Records in `docs/decisions/`. Current ADRs:
- ADR-001: OSCAR dataset exclusion (Accepted)
- ADR-002: Filter framework design (Accepted)
- ADR-003: MADLAD-400 exclusion (Accepted)
- ADR-004: Package naming (`somnlp`) (Proposed)

**Release cadence:** No fixed cadence. Releases tied to phase completion milestones.

**Audit cycle:** Full codebase audits at phase boundaries. Phase 1 audit completed 2026-03-12.

---

## 7. Success Criteria

| Criterion | Measure |
|-----------|---------|
| Phase 1 complete | Silver read-back passes; HF processor aligned; F-001/F-002/F-003 resolved |
| Phase 2 complete | Dialect-annotated dataset exported; preprocessing validator streaming; provenance traceable |
| Phase 3 complete | XLM-R classifier with F1 ≥ 0.75 on Northern/Southern/Central dialect classification |
| Phase 4 complete | REST API deployed; model card published; cited in at least one academic paper or HuggingFace leaderboard |
| Open-source health | Reproducibility score ≥ 95/100; newcomer can reproduce pipeline in <30 minutes |

---

## 8. Known Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| Solo maintainer | All decisions, all code, all docs on one person | Strict contract testing; DI architecture minimizes coupling |
| TikTok data cost | ~$1 per 1,000 comments via Apify | Budget-capped runs; TikTok MinHash disabled to maximize value of paid data |
| BBC robots.txt | Max ~350 articles/day; 3–6s rate limiting | Quota system in `CrawlLedger`; adaptive rate limiter |
| HuggingFace MC4 streaming | Dataset too large for RAM | Streaming batch checkpointing with manifest-based resume |
| Phase 2 blocked | F-001 and F-002 are CRITICAL blockers | Tracked in audit; must be resolved before Phase 2 work begins |
| Silver read-back broken | `ArrowInvalid` on JSON sidecars in Parquet partition dirs | Fix F-002 as first Phase 2 task |

---

## 9. Out of Scope

The following are explicitly not part of this project's mandate:

- Any form of PII collection, storage, or processing
- Speech recognition or text-to-speech for Somali
- Translation systems between Somali and other languages
- Dialect classification for languages other than Somali
- Commercial or proprietary licensing
- Real-time streaming inference (batch inference only in Phase 4)
- Coverage of all Somali sub-dialects (only the three primary groupings: Northern, Southern/Af-Maay, Central)

---

## 10. Revision History

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-04-20 | 1.0 | Initial charter, covering Phase 1 audit results and Phase 2–4 objectives | ilyasibrahim |

---

**Related Documents:**
- `audits/2026-03-10-phase1-audit/audit-report-final.md` — Full Phase 1 audit
- `governance/executive-brief.md` — One-page executive summary
- `docs/decisions/` — Architecture Decision Records
- `CONTRIBUTING.md` — Contribution guidelines
