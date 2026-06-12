# ADR 005 — SQLite vs PostgreSQL for Ingestion Ledger

**Date:** 2025-11-14
**Status:** Accepted (retrospective — original analysis conducted 2025-11-14; relocated into canonical ADR sequence 2026-06-12)
**Deciders:** Architecture analysis, project principal

---

## Context

The ingestion pipeline requires a crawl ledger for URL state tracking, daily quota enforcement (critical for cost control on paid APIs), and campaign lifecycle management. Two candidate backends existed: SQLite (already deployed) and PostgreSQL (partially implemented).

**PostgreSQL implementation state at decision time:** missing all four quota methods (`get_daily_quota_usage`, `increment_daily_quota`, `mark_quota_hit`, `check_quota_available`) and the `daily_quotas` table schema. These are required for TikTok cost control ($1/1k comments).

**Concurrency model:** File-based exclusive locks (`LockManager`) serialize source processing to one writer at a time. PostgreSQL's multi-writer capabilities provide no benefit under this model.

**Scale projection:** Steady-state ~2,600 ledger rows/day, database reaching ~700 MB in one year and ~3.5 GB over five years — well within SQLite's embedded deployment threshold of ~140 GB.

---

## Decision

Stay with SQLite for the ingestion ledger through at least 2028.

---

## Rationale

1. **Functionality:** SQLite implementation is production-complete including quota enforcement. PostgreSQL backend is missing quota methods required for financial risk control.
2. **Concurrency:** File locks already serialize writes; additional database-level concurrency is unnecessary.
3. **Performance:** SQLite on SSD handles 1,000–10,000 UPSERTs/sec against a peak requirement of 2–5/sec.
4. **Operational simplicity:** No additional services, authentication, or connection pooling required.

---

## Consequences

- SQLite ledger at `data/ledger/crawl_ledger.db`.
- PostgreSQL backend (`database/postgres_backend.py`) retained in code but marked incomplete; quota methods must be implemented before it can be used.
- **Monitoring trigger for re-evaluation:** database file exceeds 5 GB, concurrent writers are needed, or a distributed deployment is planned.

---

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|-----------------|
| Migrate to PostgreSQL now | Incomplete quota implementation (financial risk); zero concurrency/performance benefit at current scale |
| DuckDB | OLAP-optimised; worse fit for transactional ledger workload than SQLite |
| Redis for quota + SQLite for URL state | Added operational complexity; SQLite quota UPSERTs already fast enough |
| File-based JSON | No indexing, no atomicity, no UPSERT |

---

*Original full analysis (with benchmarks, SQL traces, and growth projections) preserved at
`.claude/reports/archive/arch/adr-sqlite-vs-postgresql-ledger-20251114.md`.*
