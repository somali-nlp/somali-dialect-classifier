"""
Database migration utilities for safe schema management.

This module provides utilities to:
- Check if required tables exist
- Verify database schema is initialized
- Guide users to run migrations if needed
- Maintain backward compatibility with both SQLite and PostgreSQL
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def check_table_exists(conn, table_name: str) -> bool:
    """
    Check if a table exists in the database.

    Works with both PostgreSQL and SQLite.

    Args:
        conn: Database connection (psycopg2 or sqlite3)
        table_name: Name of the table to check

    Returns:
        True if table exists, False otherwise
    """
    try:
        cursor = conn.cursor()

        # Try PostgreSQL query first
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table_name,))

        result = cursor.fetchone()
        return result[0] if result else False

    except Exception:
        # Fallback to SQLite query
        try:
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name=?
            """, (table_name,))

            return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"Failed to check if table {table_name} exists: {e}")
            return False


def verify_schema_initialized(conn, required_tables: Optional[list[str]] = None) -> tuple[bool, list[str]]:
    """
    Verify that required database tables exist.

    Args:
        conn: Database connection
        required_tables: List of required table names (default: crawl_ledger, pipeline_runs)

    Returns:
        Tuple of (all_exist: bool, missing_tables: list[str])
    """
    if required_tables is None:
        required_tables = ["crawl_ledger", "pipeline_runs", "rss_feeds"]

    missing_tables = []

    for table in required_tables:
        if not check_table_exists(conn, table):
            missing_tables.append(table)

    all_exist = len(missing_tables) == 0

    if not all_exist:
        logger.warning(
            f"Database schema incomplete. Missing tables: {', '.join(missing_tables)}"
        )

    return all_exist, missing_tables


def get_migration_instructions(backend: str = "postgresql") -> str:
    """
    Get instructions for running migrations based on backend.

    Args:
        backend: Database backend ('postgresql' or 'sqlite')

    Returns:
        String with migration instructions
    """
    if backend == "postgresql":
        return """
Database schema not initialized. Please run migrations:

Option 1 - Docker (Recommended):
    docker-compose down -v  # Clear existing data
    docker-compose up -d postgres  # Restart with migrations

Option 2 - Manual (Alembic):
    cd migrations/database
    alembic upgrade head

Option 3 - Legacy SQL (Deprecated):
    psql -U somali -d somali_nlp -f migrations/001_initial_schema.sql
    psql -U somali -d somali_nlp -f migrations/002_pipeline_runs_table.sql
"""
    else:  # SQLite
        return """
Database schema will be auto-initialized on first use.
If you see this message, there may be a connection issue.
"""


def ensure_schema_or_fail(conn, backend: str = "postgresql"):
    """
    Ensure database schema is initialized, raise error if not.

    This is a safety check to prevent operations on uninitialized databases.

    Args:
        conn: Database connection
        backend: Database backend type

    Raises:
        RuntimeError: If schema is not initialized
    """
    all_exist, missing_tables = verify_schema_initialized(conn)

    if not all_exist:
        instructions = get_migration_instructions(backend)
        raise RuntimeError(
            f"Database schema not initialized. Missing tables: {', '.join(missing_tables)}\n"
            f"{instructions}"
        )


def safe_create_table_if_not_exists(conn, table_name: str, create_sql: str):
    """
    Safely create a table only if it doesn't exist.

    This is for backward compatibility with SQLite auto-initialization.
    For PostgreSQL, tables should be created via migrations.

    Args:
        conn: Database connection
        table_name: Name of table to create
        create_sql: SQL CREATE TABLE statement

    Returns:
        True if table was created, False if it already existed
    """
    if check_table_exists(conn, table_name):
        logger.debug(f"Table {table_name} already exists, skipping creation")
        return False

    logger.info(f"Creating table {table_name} (backward compatibility mode)")

    try:
        cursor = conn.cursor()
        cursor.execute(create_sql)
        conn.commit()
        return True

    except Exception as e:
        logger.error(f"Failed to create table {table_name}: {e}")
        conn.rollback()
        raise
