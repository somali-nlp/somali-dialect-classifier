"""
Ledger command implementations for somali-tools CLI.

This module contains testable library code for ledger operations.
Separated from CLI to enable unit testing without Click framework.

Functions include:
- Ledger database migrations
- Lock file management
- Database status queries
- Ad-hoc SQL queries
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# LEDGER MIGRATIONS
# ============================================================================


def migrate_ledger_database(
    ledger_path: Path, migration_name: str | None = None, dry_run: bool = False
) -> dict[str, Any]:
    """
    Run ledger database migrations.

    Args:
        ledger_path: Path to SQLite ledger database
        migration_name: Specific migration to run (default: all pending)
        dry_run: If True, show what would be migrated without executing

    Returns:
        Migration result with applied migrations list

    Raises:
        FileNotFoundError: If ledger_path doesn't exist
        sqlite3.Error: If migration fails
    """
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger database not found: {ledger_path}")

    # Find migrations directory
    migrations_dir = Path(__file__).parent.parent.parent.parent / "migrations"

    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    # Find migration files
    if migration_name:
        migration_files = [migrations_dir / f"{migration_name}.sql"]
        if not migration_files[0].exists():
            raise FileNotFoundError(f"Migration not found: {migration_name}")
    else:
        migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        logger.info("No migrations found")
        return {"applied": [], "dry_run": dry_run, "total": 0}

    # Connect to database
    conn = sqlite3.connect(ledger_path)
    conn.row_factory = sqlite3.Row

    # Create migrations tracking table if needed
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """)
    conn.commit()

    # Get applied migrations
    cursor = conn.execute("SELECT migration_name FROM schema_migrations")
    applied_migrations = {row[0] for row in cursor.fetchall()}

    # Apply pending migrations
    applied = []

    for migration_file in migration_files:
        migration_name = migration_file.stem

        if migration_name in applied_migrations:
            logger.info(f"Migration {migration_name} already applied, skipping")
            continue

        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Applying migration: {migration_name}")

        # Read migration SQL
        with open(migration_file) as f:
            migration_sql = f.read()

        if dry_run:
            applied.append(
                {
                    "migration": migration_name,
                    "status": "would_apply",
                    "sql_preview": migration_sql[:200] + "..."
                    if len(migration_sql) > 200
                    else migration_sql,
                }
            )
        else:
            try:
                # Execute migration
                conn.executescript(migration_sql)

                # Record migration
                conn.execute(
                    "INSERT INTO schema_migrations (migration_name, applied_at) VALUES (?, ?)",
                    (migration_name, datetime.utcnow().isoformat()),
                )
                conn.commit()

                applied.append(
                    {
                        "migration": migration_name,
                        "status": "applied",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

                logger.info(f"Successfully applied migration: {migration_name}")

            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Failed to apply migration {migration_name}: {e}")
                applied.append({"migration": migration_name, "status": "failed", "error": str(e)})
                raise

    conn.close()

    return {"applied": applied, "dry_run": dry_run, "total": len(applied)}


# ============================================================================
# LOCK MANAGEMENT
# ============================================================================


def clear_stale_locks(
    lock_dir: Path, max_age_hours: int = 24, force: bool = False
) -> dict[str, Any]:
    """
    Clear stale locks in ledger.

    Args:
        lock_dir: Lock directory path
        max_age_hours: Maximum lock age in hours
        force: If True, clear all locks regardless of age

    Returns:
        Result with cleared locks count

    Raises:
        FileNotFoundError: If lock_dir doesn't exist
    """
    if not lock_dir.exists():
        raise FileNotFoundError(f"Lock directory not found: {lock_dir}")

    # Find all lock files
    lock_files = list(lock_dir.glob("*.lock"))

    if not lock_files:
        logger.info("No lock files found")
        return {"total_locks": 0, "cleared": 0, "retained": 0, "locks": []}

    cleared = []
    retained = []
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

    for lock_file in lock_files:
        # Get lock file modification time
        mtime = datetime.fromtimestamp(lock_file.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600

        if force or mtime < cutoff_time:
            # Remove lock
            try:
                lock_file.unlink()
                cleared.append(
                    {
                        "file": lock_file.name,
                        "age_hours": round(age_hours, 2),
                        "removed_at": datetime.now().isoformat(),
                    }
                )
                logger.info(f"Cleared lock: {lock_file.name} (age: {age_hours:.1f}h)")
            except Exception as e:
                logger.error(f"Failed to remove lock {lock_file.name}: {e}")
        else:
            retained.append({"file": lock_file.name, "age_hours": round(age_hours, 2)})

    return {
        "total_locks": len(lock_files),
        "cleared": len(cleared),
        "retained": len(retained),
        "force": force,
        "max_age_hours": max_age_hours,
        "locks": {"cleared": cleared, "retained": retained},
    }


# ============================================================================
# DATABASE STATUS
# ============================================================================


def get_ledger_status(ledger_path: Path, verbose: bool = False) -> dict[str, Any]:
    """
    Show ledger database status.

    Args:
        ledger_path: Path to SQLite ledger database
        verbose: If True, include detailed table information

    Returns:
        Status dict with counts and info

    Raises:
        FileNotFoundError: If ledger_path doesn't exist
        sqlite3.Error: If query fails
    """
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger database not found: {ledger_path}")

    conn = sqlite3.connect(ledger_path)
    conn.row_factory = sqlite3.Row

    # Get database size
    db_size_bytes = ledger_path.stat().st_size
    db_size_mb = db_size_bytes / (1024 * 1024)

    # Get schema version (latest migration)
    try:
        cursor = conn.execute(
            "SELECT migration_name FROM schema_migrations ORDER BY applied_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        schema_version = row[0] if row else "unknown"
    except sqlite3.OperationalError:
        schema_version = "pre-migration-tracking"

    # Get table counts
    tables = {}

    # Check which tables exist
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    table_names = [row[0] for row in cursor.fetchall()]

    for table_name in table_names:
        if table_name == "schema_migrations":
            continue

        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        tables[table_name] = {"count": count}

        if verbose:
            # Get column info
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            tables[table_name]["columns"] = columns

    # Get recent activity
    recent_activity = {}

    try:
        # Recent pipeline run
        cursor = conn.execute(
            "SELECT source, created_at FROM pipeline_runs ORDER BY created_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            recent_activity["last_pipeline_run"] = {"source": row[0], "timestamp": row[1]}
    except sqlite3.OperationalError:
        pass  # Table doesn't exist

    try:
        # Recent URL added
        cursor = conn.execute(
            "SELECT source, created_at FROM url_queue ORDER BY created_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            recent_activity["last_url_added"] = {"source": row[0], "timestamp": row[1]}
    except sqlite3.OperationalError:
        pass

    conn.close()

    return {
        "database": str(ledger_path),
        "size_bytes": db_size_bytes,
        "size_mb": round(db_size_mb, 2),
        "schema_version": schema_version,
        "tables": tables,
        "recent_activity": recent_activity,
        "verbose": verbose,
    }


# ============================================================================
# AD-HOC QUERIES
# ============================================================================


def query_ledger(ledger_path: Path, sql: str, format: str = "table") -> dict[str, Any]:
    """
    Execute ad-hoc ledger queries.

    Args:
        ledger_path: Path to SQLite ledger database
        sql: SQL query to execute
        format: Output format (table, json, csv)

    Returns:
        Query results in specified format

    Raises:
        FileNotFoundError: If ledger_path doesn't exist
        sqlite3.Error: If query fails
        ValueError: If query is not a SELECT statement
    """
    if not ledger_path.exists():
        raise FileNotFoundError(f"Ledger database not found: {ledger_path}")

    # Security: Only allow SELECT statements
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed. For data modifications, use migrations.")

    conn = sqlite3.connect(ledger_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()

        if not rows:
            return {"query": sql, "format": format, "row_count": 0, "columns": [], "rows": []}

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Convert to desired format
        if format == "json":
            result_rows = [dict(row) for row in rows]
        else:
            result_rows = [tuple(row) for row in rows]

        return {
            "query": sql,
            "format": format,
            "row_count": len(rows),
            "columns": columns,
            "rows": result_rows,
        }

    except sqlite3.Error as e:
        logger.error(f"Query failed: {e}")
        raise

    finally:
        conn.close()
