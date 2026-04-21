"""Hashing primitives for deduplication."""

import hashlib
import logging
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger(__name__)


class LRUHashSet:
    """
    Memory-bounded hash set with LRU eviction policy.

    Uses OrderedDict to maintain insertion/access order. When at capacity,
    evicts the least recently accessed entry. This bounds memory usage
    regardless of document count while accepting false negatives.
    """

    def __init__(self, maxsize: int = 100_000):
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")

        self.maxsize = maxsize
        self._store = OrderedDict()

    def add(self, hash_value: str) -> None:
        """Add hash to set, evicting the oldest item when at capacity."""
        if hash_value in self._store:
            self._store.move_to_end(hash_value)
            return

        if len(self._store) >= self.maxsize:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
            logger.debug(
                f"LRU eviction: removed {oldest_key[:16]}... "
                f"(cache size: {len(self._store)}/{self.maxsize})"
            )

        self._store[hash_value] = True

    def __contains__(self, hash_value: str) -> bool:
        if hash_value in self._store:
            self._store.move_to_end(hash_value)
            return True
        return False

    def __len__(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()


class TextHasher:
    """Computes deterministic hashes for text content."""

    def __init__(
        self, algorithm: str = "sha256", fields: Optional[list[str]] = None, separator: str = "|"
    ):
        self.algorithm = algorithm
        self.fields = fields or ["text"]
        self.separator = separator

    def compute_hash(self, text: str, url: Optional[str] = None, **kwargs: object) -> str:
        """Compute a stable hash from configured fields."""
        components = []

        for field in self.fields:
            if field == "text":
                components.append(text)
            elif field == "url" and url:
                components.append(url)
            elif field in kwargs:
                components.append(str(kwargs[field]))

        combined = self.separator.join(components)
        hasher = hashlib.new(self.algorithm)
        hasher.update(combined.encode("utf-8"))
        return hasher.hexdigest()

    def compute_batch(self, records: list[dict]) -> list[str]:
        """Compute hashes for a batch of records."""
        return [
            self.compute_hash(text=record.get("text", ""), url=record.get("url"), **record)
            for record in records
        ]
