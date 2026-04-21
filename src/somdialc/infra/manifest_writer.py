"""
Manifest generation for tracking daily ingestion runs.

Provides structured JSON manifests with:
- Run metadata (run_id, timestamp, version)
- Per-source ingestion stats (records, partitions, quota status)
- Aggregate totals across all sources
- Schema validation
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ManifestWriter:
    """
    Writer for daily ingestion manifests.

    Generates JSON files tracking what data was ingested during each orchestrated run.
    Enables observability, debugging, and dashboard integration.

    Manifest Schema:
        {
          "manifest_version": "1.0",
          "run_id": "run_20251113_143022_abc123",
          "timestamp": "2025-11-13T14:30:22Z",
          "orchestrator_version": "1.1.0",
          "sources": {
            "wikipedia": {
              "status": "completed",
              "records_ingested": 1234,
              "records_skipped": 8726,
              "partitions": ["2025-11-13"],
              "quota_hit": false,
              "processing_time_seconds": 45.2
            },
            "bbc": {
              "status": "quota_reached",
              "records_ingested": 350,
              "records_skipped": 0,
              "partitions": ["2025-11-13"],
              "quota_hit": true,
              "quota_limit": 350,
              "items_remaining": 127,
              "processing_time_seconds": 180.5
            }
          },
          "totals": {
            "total_records": 1584,
            "total_partitions": 1,
            "total_processing_time_seconds": 225.7,
            "sources_with_quota_hit": ["bbc"]
          }
        }
    """

    MANIFEST_VERSION = "1.0"
    ORCHESTRATOR_VERSION = "1.1.0"

    def __init__(self, manifest_dir: Path = Path("data/manifests")):
        """
        Initialize manifest writer.

        Args:
            manifest_dir: Directory to write manifest files (default: data/manifests)
        """
        self.manifest_dir = manifest_dir
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

    def create_manifest(
        self,
        run_id: str,
        sources: dict[str, dict[str, Any]],
        timestamp: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Create manifest dictionary from run results.

        Args:
            run_id: Unique run identifier
            sources: Dictionary mapping source names to their ingestion results
            timestamp: Run timestamp (None = now UTC)

        Returns:
            Manifest dictionary

        Example:
            >>> writer = ManifestWriter()
            >>> sources = {
            ...     "wikipedia": {
            ...         "status": "completed",
            ...         "records_ingested": 1234,
            ...         "records_skipped": 8726,
            ...         "partitions": ["2025-11-13"],
            ...         "quota_hit": False,
            ...         "processing_time_seconds": 45.2
            ...     }
            ... }
            >>> manifest = writer.create_manifest("run_20251113_143022", sources)
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Calculate totals
        total_records = sum(s.get("records_ingested", 0) for s in sources.values())
        total_partitions = len(
            {partition for source in sources.values() for partition in source.get("partitions", [])}
        )
        total_processing_time = sum(s.get("processing_time_seconds", 0) for s in sources.values())
        sources_with_quota_hit = [
            name for name, source in sources.items() if source.get("quota_hit", False)
        ]

        manifest = {
            "manifest_version": self.MANIFEST_VERSION,
            "run_id": run_id,
            "timestamp": timestamp.isoformat(),
            "orchestrator_version": self.ORCHESTRATOR_VERSION,
            "sources": sources,
            "totals": {
                "total_records": total_records,
                "total_partitions": total_partitions,
                "total_processing_time_seconds": round(total_processing_time, 2),
                "sources_with_quota_hit": sources_with_quota_hit,
            },
        }

        # Validate schema before returning
        self._validate_manifest(manifest)

        return manifest

    def write_manifest(
        self,
        manifest: dict[str, Any],
        filename: Optional[str] = None,
    ) -> Path:
        """
        Write manifest to file.

        Args:
            manifest: Manifest dictionary
            filename: Optional custom filename (None = use run_id.json)

        Returns:
            Path to written manifest file

        Example:
            >>> writer = ManifestWriter()
            >>> manifest = {...}  # From create_manifest()
            >>> path = writer.write_manifest(manifest)
            >>> print(f"Wrote manifest to {path}")
        """
        # Validate before writing
        self._validate_manifest(manifest)

        # Generate filename from run_id if not provided
        if filename is None:
            run_id = manifest["run_id"]
            filename = f"{run_id}.json"

        manifest_path = self.manifest_dir / filename

        # Write with pretty JSON formatting for human readability
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=False)

        logger.info(f"Wrote manifest: {manifest_path}")

        return manifest_path

    def read_manifest(self, filename: str) -> dict[str, Any]:
        """
        Read manifest from file.

        Args:
            filename: Manifest filename (e.g., "run_20251113_143022.json")

        Returns:
            Manifest dictionary

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            ValueError: If manifest schema is invalid

        Example:
            >>> writer = ManifestWriter()
            >>> manifest = writer.read_manifest("run_20251113_143022.json")
            >>> print(f"Run ingested {manifest['totals']['total_records']} records")
        """
        manifest_path = self.manifest_dir / filename

        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        # Validate schema
        self._validate_manifest(manifest)

        return manifest

    def list_manifests(
        self,
        limit: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Path]:
        """
        List manifest files in the manifest directory.

        Args:
            limit: Maximum number of manifests to return (None = all)
            start_date: Filter manifests after this date (inclusive)
            end_date: Filter manifests before this date (inclusive)

        Returns:
            List of manifest file paths, sorted by modification time (newest first)

        Example:
            >>> writer = ManifestWriter()
            >>> recent = writer.list_manifests(limit=10)
            >>> for manifest_path in recent:
            ...     manifest = writer.read_manifest(manifest_path.name)
            ...     print(f"{manifest['run_id']}: {manifest['totals']['total_records']} records")
        """
        manifests = list(self.manifest_dir.glob("*.json"))

        # Filter by date if provided
        if start_date or end_date:
            filtered = []
            for manifest_path in manifests:
                # Read manifest to get timestamp
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                    timestamp = datetime.fromisoformat(manifest["timestamp"].replace("Z", "+00:00"))

                # Apply filters
                if start_date and timestamp < start_date:
                    continue
                if end_date and timestamp > end_date:
                    continue

                filtered.append(manifest_path)

            manifests = filtered

        # Sort by modification time (newest first)
        manifests.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Apply limit
        if limit:
            manifests = manifests[:limit]

        return manifests

    def cleanup_old_manifests(self, keep_days: int = 90) -> int:
        """
        Remove manifest files older than keep_days.

        Args:
            keep_days: Number of days to retain manifests (default: 90)

        Returns:
            Number of manifests deleted

        Example:
            >>> writer = ManifestWriter()
            >>> deleted = writer.cleanup_old_manifests(keep_days=90)
            >>> print(f"Deleted {deleted} old manifests")
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
        deleted = 0

        for manifest_path in self.manifest_dir.glob("*.json"):
            # Read manifest to get timestamp
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                    timestamp = datetime.fromisoformat(manifest["timestamp"].replace("Z", "+00:00"))

                if timestamp < cutoff:
                    manifest_path.unlink()
                    deleted += 1
                    logger.info(f"Deleted old manifest: {manifest_path.name}")

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse manifest {manifest_path}: {e}")
                # Optionally delete corrupted manifests
                # manifest_path.unlink()
                # deleted += 1

        logger.info(f"Cleanup complete: deleted {deleted} manifests older than {keep_days} days")

        return deleted

    def _validate_manifest(self, manifest: dict[str, Any]) -> None:
        """
        Validate manifest schema.

        Args:
            manifest: Manifest dictionary to validate

        Raises:
            ValueError: If manifest schema is invalid
        """
        required_top_level = ["manifest_version", "run_id", "timestamp", "sources", "totals"]
        for field in required_top_level:
            if field not in manifest:
                raise ValueError(f"Missing required field in manifest: {field}")

        # Validate sources structure
        if not isinstance(manifest["sources"], dict):
            raise ValueError("Manifest 'sources' must be a dictionary")

        for source_name, source_data in manifest["sources"].items():
            required_source_fields = ["status", "records_ingested"]
            for field in required_source_fields:
                if field not in source_data:
                    raise ValueError(f"Missing required field '{field}' for source '{source_name}'")

        # Validate totals structure
        required_totals = ["total_records", "total_partitions", "total_processing_time_seconds"]
        for field in required_totals:
            if field not in manifest["totals"]:
                raise ValueError(f"Missing required field in totals: {field}")

    def get_manifest_for_run(self, run_id: str) -> Optional[dict[str, Any]]:
        """
        Get manifest for a specific run_id.

        Args:
            run_id: Run identifier

        Returns:
            Manifest dictionary or None if not found

        Example:
            >>> writer = ManifestWriter()
            >>> manifest = writer.get_manifest_for_run("run_20251113_143022")
            >>> if manifest:
            ...     print(f"Found manifest for {run_id}")
        """
        filename = f"{run_id}.json"
        manifest_path = self.manifest_dir / filename

        if not manifest_path.exists():
            return None

        return self.read_manifest(filename)

    def get_sources_with_quota_hits(self, days: int = 7) -> dict[str, int]:
        """
        Analyze quota hits across recent manifests.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            Dictionary mapping source names to number of quota hits

        Example:
            >>> writer = ManifestWriter()
            >>> quota_hits = writer.get_sources_with_quota_hits(days=7)
            >>> for source, hit_count in quota_hits.items():
            ...     print(f"{source}: {hit_count} quota hits in last 7 days")
        """
        from collections import defaultdict
        from datetime import timedelta

        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        manifests = self.list_manifests(start_date=start_date)

        quota_hits = defaultdict(int)

        for manifest_path in manifests:
            try:
                manifest = self.read_manifest(manifest_path.name)

                # Count quota hits per source
                for source_name, source_data in manifest["sources"].items():
                    if source_data.get("quota_hit", False):
                        quota_hits[source_name] += 1

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse manifest {manifest_path.name}: {e}")

        return dict(quota_hits)
