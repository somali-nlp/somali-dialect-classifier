"""Backward-compatible public API for ingestion deduplication."""

from .engine import DedupConfig, DedupEngine, deduplicate_batch
from .hash import LRUHashSet, TextHasher
from .lsh import DATASKETCH_AVAILABLE, MinHashDeduplicator, ShardedLSH

__all__ = [
    "DATASKETCH_AVAILABLE",
    "DedupConfig",
    "DedupEngine",
    "LRUHashSet",
    "MinHashDeduplicator",
    "ShardedLSH",
    "TextHasher",
    "deduplicate_batch",
]
