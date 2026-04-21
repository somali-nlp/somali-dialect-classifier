"""
Quality package for Somali Dialect Classifier.

This package handles data quality enforcement including:
- Filtering (min length, language detection, PII, profanity)
- Schema validation and record building
- Silver dataset writing
- Text cleaning pipelines

Architecture:
- FilterEngine: Orchestrates filter application
- Filters: Individual quality checks (stateless functions)
- RecordBuilder: Enforces schema compliance
- SilverDatasetWriter: Writes validated silver datasets

Entry Points:
    from somdialc.quality.filter_engine import FilterEngine
    from somdialc.quality.filters import min_length_filter
    from somdialc.quality.record_builder import RecordBuilder
    from somdialc.quality.silver_writer import SilverDatasetWriter

For filter catalog:
    from somdialc.quality.filters.catalog import FilterCatalog
"""

from .filter_engine import FilterEngine
from .record_builder import RecordBuilder
from .silver_writer import SilverDatasetWriter

# Alias for backward compatibility
SilverWriter = SilverDatasetWriter

__all__ = ["FilterEngine", "RecordBuilder", "SilverDatasetWriter", "SilverWriter"]
