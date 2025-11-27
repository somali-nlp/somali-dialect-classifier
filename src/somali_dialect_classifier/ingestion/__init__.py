"""
Ingestion package for Somali Dialect Classifier.

This package handles data collection from various sources.
"""
from .base_pipeline import BasePipeline
from .crawl_ledger import CrawlLedger
from .dedup import DedupEngine

__all__ = ["BasePipeline", "CrawlLedger", "DedupEngine"]
