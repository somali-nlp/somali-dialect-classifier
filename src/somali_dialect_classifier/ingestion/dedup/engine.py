"""Core dedup engine API and batch utilities."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .hash import LRUHashSet, TextHasher
from .lsh import DATASKETCH_AVAILABLE, MinHashDeduplicator

logger = logging.getLogger(__name__)


@dataclass
class DedupConfig:
    """Configuration for deduplication engine."""

    hash_algorithm: str = "sha256"
    hash_fields: Optional[list[str]] = None
    field_separator: str = "|"
    enable_minhash: bool = True
    num_permutations: int = 128
    shingle_size: int = 3
    similarity_threshold: float = 0.85
    seed: int = 42
    storage_path: Optional[Path] = None
    enable_sharding: bool = True
    num_shards: int = 10

    def __post_init__(self) -> None:
        if self.hash_fields is None:
            self.hash_fields = ["text", "url"]


class DedupEngine:
    """Unified deduplication engine combining exact and near-duplicate detection."""

    def __init__(self, config: Optional[DedupConfig] = None):
        self.config = config or DedupConfig()
        self.hasher = TextHasher(
            algorithm=self.config.hash_algorithm,
            fields=self.config.hash_fields,
            separator=self.config.field_separator,
        )

        self.minhash = None
        if self.config.enable_minhash and DATASKETCH_AVAILABLE:
            self.minhash = MinHashDeduplicator(
                num_permutations=self.config.num_permutations,
                shingle_size=self.config.shingle_size,
                similarity_threshold=self.config.similarity_threshold,
                seed=self.config.seed,
                storage_path=self.config.storage_path,
                enable_sharding=self.config.enable_sharding,
                num_shards=self.config.num_shards,
            )
        elif self.config.enable_minhash and not DATASKETCH_AVAILABLE:
            logger.warning(
                "MinHash deduplication requested but datasketch not available. Only exact deduplication will be used."
            )

        cache_size = int(os.environ.get("DEDUP_CACHE_SIZE", 100_000))
        self.seen_hashes = LRUHashSet(maxsize=cache_size)
        logger.info(f"Initialized dedup engine with LRU cache size: {cache_size:,}")

        self.hash_to_url = {}
        self._hash_to_url_maxsize = cache_size

    def process_document(
        self, text: str, url: str, **kwargs: object
    ) -> tuple[bool, Optional[str], Optional[str], str, Optional[str]]:
        text_hash = self.hasher.compute_hash(text=text, url=url, **kwargs)

        if text_hash in self.seen_hashes:
            canonical_url = self.hash_to_url.get(text_hash, url)
            logger.debug(
                f"Exact duplicate found: {url} matches {canonical_url} (hash: {text_hash[:16]}...)"
            )
            return True, "exact", canonical_url, text_hash, None

        minhash_signature = None
        if self.minhash:
            similar = self.minhash.is_duplicate(text)
            if similar:
                similar_url, similarity = similar
                logger.debug(
                    f"Near-duplicate found: {url} similar to {similar_url} (similarity: {similarity:.2f})"
                )
                return True, "near", similar_url, text_hash, None

            minhash_signature = self.minhash.add_document(url, text)

        self.seen_hashes.add(text_hash)
        if len(self.hash_to_url) >= self._hash_to_url_maxsize:
            oldest_key = next(iter(self.hash_to_url))
            del self.hash_to_url[oldest_key]
            logger.debug(
                f"Evicted hash_to_url entry: {oldest_key[:16]}... "
                f"(dict size: {len(self.hash_to_url)}/{self._hash_to_url_maxsize})"
            )

        self.hash_to_url[text_hash] = url
        return False, None, None, text_hash, minhash_signature

    def is_duplicate_hash(self, text_hash: str) -> bool:
        return text_hash in self.seen_hashes

    def get_canonical_url(self, text_hash: str) -> Optional[str]:
        return self.hash_to_url.get(text_hash)

    def add_known_hash(self, text_hash: str, url: Optional[str] = None) -> None:
        self.seen_hashes.add(text_hash)
        if url:
            self.hash_to_url[text_hash] = url

    def get_statistics(self) -> dict:
        stats = {
            "total_hashes": len(self.seen_hashes),
            "exact_dedup_enabled": True,
            "near_dedup_enabled": self.minhash is not None,
        }
        if self.minhash:
            stats["minhash_documents"] = len(self.minhash.document_hashes)
            stats["minhash_threshold"] = self.config.similarity_threshold
        return stats

    def check_discovery_stage(self, url: str, ledger) -> bool:
        try:
            url_state = ledger.get_url_state(url)
            if url_state and url_state.get("state") in ["processed", "duplicate"]:
                logger.info(f"Skipping already processed URL: {url}")
                return True
            return False
        except Exception as err:
            logger.warning(f"Error checking URL state for {url}: {err}")
            return False

    def check_file_duplicate(self, filepath: Path, ledger, source: str) -> tuple[bool, Optional[str]]:
        import hashlib

        sha256 = hashlib.sha256()
        with open(filepath, "rb") as handle:
            for chunk in iter(lambda: handle.read(4096), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()

        try:
            if ledger:
                existing = ledger.check_file_checksum(checksum, source)
                if existing:
                    logger.info(
                        f"File already processed: {existing['url']} (checksum: {checksum[:16]}...)"
                    )
                    return True, checksum
                logger.debug(f"File checksum computed: {checksum[:16]}...")
            else:
                logger.debug(f"File checksum computed (no ledger): {checksum[:16]}...")
            return False, checksum
        except Exception as err:
            logger.warning(f"Error checking file checksum: {err}")
            return False, checksum


def deduplicate_batch(
    records: list[dict], dedup_engine: DedupEngine, text_field: str = "text", url_field: str = "url"
) -> tuple[list[dict], list[dict]]:
    """Deduplicate a batch of records while preserving dedup metadata."""
    unique = []
    duplicates = []

    for record in records:
        text = record.get(text_field, "")
        url = record.get(url_field, "")
        is_dup, dup_type, similar_url, text_hash, minhash_sig = dedup_engine.process_document(
            text, url
        )

        record["text_hash"] = text_hash
        if minhash_sig:
            record["minhash_signature"] = minhash_sig
        if is_dup and similar_url:
            record["duplicate_of"] = similar_url
            record["duplicate_type"] = dup_type

        if is_dup:
            duplicates.append(record)
        else:
            unique.append(record)

    return unique, duplicates
