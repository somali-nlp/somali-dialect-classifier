# Project Lifecycle & Roadmap

**Last Updated**: 2025-10-16
**Current Stage**: Data Curation (Phase 1) - ✅ **COMPLETE**

## Project Overview

The Somali Dialect Classifier is a multi-phase project to build a machine learning system for classifying Somali text by dialect, register, and domain.

**Goal**: Enable dialect-aware NLP applications for Somali language processing

**Stakeholders**:
- **Data Engineering**: Pipeline development, data quality
- **ML Engineering**: Model development, experiment tracking
- **MLOps**: Deployment, monitoring, model serving
- **Research**: Annotation guidelines, evaluation metrics

---

## Current Status: Phase 1 Complete ✅

### Phase 1: Data Curation & Preprocessing (COMPLETE)

**Timeline**: January 2025 - October 2025
**Status**: ✅ Production-ready

#### Completed Deliverables

1. **Data Pipelines** ✅
   - Wikipedia-Somali processor (50K+ articles)
   - BBC-Somali processor (news articles with scraping)
   - HuggingFace datasets processor (MC4, OSCAR, MADLAD-400)
   - Unified silver dataset schema (Parquet)

2. **Quality Framework** ✅
   - Pluggable filter system
   - Length, language, namespace filters
   - Topic enrichment heuristics
   - Filter statistics logging

3. **Infrastructure** ✅
   - Partitioned data lake (raw/staging/processed/silver)
   - Resume-capable extraction (JSONL batching)
   - Configuration management (pydantic-settings)
   - CLI tools (wikisom, bbcsom, hfsom)

4. **Testing & Quality** ✅
   - 165+ tests (unit, integration, contract)
   - Fixture-based testing
   - CI-ready test suite
   - Regression tests for edge cases

5. **Documentation** ✅
   - 10+ comprehensive guides
   - API reference
   - Architecture decision records
   - Processing pipeline walkthroughs

#### Key Metrics

| Metric | Value |
|--------|-------|
| Data Sources | 3 (Wikipedia, BBC, HuggingFace) |
| Total Records Processed | ~500K+ (sample runs) |
| Test Coverage | 165+ tests |
| Documentation Pages | 15+ |
| Lines of Code | ~8,000 |
| Filter Pass Rate | ~75% (varies by source) |

---

## Phase 2: Labeling & Annotation (NEXT - Q1 2026)

**Timeline**: January 2026 - March 2026
**Owner**: Research + Data Engineering
**Status**: 📋 Planning

### Objectives

1. Define annotation schema for dialect/domain classification
2. Build annotation interface and guidelines
3. Label initial dataset (5K-10K samples)
4. Measure inter-annotator agreement
5. Establish active learning workflow

### Deliverables

- [ ] Annotation guidelines document
- [ ] Label schema (dialect taxonomy)
- [ ] Annotation interface (Label Studio / Prodigy)
- [ ] Labeled dataset v1.0 (5K samples minimum)
- [ ] Inter-annotator agreement report (Kappa > 0.7 target)
- [ ] Active learning pipeline for model-assisted labeling

### Milestones

| Milestone | Target Date | Dependencies |
|-----------|-------------|--------------|
| Annotation schema finalized | 2026-01-15 | Research team alignment |
| Interface setup | 2026-01-31 | Engineering bandwidth |
| First 1K labels | 2026-02-15 | Annotator availability |
| IAA evaluation | 2026-02-28 | 1K labels complete |
| 5K labels complete | 2026-03-31 | Full team engagement |

### Key Decisions

1. **Dialect Taxonomy**: Northern vs. Southern? Mogadishu vs. Hargeysa? Domain-based?
2. **Annotation Tool**: Label Studio (open-source) vs. Prodigy (licensed)
3. **Annotator Pool**: In-house vs. crowdsourcing vs. expert linguists
4. **Label Granularity**: Binary, multi-class, or hierarchical labels

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Low inter-annotator agreement | High | Refine guidelines, add training phase |
| Insufficient labeled data | High | Implement active learning early |
| Annotator availability | Medium | Contract backup annotators |
| Dialect ambiguity | Medium | Allow multi-label / confidence scores |

---

## Phase 3: Model Development (Q2 2026)

**Timeline**: April 2026 - June 2026
**Owner**: ML Engineering
**Status**: 📋 Planning

### Objectives

1. Establish baseline models (rule-based, heuristic)
2. Train initial classifiers (logistic regression, BERT-based)
3. Experiment tracking with MLflow
4. Model evaluation on hold-out test set
5. Select best model for deployment

### Planned Experiments

#### Baseline Models

1. **Heuristic Classifier**: Lexicon-based (already have dialect_heuristic_filter)
2. **TF-IDF + Logistic Regression**: Fast, interpretable baseline
3. **FastText**: Word embeddings + classification

#### Neural Models

1. **mBERT**: Multilingual BERT fine-tuning
2. **XLM-RoBERTa**: Better multilingual support
3. **AfriBERTa**: Africa-focused language model
4. **DistilBERT**: Faster inference for production

### Evaluation Metrics

- **Primary**: F1-score (weighted)
- **Secondary**: Precision, Recall, Confusion Matrix
- **Interpretability**: SHAP values, attention visualization

### Deliverables

- [ ] Baseline model results report
- [ ] MLflow experiment tracking setup
- [ ] Model comparison report (3+ architectures)
- [ ] Best model checkpoint
- [ ] Model card (performance, limitations, ethics)

---

## Phase 4: Deployment & Serving (Q3 2026)

**Timeline**: July 2026 - September 2026
**Owner**: MLOps
**Status**: 📋 Planning

### Objectives

1. Package model for serving (ONNX/TorchScript)
2. Build REST API (FastAPI)
3. Deploy to staging environment
4. Load testing and performance optimization
5. Production deployment with monitoring

### Infrastructure

- **Serving**: FastAPI + Uvicorn
- **Containerization**: Docker
- **Orchestration**: Kubernetes / AWS ECS
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack
- **Model Registry**: MLflow

### Deliverables

- [ ] Model serving API
- [ ] Docker image
- [ ] Kubernetes manifests
- [ ] Monitoring dashboards
- [ ] Production deployment runbook
- [ ] SLA definition (latency, uptime)

---

## Phase 5: Iteration & Improvement (Q4 2026+)

**Timeline**: Ongoing
**Owner**: Full Team
**Status**: 📋 Planning

### Objectives

1. Monitor model performance in production
2. Collect production feedback for retraining
3. Expand labeled dataset
4. Retrain with additional data
5. A/B test model improvements

### Key Activities

- **Model Retraining**: Quarterly or as needed
- **Data Drift Monitoring**: Detect distribution shifts
- **Bias Audits**: Ensure fair dialect representation
- **Feature Requests**: User-driven improvements
- **Performance Optimization**: Latency, throughput

---

## Cross-Cutting Concerns

### Data Quality

**Owner**: Data Engineering
**Ongoing Activities**:
- Monitor filter pass rates
- Investigate high rejection rates
- Update lexicons for topic enrichment
- Deduplicate silver dataset

### Ethics & Bias

**Owner**: Research + ML Engineering
**Considerations**:
- Ensure balanced dialect representation in training data
- Avoid reinforcing stereotypes
- Document known biases and limitations
- Engage Somali language community for feedback

### Security & Privacy

**Owner**: MLOps
**Requirements**:
- No PII in training data
- Secure API authentication
- Rate limiting
- Data encryption at rest and in transit

---

## Success Criteria by Phase

| Phase | Success Metric | Target |
|-------|----------------|--------|
| Phase 1 (Data) | Records in silver dataset | 500K+ ✅ |
| Phase 2 (Labels) | Labeled samples | 5K+ |
| Phase 2 (Labels) | Inter-annotator agreement (Kappa) | >0.7 |
| Phase 3 (Model) | F1-score on test set | >0.80 |
| Phase 3 (Model) | Inference latency (p95) | <100ms |
| Phase 4 (Deploy) | API uptime | >99.5% |
| Phase 4 (Deploy) | API latency (p95) | <200ms |
| Phase 5 (Prod) | Model drift detection | <5% monthly |

---

## Dependencies & Blockers

### Current Blockers (Phase 2)

1. **Annotation Schema**: Needs Research team input on dialect taxonomy
2. **Budget**: Annotation costs (tooling, annotators)
3. **Annotator Recruitment**: Need native Somali speakers

### Upcoming Blockers (Phase 3-4)

1. **Compute Resources**: GPU for model training
2. **Deployment Infrastructure**: Cloud environment setup
3. **Production Access**: Permissions for deployment

---

## Resource Allocation

| Phase | Engineering | Research | MLOps | Budget |
|-------|-------------|----------|-------|--------|
| Phase 1 (Data) | 3 months FTE | - | - | $0 |
| Phase 2 (Labels) | 1 month FTE | 2 months FTE | - | $5K-10K |
| Phase 3 (Model) | 2 months FTE | 1 month FTE | - | $2K (compute) |
| Phase 4 (Deploy) | 1 month FTE | - | 2 months FTE | $5K (infra) |
| Phase 5 (Ops) | 0.5 months/quarter | - | 1 month/quarter | $3K/quarter |

---

## Communication Plan

### Weekly Updates

- **Audience**: Team
- **Format**: Slack summary
- **Content**: Progress, blockers, asks

### Monthly Reviews

- **Audience**: Stakeholders
- **Format**: Presentation + demo
- **Content**: Milestones, metrics, roadmap adjustments

### Quarterly Business Reviews

- **Audience**: Leadership
- **Format**: Written report + presentation
- **Content**: ROI, impact, strategic alignment

---

## See Also

- [Future Work](future-work.md) - Backlog and enhancement ideas
- [Architecture](../overview/architecture.md) - Technical design
- [Data Pipeline](../overview/data-pipeline-architecture.md) - Current data flow
- [Deployment Guide](../operations/deployment.md) - Production setup (when available)

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
