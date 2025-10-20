# Documentation Best Practices (MLOps)

This document outlines the documentation structure and best practices for the Somali Dialect Classifier project.

## Directory Structure

```
somali-dialect-classifier/
├── README.md                    # User-facing: Installation, usage, features
├── CHANGELOG.md                 # Production: Release notes, version history
├── CONTRIBUTING.md              # Developer-facing: How to contribute
├── CODE_OF_CONDUCT.md           # Community standards
├── LICENSE                      # Legal terms
├── .gitignore                   # Excludes temporary artifacts
│
├── docs/                        # Technical documentation
│   ├── FILTER_FRAMEWORK_DESIGN.md  # Design doc for filter system
│   └── ...                      # Future: Architecture, API reference
│
└── .archive/                    # Temporary development artifacts (gitignored)
    ├── FIXES_SUMMARY.md         # Implementation scratch work
    ├── FINAL_SUMMARY.md         # Session summaries
    └── ...                      # Other temporary docs
```

## What Goes Where?

### 1. Root Level (Committed to Git)

**README.md** - Primary documentation for users and developers
- Installation instructions
- Usage examples with CLI commands
- Project structure overview
- Configuration options
- Development setup
- Contributing guidelines reference

**CHANGELOG.md** - Version history and release notes
- Follows [Keep a Changelog](https://keepachangelog.com/) format
- Semantic versioning (MAJOR.MINOR.PATCH)
- Categorized changes: Added, Changed, Fixed, Deprecated, Removed, Security
- Used for: Release notes, tracking breaking changes, understanding project evolution

**CONTRIBUTING.md** - Developer onboarding
- How to set up development environment
- Code style and quality standards
- Testing requirements
- PR submission process

**CODE_OF_CONDUCT.md** - Community standards
- Expected behavior for contributors
- Reporting mechanisms for violations

### 2. docs/ Directory (Committed to Git)

**Purpose**: Technical documentation, design decisions, architecture

**Examples**:
- `docs/FILTER_FRAMEWORK_DESIGN.md` - Filter system architecture
- `docs/ARCHITECTURE.md` - High-level system design
- `docs/API.md` - API reference (if building library)
- `docs/DEPLOYMENT.md` - Production deployment guide

**Guidelines**:
- Keep docs evergreen (update as code evolves)
- Version-control alongside code
- Link from README for discoverability

### 3. .archive/ Directory (NOT Committed - Gitignored)

**Purpose**: Temporary development artifacts, scratch work, session summaries

**Examples**:
- Implementation summaries (FIXES_SUMMARY.md, FINAL_SUMMARY.md)
- Code review responses (PRINCIPAL_MLE_FEEDBACK_RESPONSE.md)
- Session notes, debugging logs
- Experimental design docs that never shipped

**Guidelines**:
- Add `.archive/` to `.gitignore`
- Use pattern matching: `*_SUMMARY.md`, `*_FEEDBACK*.md`, `*_STATUS.md`
- Keep locally for context, but don't commit
- Archive contains historical record of how decisions were made

## MLOps Best Practices

### 1. Separation of Concerns

| Type | Location | Committed? | Audience | Lifecycle |
|------|----------|------------|----------|-----------|
| **User Documentation** | README.md | ✅ Yes | End users, new developers | Long-term (updated with releases) |
| **Release History** | CHANGELOG.md | ✅ Yes | DevOps, stakeholders | Long-term (append-only) |
| **Technical Design** | docs/ | ✅ Yes | Senior engineers, architects | Medium-term (evolves with system) |
| **Implementation Notes** | .archive/ | ❌ No | Original implementer | Short-term (session context) |

### 2. CHANGELOG.md vs. Implementation Summaries

**CHANGELOG.md** (Production):
```markdown
## [1.2.0] - 2025-01-15

### Added
- Filter framework for quality control (5 stateless filters)
- Force reprocessing flag for pipelines

### Fixed
- BBC cache invalidation on parameter changes
```

**Implementation Summary** (Archive):
```markdown
# FIXES_SUMMARY.md

## HIGH Priority Issue #1: Reprocessing Blocked
**Problem**: When running `wikisom-download` twice, the second run...
**Root Cause**: The `process()` method in `base_pipeline.py:142`...
**Solution**: Added `force` parameter to `BasePipeline.__init__()`...
**Testing**: Created `test_force_reprocessing.py` with 8 tests...
**Files Modified**:
- src/somali_dialect_classifier/preprocessing/base_pipeline.py:78-82
- tests/test_force_reprocessing.py:1-242
```

**Key Differences**:
- CHANGELOG: **What** changed (user-facing)
- Implementation Summary: **How** and **why** (developer-facing, internal)

### 3. Automated Changelog Generation

For mature projects, use commit conventions to auto-generate CHANGELOG:

```bash
# Conventional Commits (https://www.conventionalcommits.org/)
git commit -m "feat(filters): add langid_filter with Somali vocabulary"
git commit -m "fix(bbc): invalidate cache on max_articles change"
git commit -m "docs(readme): add filter framework section"

# Generate CHANGELOG with tools like:
# - git-cliff (https://git-cliff.org/)
# - standard-version (https://github.com/conventional-changelog/standard-version)
# - semantic-release (https://semantic-release.gitbook.io/)
```

### 4. Documentation as Code

- **Version control**: Docs live in same repo as code
- **Review process**: Docs reviewed in PRs alongside code
- **CI/CD**: Validate links, spell-check, build static sites
- **Single source of truth**: Avoid duplicate docs in Confluence, Notion, etc.

### 5. README Length Management

When README exceeds 400-500 lines, split into:
- **README.md**: Quick start, installation, basic usage
- **docs/USER_GUIDE.md**: Comprehensive usage examples
- **docs/DEVELOPER_GUIDE.md**: Architecture, testing, contributing
- **docs/API.md**: API reference (auto-generated from docstrings)

### 6. When to Archive vs. Delete

**Archive** (.archive/):
- Implementation summaries with technical details
- Code review responses with context
- Design explorations that informed decisions
- Useful for: Onboarding new team members, understanding "why" decisions were made

**Delete** (never commit):
- Truly temporary scratch work
- Duplicate information (already in CHANGELOG)
- Outdated docs that conflict with current state

## Tools and Automation

### Changelog Generation
```bash
# Install git-cliff
cargo install git-cliff

# Generate changelog from git history
git cliff --output CHANGELOG.md
```

### Documentation Linting
```bash
# Markdown linting
npm install -g markdownlint-cli
markdownlint '**/*.md' --ignore node_modules

# Link checking
npm install -g markdown-link-check
markdown-link-check README.md
```

### Documentation Site Generation
```bash
# MkDocs (Python)
pip install mkdocs mkdocs-material
mkdocs serve

# Sphinx (Python API docs)
pip install sphinx
sphinx-build -b html docs/ docs/_build

# Docusaurus (React-based)
npx create-docusaurus@latest docs classic
```

## Summary

**Commit to Git**:
- ✅ README.md - User-facing documentation
- ✅ CHANGELOG.md - Release history
- ✅ docs/ - Technical design docs

**Keep Local Only**:
- ❌ .archive/ - Implementation summaries
- ❌ Session notes, scratch work

**Golden Rule**: If it helps **future you or your team** understand **what the system does**, commit it. If it only helps **current you** remember **what you did yesterday**, archive it.
