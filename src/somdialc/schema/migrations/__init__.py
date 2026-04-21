"""
Schema migration framework.

Provides base classes and utilities for managing schema migrations.
"""

from .base import SchemaMigration
from .manager import MigrationManager

__all__ = ["SchemaMigration", "MigrationManager"]
