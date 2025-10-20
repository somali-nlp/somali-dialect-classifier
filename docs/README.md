# Documentation

Welcome to the Somali Dialect Classifier documentation. This guide will help you navigate the comprehensive technical documentation for the project.

## Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| [Architecture](ARCHITECTURE.md) | System design, patterns, and technical decisions | Developers, Architects |
| [Data Pipeline](DATA_PIPELINE.md) | ETL architecture and data flow | Data Engineers, ML Engineers |
| [API Reference](API_REFERENCE.md) | Complete API documentation | Developers |
| [Configuration](CONFIGURATION.md) | Environment setup and configuration management | DevOps, Developers |
| [Deployment](DEPLOYMENT.md) | Production deployment guide | DevOps, SRE |
| [Testing](TESTING.md) | Testing strategies and examples | Developers, QA Engineers |
| [Filter Framework](FILTER_FRAMEWORK_DESIGN.md) | Quality control filter design | Data Scientists, ML Engineers |

---

## Documentation Overview

### For New Users

If you're new to the project, start here:

1. **[README.md](../README.md)** (Project root) - Project overview, quick start, and installation
2. **[Architecture](ARCHITECTURE.md)** - Understand the system design and components
3. **[Data Pipeline](DATA_PIPELINE.md)** - Learn how data flows through the system
4. **[API Reference](API_REFERENCE.md)** - Explore the APIs and write your first code

**Quick Start**:
```bash
# Install
pip install somali-dialect-classifier[config]

# Run Wikipedia pipeline
wikisom-download

# Run BBC scraper
bbcsom-download --max-articles 100
```

### For Developers

Building new features or extending the system:

1. **[Architecture](ARCHITECTURE.md)** - Design principles (SOLID, design patterns)
2. **[API Reference](API_REFERENCE.md)** - Complete API documentation with examples
3. **[Testing](TESTING.md)** - Write tests following project standards
4. **[Configuration](CONFIGURATION.md)** - Configure development environment
5. **[Filter Framework](FILTER_FRAMEWORK_DESIGN.md)** - Add custom data quality filters

**Common Tasks**:
- **Add new data source**: Extend `BasePipeline` (see [Architecture](ARCHITECTURE.md#basepipeline-contract))
- **Add new filter**: Implement filter function (see [API Reference](API_REFERENCE.md#filters))
- **Run tests**: `pytest` (see [Testing](TESTING.md))

### For Data Engineers

Working with the data pipeline:

1. **[Data Pipeline](DATA_PIPELINE.md)** - Medallion architecture (Bronze → Silver → Gold)
2. **[Filter Framework](FILTER_FRAMEWORK_DESIGN.md)** - Data quality validation
3. **[Configuration](CONFIGURATION.md)** - Configure data paths and scraping parameters
4. **[Deployment](DEPLOYMENT.md)** - Schedule and orchestrate pipelines

**Common Tasks**:
- **Process new data**: Run `wikisom-download` or `bbcsom-download`
- **View silver dataset**: Read Parquet files with PyArrow/Pandas
- **Add quality filters**: Register filters in processor's `_register_filters()` method
- **Schedule pipelines**: Use cron, systemd timers, or Prefect/Airflow

### For DevOps/SRE

Deploying and operating in production:

1. **[Deployment](DEPLOYMENT.md)** - Production deployment guide (Docker, Kubernetes, cloud)
2. **[Configuration](CONFIGURATION.md)** - Environment variables and secrets management
3. **[Testing](TESTING.md)** - Integration testing and CI/CD
4. **[Monitoring](DEPLOYMENT.md#monitoring-and-alerting)** - Observability and alerting

**Common Tasks**:
- **Deploy to production**: Follow [Deployment Guide](DEPLOYMENT.md)
- **Configure environment**: Set `SDC_*` environment variables (see [Configuration](CONFIGURATION.md))
- **Set up monitoring**: Prometheus metrics, health checks (see [Deployment](DEPLOYMENT.md#monitoring-and-alerting))
- **Disaster recovery**: Backup and restore procedures (see [Deployment](DEPLOYMENT.md#backup-and-disaster-recovery))

### For ML Engineers

Preparing data for dialect classification models:

1. **[Data Pipeline](DATA_PIPELINE.md)** - Understand data quality and schema
2. **[Filter Framework](FILTER_FRAMEWORK_DESIGN.md)** - Add dialect-specific filters
3. **[API Reference](API_REFERENCE.md)** - Programmatic access to silver datasets
4. **[Architecture](ARCHITECTURE.md)** - Extensibility for ML pipelines

**Common Tasks**:
- **Access silver data**: Use `SilverDatasetWriter.read()` (see [API Reference](API_REFERENCE.md#silverdatasetwriter))
- **Add dialect heuristics**: Use `dialect_heuristic_filter` (see [Filter Framework](FILTER_FRAMEWORK_DESIGN.md))
- **Enrich metadata**: Filters can add metadata without dropping records
- **Prepare training data**: Convert Parquet to HuggingFace datasets

---

## Document Details

### [Architecture](ARCHITECTURE.md)

**System design, patterns, and technical decisions**

**Topics covered**:
- High-level system overview (medallion architecture)
- Design principles (SOLID, DRY, separation of concerns)
- Component architecture (BasePipeline, cleaners, filters, writers)
- Data flow through layers (Bronze → Silver → Gold)
- Design patterns (Template Method, Strategy, Pipeline)
- Technology stack justification
- Directory structure conventions

**Key sections**:
- BasePipeline contract and extension points
- Text cleaning pipeline architecture
- Filter framework design
- Silver dataset schema enforcement

**Best for**: Understanding how the system works and why design decisions were made.

---

### [Data Pipeline](DATA_PIPELINE.md)

**ETL architecture and comprehensive data flow documentation**

**Topics covered**:
- Medallion architecture layers (Bronze, Silver, Gold)
- Processing stages (download, extract, process)
- Source-specific pipelines (Wikipedia, BBC)
- Data quality filters and validation
- Performance optimization strategies
- Monitoring and observability

**Key sections**:
- Bronze layer (raw, immutable data)
- Staging layer (intermediate extracts)
- Silver layer (cleaned, schema-enforced Parquet)
- Deduplication strategies
- Partitioning schemes

**Best for**: Understanding data flow, quality control, and pipeline stages.

---

### [API Reference](API_REFERENCE.md)

**Complete API documentation with examples**

**Topics covered**:
- BasePipeline class (methods, parameters, abstract methods)
- Processors (WikipediaSomaliProcessor, BBCSomaliProcessor)
- Text cleaners (WikiMarkupCleaner, HTMLCleaner, WhitespaceCleaner)
- Filters (min_length, langid, dialect_heuristic, namespace, custom)
- Record utilities (generate_text_hash, generate_record_id, build_silver_record)
- SilverDatasetWriter (write, read, schema)

**Key sections**:
- Function signatures with type annotations
- Parameter descriptions
- Return value documentation
- Code examples for each API
- Error handling patterns

**Best for**: Writing code that uses the preprocessing pipeline programmatically.

---

### [Configuration](CONFIGURATION.md)

**Environment setup and configuration management**

**Topics covered**:
- Configuration hierarchy (defaults → .env → env vars)
- Environment variable reference (all `SDC_*` variables)
- Configuration sections (DataConfig, ScrapingConfig, LoggingConfig)
- Programmatic configuration access
- Environment-specific configs (dev, staging, prod)
- Security best practices (secrets management, principle of least privilege)

**Key sections**:
- Complete environment variable reference table
- .env file examples for different environments
- Docker and cloud deployment configurations
- Troubleshooting configuration issues

**Best for**: Setting up development environments and configuring production deployments.

---

### [Deployment](DEPLOYMENT.md)

**Production deployment and operations guide**

**Topics covered**:
- Prerequisites (system requirements, dependencies)
- Installation steps (pip, Docker, source)
- Environment configuration (systemd, Docker, cloud)
- Scheduling (cron, systemd timers, Prefect, Airflow)
- Docker containerization with compose
- Cloud deployment (AWS, GCP, Azure)
- Monitoring and alerting (logs, metrics, health checks)
- Backup and disaster recovery
- Scaling strategies (horizontal, vertical)
- Security hardening (network, files, secrets, audit)

**Key sections**:
- Systemd service and timer configurations
- Docker and docker-compose examples
- AWS ECS/Fargate, GCP Cloud Run, Azure Container Instances
- Prometheus metrics and health endpoints
- Backup automation and recovery procedures

**Best for**: Deploying and operating the system in production environments.

---

### [Testing](TESTING.md)

**Testing strategies, patterns, and examples**

**Topics covered**:
- Testing philosophy and pyramid
- Unit testing (pytest patterns)
- Integration testing (end-to-end flows)
- Contract testing (BasePipeline compliance)
- Fixtures and mocks
- Test coverage standards
- CI/CD integration
- Performance testing

**Key sections**:
- Unit test examples for cleaners, filters, utilities
- Integration test patterns for full pipelines
- Contract tests for BasePipeline subclasses
- Mocking external dependencies (HTTP, file I/O)

**Best for**: Writing reliable tests and ensuring code quality.

---

### [Filter Framework](FILTER_FRAMEWORK_DESIGN.md)

**Data quality filter design and implementation**

**Topics covered**:
- Filter function signature and contract
- Built-in filters (length, language, dialect, namespace)
- Filter composition and chaining
- Metadata enrichment patterns
- Custom filter development
- Performance considerations
- Filter registration in pipelines

**Key sections**:
- Filter contract specification
- Filter examples with test cases
- Best practices for filter design
- Performance optimization strategies

**Best for**: Understanding and extending the data quality validation system.

---

## Contributing to Documentation

### Documentation Standards

- **Markdown format**: All documentation in Markdown (.md)
- **Clear structure**: Use headings, tables, and lists for organization
- **Code examples**: Provide working code snippets with explanations
- **Cross-references**: Link between related documentation sections
- **Keep updated**: Update docs when changing code

### Adding New Documentation

1. **Create new .md file** in `docs/` directory
2. **Follow existing structure**: Use same heading levels and formatting
3. **Add to this README**: Update quick navigation table and document details
4. **Cross-reference**: Link from related documents

### Documentation Checklist

When creating or updating documentation:

- [ ] Clear purpose statement at top
- [ ] Table of contents for documents >500 lines
- [ ] Code examples with comments
- [ ] Links to related documentation
- [ ] Tested code snippets (verify they work)
- [ ] Proper headings hierarchy (H1 → H2 → H3)
- [ ] Consistent terminology across docs
- [ ] Updated "Last updated" date (if applicable)

### Writing Style Guide

**Do**:
- Use active voice ("Run the command" not "The command should be run")
- Provide context before diving into details
- Include examples for abstract concepts
- Explain "why" not just "what"
- Use consistent terminology

**Don't**:
- Assume prior knowledge without links to prerequisites
- Use jargon without explanation
- Leave code examples untested
- Duplicate content (link to single source of truth)

### Documentation Review Process

1. **Self-review**: Check formatting, links, code examples
2. **Peer review**: Have another developer review for clarity
3. **Test examples**: Run all code snippets to verify correctness
4. **Update cross-references**: Ensure related docs are updated

---

## Documentation Roadmap

### Current Status

✅ **Complete**:
- Architecture overview
- Data pipeline documentation
- API reference
- Configuration guide
- Deployment guide
- Testing guide
- Filter framework design

### Planned Additions

🚧 **In Progress**:
- Performance tuning guide
- Troubleshooting playbook
- FAQ document

📋 **Backlog**:
- Model training guide (dialect classifier)
- Data labeling workflow
- Advanced filtering techniques
- Multi-language support guide
- Contributor guidelines (expanded)

---

## Getting Help

### Documentation Issues

If you find errors or have suggestions for improving documentation:

1. **Open an issue**: Use GitHub issue tracker with `documentation` label
2. **Submit a PR**: Contribute fixes and improvements directly
3. **Ask questions**: Use GitHub Discussions for clarification

### Support Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, design discussions
- **Email**: [your-email@example.com] for security issues

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-15 | Initial documentation release |
| - | - | Architecture, Data Pipeline, API Reference, Configuration, Deployment, Testing, Filter Framework |

---

## License

This documentation is licensed under [MIT License](../LICENSE), same as the project code.

---

**Last Updated**: 2025-10-15

**Maintained By**: Somali NLP Team

**Questions?** Open an issue on [GitHub](https://github.com/your-org/somali-dialect-classifier/issues)
