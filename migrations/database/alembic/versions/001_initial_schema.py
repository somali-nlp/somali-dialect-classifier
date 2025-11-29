"""Initial schema - crawl ledger and RSS feeds

Revision ID: 001
Revises:
Create Date: 2025-11-11

This migration creates the initial database schema including:
- crawl_ledger table for URL tracking and deduplication
- rss_feeds table for ethical scraping throttling
- schema_version table for migration tracking
- All necessary indexes for query performance
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema."""

    # URLs tracking table
    op.execute("""
        CREATE TABLE IF NOT EXISTS crawl_ledger (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            discovered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            last_fetched_at TIMESTAMP WITH TIME ZONE,
            http_status INTEGER,

            -- Deduplication fields (aligned with silver_writer.SCHEMA)
            text_hash TEXT,
            minhash_signature TEXT,

            -- Record linkage
            silver_id TEXT,

            -- State tracking
            state TEXT NOT NULL,
            retry_count INTEGER DEFAULT 0,
            error_message TEXT,

            -- HTTP metadata for conditional requests
            etag TEXT,
            last_modified TEXT,
            content_length INTEGER,

            -- Generic metadata (JSONB for better indexing)
            metadata JSONB,

            -- Audit fields
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # Performance indexes for query optimization
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_ledger_source ON crawl_ledger(source)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_ledger_state ON crawl_ledger(state)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_ledger_source_state ON crawl_ledger(source, state)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_ledger_text_hash ON crawl_ledger(text_hash) WHERE text_hash IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_ledger_minhash ON crawl_ledger(minhash_signature) WHERE minhash_signature IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_ledger_silver_id ON crawl_ledger(silver_id) WHERE silver_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_ledger_discovered_at ON crawl_ledger(discovered_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_ledger_updated_at ON crawl_ledger(updated_at)")

    # GIN index for JSONB metadata queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_ledger_metadata ON crawl_ledger USING GIN (metadata)")

    # RSS feed tracking table for ethical scraping
    op.execute("""
        CREATE TABLE IF NOT EXISTS rss_feeds (
            id SERIAL PRIMARY KEY,
            feed_url TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            last_fetched_at TIMESTAMP WITH TIME ZONE,
            items_found INTEGER,
            fetch_count INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_rss_feeds_source ON rss_feeds(source)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rss_feeds_last_fetched ON rss_feeds(last_fetched_at)")

    # Schema version table for migration tracking
    op.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("INSERT INTO schema_version (version) VALUES (1) ON CONFLICT (version) DO NOTHING")


def downgrade() -> None:
    """Drop initial schema."""
    op.execute("DROP TABLE IF EXISTS rss_feeds CASCADE")
    op.execute("DROP TABLE IF EXISTS crawl_ledger CASCADE")
    op.execute("DROP TABLE IF EXISTS schema_version CASCADE")
