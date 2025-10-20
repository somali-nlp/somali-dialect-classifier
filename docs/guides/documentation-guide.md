# Documentation Guide

**Purpose**: Establish documentation standards and guidelines for the Somali Dialect Classifier project
**Audience**: Contributors, maintainers, and documentation writers
**Last Updated**: 2025-10-18

---

## Table of Contents

1. [Documentation Philosophy](#documentation-philosophy)
2. [Documentation Structure](#documentation-structure)
3. [Writing Guidelines](#writing-guidelines)
4. [Documentation Types](#documentation-types)
5. [Templates](#templates)
6. [Style Guide](#style-guide)
7. [Review Process](#review-process)
8. [Maintenance](#maintenance)

---

## Documentation Philosophy

### Core Principles

1. **Clarity Over Cleverness**: Write for humans, not to impress. Use simple, direct language.
2. **Practical Over Perfect**: Focus on what developers actually need, not theoretical completeness.
3. **Consistent Structure**: Similar documents should follow similar patterns for easy navigation.
4. **Discoverability**: Make it easy to find information through clear organization and cross-linking.
5. **Maintainability**: Create systems that scale as the project grows.
6. **Completeness**: Cover the full picture, including edge cases and error scenarios.

### Target Audiences

Documentation should serve these personas:

- **New Users**: Installing and running their first pipeline
- **Developers**: Building new features or extending the system
- **Data Engineers**: Working with the data pipeline and quality filters
- **DevOps/SRE**: Deploying and operating in production
- **ML Engineers**: Preparing data for dialect classification models

---

## Documentation Structure

### Directory Organization

```
somali-dialect-classifier/
├── README.md                      # Primary entry point
├── CHANGELOG.md                   # Version history
├── CONTRIBUTING.md                # Contribution guidelines
├── DOCUMENTATION_GUIDE.md         # This file
├── CODE_OF_CONDUCT.md            # Community standards
├── LICENSE                        # Legal terms
│
├── docs/                          # Technical documentation
│   ├── index.md                  # Documentation hub
│   │
│   ├── overview/                  # High-level architecture
│   │   ├── architecture.md       # System design
│   │   └── data-pipeline.md     # Pipeline flow
│   │
│   ├── howto/                     # Task-oriented guides
│   │   ├── processing-pipelines.md
│   │   ├── configuration.md
│   │   ├── custom-filters.md
│   │   └── huggingface-integration.md
│   │
│   ├── reference/                 # API and technical specs
│   │   └── api.md
│   │
│   ├── operations/                # Deployment and ops
│   │   ├── deployment.md
│   │   └── testing.md
│   │
│   ├── decisions/                 # Architecture Decision Records
│   │   ├── 001-oscar-exclusion.md
│   │   ├── 002-filter-framework.md
│   │   ├── 003-madlad-400-exclusion.md
│   │   └── template.md
│   │
│   ├── roadmap/                   # Project lifecycle
│   │   ├── lifecycle.md
│   │   └── future-work.md
│   │
│   └── templates/                 # Documentation templates
│       ├── adr-template.md
│       ├── howto-template.md
│       └── feature-template.md
│
└── .archive/                      # Temporary dev docs (NOT committed)
    ├── IMPLEMENTATION_SUMMARY.md
    ├── MADLAD400_STATUS.md
    └── HUGGINGFACE_SETUP_GUIDE.md
```

### What Goes Where?

| Document Type | Location | Committed? | Purpose |
|--------------|----------|------------|---------|
| **Quick Start** | README.md | ✅ Yes | Installation, basic usage, project overview |
| **Release Notes** | CHANGELOG.md | ✅ Yes | Version history, breaking changes |
| **Architecture** | docs/overview/ | ✅ Yes | System design, patterns, decisions |
| **How-To Guides** | docs/howto/ | ✅ Yes | Task-oriented walkthroughs |
| **API Reference** | docs/reference/ | ✅ Yes | Complete API documentation |
| **Operations** | docs/operations/ | ✅ Yes | Deployment, testing, monitoring |
| **Decisions** | docs/decisions/ | ✅ Yes | ADRs with rationale |
| **Roadmap** | docs/roadmap/ | ✅ Yes | Project phases, future work |
| **Dev Notes** | .archive/ | ❌ No | Temporary implementation summaries |

---

## Writing Guidelines

### Structure Every Document

Every documentation file should include:

1. **Title** (H1): Clear, descriptive title
2. **Metadata**: Last updated date, status if applicable
3. **Table of Contents**: For documents >200 lines
4. **Introduction**: What this document covers and who it's for
5. **Body**: Well-organized content with clear headings
6. **Examples**: Working code samples
7. **See Also**: Links to related documentation
8. **Frontmatter** (optional): For automated doc generators

### Use Headings Hierarchically

```markdown
# Title (H1) - One per document

## Major Section (H2)

### Subsection (H3)

#### Detail (H4) - Rarely needed
```

### Write Clear Code Examples

```python
# ❌ Bad Example - No context
processor.run()

# ✅ Good Example - Complete and runnable
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

processor = WikipediaSomaliProcessor(force=False)
processor.run()  # Downloads, extracts, and processes Wikipedia data
print(f"Silver dataset created at: {processor._get_silver_path()}")
```

### Include Expected Outputs

```bash
# Command
wikisom-download

# Expected output
2025-10-18 10:30:00 - INFO - Phase 1/3: Downloading Wikipedia dump...
2025-10-18 10:32:15 - INFO - Phase 2/3: Extracting articles...
2025-10-18 10:35:40 - INFO - Phase 3/3: Processing and filtering...
2025-10-18 10:37:20 - INFO - ✓ Complete: 15,432 articles processed
```

### Cross-Reference Related Docs

```markdown
See also:
- [Architecture Overview](../overview/architecture.md) - System design
- [Custom Filters Guide](custom-filters.md) - Writing filters
- [API Reference](../reference/api.md) - Complete API docs
```

---

## Documentation Types

### 1. README Files

**Purpose**: Primary entry point for users and contributors

**Content**:
- Project description and goals
- Installation instructions
- Quick start examples
- Directory structure overview
- Link to comprehensive docs
- Contributing guidelines reference

**Length**: 300-500 lines max

**Example**: [Root README.md](README.md)

### 2. How-To Guides

**Purpose**: Task-oriented walkthroughs

**Structure**:
```markdown
# Task Name

## Prerequisites
- What you need before starting

## Steps
1. First step with code example
2. Second step with code example
3. Verification step

## Expected Outcome
What you should see

## Troubleshooting
Common issues and solutions

## See Also
Related guides
```

**Examples**:
- [Processing Pipelines](docs/howto/processing-pipelines.md)
- [Custom Filters](docs/howto/custom-filters.md)
- [HuggingFace Integration](docs/howto/huggingface-integration.md)

### 3. Architecture Documentation

**Purpose**: Explain system design and technical decisions

**Content**:
- High-level architecture diagrams
- Component responsibilities
- Design patterns used
- Technology stack
- Extension points
- Performance considerations

**Example**: [Architecture Overview](docs/overview/architecture.md)

### 4. Architecture Decision Records (ADRs)

**Purpose**: Document significant technical decisions

**Structure**: Use [ADR template](docs/decisions/template.md)

**Examples**:
- [ADR-001: OSCAR Exclusion](docs/decisions/001-oscar-exclusion.md)
- [ADR-002: Filter Framework](docs/decisions/002-filter-framework.md)
- [ADR-003: MADLAD-400 Exclusion](docs/decisions/003-madlad-400-exclusion.md)

### 5. API Reference

**Purpose**: Complete technical specification

**Content**:
- All public classes, functions, and methods
- Parameter descriptions with types
- Return values
- Exceptions
- Usage examples
- Notes on edge cases

**Format**: Auto-generated from docstrings when possible

### 6. CHANGELOG

**Purpose**: Track version history and changes

**Format**: Follow [Keep a Changelog](https://keepachangelog.com/)

**Categories**:
- Added: New features
- Changed: Changes to existing functionality
- Deprecated: Soon-to-be removed features
- Removed: Removed features
- Fixed: Bug fixes
- Security: Security vulnerability fixes

**Example**: [CHANGELOG.md](CHANGELOG.md)

---

## Templates

### ADR Template

Location: [docs/decisions/template.md](docs/decisions/template.md)

```markdown
# ADR-XXX: Decision Title

**Status**: Accepted | Proposed | Deprecated
**Date**: YYYY-MM-DD
**Deciders**: Team members involved

## Context
What is the issue we're addressing?

## Decision
What did we decide?

## Rationale
Why did we decide this?

## Consequences
What are the implications (positive and negative)?

## Alternatives Considered
What other options did we evaluate?
```

### How-To Template

```markdown
# How to [Task]

**Difficulty**: Beginner | Intermediate | Advanced
**Time Required**: X minutes
**Prerequisites**: List requirements

## Overview
Brief description of what this guide accomplishes.

## Steps

### Step 1: [Action]
Detailed explanation with code example.

### Step 2: [Action]
Detailed explanation with code example.

### Step 3: [Verification]
How to confirm success.

## Complete Example
Full working code.

## Troubleshooting
Common issues and solutions.

## Next Steps
What to do next.

## See Also
- Related guide 1
- Related guide 2
```

---

## Style Guide

### Language and Tone

- Use **present tense**: "The processor creates..." not "The processor will create..."
- Use **active voice**: "The filter rejects records" not "Records are rejected by the filter"
- Use **second person** for instructions: "You can configure..." not "One can configure..."
- Be **concise**: Eliminate unnecessary words
- Be **specific**: "Install version 3.9+" not "Install Python"

### Formatting Conventions

#### Code

- Use **backticks** for inline code: `config.data.raw_dir`
- Use **fenced code blocks** with language specification:
  ````markdown
  ```python
  from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor
  ```
  ````

#### File Paths

- Use **inline code** for paths: `/Users/name/project/data`
- Use **forward slashes** even on Windows: `data/raw/file.txt`

#### Commands

```bash
# Always show the command prompt or context
wikisom-download --force
```

#### Lists

- Use **numbered lists** for sequential steps
- Use **bullet lists** for unordered items
- Indent nested lists with 2-4 spaces

#### Tables

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
```

#### Emphasis

- Use **bold** for important concepts: **mandatory requirement**
- Use *italics* for gentle emphasis: *optional parameter*
- Use `code` for technical terms: `BasePipeline`

### File Naming

- Use **kebab-case**: `processing-pipelines.md` not `Processing_Pipelines.md`
- Be **descriptive**: `huggingface-integration.md` not `hf.md`
- Use **.md extension** for Markdown files
- Number ADRs sequentially: `001-decision-name.md`

### Markdown Best Practices

#### Links

```markdown
# ✅ Relative links
See [Architecture](../overview/architecture.md)

# ❌ Absolute paths (break on different systems)
See [Architecture](/Users/name/project/docs/overview/architecture.md)
```

#### Images

```markdown
# Include alt text
![Architecture Diagram](../images/architecture.png)

# Reference from images/ directory
![Data Flow](../images/data-flow.png)
```

#### Admonitions (if supported)

```markdown
> **Note**: This is important information.

> **Warning**: This could cause data loss.

> **Tip**: This is a helpful suggestion.
```

---

## Review Process

### Documentation Pull Requests

All documentation changes should:

1. **Follow this guide**: Adhere to structure and style guidelines
2. **Include examples**: Provide working code samples
3. **Cross-reference**: Link to related documentation
4. **Update index**: Add to docs/index.md if new document
5. **Check links**: Verify all links work
6. **Test code**: Ensure all code examples run
7. **Update CHANGELOG**: Note documentation improvements

### Review Checklist

- [ ] Title and headers are clear and hierarchical
- [ ] Introduction explains purpose and audience
- [ ] Code examples are complete and runnable
- [ ] Expected outputs are shown
- [ ] Common issues are addressed in troubleshooting
- [ ] Cross-references to related docs exist
- [ ] File naming follows conventions
- [ ] Markdown is valid and renders correctly
- [ ] Language is clear, concise, and consistent
- [ ] Spelling and grammar are correct

---

## Maintenance

### Keeping Documentation Current

#### When Code Changes

- Update affected documentation in **the same PR**
- Update CHANGELOG.md with documentation changes
- Check for broken links or outdated examples

#### Regular Reviews

- **Quarterly**: Review all docs for accuracy
- **Before releases**: Ensure docs reflect current version
- **After major changes**: Update architecture and API docs

#### Documentation Debt

Track documentation issues as:

```markdown
# In docs/overview/architecture.md

<!-- TODO: Add section on distributed processing when implemented -->
<!-- TODO: Update performance benchmarks after optimization -->
```

Or use GitHub issues with `documentation` label.

### Version-Specific Documentation

For breaking changes, document both old and new approaches:

```markdown
## Configuration (v2.0+)

New unified configuration system:
\```python
from somali_dialect_classifier.config import get_config
config = get_config()
\```

## Configuration (v1.x - Deprecated)

Old configuration approach (deprecated in v2.0):
\```python
# This still works but will be removed in v3.0
from somali_dialect_classifier import Config
config = Config()
\```
```

---

## Tools and Automation

### Recommended Tools

#### Documentation Linting

```bash
# Markdown linting
npm install -g markdownlint-cli
markdownlint 'docs/**/*.md'

# Link checking
npm install -g markdown-link-check
find docs -name '*.md' -exec markdown-link-check {} \;
```

#### Documentation Generators

```bash
# MkDocs (Python)
pip install mkdocs mkdocs-material
mkdocs serve

# Sphinx (Python API docs)
pip install sphinx sphinx_rtd_theme
sphinx-build -b html docs/ docs/_build
```

#### Spell Checking

```bash
# Use aspell
aspell check docs/overview/architecture.md

# Or use VS Code spell checker extension
code --install-extension streetsidesoftware.code-spell-checker
```

### CI/CD Integration

Add to `.github/workflows/docs.yml`:

```yaml
name: Documentation

on:
  pull_request:
    paths: ['docs/**', '*.md']

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Lint Markdown
        run: |
          npm install -g markdownlint-cli
          markdownlint 'docs/**/*.md' 'README.md'
      - name: Check Links
        run: |
          npm install -g markdown-link-check
          find . -name '*.md' -exec markdown-link-check {} \;
```

---

## Examples and Anti-Patterns

### Good Example

```markdown
# Processing Wikipedia Data

This guide shows you how to download and process Wikipedia Somali articles.

**Time Required**: 30-45 minutes
**Prerequisites**: Installed package with `pip install -e .`

## Quick Start

\```python
from somali_dialect_classifier.preprocessing import WikipediaSomaliProcessor

processor = WikipediaSomaliProcessor()
processor.run()
\```

## Expected Output

\```
2025-10-18 10:30:00 - INFO - Downloading Wikipedia dump...
...
2025-10-18 10:45:00 - INFO - ✓ Processed 15,432 articles
\```

## See Also
- [BBC Somali Processing](bbc-processing.md)
- [Configuration Guide](configuration.md)
```

### Anti-Patterns to Avoid

#### ❌ No Context

```markdown
# Process
Run this:
\```
processor.run()
\```
```

#### ❌ Vague Language

```markdown
The system might fail if you don't configure things properly.
```

#### ✅ Better

```markdown
The processor raises `FileNotFoundError` if the raw directory doesn't exist. Ensure you've run `download()` before `extract()`.
```

#### ❌ Broken or Absolute Links

```markdown
See [Architecture](/Users/ilyas/docs/architecture.md)
```

#### ✅ Better

```markdown
See [Architecture](../overview/architecture.md)
```

---

## Getting Help

### Documentation Questions

- **Open an issue**: Use GitHub issue tracker with `documentation` label
- **Submit a PR**: Fix documentation directly and submit for review
- **Ask in discussions**: Use GitHub Discussions for clarifications

### Contributing Documentation

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to set up development environment
- PR submission process
- Code of conduct

---

## Summary

### Quick Reference

| Task | Action |
|------|--------|
| **Add new guide** | Use [how-to template](#how-to-template), place in `docs/howto/` |
| **Document decision** | Use [ADR template](#adr-template), place in `docs/decisions/` |
| **Update API** | Modify docstrings, regenerate reference |
| **Fix broken link** | Use relative paths, test with link checker |
| **Report doc issue** | Open GitHub issue with `documentation` label |

### Golden Rules

1. **Update docs with code changes** - Documentation in same PR as code
2. **Write for your audience** - Know who will read this
3. **Show, don't tell** - Include working examples
4. **Link generously** - Cross-reference related docs
5. **Keep it current** - Review and update regularly
6. **Be consistent** - Follow established patterns
7. **Test your examples** - Ensure code actually works

---

**Last Updated**: 2025-10-20
**Maintainers**: Somali NLP Contributors
