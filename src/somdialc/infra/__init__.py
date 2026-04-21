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
    from somdialc.infra.config import get_config
    from somdialc.infra.data_manager import DataManager
    from somdialc.infra.metrics import MetricsCollector
    from somdialc.infra.http import HTTPSessionFactory

Submodules are imported directly (most are function-based):
    from somdialc.infra.aggregation import calculate_volume_weighted_quality
    from somdialc.infra.filter_analysis import FilterAnalyzer
    from somdialc.infra.logging_utils import generate_run_id
"""

from .config import get_config
from .data_manager import DataManager

__all__ = ["get_config", "DataManager"]
