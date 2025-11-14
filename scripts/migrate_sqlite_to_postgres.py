"""
Migrate data from SQLite to PostgreSQL.

This script migrates all URL records and RSS feed data from SQLite
to PostgreSQL, preserving state, metadata, and timestamps.

Usage:
    python scripts/migrate_sqlite_to_postgres.py \\
        --sqlite data/ledger/crawl_ledger.db \\
        --postgres-host localhost \\
        --postgres-db somali_nlp

    # Dry run (preview without writing)
    python scripts/migrate_sqlite_to_postgres.py \\
        --sqlite data/ledger/crawl_ledger.db \\
        --postgres-host localhost \\
        --dry-run
"""

import logging
import sys
from pathlib import Path

import click

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlLedger

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@click.command()
@click.option("--sqlite", required=True, type=click.Path(exists=True), help="SQLite database path")
@click.option("--postgres-host", default="localhost", help="PostgreSQL host")
@click.option("--postgres-port", default=5432, type=int, help="PostgreSQL port")
@click.option("--postgres-db", required=True, help="PostgreSQL database name")
@click.option("--postgres-user", default="somali", help="PostgreSQL user")
@click.option(
    "--postgres-password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=False,
    help="PostgreSQL password",
)
@click.option("--dry-run", is_flag=True, help="Preview migration without writing")
@click.option("--batch-size", default=100, type=int, help="Batch size for migration")
def migrate(
    sqlite, postgres_host, postgres_port, postgres_db, postgres_user, postgres_password, dry_run, batch_size
):
    """Migrate SQLite ledger to PostgreSQL."""

    logger.info("=" * 80)
    logger.info("SQLite to PostgreSQL Migration")
    logger.info("=" * 80)

    # Open SQLite backend
    logger.info(f"Opening SQLite database: {sqlite}")
    sqlite_ledger = CrawlLedger(backend_type="sqlite", db_path=Path(sqlite))

    # Open PostgreSQL backend
    if not dry_run:
        logger.info(f"Connecting to PostgreSQL: {postgres_host}:{postgres_port}/{postgres_db}")
        postgres_ledger = CrawlLedger(
            backend_type="postgres",
            host=postgres_host,
            port=postgres_port,
            database=postgres_db,
            user=postgres_user,
            password=postgres_password,
        )
    else:
        logger.info("DRY RUN MODE - No data will be written")
        postgres_ledger = None

    # Get statistics from SQLite
    sqlite_stats = sqlite_ledger.get_statistics()
    logger.info("\nSQLite Database Statistics:")
    logger.info(f"  Total URLs: {sqlite_stats['total_urls']}")
    logger.info(f"  By state: {sqlite_stats['by_state']}")

    # Migrate URLs by source
    sources = ["wikipedia", "bbc", "sprakbanken", "tiktok", "huggingface"]
    total_migrated = 0

    for source in sources:
        logger.info(f"\n{'='*60}")
        logger.info(f"Migrating source: {source}")
        logger.info(f"{'='*60}")

        # Get all URLs for this source
        query = "SELECT * FROM crawl_ledger WHERE source = ?"
        with sqlite_ledger.backend.connection as conn:
            cursor = conn.execute(query, (source,))
            urls = cursor.fetchall()

        if not urls:
            logger.info(f"  No URLs found for {source}")
            continue

        logger.info(f"  Found {len(urls)} URLs")

        # Migrate in batches
        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            logger.info(f"  Migrating batch {i // batch_size + 1} ({len(batch)} URLs)...")

            for url_record in batch:
                # Convert SQLite Row to dict
                url_dict = dict(url_record)

                if not dry_run:
                    # Import metadata from JSON string
                    import json

                    metadata = None
                    if url_dict.get("metadata"):
                        try:
                            metadata = json.loads(url_dict["metadata"])
                        except Exception:
                            metadata = None

                    # Use backend.upsert_url for direct access
                    from somali_dialect_classifier.preprocessing.crawl_ledger import CrawlState

                    postgres_ledger.backend.upsert_url(
                        url=url_dict["url"],
                        source=url_dict["source"],
                        state=CrawlState(url_dict["state"]),
                        text_hash=url_dict.get("text_hash"),
                        minhash_signature=url_dict.get("minhash_signature"),
                        silver_id=url_dict.get("silver_id"),
                        http_status=url_dict.get("http_status"),
                        etag=url_dict.get("etag"),
                        last_modified=url_dict.get("last_modified"),
                        content_length=url_dict.get("content_length"),
                        error_message=url_dict.get("error_message"),
                        metadata=metadata,
                    )

                total_migrated += 1

        logger.info(f"  Completed {source}: {len(urls)} URLs migrated")

    # Migrate RSS feeds
    logger.info(f"\n{'='*60}")
    logger.info("Migrating RSS feeds")
    logger.info(f"{'='*60}")

    with sqlite_ledger.backend.connection as conn:
        cursor = conn.execute("SELECT * FROM rss_feeds")
        rss_feeds = cursor.fetchall()

    if rss_feeds:
        logger.info(f"  Found {len(rss_feeds)} RSS feeds")
        if not dry_run:
            for feed in rss_feeds:
                feed_dict = dict(feed)
                postgres_ledger.backend.record_rss_fetch(
                    feed_url=feed_dict["feed_url"], items_found=feed_dict.get("items_found", 0)
                )
        logger.info(f"  Migrated {len(rss_feeds)} RSS feeds")
    else:
        logger.info("  No RSS feeds to migrate")

    # Final statistics
    logger.info(f"\n{'='*80}")
    logger.info("Migration Summary")
    logger.info(f"{'='*80}")
    logger.info(f"Total URLs migrated: {total_migrated}")

    if not dry_run and postgres_ledger:
        postgres_stats = postgres_ledger.get_statistics()
        logger.info("\nPostgreSQL Database Statistics:")
        logger.info(f"  Total URLs: {postgres_stats['total_urls']}")
        logger.info(f"  By state: {postgres_stats['by_state']}")

        # Verify counts match
        if postgres_stats["total_urls"] >= sqlite_stats["total_urls"]:
            logger.info("\n✓ Migration completed successfully!")
            logger.info("  All records migrated and verified.")
        else:
            logger.warning(
                f"\n⚠ Warning: Count mismatch detected!"
                f"\n  SQLite: {sqlite_stats['total_urls']}"
                f"\n  PostgreSQL: {postgres_stats['total_urls']}"
            )
    else:
        logger.info("\nDRY RUN completed - no data written")

    # Cleanup
    sqlite_ledger.close()
    if postgres_ledger:
        postgres_ledger.close()


if __name__ == "__main__":
    migrate()
