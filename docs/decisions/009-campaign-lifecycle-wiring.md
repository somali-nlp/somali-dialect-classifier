# ADR-009: Campaign Lifecycle Wiring via Run-Registration Hook

**Date:** 2026-06-12  
**Status:** Accepted  
**Deciders:** Coordinator (campaign-readiness-audit-20260611.md recommendations)

---

## Context

The `campaigns` table has been empty since the project started despite documentation claiming that `campaign_init_001` auto-creates on the first pipeline run (CAMP-2 in the campaign-readiness audit).

Root cause: `start_campaign` was only reachable through `is_initial_collection_phase()` in `orchestration/flows.py`, which is only called from `run_all_pipelines()` (the `somali-orchestrate` CLI). All five production data runs used per-source CLI commands (`wikisom-download`, `bbcsom-download`, etc.) which bypass `run_all_pipelines()` entirely. The orchestrator was never invoked in production.

Additionally, `complete_campaign()` was never called anywhere — the documented "auto-completes after 6 days" was unimplemented (CAMP-8).

Three options were considered for fixing this:

1. **Lifecycle hook at run registration** — add campaign logic to `_ensure_pipeline_run_registered()` in `BasePipeline`, which fires at every real execution path.
2. **Orchestrator-only routing** — document and enforce `somali-orchestrate` as the only supported production invocation, fixing the per-source CLI paths.
3. **CLI namespace break** — add a `--campaign` / `--purpose` flag to every per-source CLI command.

---

## Decision

**Option 1: Lifecycle hook at run registration** was chosen.

`BasePipeline._ensure_pipeline_run_registered()` was already designated as the single hook for campaign/provenance logic (code comment, Round 1 code-quality batch). The method fires at the entry of `run()` and `process()` for every execution path — orchestrator, per-source CLI, and notebook/script. No user-facing interface changes are needed.

The `is_initial_collection_phase()` function in `flows.py` was the only place `start_campaign()` was called. It has been refactored to a read-only status check (no `start_campaign()` call) to eliminate two competing campaign initializers. The lifecycle hook is now the single authoritative place where campaigns are started and completed.

---

## Schema

Two columns were added to `pipeline_runs`:

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `run_purpose` | TEXT NOT NULL | `'production'` | Values: `production`, `validation`, `test` |
| `campaign_id` | TEXT NULL | `NULL` | Set only for ACTIVE production runs |

**SQLite:** `_apply_schema_v2()` in `SQLiteLedger.initialize_schema()` uses `ALTER TABLE ADD COLUMN`. Idempotent via `OperationalError` guard. Applied automatically on `SQLiteLedger` construction.

**PostgreSQL:** Alembic migration `003_pipeline_runs_provenance.py` (`revision=003`, `down_revision=002`). Uses `op.add_column` with `server_default='production'`.

The production database (`data/ledger/crawl_ledger.db`) was migrated in-place: 5 COMPLETED rows gained `run_purpose='production'`, `campaign_id=NULL`.

---

## Purpose Source

`run_purpose` is read from `get_config()` via:

```python
config = get_config()
run_cfg = getattr(config, "run", None)
purpose = getattr(run_cfg, "purpose", "production") if run_cfg is not None else "production"
```

The defensive `getattr` fallback ensures correct behaviour regardless of whether the parallel config Executor (manifest `hm-019ebd66-100d`) has landed `SDC_RUN__PURPOSE` in `infra/config.py` yet. When the config field is absent, `_get_run_purpose()` returns `"production"`.

Environment variable overrides:
- Tests: `SDC_RUN__PURPOSE=test` (set in `tests/conftest.py` `isolated_pipeline_env` fixture)
- Validation script: `SDC_RUN__PURPOSE=validation` (set at top of `scripts/verify_silver_e2e.py`)

---

## Campaign Lifecycle Behaviour

On every call to `_ensure_pipeline_run_registered()`:

1. `run_purpose` is resolved from config.
2. If `run_purpose != "production"`: campaign logic is skipped entirely. `campaign_id` stays `NULL` on the row.
3. If `run_purpose == "production"`:
   a. `get_campaign_status(campaign_id)` is called.
   b. If `None` → `start_campaign(campaign_id, name, {"duration_days": N})` (auto-init).
   c. If `ACTIVE` and `now >= start_date + duration_days` → `complete_campaign(campaign_id)` (auto-complete, CAMP-8 implemented).
   d. If still `ACTIVE` → `stamp_run_campaign(run_id, campaign_id)` stamps the run row.

Campaign `duration_days` defaults to 6. The parallel config Executor is expected to wire `SDC_RUN__CAMPAIGN_ID` (default `campaign_init_001`) and `SDC_RUN__DURATION_DAYS` (default 6) via `infra/config.py`.

---

## Provenance Flow

`run_purpose` and `campaign_id` flow through three layers:

1. **Ledger (`pipeline_runs`)**: stored at registration time.
2. **Silver `source_metadata`**: injected in `_process_record_stream()` in `BasePipeline` via `augmented_meta["run_purpose"]` and `augmented_meta["campaign_id"]`. No Parquet schema change (both fields go into the existing `source_metadata` JSON string).
3. **Manifests (`data/manifests/<run_id>.json`)**: `_finalise_pipeline_run()` calls `_write_run_manifest()` on every COMPLETED run. This wires CAMP-11 for the per-source CLI path; the orchestrator manifest from `run_all_pipelines()` remains as a full-run summary.

---

## flows.py Reconciliation

`is_initial_collection_phase()` (flows.py lines 236–257 before this change) previously called `start_campaign()` inline when the campaign was absent. This created a second, competing campaign initializer.

**Resolution**: the function now only reads campaign status. It returns `True` if `status == "ACTIVE"`, `False` otherwise (absent, COMPLETED). It does not call `start_campaign()`. The lifecycle hook in `_ensure_pipeline_run_registered()` is the only campaign initializer.

This is a safe change for the orchestrator path: `should_run_source()` calls `is_initial_collection_phase()` to decide whether cadence logic applies. The first orchestrated production run will trigger `_ensure_pipeline_run_registered()` which auto-inits the campaign; subsequent calls to `is_initial_collection_phase()` will find it `ACTIVE` and return `True` as before.

---

## DATA-8: Sprakbanken Quota Accounting

The `increment_daily_quota` call in `sprakbanken_somali_processor.py` previously counted `count=1` per corpus file. After this change it counts `count=texts_count` (records extracted from that file). This aligns Sprakbanken's `daily_quotas.records_ingested` with the record-level granularity used by BBC, HuggingFace, and Wikipedia. The quota_limit value (10/day) remains corpus-level in `OrchestrationConfig`; the accounting metric is now consistent.

---

## Consequences

**Positive:**
- Campaign lifecycle is now reachable from every real execution path.
- `complete_campaign()` is called for the first time in the codebase.
- Silver records carry `run_purpose` and `campaign_id` for downstream filtering.
- Every completed per-source run writes a manifest (CAMP-11 resolved).
- No user-facing interface change required.

**Negative / Watch:**
- The `_handle_campaign_lifecycle()` method uses `ledger.get_pipeline_run.__self__.backend.connection` to read `start_date` from `campaigns` — this accesses the SQLite connection directly. A cleaner approach would be to add `get_campaign_start_date()` to the backend interface; deferred as low-priority refactoring (TD).
- `is_initial_collection_phase()` no longer auto-starts campaigns for the orchestrator path alone. Any operator who invokes `somali-orchestrate` before any per-source CLI run will now get a campaign NOT auto-started by the orchestrator (it requires at least one production `BasePipeline.run()` call). In practice this is acceptable because the orchestrator calls `_run_locked_pipeline_task()` which constructs and calls a processor, triggering the hook.
