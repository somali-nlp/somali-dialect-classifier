-- Crawl Ledger Schema v1.0
-- Compatible with both SQLite and PostgreSQL (with minor syntax adjustments)
-- Aligned with silver_writer.SCHEMA for seamless integration

-- Schema versioning table
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main crawl ledger table
CREATE TABLE IF NOT EXISTS crawl_ledger (
    url TEXT PRIMARY KEY,
    source TEXT NOT NULL,  -- bbc|wikipedia|mc4|sprakbanken
    discovered_at TIMESTAMP NOT NULL,
    last_fetched_at TIMESTAMP,
    http_status INTEGER,

    -- Deduplication fields (aligned with silver_writer.SCHEMA)
    text_hash TEXT,  -- SHA256 for exact dedup (matches silver_writer.SCHEMA)
    minhash_signature TEXT,  -- MinHash for near-dedup (added Phase 1)

    -- Record linkage (connect to silver dataset)
    silver_id TEXT,  -- References silver dataset id field

    -- State tracking
    state TEXT NOT NULL,  -- discovered|fetched|processed|failed|skipped|duplicate
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,

    -- HTTP metadata for conditional requests
    etag TEXT,
    last_modified TEXT,
    content_length INTEGER,

    -- Generic metadata (JSON in SQLite, JSONB in PostgreSQL)
    metadata TEXT,  -- JSON blob for source-specific fields

    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RSS feed tracking table for ethical scraping
CREATE TABLE IF NOT EXISTS rss_feeds (
    feed_url TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    last_fetched_at TIMESTAMP,
    items_found INTEGER,
    fetch_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_source_state ON crawl_ledger(source, state);
CREATE INDEX IF NOT EXISTS idx_text_hash ON crawl_ledger(text_hash);
CREATE INDEX IF NOT EXISTS idx_minhash ON crawl_ledger(minhash_signature);
CREATE INDEX IF NOT EXISTS idx_silver_id ON crawl_ledger(silver_id);
CREATE INDEX IF NOT EXISTS idx_discovered_at ON crawl_ledger(discovered_at);
CREATE INDEX IF NOT EXISTS idx_updated_at ON crawl_ledger(updated_at);

-- RSS feed indexes
CREATE INDEX IF NOT EXISTS idx_rss_source ON rss_feeds(source);
CREATE INDEX IF NOT EXISTS idx_rss_last_fetch ON rss_feeds(last_fetched_at);

-- Example queries:

-- Get URLs pending processing
-- SELECT url FROM crawl_ledger
-- WHERE source = 'bbc' AND state IN ('discovered', 'fetched')
-- ORDER BY discovered_at ASC
-- LIMIT 100;

-- Check for duplicates
-- SELECT url FROM crawl_ledger
-- WHERE text_hash = 'abc123...';

-- Get RSS throttling info
-- SELECT feed_url, last_fetched_at
-- FROM rss_feeds
-- WHERE feed_url = 'https://www.bbc.com/somali/index.xml';

-- Statistics
-- SELECT source, state, COUNT(*) as count
-- FROM crawl_ledger
-- GROUP BY source, state;

-- Cleanup old failures
-- DELETE FROM crawl_ledger
-- WHERE state = 'failed'
-- AND retry_count >= 3
-- AND updated_at < datetime('now', '-30 days');