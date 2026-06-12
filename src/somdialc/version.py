"""
Version information for Somali Dialect Classifier.

Package version is the single source of truth and is read from installed
package metadata (pyproject.toml).  The package must be installed (e.g.
``pip install -e .``) before this module is imported in production or CI.

__pipeline_version__ tracks the silver data schema version independently
from the package release version and must be updated manually whenever
the silver Parquet schema changes.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("somali-dialect-classifier")
except PackageNotFoundError as exc:
    raise PackageNotFoundError(
        "somali-dialect-classifier is not installed. "
        "Run 'pip install -e .' from the project root before importing."
    ) from exc

# Data-schema version — independent of the package release version.
# Increment this whenever the silver Parquet schema changes.
__pipeline_version__ = "2.1.0"
