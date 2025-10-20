# Somali Dialect Classifier Documentation

**Last Updated**: 2025-01-19

Welcome to the Somali Dialect Classifier documentation. This project provides a comprehensive pipeline for collecting, processing, and preparing Somali language data for dialect classification and NLP research.

---

## Quick Start

```bash
# Install
pip install -e ".[config]"

# Run individual pipelines
wikisom-download
bbcsom-download --max-articles 100
hfsom-download mc4 --max-records 10000

# Or orchestrate all pipelines together
somali-orchestrate --pipeline all
```

**→ See [Data Pipeline Guide](guides/data-pipeline.md) for complete documentation**

---

## Documentation Structure

### 📘 Essential Guides

Start here for practical usage:

- **[Data Pipeline Guide](guides/data-pipeline.md)** - **⭐ Complete guide to data collection and processing**
- **[Dashboard Guide](guides/dashboard.md)** - **⭐ Interactive metrics dashboard deployment and usage**
- **[Portfolio Guide](guides/portfolio.md)** - **⭐ Showcasing this project in your portfolio, resume, and interviews**
- **[Documentation Guide](guides/documentation-guide.md)** - Standards for writing and maintaining documentation

### 📖 Overview - Understanding the System

High-level architecture and system design:

- **[Architecture](overview/architecture.md)** - System design, patterns, and technical decisions
- **[Data Flow](overview/data-pipeline-architecture.md)** - ETL architecture and processing stages

### 🛠️ How-To Guides - Practical Walkthroughs

Task-oriented guides for common workflows:

- **[Processing Pipelines](howto/processing-pipelines.md)** - Quick-start guide comparing all four data sources
- **[Wikipedia Integration](howto/wikipedia-integration.md)** - Complete guide to Wikipedia dumps, XML parsing, namespace filtering
- **[BBC Integration](howto/bbc-integration.md)** - Ethical web scraping, topic enrichment, rate limiting
- **[HuggingFace Integration](howto/huggingface-integration.md)** - Streaming datasets, manifests, JSONL batching (MC4)
- **[Språkbanken Integration](howto/sprakbanken-integration.md)** - All 23 corpora, domain mapping, metadata extraction
- **[Custom Filters](howto/custom-filters.md)** - Writing and registering quality filters
- **[Configuration](howto/configuration.md)** - Environment setup and config management
- **[Troubleshooting](howto/troubleshooting.md)** - Common issues and solutions

### 📚 Reference - API Documentation

Technical specifications and API reference:

- **[API Reference](reference/api.md)** - Complete API documentation with examples
- **[Silver Schema](reference/silver-schema.md)** - Silver dataset schema specification
- **[Filters Reference](reference/filters.md)** - Built-in filter documentation
- **[Text Cleaning](reference/text-cleaning.md)** - Cleaning pipeline reference (coming soon)

### ⚙️ Operations - Deployment & MLOps

Production deployment and operations:

- **[Deployment](operations/deployment.md)** - Production deployment guide
- **[Testing](operations/testing.md)** - Testing strategies and patterns
- **[MLOps Playbook](../operations/mlops-playbook.md)** - MLflow, monitoring (coming soon)

### 🗺️ Project - Roadmap & Plans

Project lifecycle and future plans:

- **[Lifecycle & Roadmap](roadmap/lifecycle.md)** - Project phases, milestones, and current status
- **[Future Work](roadmap/future-work.md)** - Backlog and enhancement ideas

### 🧠 Decisions - Architecture Decision Records

Design rationale and trade-offs:

- **[ADR-001: OSCAR Exclusion](decisions/001-oscar-exclusion.md)** - Why we excluded OSCAR initially
- **[ADR-002: Filter Framework](decisions/002-filter-framework.md)** - Silver floor hooks and quality filters
- **[ADR-003: MADLAD-400 Exclusion](decisions/003-madlad-400-exclusion.md)** - Why we excluded MADLAD-400

**Templates**: [ADR Template](templates/adr-template.md) | [How-To Template](templates/howto-template.md)

### 📚 Guides

Project-wide guidelines and standards:

- **[Documentation Guide](guides/documentation-guide.md)** - Standards for writing and maintaining documentation

---

## Quick Navigation by Role

### 🆕 New Users

If you're new to the project, start here:

1. [Root README](../README.md) - Project overview and installation
2. [Architecture](overview/architecture.md) - System design
3. [Processing Pipelines](howto/processing-pipelines.md) - Run your first pipeline

### 👨‍💻 Developers

Building new features or extending the system:

1. [Architecture](overview/architecture.md) - Design principles (SOLID, design patterns)
2. [API Reference](reference/api.md) - Complete API with examples
3. [Testing](operations/testing.md) - Write tests following project standards
4. [Custom Filters](howto/custom-filters.md) - Add custom data quality filters

**Common Tasks**:
- **Add new data source**: Extend `BasePipeline` (see [Architecture](overview/architecture.md))
- **Add new filter**: Implement filter function (see [Custom Filters](howto/custom-filters.md))
- **Run tests**: `pytest` (see [Testing](operations/testing.md))

### 📊 Data Engineers

Working with the data pipeline:

1. [Data Pipeline](overview/data-pipeline-architecture.md) - Medallion architecture (Raw → Silver → Gold)
2. [Processing Pipelines](howto/processing-pipelines.md) - Source-specific walkthroughs
3. [Filter Framework](decisions/002-filter-framework.md) - Data quality validation
4. [Configuration](howto/configuration.md) - Configure data paths and parameters

**Common Tasks**:
- **Process new data**: Run `wikisom-download` or `bbcsom-download`
- **View silver dataset**: Read Parquet files with PyArrow/Pandas
- **Add quality filters**: See [Custom Filters Guide](howto/custom-filters.md)
- **Schedule pipelines**: See [Deployment Guide](operations/deployment.md#orchestration)

### 🔧 DevOps/SRE

Deploying and operating in production:

1. [Deployment](operations/deployment.md) - Docker, Kubernetes, cloud deployment
2. [Configuration](howto/configuration.md) - Environment variables and secrets
3. [Testing](operations/testing.md) - Integration testing and CI/CD
4. [Lifecycle](roadmap/lifecycle.md) - Project phases and infrastructure needs

**Common Tasks**:
- **Deploy to production**: Follow [Deployment Guide](operations/deployment.md)
- **Configure environment**: Set `SDC_*` environment variables
- **Set up monitoring**: Prometheus metrics, health checks
- **Disaster recovery**: Backup and restore procedures

### 🤖 ML Engineers

Preparing data for dialect classification models:

1. [Data Pipeline](overview/data-pipeline-architecture.md) - Understand data quality and schema
2. [Filter Framework](decisions/002-filter-framework.md) - Add dialect-specific filters
3. [Lifecycle](roadmap/lifecycle.md) - Current phase and upcoming model work
4. [Future Work](roadmap/future-work.md) - Model experimentation plans

**Common Tasks**:
- **Access silver data**: Read Parquet from `data/processed/silver/`
- **Add dialect heuristics**: Use `dialect_heuristic_filter`
- **Enrich metadata**: Filters can add metadata without dropping records
- **Prepare training data**: Convert Parquet to HuggingFace datasets

---

## Project Status

### Current Phase: Data Curation (Phase 1) ✅ COMPLETE

- ✅ Data pipelines for **all four sources** with production MLOps integration
- ✅ Structured logging with JSON output and context injection
- ✅ Metrics collection and automated quality reports
- ✅ Crawl ledger for URL state tracking and resume capability
- ✅ Two-tier deduplication (exact + near-duplicate)
- ✅ Configuration-driven ethical scraping policies
- ✅ Quality filter framework with pluggable filters
- ✅ Unified silver dataset schema across all sources
- ✅ 165+ tests with CI integration
- ✅ Comprehensive documentation with dedicated integration guides

### Next Phase: Labeling & Annotation (Phase 2) 📋 Planning

- Annotation guidelines
- Labeling interface
- Initial labeled dataset (5K+ samples)
- Active learning workflow

See [Lifecycle & Roadmap](roadmap/lifecycle.md) for detailed milestones.

---

## Key Concepts

### Silver Dataset

All processors write to a unified silver dataset with this schema:

```python
{
    "id": "uuid-v4",
    "text": "cleaned text",
    "title": "article title",
    "source": "Wikipedia-Somali | BBC-Somali | HuggingFace-Somali_* | Sprakbanken-Somali-*",
    "source_type": "wiki | news | web | corpus",
    "language": "so",
    "license": "CC-BY-SA-3.0 | BBC Terms of Use | ODC-BY-1.0 | CC BY 4.0",
    "tokens": 1234,
    "source_metadata": {
        "detected_lang": "so",
        "lang_confidence": 0.85,
        "dialect_markers": {"sports": 2},
        "domain": "news_regional"  # Språkbanken-specific
    }
}
```

### Quality Filters

All pipelines use pluggable filters for data quality:

1. **min_length_filter** - Removes short texts (<50 chars)
2. **langid_filter** - Detects and filters non-Somali content
3. **dialect_heuristic_filter** - Enriches with topic/dialect markers
4. **namespace_filter** - Wikipedia-specific page filtering

See [Custom Filters Guide](howto/custom-filters.md) for details.

### Three-Phase Pipeline

All processors follow the same pattern:

1. **Download** - Fetch raw data (Wikipedia dumps, BBC articles, HF datasets)
2. **Extract** - Parse and stage data (XML, JSON, JSONL)
3. **Process** - Clean, filter, and write to silver dataset (Parquet)

See [Processing Pipelines Guide](howto/processing-pipelines.md) for walkthroughs.

---

## Contributing to Documentation

### Documentation Standards

Complete documentation guidelines are available in the [Documentation Guide](guides/documentation-guide.md).

**Key Principles**:
- **Clarity over cleverness**: Write for humans, not to impress
- **Practical over perfect**: Focus on what developers actually need
- **Consistent structure**: Similar docs follow similar patterns
- **Lowercase kebab-case**: `data-pipeline.md` (not `DATA_PIPELINE.md`)

### Templates Available

- **[ADR Template](templates/adr-template.md)** - For architecture decision records
- **[How-To Template](templates/howto-template.md)** - For task-oriented guides

### Adding New Documentation

1. Choose appropriate directory (`overview/`, `howto/`, `reference/`, etc.)
2. Use the appropriate template from `docs/templates/`
3. Follow the [Documentation Guide](guides/documentation-guide.md)
4. Add cross-references from related documents
5. Update this index with the new document

### Documentation Review

See [Documentation Guide](guides/documentation-guide.md) for comprehensive writing guidelines, style guide, and review process.

---

## Getting Help

### Documentation Issues

- **Open an issue**: Use GitHub issue tracker with `documentation` label
- **Submit a PR**: Contribute fixes and improvements directly
- **Ask questions**: Use GitHub Discussions

### Support Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, design discussions

---

## Related Resources

### External Documentation

- **Root README**: [../README.md](../README.md) - High-level project overview
- **CHANGELOG**: [../CHANGELOG.md](../CHANGELOG.md) - Release notes and version history
- **Contributing**: [../CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- **Code of Conduct**: [../CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) - Community standards

### Data Sources

- [Wikimedia Dumps](https://dumps.wikimedia.org/) - Wikipedia Somali dumps
- [BBC Somali](https://www.bbc.com/somali) - News articles
- [HuggingFace Datasets](https://huggingface.co/datasets) - MC4, OSCAR, MADLAD-400

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-10-16 | Documentation restructure - hierarchical organization |
| 1.0.0 | 2025-01-15 | Initial documentation release |

---

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
