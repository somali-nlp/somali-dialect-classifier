# ADR 007 — Apify for TikTok Comment Collection

**Date:** 2025-11-10 (decision made during Phase 1 source integration; recorded retrospectively 2026-06-12)
**Status:** Accepted (retrospective)
**Deciders:** Project principal

---

## Context

Somali is spoken extensively on TikTok; user comments are a valuable source of colloquial and
regional dialect data unavailable from formal sources (news, Wikipedia, academic corpora).
TikTok has no public API for comment access. Collection options are:

1. **Direct scraping** of TikTok's web interface
2. **Apify cloud actors** (managed scraping infrastructure)
3. **Third-party TikTok API wrappers** (various)
4. **Manual export** (not scalable)

---

## Decision

Use **Apify** (`TikTokCommentScraper` actor) via the Apify REST API, accessed through
`src/somdialc/ingestion/apify_tiktok_client.py`.

**Cost model:** $1 per 1,000 comments (Apify actor pricing as of 2025-11-10).

**Cost guard implemented in June 2026:** `apify_tiktok_client.py` adds an idempotency guard on
POST retry — if the actor run was created despite a non-2xx response, the existing `run_id` is
used rather than re-POSTing (which would trigger a duplicate charge). The daily quota system in
the crawl ledger provides a second cost guard (configurable per-run comment cap).

**Target volume:** ~30,000 comments. At current pricing: ~$30 total collection cost.

---

## Rationale

1. **TikTok ToS and rate-limit complexity:** Direct scraping requires maintaining session state,
   rotating user agents, and handling JavaScript-heavy pages. Apify manages this at the infrastructure level.
2. **Reliability:** Apify actors are maintained by the platform; changes to TikTok's front end
   are handled upstream.
3. **Cost predictability:** Per-comment pricing is auditable; daily quota enforcement in the
   crawl ledger prevents runaway spend.
4. **Simplicity:** The client implementation is ~300 LOC; the equivalent direct scraper would be
   significantly larger and higher maintenance.

---

## Cost and Risk

| Risk | Severity | Mitigation |
|------|----------|------------|
| Apify billing if POST retried on network error | High | Idempotency guard in `apify_tiktok_client.py` (June 2026) |
| Cost overrun from large video URL list | High | Per-run quota cap in crawl ledger (`SDC_SCRAPING__TIKTOK__DAILY_QUOTA`) |
| Actor deprecation or pricing change | Medium | Monitor Apify changelog; fallback path is direct scraping |
| TikTok blocks Apify infrastructure | Medium | No mitigation within scope; reassess if collection rate drops |
| API token exposure | Medium | Token stored in `.env`, excluded from git; Gitleaks pre-commit hook |

**Estimated annual cost at steady-state refresh cadence (7-day, ~500 comments/run):**
~$26/year. Unexpected re-charges are the primary financial risk; the idempotency guard directly
addresses this.

---

## Consequences

- `SDC_SCRAPING__TIKTOK__APIFY_API_TOKEN` must be set for TikTok collection to run.
- The pipeline will silently skip TikTok collection if the token is absent (controlled by `tiktok_somali_processor.py`).
- All TikTok runs must go through the crawl ledger quota system; direct calls to the Apify API
  outside the processor are not audited.
- If Apify pricing rises materially, re-evaluate direct scraping or a managed alternative such as
  Bright Data or ScraperAPI.

---

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|-----------------|
| Direct TikTok scraping | High maintenance; fragile against front-end changes; TikTok aggressively fingerprints scrapers |
| TikTok Research API | Requires institutional application; not available for individual researchers at time of decision |
| Manual data collection | Not scalable beyond a few hundred comments |
| Skip TikTok entirely | Colloquial and Southern dialect data (Af-Maay) is underrepresented in formal sources; TikTok is a meaningful signal |
