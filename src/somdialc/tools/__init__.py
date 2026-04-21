"""
Somali Dialect Classifier CLI Tools.

Unified command-line interface for operational tasks including metrics
consolidation, ledger management, data validation, and dashboard operations.

This package consolidates scattered scripts into a cohesive CLI with consistent
UX, comprehensive help text, and testable library code.

Entry Point:
    somali-tools - Main CLI entry point (defined in cli.py)

Command Groups:
    - metrics: Metrics management and analysis
    - ledger: Ledger database operations
    - data: Dataset validation and quality checks
    - dashboard: Dashboard build and deployment

Usage:
    somali-tools --help
    somali-tools metrics consolidate --help
    somali-tools ledger status
"""

__version__ = "0.2.0"

__all__ = ["__version__"]
