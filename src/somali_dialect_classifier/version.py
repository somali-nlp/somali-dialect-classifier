"""
Version information for Somali Dialect Classifier.

This module provides a single source of truth for version numbers.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    # Read version from installed package metadata
    __version__ = version("somali-dialect-classifier")
except PackageNotFoundError:
    # Fallback for development/editable install
    __version__ = "2.1.0-dev"

# Pipeline version tracks data schema version
# Should be updated when silver schema changes
__pipeline_version__ = "2.1.0"
