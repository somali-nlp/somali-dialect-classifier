import logging
from pathlib import Path
from typing import Any, Optional

try:
    import mlflow
except ImportError:
    mlflow = None

logger = logging.getLogger(__name__)


class MLFlowTracker:
    """
    Wrapper for MLFlow tracking to standardize experiment logging.
    """

    def __init__(self, experiment_name: str = "somali_dialect_classifier"):
        self.experiment_name = experiment_name
        if mlflow is not None:
            mlflow.set_experiment(experiment_name)
        else:
            logger.warning("mlflow not installed; tracking disabled")

    def start_run(self, run_name: Optional[str] = None):
        """Start a new MLFlow run."""
        if mlflow is not None:
            return mlflow.start_run(run_name=run_name)
        return None

    def log_params(self, params: dict[str, Any]):
        """Log configuration parameters."""
        if mlflow is not None:
            mlflow.log_params(params)

    def log_param(self, key: str, value: Any):
        """Log a single configuration parameter."""
        if mlflow is not None:
            mlflow.log_param(key, value)

    def log_metrics(self, metrics: dict[str, float], step: Optional[int] = None):
        """Log operational metrics."""
        if mlflow is not None:
            mlflow.log_metrics(metrics, step=step)

    def log_metric(self, key: str, value: float, step: Optional[int] = None):
        """Log a single operational metric."""
        if mlflow is not None:
            mlflow.log_metric(key, value, step=step)

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        """Log a local file as an artifact."""
        if mlflow is not None:
            if Path(local_path).exists():
                mlflow.log_artifact(local_path, artifact_path)
            else:
                logger.warning(f"Artifact not found: {local_path}")

    def set_tags(self, tags: dict[str, Any]):
        """Log a batch of tags."""
        if mlflow is not None:
            mlflow.set_tags(tags)

    def set_tag(self, key: str, value: Any):
        """Log a single tag."""
        if mlflow is not None:
            mlflow.set_tag(key, value)

    def end_run(self, status: str = "FINISHED"):
        """End the current run."""
        if mlflow is not None:
            mlflow.end_run(status=status)
