"""MinHash and LSH primitives for near-duplicate detection."""

import json
import logging
import pickle
from pathlib import Path
from typing import Optional

try:
    from datasketch import MinHash, MinHashLSH

    DATASKETCH_AVAILABLE = True
except ImportError:
    DATASKETCH_AVAILABLE = False
    MinHash = None
    MinHashLSH = None


logger = logging.getLogger(__name__)


class ShardedLSH:
    """Sharded LSH index for faster near-duplicate lookups."""

    def __init__(self, num_shards: int = 10, threshold: float = 0.8, num_perm: int = 128):
        if not DATASKETCH_AVAILABLE:
            raise ImportError(
                "datasketch library is required for ShardedLSH. Install it with: pip install datasketch"
            )

        self.num_shards = num_shards
        self.threshold = threshold
        self.num_perm = num_perm
        self.shards = {
            i: MinHashLSH(threshold=threshold, num_perm=num_perm) for i in range(num_shards)
        }
        logger.info(f"Initialized ShardedLSH with {num_shards} shards")

    def _get_shard_id(self, key: str) -> int:
        return hash(key) % self.num_shards

    def insert(self, key: str, minhash: MinHash) -> None:
        shard_id = self._get_shard_id(key)
        self.shards[shard_id].insert(key, minhash)

    def query(self, minhash: MinHash) -> list[str]:
        results = []
        for shard in self.shards.values():
            results.extend(shard.query(minhash))
        return results

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        for shard_id, lsh in self.shards.items():
            shard_path = directory / f"lsh_shard_{shard_id:03d}.pkl"
            with open(shard_path, "wb") as handle:
                pickle.dump(lsh, handle)

        metadata_path = directory / "sharded_lsh_metadata.json"
        with open(metadata_path, "w") as handle:
            json.dump(
                {
                    "num_shards": self.num_shards,
                    "threshold": self.threshold,
                    "num_perm": self.num_perm,
                },
                handle,
            )

        logger.info(f"Saved {self.num_shards} LSH shards to {directory}")

    def load(self, directory: Path) -> bool:
        if not directory.exists():
            logger.warning(f"Shard directory does not exist: {directory}")
            return False

        metadata_path = directory / "sharded_lsh_metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as handle:
                metadata = json.load(handle)
                self.num_shards = metadata["num_shards"]
                self.threshold = metadata["threshold"]
                self.num_perm = metadata["num_perm"]

        loaded_count = 0
        for shard_id in range(self.num_shards):
            shard_path = directory / f"lsh_shard_{shard_id:03d}.pkl"
            if shard_path.exists():
                with open(shard_path, "rb") as handle:
                    self.shards[shard_id] = pickle.load(handle)
                    loaded_count += 1

        if loaded_count == self.num_shards:
            logger.info(f"Loaded {loaded_count} LSH shards from {directory}")
            return True

        logger.warning(f"Only loaded {loaded_count}/{self.num_shards} shards from {directory}")
        return False

    def get_shard_stats(self) -> dict[int, int]:
        stats = {}
        for shard_id, lsh in self.shards.items():
            try:
                stats[shard_id] = len(lsh.keys)
            except AttributeError:
                stats[shard_id] = 0
        return stats


class MinHashDeduplicator:
    """Near-duplicate detection using MinHash LSH."""

    def __init__(
        self,
        num_permutations: int = 128,
        shingle_size: int = 3,
        similarity_threshold: float = 0.85,
        seed: int = 42,
        storage_path: Optional[Path] = None,
        enable_sharding: bool = True,
        num_shards: int = 10,
    ):
        if not DATASKETCH_AVAILABLE:
            raise ImportError(
                "datasketch library is required for MinHash deduplication. Install it with: pip install datasketch"
            )

        self.num_permutations = num_permutations
        self.shingle_size = shingle_size
        self.similarity_threshold = similarity_threshold
        self.seed = seed
        self.storage_path = storage_path
        self.enable_sharding = enable_sharding
        self.num_shards = num_shards

        if enable_sharding and num_shards > 1:
            self.lsh = ShardedLSH(
                num_shards=num_shards,
                threshold=similarity_threshold,
                num_perm=num_permutations,
            )
            self.is_sharded = True
            logger.info(f"Using ShardedLSH with {num_shards} shards for 2-3x performance")
        else:
            self.lsh = MinHashLSH(threshold=similarity_threshold, num_perm=num_permutations)
            self.is_sharded = False
            logger.info("Using monolithic LSH index")

        # signature -> url mapping. Content-keyed so callers can safely reuse
        # URLs across documents (e.g., Sprakbanken corpus URLs that span many
        # texts). LSH itself is also keyed by signature; see add_document().
        self.document_hashes: dict[str, str] = {}
        if storage_path and storage_path.exists():
            self._load_lsh_index()

    def _create_shingles(self, text: str) -> set[str]:
        words = text.lower().split()
        shingles = set()
        for index in range(len(words) - self.shingle_size + 1):
            shingles.add(" ".join(words[index : index + self.shingle_size]))
        return shingles

    def compute_minhash(self, text: str) -> MinHash:
        shingles = self._create_shingles(text)
        minhash = MinHash(num_perm=self.num_permutations, seed=self.seed)
        for shingle in shingles:
            minhash.update(shingle.encode("utf-8"))
        return minhash

    def compute_signature(self, text: str) -> str:
        minhash = self.compute_minhash(text)
        return ",".join(str(value) for value in minhash.hashvalues)

    def signature_from_string(self, signature_str: str) -> MinHash:
        hashvalues = [int(value) for value in signature_str.split(",")]
        minhash = MinHash(num_perm=self.num_permutations, seed=self.seed)
        minhash.hashvalues = tuple(hashvalues)
        return minhash

    def add_document(self, url: str, text: str) -> str:
        minhash = self.compute_minhash(text)
        signature = ",".join(str(value) for value in minhash.hashvalues)

        # Index by signature, not URL: MinHash signatures are content-derived
        # and unique per text, so callers can reuse URLs (Sprakbanken corpus
        # URLs map to many texts) without colliding inside datasketch's LSH.
        if signature in self.document_hashes:
            return signature

        self.lsh.insert(signature, minhash)
        self.document_hashes[signature] = url
        return signature

    def find_similar(self, text: str, threshold: Optional[float] = None) -> list[tuple[str, float]]:
        threshold = self.similarity_threshold if threshold is None else threshold
        query_minhash = self.compute_minhash(text)
        similar_signatures = self.lsh.query(query_minhash)

        results = []
        for signature in similar_signatures:
            url = self.document_hashes.get(signature)
            if url is None:
                continue
            doc_minhash = self.signature_from_string(signature)
            similarity = query_minhash.jaccard(doc_minhash)
            if similarity >= threshold:
                results.append((url, similarity))

        results.sort(key=lambda item: item[1], reverse=True)
        return results

    def is_duplicate(
        self, text: str, threshold: Optional[float] = None
    ) -> Optional[tuple[str, float]]:
        similar = self.find_similar(text, threshold)
        if similar:
            return similar[0]
        return None

    def _save_lsh_index(self) -> None:
        if not self.storage_path:
            logger.warning("No storage_path configured, skipping LSH index save")
            return

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            if self.is_sharded:
                shard_dir = self.storage_path.parent / f"{self.storage_path.stem}_shards"
                self.lsh.save(shard_dir)
                metadata = {
                    "is_sharded": True,
                    "num_shards": self.num_shards,
                    "document_hashes": self.document_hashes,
                    "num_permutations": self.num_permutations,
                    "shingle_size": self.shingle_size,
                    "similarity_threshold": self.similarity_threshold,
                    "seed": self.seed,
                    "shard_dir": str(shard_dir),
                }
                with open(self.storage_path, "wb") as handle:
                    pickle.dump(metadata, handle)
                logger.info(
                    f"Saved ShardedLSH index to {shard_dir} ({len(self.document_hashes)} documents)"
                )
            else:
                index_data = {
                    "is_sharded": False,
                    "lsh": self.lsh,
                    "document_hashes": self.document_hashes,
                    "num_permutations": self.num_permutations,
                    "shingle_size": self.shingle_size,
                    "similarity_threshold": self.similarity_threshold,
                    "seed": self.seed,
                }
                with open(self.storage_path, "wb") as handle:
                    pickle.dump(index_data, handle)
                logger.info(
                    f"Saved LSH index to {self.storage_path} ({len(self.document_hashes)} documents)"
                )
        except Exception as err:
            logger.error(f"Failed to save LSH index: {err}")

    def _load_lsh_index(self) -> bool:
        if not self.storage_path or not self.storage_path.exists():
            logger.debug("No LSH index found at storage path")
            return False

        try:
            with open(self.storage_path, "rb") as handle:
                index_data = pickle.load(handle)

            if index_data.get("is_sharded", False):
                shard_dir = Path(index_data["shard_dir"])
                self.num_shards = index_data["num_shards"]
                self.is_sharded = True
                self.lsh = ShardedLSH(
                    num_shards=self.num_shards,
                    threshold=index_data["similarity_threshold"],
                    num_perm=index_data["num_permutations"],
                )
                if not self.lsh.load(shard_dir):
                    logger.warning("Failed to load all shards")
                    return False

                self.document_hashes = index_data["document_hashes"]
                self.num_permutations = index_data["num_permutations"]
                self.shingle_size = index_data["shingle_size"]
                self.similarity_threshold = index_data["similarity_threshold"]
                self.seed = index_data["seed"]
                logger.info(
                    f"Loaded ShardedLSH index from {shard_dir} ({len(self.document_hashes)} documents)"
                )
                return True

            self.lsh = index_data["lsh"]
            self.document_hashes = index_data["document_hashes"]
            self.num_permutations = index_data["num_permutations"]
            self.shingle_size = index_data["shingle_size"]
            self.similarity_threshold = index_data["similarity_threshold"]
            self.seed = index_data["seed"]
            self.is_sharded = False
            logger.info(
                f"Loaded LSH index from {self.storage_path} ({len(self.document_hashes)} documents)"
            )
            return True
        except Exception as err:
            logger.warning(f"Failed to load LSH index: {err}")
            return False

    def save(self) -> None:
        self._save_lsh_index()
