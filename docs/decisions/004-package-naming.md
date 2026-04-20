# ADR-004: Package Naming — Rename `somali_dialect_classifier` to `somnlp`

**Template for Architecture Decision Records documenting important technical and design decisions.**

**Last Updated:** 2026-04-20

**Status**: Proposed  
**Date**: 2026-04-20  
**Deciders**: ilyasibrahim  
**Supersedes**: N/A

---

---

## Table of Contents

- [Context](#context)
  - [Background](#background)
  - [Problem Statement](#problem-statement)
- [Decision](#decision)
  - [Implementation Details](#implementation-details)
- [Rationale](#rationale)
  - [Key Benefits](#key-benefits)
  - [Trade-offs Accepted](#trade-offs-accepted)
- [Alternatives Considered](#alternatives-considered)
  - [Alternative 1: sdc](#alternative-1-sdc)
  - [Alternative 2: sodic](#alternative-2-sodic)
  - [Alternative 3: afsoom](#alternative-3-afsoom)
  - [Alternative 4: Keep as-is](#alternative-4-keep-as-is)
- [Consequences](#consequences)
  - [Positive Consequences](#positive-consequences)
  - [Negative Consequences](#negative-consequences)
  - [Neutral Consequences](#neutral-consequences)
- [Implementation Plan](#implementation-plan)
  - [Phase 1: Preparation](#phase-1-preparation)
  - [Phase 2: Rename](#phase-2-rename)
  - [Phase 3: Verification](#phase-3-verification)
  - [Success Criteria](#success-criteria)
- [References](#references)
- [Revision History](#revision-history)
- [Notes](#notes)

---

## Context

**What is the issue that we're addressing?**

The current Python import path `somali_dialect_classifier` is too long for everyday use and encodes a scope that the project is already outgrowing. As the project expands toward corpus curation, preprocessing, and model training for Somali NLP broadly, locking the import name to "dialect classifier" creates a naming mismatch that will require a rename under worse conditions later.

### Background

The project currently has:
- ~90 Python source files in `src/somali_dialect_classifier/`
- ~70 test files importing from `somali_dialect_classifier.*`
- 10 CLI entry points in `pyproject.toml`
- Numerous documentation files and README examples using the current import path

The `pyproject.toml` `[project].name` is `somali-dialect-classifier`, which is already a good PyPI identifier and can remain unchanged. The rename proposed here affects only the **Python import path** (the `src/` directory name and all `import` statements).

### Problem Statement

`somali_dialect_classifier` is 26 characters, too long for routine imports, and scoped too narrowly (dialect classification) for a project that covers corpus curation, quality filtering, orchestration, dashboard observability, and future model training across all Somali NLP tasks.

---

## Decision

**We will rename the Python package import path from `somali_dialect_classifier` to `somnlp`.**

The PyPI distribution name (`somali-dialect-classifier` in `pyproject.toml [project].name`) is not changed — it remains distinct and descriptive for discovery. Only the importable package name changes.

### Implementation Details

1. Rename `src/somali_dialect_classifier/` → `src/somnlp/`
2. Update all `import somali_dialect_classifier.*` and `from somali_dialect_classifier.*` statements — approximately 90 source files
3. Update all test imports — approximately 70 test files
4. Update all 10 CLI entry points in `pyproject.toml` (e.g., `somali_dialect_classifier.tools.cli:main` → `somnlp.tools.cli:main`)
5. Update `pyproject.toml` `[tool.mypy]` and `[tool.ruff]` source paths
6. Update all documentation, docstring examples, and README code blocks referencing the old import path
7. Update CI workflow steps that reference the package path directly

---

## Rationale

**Why did we decide this way?**

### Key Benefits

1. **Brevity and ergonomics**: `from somnlp.ingestion import BasePipeline` is readable and typeable. `from somali_dialect_classifier.ingestion import BasePipeline` is 26 characters for the module path alone.
2. **Scope-neutral**: `somnlp` ("Somali NLP") does not encode the current phase's focus (dialect classification). As the project adds preprocessing, training, and serving layers, the import path remains accurate.
3. **PyPI-safe**: `somnlp` is short enough to be unlikely to conflict with existing packages. (Verify with `pip index versions somnlp` before executing the rename.)
4. **Pronounceable**: Can be verbalized as "som-NLP" in verbal communication and documentation.
5. **Consistent with ecosystem conventions**: Short, project-specific abbreviations are standard in the Python NLP ecosystem (`spacy`, `nltk`, `stanza`, `flair`).

### Trade-offs Accepted

- **Import churn**: Every file that imports from the old path requires updating — approximately 160 files (90 source + 70 test). A grep-based automated refactor mitigates manual effort.
- **Temporary documentation drift**: Any external references, blog posts, or citations using the old import path will break. Since the project has not been formally published externally, this risk is low at this stage.
- **PyPI name divergence**: The installable name (`somali-dialect-classifier`) and the importable name (`somnlp`) will differ. This is a common and accepted pattern (`scikit-learn` / `sklearn`, `pillow` / `PIL`).

---

## Alternatives Considered

**What other options did we evaluate?**

### Alternative 1: sdc

**Description**: Abbreviate to the project's initials: `sdc`.

**Pros**:
- Very short (3 characters)
- Obvious abbreviation of the current name

**Cons**:
- `sdc` is a generic abbreviation with multiple meanings in the Python ecosystem
- Does not convey the Somali language domain to new contributors
- Carries the same "dialect classifier" scope limitation as the current name

**Why Rejected**: Poor discoverability and high collision risk.

---

### Alternative 2: sodic

**Description**: Somali Dialect Classifier → `sodic`.

**Pros**:
- Somewhat pronounceable
- Retains the "dialect" framing

**Cons**:
- Still encodes "dialect" in the name, locking scope
- Not an established abbreviation; a new contributor would not guess it
- 5 characters — not significantly shorter than `somnlp`

**Why Rejected**: Scope-limiting and unintuitive.

---

### Alternative 3: afsoom

**Description**: From "Af-Soomaali" (the Somali language in Somali) → `afsoom`.

**Pros**:
- Culturally meaningful
- Unique and unlikely to conflict on PyPI

**Cons**:
- Not immediately recognizable to non-Somali speakers
- Harder to search for without context
- 6 characters with no NLP signal

**Why Rejected**: Meaningful but opaque to the broader NLP community.

---

### Alternative 4: Keep as-is

**Description**: Retain `somali_dialect_classifier` as the import path.

**Pros**:
- Zero migration cost
- No risk of breaking external references

**Cons**:
- 26-character import path is ergonomically painful in day-to-day development
- Name will require a rename under worse conditions if the project scope expands and the name becomes misleading (e.g., when Phase 3/4 add non-dialect functionality)
- Best time to rename is before the project has significant external citations or users

**Why Rejected**: Technical debt that grows with each phase. The cost of renaming now (before external publication) is far lower than the cost of renaming after Phase 4 release.

---

## Consequences

**What are the implications of this decision?**

### Positive Consequences

- Import paths in documentation, tutorials, and daily development are shorter and clearer
- The package identity is no longer phase-constrained
- Establishes a stable, final import path before the first external publication

### Negative Consequences

- ~160 files require import statement updates — mitigated by automated grep refactor
- Any early-adopter code or documentation using `somali_dialect_classifier` will break — acceptable risk given pre-publication status

### Neutral Consequences

- `pyproject.toml [project].name` remains `somali-dialect-classifier` (PyPI name, distinct from import path)
- All CLI commands (`wikisom-download`, `somali-tools`, etc.) are unchanged — they are defined in `[project.scripts]` entry points and reference the internal package path, which will be updated
- `CLAUDE.md`, `.github/` templates, and CI workflows reference CLI commands, not import paths — minimal update needed

---

## Implementation Plan

**How will this decision be executed?**

### Phase 1: Preparation

- Verify `somnlp` is not taken on PyPI: `pip index versions somnlp`
- Create a feature branch: `refactor/rename-somnlp`
- Tag current `main` as `pre-rename` for rollback reference

### Phase 2: Rename

1. `mv src/somali_dialect_classifier src/somnlp`
2. Grep-based refactor: `find . -type f -name "*.py" | xargs sed -i 's/somali_dialect_classifier/somnlp/g'`
3. Update `pyproject.toml`:
   - `[tool.mypy] packages = ["somnlp"]`
   - All `[project.scripts]` entry points (`somnlp.tools.cli:main`, etc.)
   - `[tool.ruff.lint] src = ["src"]` — unchanged
4. Update documentation: `find docs/ -name "*.md" | xargs grep -l "somali_dialect_classifier" | xargs sed -i 's/somali_dialect_classifier/somnlp/g'`
5. Update `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`
6. Update `src/dashboard/README.md` and any JS files referencing the package path

### Phase 3: Verification

1. `pip install -e ".[dev]"` — confirm `somnlp` is importable
2. `python -c "import somnlp; print(somnlp.__version__)"` — smoke test
3. `pytest` — full test suite must pass
4. `ruff check src/` and `mypy src/` — no new errors
5. `grep -r "somali_dialect_classifier" src/ tests/` — must return 0 results

### Success Criteria

- All tests pass under `somnlp` import path
- `grep -r "somali_dialect_classifier" src/ tests/` returns no results
- All CLI entry points work: `wikisom-download --help`, `somali-tools --help`
- No ruff or mypy regressions
- `pip install -e .` succeeds and `import somnlp` works in a clean virtual environment

---

## References

- [scikit-learn vs sklearn naming convention](https://scikit-learn.org/stable/faq.html#why-is-there-a-scikit-learn-and-sklearn-package-on-pypi)
- [PEP 8 — Package and Module Names](https://peps.python.org/pep-0008/#package-and-module-names)

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2026-04-20 | Initial draft | ilyasibrahim |

---

## Notes

- This rename must happen before any Phase 4 external publication or HuggingFace Hub model/dataset card, since those will reference the import path in code examples.
- The `dedup.py` F-003 bug fix (Phase 2 prerequisite) should land on the same branch or immediately prior to this rename to keep diff scopes clean.
- After rename, update the `CLAUDE.md` `[Key Files]` table to reflect the new path.

---

**Date**: 2026-04-20  
**Status**: Proposed

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index
- [ADR-001: OSCAR Exclusion](./001-oscar-exclusion.md)
- [Project Charter](../../PROJECT_CHARTER.md)

**Maintainers**: Somali NLP Contributors
