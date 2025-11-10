#!/usr/bin/env python3
"""
Migrate ledger entries from 'discovered' to 'processed' state and backfill hashes.

This script fixes the issue where Nov 2 data is stuck in 'discovered' state,
preventing historic hash loading on subsequent runs.
"""

import sqlite3
import duckdb
from pathlib import Path
from datetime import datetime
import hashlib

def main():
    ledger_path = Path("data/ledger/crawl_ledger.db")

    print("=" * 80)
    print("LEDGER STATE MIGRATION")
    print("=" * 80)

    # Connect to ledger
    ledger_conn = sqlite3.connect(ledger_path)
    ledger_conn.row_factory = sqlite3.Row

    # Step 1: Standardize source naming (lowercase → PascalCase)
    print("\n[1] Standardizing source names...")

    naming_fixes = [
        ('wikipedia', 'Wikipedia-Somali'),
        ('bbc', 'BBC-Somali'),
        ('tiktok', 'TikTok-Somali'),
        ('sprakbanken', 'Sprakbanken-Somali'),
    ]

    for old_name, new_name in naming_fixes:
        cursor = ledger_conn.execute(
            "SELECT COUNT(*) FROM crawl_ledger WHERE source = ?",
            (old_name,)
        )
        count = cursor.fetchone()[0]

        if count > 0:
            print(f"  Updating {count} entries: '{old_name}' → '{new_name}'")
            ledger_conn.execute(
                "UPDATE crawl_ledger SET source = ?, updated_at = CURRENT_TIMESTAMP WHERE source = ?",
                (new_name, old_name)
            )

    ledger_conn.commit()

    # Step 2: Check current state distribution
    print("\n[2] Current state distribution:")
    cursor = ledger_conn.execute("""
        SELECT source, state, COUNT(*) as count, COUNT(text_hash) as with_hash
        FROM crawl_ledger
        WHERE source IN ('Wikipedia-Somali', 'BBC-Somali', 'Sprakbanken-Somali')
        GROUP BY source, state
        ORDER BY source, state
    """)

    for row in cursor:
        print(f"  {row['source']:<25} | {row['state']:<12} | {row['count']:>6} entries | {row['with_hash']:>6} with hash")

    # Step 3: Extract hashes from silver dataset for Nov 9 processed data
    print("\n[3] Extracting hashes from silver dataset...")

    duckdb_conn = duckdb.connect()

    sources_to_process = [
        ('Wikipedia-Somali', 'data/processed/silver/source=Wikipedia-Somali/date_accessed=2025-11-09/*.parquet'),
        ('BBC-Somali', 'data/processed/silver/source=BBC-Somali/date_accessed=*/part-*.parquet'),
        ('Sprakbanken-Somali', 'data/processed/silver/source=Sprakbanken-Somali/date_accessed=*/part-*.parquet'),
    ]

    hash_updates = []

    for source, pattern in sources_to_process:
        try:
            # Extract url and text_hash from silver parquet
            result = duckdb_conn.execute(f"""
                SELECT url, text_hash, text
                FROM '{pattern}'
                WHERE text_hash IS NOT NULL
            """).fetchall()

            print(f"  {source}: Found {len(result)} records with hashes in silver")

            for url, text_hash, text in result:
                # If text_hash is null in silver, compute it
                if not text_hash and text:
                    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

                hash_updates.append((text_hash, url, source))

        except Exception as e:
            print(f"  {source}: No silver data found or error: {e}")

    print(f"\n  Total hashes extracted: {len(hash_updates)}")

    # Step 4: Backfill hashes into ledger
    print("\n[4] Backfilling hashes into ledger...")

    backfilled = 0
    for text_hash, url, source in hash_updates:
        # Check if entry exists in ledger
        cursor = ledger_conn.execute(
            "SELECT state, text_hash FROM crawl_ledger WHERE url = ? AND source = ?",
            (url, source)
        )
        row = cursor.fetchone()

        if row:
            current_state = row['state'] if row else None
            current_hash = row['text_hash'] if row else None

            # Update state to 'processed' and add hash if missing
            if current_state in ('discovered', 'fetched') or not current_hash:
                ledger_conn.execute("""
                    UPDATE crawl_ledger
                    SET state = 'processed',
                        text_hash = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE url = ? AND source = ?
                """, (text_hash, url, source))
                backfilled += 1

    ledger_conn.commit()
    print(f"  Backfilled {backfilled} entries")

    # Step 5: Verify migration
    print("\n[5] Post-migration verification:")
    cursor = ledger_conn.execute("""
        SELECT source, state, COUNT(*) as count, COUNT(text_hash) as with_hash
        FROM crawl_ledger
        WHERE source IN ('Wikipedia-Somali', 'BBC-Somali', 'Sprakbanken-Somali')
        GROUP BY source, state
        ORDER BY source, state
    """)

    for row in cursor:
        print(f"  {row['source']:<25} | {row['state']:<12} | {row['count']:>6} entries | {row['with_hash']:>6} with hash")

    # Check for any processed entries without hashes (should be 0)
    cursor = ledger_conn.execute("""
        SELECT COUNT(*) FROM crawl_ledger
        WHERE state = 'processed' AND text_hash IS NULL
    """)
    orphaned = cursor.fetchone()[0]

    if orphaned > 0:
        print(f"\n  ⚠️  WARNING: {orphaned} 'processed' entries still missing hashes")
    else:
        print(f"\n  ✅ All 'processed' entries have hashes")

    ledger_conn.close()
    duckdb_conn.close()

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
