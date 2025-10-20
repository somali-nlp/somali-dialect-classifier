"""
Workflow orchestration for Somali Dialect Classifier data pipelines.

Provides Prefect-based orchestration for coordinating data collection,
processing, and quality monitoring across all four data sources.
"""

from .flows import (
    run_wikipedia_pipeline,
    run_bbc_pipeline,
    run_huggingface_pipeline,
    run_sprakbanken_pipeline,
    run_all_pipelines,
)

__all__ = [
    "run_wikipedia_pipeline",
    "run_bbc_pipeline",
    "run_huggingface_pipeline",
    "run_sprakbanken_pipeline",
    "run_all_pipelines",
]
