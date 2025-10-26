"""
Dashboard deployment automation for Somali NLP project.

Handles automatic deployment of metrics to GitHub Pages dashboard after
data ingestion pipeline completes. Includes validation, batching, and
error handling.
"""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """Configuration for dashboard deployment."""

    metrics_dir: Path
    git_remote: str = "origin"
    git_branch: str = "main"
    commit_prefix: str = "chore(metrics)"
    auto_push: bool = True
    validate_metrics: bool = True
    batch_mode: bool = True
    min_sources_for_deploy: int = 1


class MetricsValidator:
    """Validates metrics files before deployment."""

    REQUIRED_SNAPSHOT_FIELDS = ["run_id", "source", "timestamp"]

    @staticmethod
    def extract_metrics_data(data: dict) -> Tuple[dict, dict]:
        """
        Extract snapshot and statistics from metrics file, supporting both
        v3.0 (nested) and legacy (top-level) schemas.

        Args:
            data: Parsed metrics JSON

        Returns:
            Tuple of (snapshot, statistics)
        """
        # Check for v3.0 schema with legacy_metrics wrapper
        if "_schema_version" in data and data.get("_schema_version") == "3.0":
            legacy_metrics = data.get("legacy_metrics", {})
            snapshot = legacy_metrics.get("snapshot", {})
            statistics = legacy_metrics.get("statistics", {})
        else:
            # Legacy schema with top-level fields
            snapshot = data.get("snapshot", {})
            statistics = data.get("statistics", {})

        return snapshot, statistics

    @staticmethod
    def validate_metrics_file(file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate a single metrics JSON file.

        Args:
            file_path: Path to metrics file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(file_path) as f:
                data = json.load(f)

            # Extract snapshot and statistics (handles both v3.0 and legacy)
            snapshot, statistics = MetricsValidator.extract_metrics_data(data)

            # Check snapshot exists and has required fields
            if not snapshot:
                return False, "Missing required field: snapshot"

            for field in MetricsValidator.REQUIRED_SNAPSHOT_FIELDS:
                if field not in snapshot:
                    return False, f"Missing snapshot field: {field}"

            # Validate timestamp format
            timestamp = snapshot.get("timestamp", "")
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return False, f"Invalid timestamp format: {timestamp}"

            # Check for reasonable data values
            if not statistics:
                return False, "Missing required field: statistics"
            if not isinstance(statistics, dict):
                return False, "Statistics must be a dictionary"

            return True, None

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"

    @staticmethod
    def validate_all_metrics(metrics_dir: Path) -> Tuple[List[Path], List[Tuple[Path, str]]]:
        """
        Validate all metrics files in directory.

        Args:
            metrics_dir: Directory containing metrics files

        Returns:
            Tuple of (valid_files, invalid_files_with_errors)
        """
        valid_files = []
        invalid_files = []

        if not metrics_dir.exists():
            logger.warning(f"Metrics directory does not exist: {metrics_dir}")
            return valid_files, invalid_files

        for metrics_file in metrics_dir.glob("*_processing.json"):
            is_valid, error = MetricsValidator.validate_metrics_file(metrics_file)
            if is_valid:
                valid_files.append(metrics_file)
            else:
                invalid_files.append((metrics_file, error))
                logger.warning(f"Invalid metrics file {metrics_file.name}: {error}")

        return valid_files, invalid_files


class GitOperations:
    """Handles Git operations for dashboard deployment."""

    @staticmethod
    def check_git_available() -> bool:
        """Check if git is available in PATH."""
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def is_git_repo(repo_path: Path) -> bool:
        """Check if directory is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=repo_path,
                capture_output=True,
                check=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def get_repo_status(repo_path: Path) -> Dict[str, any]:
        """
        Get current repository status.

        Returns:
            Dictionary with status information
        """
        try:
            # Check for uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                check=True,
                text=True,
                timeout=10,
            )

            # Check current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                check=True,
                text=True,
                timeout=5,
            )

            # Check if remote exists
            remote_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )

            return {
                "has_changes": bool(status_result.stdout.strip()),
                "current_branch": branch_result.stdout.strip(),
                "has_remote": remote_result.returncode == 0,
                "remote_url": remote_result.stdout.strip() if remote_result.returncode == 0 else None,
            }
        except Exception as e:
            logger.error(f"Failed to get repo status: {e}")
            return {
                "has_changes": False,
                "current_branch": "unknown",
                "has_remote": False,
                "remote_url": None,
            }

    @staticmethod
    def stage_files(repo_path: Path, file_patterns: List[str]) -> bool:
        """
        Stage files matching patterns.

        Args:
            repo_path: Repository root path
            file_patterns: List of file patterns to stage

        Returns:
            True if successful
        """
        try:
            for pattern in file_patterns:
                subprocess.run(
                    ["git", "add", pattern],
                    cwd=repo_path,
                    capture_output=True,
                    check=True,
                    timeout=10,
                )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stage files: {e.stderr.decode()}")
            return False

    @staticmethod
    def commit_changes(repo_path: Path, message: str) -> bool:
        """
        Commit staged changes.

        Args:
            repo_path: Repository root path
            message: Commit message

        Returns:
            True if successful
        """
        try:
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_path,
                capture_output=True,
                check=True,
                text=True,
                timeout=30,
            )
            return True
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else e.stdout
            logger.error(f"Failed to commit changes: {error_msg}")
            return False

    @staticmethod
    def push_changes(repo_path: Path, remote: str = "origin", branch: str = "main") -> bool:
        """
        Push changes to remote repository.

        Args:
            repo_path: Repository root path
            remote: Remote name
            branch: Branch name

        Returns:
            True if successful
        """
        try:
            result = subprocess.run(
                ["git", "push", remote, branch],
                cwd=repo_path,
                capture_output=True,
                check=True,
                text=True,
                timeout=60,
            )
            logger.info(f"Successfully pushed to {remote}/{branch}")
            return True
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else e.stdout
            logger.error(f"Failed to push changes: {error_msg}")
            return False


class DashboardDeployer:
    """Main deployment orchestrator for dashboard metrics."""

    def __init__(self, config: DeploymentConfig):
        """
        Initialize deployer with configuration.

        Args:
            config: Deployment configuration
        """
        self.config = config
        self.repo_path = self._find_repo_root()

    def _find_repo_root(self) -> Path:
        """Find the git repository root from metrics directory."""
        current = self.config.metrics_dir.resolve()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        raise RuntimeError(f"Not in a git repository: {self.config.metrics_dir}")

    def _get_metrics_summary(self, metrics_files: List[Path]) -> Dict[str, any]:
        """
        Generate summary of metrics being deployed.

        Args:
            metrics_files: List of valid metrics files

        Returns:
            Summary dictionary
        """
        sources = set()
        total_records = 0
        timestamps = []

        for file_path in metrics_files:
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    # Use helper to extract snapshot (handles both v3.0 and legacy)
                    snapshot, _ = MetricsValidator.extract_metrics_data(data)
                    sources.add(snapshot.get("source", "unknown"))
                    total_records += snapshot.get("records_written", 0)
                    timestamps.append(snapshot.get("timestamp", ""))
            except Exception as e:
                logger.warning(f"Failed to read {file_path.name}: {e}")

        return {
            "sources": sorted(list(sources)),
            "source_count": len(sources),
            "total_records": total_records,
            "file_count": len(metrics_files),
            "latest_timestamp": max(timestamps) if timestamps else None,
        }

    def _generate_commit_message(self, summary: Dict[str, any]) -> str:
        """
        Generate Conventional Commits compliant commit message.

        Args:
            summary: Metrics summary dictionary

        Returns:
            Formatted commit message
        """
        sources = summary["sources"]
        source_count = summary["source_count"]
        file_count = summary["file_count"]
        total_records = summary["total_records"]

        # Generate concise source description
        if source_count == 1:
            source_desc = sources[0]
        elif source_count <= 3:
            source_desc = ", ".join(sources)
        else:
            source_desc = f"{source_count} sources"

        # Main commit message
        title = f"{self.config.commit_prefix}: update metrics for {source_desc}"

        # Detailed body
        body_lines = [
            "",
            f"Updated {file_count} metrics file(s) from {source_count} data source(s).",
            f"Total records processed: {total_records:,}",
            "",
            "Sources:",
        ]

        for source in sources:
            body_lines.append(f"  - {source}")

        body_lines.extend([
            "",
            "This update triggers automatic dashboard deployment via GitHub Actions.",
        ])

        return "\n".join([title] + body_lines)

    def validate_environment(self) -> Tuple[bool, List[str]]:
        """
        Validate deployment environment prerequisites.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check git availability
        if not GitOperations.check_git_available():
            errors.append("Git is not available in PATH")

        # Check if in git repo
        if not GitOperations.is_git_repo(self.repo_path):
            errors.append(f"Not a git repository: {self.repo_path}")

        # Check metrics directory
        if not self.config.metrics_dir.exists():
            errors.append(f"Metrics directory does not exist: {self.config.metrics_dir}")

        # Check repository status
        if not errors:
            status = GitOperations.get_repo_status(self.repo_path)
            if not status["has_remote"]:
                errors.append(f"No remote repository configured for '{self.config.git_remote}'")

        return len(errors) == 0, errors

    def deploy(self, dry_run: bool = False) -> bool:
        """
        Execute deployment workflow.

        Args:
            dry_run: If True, validate but don't commit/push

        Returns:
            True if successful
        """
        logger.info("=" * 80)
        logger.info("DASHBOARD DEPLOYMENT STARTING")
        logger.info("=" * 80)

        # Step 1: Validate environment
        logger.info("Validating deployment environment...")
        is_valid, errors = self.validate_environment()
        if not is_valid:
            logger.error("Environment validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        # Step 2: Validate metrics files
        if self.config.validate_metrics:
            logger.info("Validating metrics files...")
            valid_files, invalid_files = MetricsValidator.validate_all_metrics(
                self.config.metrics_dir
            )

            if invalid_files:
                logger.warning(f"Found {len(invalid_files)} invalid metrics files:")
                for file_path, error in invalid_files:
                    logger.warning(f"  - {file_path.name}: {error}")

            if not valid_files:
                logger.error("No valid metrics files found to deploy")
                return False

            logger.info(f"Validated {len(valid_files)} metrics files")
        else:
            valid_files = list(self.config.metrics_dir.glob("*_processing.json"))

        # Step 3: Check minimum sources requirement
        summary = self._get_metrics_summary(valid_files)
        if self.config.batch_mode and summary["source_count"] < self.config.min_sources_for_deploy:
            logger.info(
                f"Batch mode: waiting for more sources "
                f"({summary['source_count']}/{self.config.min_sources_for_deploy})"
            )
            return False

        # Step 4: Check git status
        status = GitOperations.get_repo_status(self.repo_path)
        logger.info(f"Current branch: {status['current_branch']}")

        if status["current_branch"] != self.config.git_branch:
            logger.warning(
                f"Current branch '{status['current_branch']}' does not match "
                f"target branch '{self.config.git_branch}'"
            )

        # Step 5: Generate commit message
        commit_message = self._generate_commit_message(summary)
        logger.info("Generated commit message:")
        for line in commit_message.split("\n"):
            logger.info(f"  {line}")

        if dry_run:
            logger.info("=" * 80)
            logger.info("DRY RUN - No changes will be committed")
            logger.info("=" * 80)
            logger.info(f"Would deploy {len(valid_files)} metrics files")
            logger.info(f"Sources: {', '.join(summary['sources'])}")
            return True

        # Step 6: Stage metrics files
        logger.info("Staging metrics files...")
        metrics_pattern = str(self.config.metrics_dir / "*_processing.json")
        if not GitOperations.stage_files(self.repo_path, [metrics_pattern]):
            logger.error("Failed to stage metrics files")
            return False

        # Step 7: Commit changes
        logger.info("Committing changes...")
        if not GitOperations.commit_changes(self.repo_path, commit_message):
            logger.error("Failed to commit changes")
            return False

        # Step 8: Push to remote
        if self.config.auto_push:
            logger.info(f"Pushing to {self.config.git_remote}/{self.config.git_branch}...")
            if not GitOperations.push_changes(
                self.repo_path,
                self.config.git_remote,
                self.config.git_branch,
            ):
                logger.error("Failed to push changes")
                logger.warning(
                    "Changes committed locally but not pushed. "
                    "You may need to push manually."
                )
                return False
        else:
            logger.info("Auto-push disabled. Changes committed locally only.")

        logger.info("=" * 80)
        logger.info("DASHBOARD DEPLOYMENT SUCCESSFUL")
        logger.info("=" * 80)
        logger.info(f"Deployed {len(valid_files)} metrics files")
        logger.info(f"Sources: {', '.join(summary['sources'])}")
        logger.info(f"Total records: {summary['total_records']:,}")
        logger.info("")
        logger.info("GitHub Actions will now rebuild the dashboard automatically.")
        logger.info("Monitor deployment at: https://github.com/somali-nlp/somali-dialect-classifier/actions")

        return True


def create_default_config(project_root: Optional[Path] = None) -> DeploymentConfig:
    """
    Create default deployment configuration.

    Args:
        project_root: Project root directory (auto-detected if None)

    Returns:
        DeploymentConfig instance
    """
    if project_root is None:
        # Try to find project root from current file location
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent

    metrics_dir = project_root / "data" / "metrics"

    return DeploymentConfig(
        metrics_dir=metrics_dir,
        git_remote="origin",
        git_branch="main",
        commit_prefix="chore(metrics)",
        auto_push=True,
        validate_metrics=True,
        batch_mode=True,
        min_sources_for_deploy=1,
    )
