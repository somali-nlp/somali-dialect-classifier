"""
Database backends for Somali NLP project.

Provides scalable database implementations for the crawl ledger system.
"""

from .postgres_ledger import PostgresLedger

__all__ = ["PostgresLedger"]
