# Internal Documentation Archive

This directory contains internal development documentation that has been archived to maintain a clean project structure.

## Purpose

These documents were created during development for internal tracking, planning, and team coordination. They provide valuable historical context but are not part of the user-facing documentation.

## Archived Documents

### DASHBOARD_CHANGELOG_20251027.md
**Original Location**: `/DASHBOARD_CHANGELOG.md` (project root)
**Reason for Archiving**: Very detailed internal changelog with implementation phases, planned features, v3.2.0 roadmap, and test infrastructure details.

**Contents**:
- Detailed version history (v3.1.0, v3.0.0, v2.1.0, v2.0.0, v1.0.0)
- Implementation phases and milestones
- Test infrastructure documentation (239 tests)
- Migration guides for developers
- Breaking changes and upgrade checklists
- Internal roadmap planning (Q4 2025 - Q2 2026)
- Deprecation notices and rollback procedures

### REFACTORING_SUMMARY_20251027.md
**Original Location**: `/docs/REFACTORING_SUMMARY.md`
**Reason for Archiving**: Internal refactoring deliverables, implementation details, and development next steps.

**Contents**:
- Metrics pipeline backend refactoring summary
- Pydantic schema models implementation
- Refactored metrics consolidation details
- Filter breakdown instrumentation
- Unit test coverage (23 tests)
- CI/CD validation script details
- Known limitations and next steps
- Code review checklist

### dashboard-features-status_20251027.md
**Original Location**: `/docs/guides/dashboard-features-status.md`
**Reason for Archiving**: Implementation status tracking with phases, test coverage percentages, and planned vs implemented features.

**Contents**:
- Detailed feature implementation status
- Test coverage summary (239 tests, 17% implemented)
- Planned features roadmap (v3.2.0, v3.3.0, v3.4.0)
- Test execution instructions
- Feature request process
- Documentation update checklists

## Why Archive?

These documents were archived because they:
1. Contain extensive internal implementation details not relevant to end users
2. Track development phases and planning that are now complete
3. Include granular test coverage percentages and internal metrics
4. Mix user-facing information with developer-only planning details
5. Are better suited as historical reference than active documentation

## User-Facing Documentation

For current, user-focused documentation, please refer to:
- **README.md** - Project overview and quick start
- **docs/** - Main documentation directory
- **docs/guides/** - User guides and tutorials
- **docs/api/** - API reference documentation

## Internal Documentation Best Practices

When creating new internal documentation:
1. Clearly mark documents as "Internal" in the title or header
2. Store in `.archive/documentation/` if purely for development reference
3. Use timestamped filenames when archiving (YYYYMMDD format)
4. Update this README when adding new archived documents
5. Keep user-facing documentation separate and concise

## Retrieval

These documents remain accessible for:
- Historical reference
- Understanding design decisions
- Reviewing past implementation approaches
- Auditing development process
- Training new team members

## Last Updated

2025-10-27
