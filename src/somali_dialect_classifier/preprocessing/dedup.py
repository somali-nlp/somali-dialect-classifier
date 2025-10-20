"""
Deduplication engine for text data.

Provides two-tier deduplication:
1. Exact deduplication using SHA256 hashing
2. Near-duplicate detection using MinHash LSH

Integrated with crawl ledger for state tracking.
"""

import hashlib
import logging
from typing import List, Optional, Tuple, Set
from dataclasses import dataclass

try:
    from datasketch import MinHash, MinHashLSH
    DATASKETCH_AVAILABLE = True
except ImportError:
    DATASKETCH_AVAILABLE = False
    MinHash = None
    MinHashLSH = None


logger = logging.getLogger(__name__)


@dataclass
class DedupConfig:
    """Configuration for deduplication engine."""

    # Exact deduplication settings
    hash_algorithm: str = "sha256"
    hash_fields: List[str] = None  # Default: ["text", "url"]
    field_separator: str = "|"

    # MinHash settings
    enable_minhash: bool = True
    num_permutations: int = 128
    shingle_size: int = 3  # Word n-grams
    similarity_threshold: float = 0.85  # Jaccard similarity
    seed: int = 42

    def __post_init__(self):
        """Set defaults."""
        if self.hash_fields is None:
            self.hash_fields = ["text", "url"]


class TextHasher:
    """
    Computes deterministic hashes for text content.

    Aligned with silver_writer.SCHEMA.text_hash field.
    """

    def __init__(
        self,
        algorithm: str = "sha256",
        fields: List[str] = None,
        separator: str = "|"
    ):
        """
        Initialize text hasher.

        Args:
            algorithm: Hash algorithm (sha256, md5, blake2b)
            fields: Fields to include in hash (e.g., ["text", "url"])
            separator: Separator for combining fields
        """
        self.algorithm = algorithm
        self.fields = fields or ["text"]
        self.separator = separator

    def compute_hash(self, text: str, url: Optional[str] = None, **kwargs) -> str:
        """
        Compute hash for text content.

        Args:
            text: Main text content
            url: Optional URL
            **kwargs: Additional fields to include

        Returns:
            Hexadecimal hash string

        Example:
            >>> hasher = TextHasher(fields=["text", "url"])
            >>> hash_val = hasher.compute_hash(text="Hello world", url="https://example.com")
        """
        # Combine fields
        components = []

        for field in self.fields:
            if field == "text":
                components.append(text)
            elif field == "url" and url:
                components.append(url)
            elif field in kwargs:
                components.append(str(kwargs[field]))

        combined = self.separator.join(components)

        # Compute hash
        hasher = hashlib.new(self.algorithm)
        hasher.update(combined.encode('utf-8'))

        return hasher.hexdigest()

    def compute_batch(self, records: List[dict]) -> List[str]:
        """
        Compute hashes for batch of records.

        Args:
            records: List of record dictionaries

        Returns:
            List of hash values
        """
        return [
            self.compute_hash(
                text=record.get("text", ""),
                url=record.get("url"),
                **record
            )
            for record in records
        ]


class MinHashDeduplicator:
    """
    Near-duplicate detection using MinHash LSH.

    Uses Jaccard similarity on word shingles to detect similar documents.
    """

    def __init__(
        self,
        num_permutations: int = 128,
        shingle_size: int = 3,
        similarity_threshold: float = 0.85,
        seed: int = 42
    ):
        """
        Initialize MinHash deduplicator.

        Args:
            num_permutations: Number of hash functions (higher = more accurate)
            shingle_size: Word n-gram size for shingling
            similarity_threshold: Jaccard similarity threshold
            seed: Random seed for reproducibility
        """
        if not DATASKETCH_AVAILABLE:
            raise ImportError(
                "datasketch library is required for MinHash deduplication. "
                "Install it with: pip install datasketch"
            )

        self.num_permutations = num_permutations
        self.shingle_size = shingle_size
        self.similarity_threshold = similarity_threshold
        self.seed = seed

        # Initialize LSH index
        self.lsh = MinHashLSH(
            threshold=similarity_threshold,
            num_perm=num_permutations
        )

        # Track inserted documents
        self.document_hashes = {}  # url -> minhash_signature

    def _create_shingles(self, text: str) -> Set[str]:
        """
        Create word shingles from text.

        Args:
            text: Input text

        Returns:
            Set of shingles (word n-grams)
        """
        # Tokenize (simple whitespace split)
        words = text.lower().split()

        # Create n-grams
        shingles = set()
        for i in range(len(words) - self.shingle_size + 1):
            shingle = " ".join(words[i:i + self.shingle_size])
            shingles.add(shingle)

        return shingles

    def compute_minhash(self, text: str) -> MinHash:
        """
        Compute MinHash signature for text.

        Args:
            text: Input text

        Returns:
            MinHash object
        """
        # Create shingles
        shingles = self._create_shingles(text)

        # Create MinHash
        minhash = MinHash(num_perm=self.num_permutations, seed=self.seed)

        # Add shingles to MinHash
        for shingle in shingles:
            minhash.update(shingle.encode('utf-8'))

        return minhash

    def compute_signature(self, text: str) -> str:
        """
        Compute MinHash signature as string for storage.

        Args:
            text: Input text

        Returns:
            Serialized MinHash signature
        """
        minhash = self.compute_minhash(text)

        # Convert to string (hex of hash values)
        signature = ','.join(str(h) for h in minhash.hashvalues)

        return signature

    def signature_from_string(self, signature_str: str) -> MinHash:
        """
        Reconstruct MinHash from stored signature string.

        Args:
            signature_str: Serialized signature

        Returns:
            MinHash object
        """
        # Parse hash values
        hashvalues = [int(h) for h in signature_str.split(',')]

        # Create MinHash with same parameters
        minhash = MinHash(num_perm=self.num_permutations, seed=self.seed)
        minhash.hashvalues = tuple(hashvalues)

        return minhash

    def add_document(self, url: str, text: str) -> str:
        """
        Add document to LSH index.

        Args:
            url: Document identifier (URL)
            text: Document text

        Returns:
            MinHash signature string
        """
        # Compute MinHash
        minhash = self.compute_minhash(text)

        # Add to LSH index
        self.lsh.insert(url, minhash)

        # Store signature
        signature = ','.join(str(h) for h in minhash.hashvalues)
        self.document_hashes[url] = signature

        return signature

    def find_similar(self, text: str, threshold: Optional[float] = None) -> List[Tuple[str, float]]:
        """
        Find similar documents in index.

        Args:
            text: Query text
            threshold: Similarity threshold (None = use default)

        Returns:
            List of (url, similarity) tuples
        """
        if threshold is None:
            threshold = self.similarity_threshold

        # Compute MinHash for query
        query_minhash = self.compute_minhash(text)

        # Query LSH index
        similar_urls = self.lsh.query(query_minhash)

        # Compute exact similarities
        results = []
        for url in similar_urls:
            if url in self.document_hashes:
                # Reconstruct MinHash from stored signature
                doc_minhash = self.signature_from_string(self.document_hashes[url])

                # Compute Jaccard similarity
                similarity = query_minhash.jaccard(doc_minhash)

                if similarity >= threshold:
                    results.append((url, similarity))

        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def is_duplicate(self, text: str, threshold: Optional[float] = None) -> Optional[Tuple[str, float]]:
        """
        Check if text is a near-duplicate of existing document.

        Args:
            text: Query text
            threshold: Similarity threshold

        Returns:
            (url, similarity) of most similar document, or None
        """
        similar = self.find_similar(text, threshold)

        if similar:
            return similar[0]  # Return most similar
        return None


class DedupEngine:
    """
    Unified deduplication engine combining exact and near-duplicate detection.
    """

    def __init__(self, config: Optional[DedupConfig] = None):
        """
        Initialize dedup engine.

        Args:
            config: Deduplication configuration
        """
        self.config = config or DedupConfig()

        # Initialize exact dedup hasher
        self.hasher = TextHasher(
            algorithm=self.config.hash_algorithm,
            fields=self.config.hash_fields,
            separator=self.config.field_separator
        )

        # Initialize MinHash deduplicator if enabled
        self.minhash = None
        if self.config.enable_minhash and DATASKETCH_AVAILABLE:
            self.minhash = MinHashDeduplicator(
                num_permutations=self.config.num_permutations,
                shingle_size=self.config.shingle_size,
                similarity_threshold=self.config.similarity_threshold,
                seed=self.config.seed
            )
        elif self.config.enable_minhash and not DATASKETCH_AVAILABLE:
            logger.warning(
                "MinHash deduplication requested but datasketch not available. "
                "Only exact deduplication will be used."
            )

        # Track seen hashes for exact dedup
        self.seen_hashes = set()

    def process_document(
        self,
        text: str,
        url: str,
        **kwargs
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Process document for deduplication.

        Returns:
            (is_duplicate, text_hash, minhash_signature)
            - is_duplicate: True if duplicate found
            - text_hash: SHA256 hash of content
            - minhash_signature: MinHash signature (if enabled)
        """
        # Compute exact hash
        text_hash = self.hasher.compute_hash(text=text, url=url, **kwargs)

        # Check exact duplicate
        if text_hash in self.seen_hashes:
            logger.debug(f"Exact duplicate found: {url} (hash: {text_hash[:16]}...)")
            return (True, text_hash, None)

        # Compute MinHash signature if enabled
        minhash_signature = None
        if self.minhash:
            # Check near-duplicates
            similar = self.minhash.is_duplicate(text)
            if similar:
                similar_url, similarity = similar
                logger.debug(
                    f"Near-duplicate found: {url} similar to {similar_url} "
                    f"(similarity: {similarity:.2f})"
                )
                return (True, text_hash, None)

            # Not a duplicate, add to index
            minhash_signature = self.minhash.add_document(url, text)

        # Record hash as seen
        self.seen_hashes.add(text_hash)

        return (False, text_hash, minhash_signature)

    def is_duplicate_hash(self, text_hash: str) -> bool:
        """Check if hash was already seen."""
        return text_hash in self.seen_hashes

    def add_known_hash(self, text_hash: str):
        """Add hash to seen set (from ledger)."""
        self.seen_hashes.add(text_hash)

    def get_statistics(self) -> dict:
        """Get deduplication statistics."""
        stats = {
            "total_hashes": len(self.seen_hashes),
            "exact_dedup_enabled": True,
            "near_dedup_enabled": self.minhash is not None
        }

        if self.minhash:
            stats["minhash_documents"] = len(self.minhash.document_hashes)
            stats["minhash_threshold"] = self.config.similarity_threshold

        return stats


# Helper function for batch processing

def deduplicate_batch(
    records: List[dict],
    dedup_engine: DedupEngine,
    text_field: str = "text",
    url_field: str = "url"
) -> Tuple[List[dict], List[dict]]:
    """
    Deduplicate batch of records.

    Args:
        records: List of record dictionaries
        dedup_engine: DedupEngine instance
        text_field: Field name containing text
        url_field: Field name containing URL

    Returns:
        (unique_records, duplicate_records)
    """
    unique = []
    duplicates = []

    for record in records:
        text = record.get(text_field, "")
        url = record.get(url_field, "")

        is_dup, text_hash, minhash_sig = dedup_engine.process_document(text, url)

        # Add dedup fields to record
        record["text_hash"] = text_hash
        if minhash_sig:
            record["minhash_signature"] = minhash_sig

        if is_dup:
            duplicates.append(record)
        else:
            unique.append(record)

    return unique, duplicates


# Example usage
if __name__ == "__main__":
    # Create dedup engine
    config = DedupConfig(
        hash_fields=["text"],  # Hash only text content
        enable_minhash=True,
        similarity_threshold=0.85
    )

    engine = DedupEngine(config)

    # Test documents
    docs = [
        ("url1", "The quick brown fox jumps over the lazy dog"),
        ("url2", "The quick brown fox jumps over the lazy dog"),  # Exact duplicate
        ("url3", "The quick brown fox leaps over the lazy dog"),  # Near duplicate
        ("url4", "A completely different document about cats"),
    ]

    for url, text in docs:
        is_dup, hash_val, minhash_sig = engine.process_document(text, url)
        print(f"{url}: duplicate={is_dup}, hash={hash_val[:16]}...")