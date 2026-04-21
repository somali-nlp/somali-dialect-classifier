# ADR-004: Package Naming — Rename `somali_dialect_classifier` to `somdialc`

**Last Updated:** 2026-04-21

**Status**: Accepted  
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

The current Python import path `somali_dialect_classifier` is too long for everyday use (26 characters) and creates friction in daily development. A shorter, accurate abbreviation is needed before the first external publication or HuggingFace Hub release.

### Background

The project currently has:
- ~90 Python source files in `src/somali_dialect_classifier/`
- ~70 test files importing from `somali_dialect_classifier.*`
- 10 CLI entry points in `pyproject.toml`
- Numerous documentation files and README examples using the current import path

The `pyproject.toml` `[project].name` is `somali-dialect-classifier`, which is already a good PyPI identifier and can remain unchanged. The rename proposed here affects only the **Python import path** (the `src/` directory name and all `import` statements).

### Problem Statement

`somali_dialect_classifier` is 26 characters — too long for routine imports. The project's core mission through Phase 3 is specifically Somali dialect classification (data curation, quality filtering, model training, evaluation). The name should be short and accurately reflect that scope without overstating it.

---

## Decision

**We will rename the Python package import path from `somali_dialect_classifier` to `somdialc`.**

`somdialc` = **Som**ali + **Dial**ect + **C**lassifier. It is 8 characters, accurately scoped to the project's mission, and does not overstate ambitions beyond dialect classification.

The PyPI distribution name (`somali-dialect-classifier` in `pyproject.toml [project].name`) is not changed — it remains distinct and descriptive for discovery. Only the importable package name changes.

### Implementation Details

1. Rename `src/somali_dialect_classifier/` → `src/somdialc/`
2. Update all `import somali_dialect_classifier.*` and `from somali_dialect_classifier.*` statements — approximately 90 source files
3. Update all test imports — approximately 70 test files
4. Update all 10 CLI entry points in `pyproject.toml` (e.g., `somali_dialect_classifier.tools.cli:main` → `somdialc.tools.cli:main`)
5. Update `pyproject.toml` `[tool.mypy]` and `[tool.ruff]` source paths
6. Update all documentation, docstring examples, and README code blocks referencing the old import path
7. Update CI workflow steps that reference the package path directly

---

## Rationale

**Why did we decide this way?**

### Key Benefits

1. **Brevity and ergonomics**: `from somdialc.ingestion import BasePipeline` is readable and typeable. `from somali_dialect_classifier.ingestion import BasePipeline` is 26 characters for the module path alone.
2. **Accurately scoped**: `somdialc` encodes the project's actual mission — Somali dialect classification — without overstating it as a general-purpose Somali NLP toolkit. The name will remain accurate through Phase 3.
3. **PyPI-safe**: `somdialc` is unlikely to conflict with existing packages. (Verify with `pip index versions somdialc` before executing the rename.)
4. **Pronounceable**: Can be verbalized as "som-dial-see" in verbal communication and documentation.
5. **Consistent with ecosystem conventions**: Short, project-specific abbreviations are standard in the Python NLP ecosystem (`spacy`, `nltk`, `stanza`, `flair`).

### Trade-offs Accepted

- **Import churn**: Every file that imports from the old path requires updating — approximately 160 files (90 source + 70 test). A grep-based automated refactor mitigates manual effort.
- **Temporary documentation drift**: Any external references, blog posts, or citations using the old import path will break. Since the project has not been formally published externally, this risk is low at this stage.
- **PyPI name divergence**: The installable name (`somali-dialect-classifier`) and the importable name (`somdialc`) will differ. This is a common and accepted pattern (`scikit-learn` / `sklearn`, `pillow` / `PIL`).

---

## Alternatives Considered

**What other options did we evaluate?**

### Alternative 1: somnlp

**Description**: Somali NLP → `somnlp`.

**Pros**:
- Very short (6 characters)
- Scope-neutral name that doesn't lock the project to dialect classification

**Cons**:
- Too broad: the project is not a general-purpose Somali NLP toolkit. It is specifically a dialect classifier covering data curation, quality filtering, and model training for that task. Claiming "Somali NLP" overstates the project's mission and creates identity confusion if the broader NLP ecosystem produces other Somali language tools.
- A contributor seeing `import somnlp` has no signal that the tool is about dialect classification.

**Why Rejected**: Scope too broad relative to the project's actual and planned deliverables through Phase 3.

---

### Alternative 2: sdc

**Description**: Abbreviate to the project's initials: `sdc`.

**Pros**:
- Very short (3 characters)

**Cons**:
- Generic abbreviation with multiple meanings in the Python ecosystem
- No Somali language signal for new contributors
- High collision risk on PyPI

**Why Rejected**: Poor discoverability and high collision risk.

---

### Alternative 3: sodic

**Description**: Somali Dialect Classifier → `sodic`.

**Pros**:
- Somewhat pronounceable
- Retains the "dialect" framing

**Cons**:
- Not an established abbreviation; a new contributor would not guess it
- 5 characters without the "classifier" signal that distinguishes it from a lexicon or corpus tool

**Why Rejected**: Unintuitive and incomplete mapping to the project name.

---

### Alternative 4: afsoom

**Description**: From "Af-Soomaali" (the Somali language in Somali) → `afsoom`.

**Pros**:
- Culturally meaningful
- Unique and unlikely to conflict on PyPI

**Cons**:
- Not immediately recognizable to non-Somali speakers
- No NLP or classification signal
- 6 characters with no domain hint

**Why Rejected**: Meaningful but opaque to the broader NLP community.

---

### Alternative 5: Keep as-is

**Description**: Retain `somali_dialect_classifier` as the import path.

**Pros**:
- Zero migration cost
- No risk of breaking external references

**Cons**:
- 26-character import path is ergonomically painful in day-to-day development
- Best time to rename is before the project has significant external citations or users

**Why Rejected**: Technical debt that grows with each phase. The cost of renaming now (before external publication) is far lower than after Phase 4 release.

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

- Verify `somdialc` is not taken on PyPI: `pip index versions somdialc`
- Create a feature branch: `refactor/rename-somdialc`
- Tag current `main` as `pre-rename` for rollback reference

### Phase 2: Rename

1. `mv src/somali_dialect_classifier src/somdialc`
2. Grep-based refactor: `find . -type f -name "*.py" | xargs sed -i 's/somali_dialect_classifier/somdialc/g'`
3. Update `pyproject.toml`:
   - `[tool.mypy] packages = ["somdialc"]`
   - All `[project.scripts]` entry points (`somdialc.tools.cli:main`, etc.)
   - `[tool.ruff.lint] src = ["src"]` — unchanged
4. Update documentation: `find docs/ -name "*.md" | xargs grep -l "somali_dialect_classifier" | xargs sed -i 's/somali_dialect_classifier/somdialc/g'`
5. Update `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`
6. Update `src/dashboard/README.md` and any JS files referencing the package path

### Phase 3: Verification

1. `pip install -e ".[dev]"` — confirm `somdialc` is importable
2. `python -c "import somdialc; print(somdialc.__version__)"` — smoke test
3. `pytest` — full test suite must pass
4. `ruff check src/` and `mypy src/` — no new errors
5. `grep -r "somali_dialect_classifier" src/ tests/` — must return 0 results

### Success Criteria

- All tests pass under `somdialc` import path
- `grep -r "somali_dialect_classifier" src/ tests/` returns no results
- All CLI entry points work: `wikisom-download --help`, `somali-tools --help`
- No ruff or mypy regressions
- `pip install -e .` succeeds and `import somdialc` works in a clean virtual environment

---

## References

- [scikit-learn vs sklearn naming convention](https://scikit-learn.org/stable/faq.html#why-is-there-a-scikit-learn-and-sklearn-package-on-pypi)
- [PEP 8 — Package and Module Names](https://peps.python.org/pep-0008/#package-and-module-names)

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2026-04-20 | Initial draft (proposed `somnlp`) | ilyasibrahim |
| 2026-04-21 | Revised decision to `somdialc`; `somnlp` moved to rejected alternatives (scope too broad); status → Accepted | ilyasibrahim |

---

## Notes

- This rename must happen before any Phase 4 external publication or HuggingFace Hub model/dataset card, since those will reference the import path in code examples.
- F-003 (dedup refactor) was committed prior to this rename — branch is clean.
- After rename, update the `CLAUDE.md` `[Key Files]` table to reflect the new `somdialc` path.
- The `somnlp` name was evaluated and rejected on 2026-04-21 as too broad for a project with a specific dialect-classification mission.

---

**Date**: 2026-04-21  
**Status**: Accepted

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index
- [ADR-001: OSCAR Exclusion](./001-oscar-exclusion.md)
- [Project Charter](../../PROJECT_CHARTER.md)

**Maintainers**: Somali NLP Contributors
