"""
Infrastructure package for Somali Dialect Classifier.

This package provides cross-cutting infrastructure services including:
- Configuration management (environment variables, defaults)
- Data path management (raw, staging, processed, silver)
- Metrics collection and aggregation
- Manifest generation
- HTTP utilities (rate-limited clients)
- Logging utilities
- Security utilities (secret redaction)

Architecture:
- Config: Singleton configuration with Pydantic validation
- DataManager: Centralized data path management
- Metrics: Metrics collection, schema, aggregation
- Logging: Structured logging with run IDs

Entry Points:
    from somali_dialect_classifier.infra.config import get_config
    from somali_dialect_classifier.infra.data_manager import DataManager
    from somali_dialect_classifier.infra.metrics import MetricsCollector
    from somali_dialect_classifier.infra.http import HTTPSessionFactory

Submodules are imported directly (most are function-based):
    from somali_dialect_classifier.infra.aggregation import calculate_volume_weighted_quality
    from somali_dialect_classifier.infra.filter_analysis import FilterAnalyzer
    from somali_dialect_classifier.infra.logging_utils import generate_run_id
"""

from .config import get_config
from .data_manager import DataManager

__all__ = ["get_config", "DataManager"]
