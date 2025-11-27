# MLFlow Experiment Tracking

**Comprehensive guide to experiment tracking, metric logging, and run management using MLFlow.**

**Last Updated:** 2025-11-21

## Table of Contents
- [Overview](#overview)
- [Usage](#usage)
- [Configuration](#configuration)
- [Programmatic Usage](#programmatic-usage)
- [Integration with BasePipeline](#integration-with-basepipeline)

---

## Overview

The Somali Dialect Classifier uses [MLFlow](https://mlflow.org/) for experiment tracking, metric logging, and run management. This ensures that every data ingestion and processing run is reproducible and its metrics are captured systematically.

### What is Tracked?

-   **Context Tags**:
    -   `git_commit`: Code version hash.
    -   `config_hash`: Configuration state hash.
    -   `hostname`, `os`, `python_version`: Execution environment details.
    -   `status`: Run outcome (`success` or `failed`).
-   **Parameters**: Configuration settings (e.g., `max_articles`, `batch_size`, `model_name`).
-   **Headline Metrics**: Key indicators logged directly to MLflow:
    -   `quality_pass_rate`
    -   `records_processed`
    -   `records_written`
    -   `records_filtered`
-   **Artifacts**: Output files (e.g., `manifest.json`, `metrics.json` with detailed stats).

## Usage

### Automatic Logging

When you run a pipeline via the CLI or Orchestrator, MLFlow tracking is active by default.

```bash
# Run a pipeline
somali-orchestrate --pipeline wikipedia
```

This will:
1.  Start a new MLFlow run.
2.  Log parameters from the configuration.
3.  Log metrics during execution.
4.  End the run upon completion (or failure).

### Viewing the UI

To view the MLFlow UI and explore your runs:

```bash
mlflow ui
```

Then navigate to `http://127.0.0.1:5000` in your browser.

## Programmatic Usage

If you are extending the pipeline or adding custom tracking, you can use the `MLFlowTracker` class directly.

```python
from somali_dialect_classifier.infra.tracking import MLFlowTracker

tracker = MLFlowTracker(experiment_name="my_experiment")

with tracker.start_run(run_name="custom_run"):
    tracker.log_param("my_param", 10)
    # ... do work ...
    tracker.log_metric("accuracy", 0.95)
```

## Configuration

MLFlow stores data in `./mlruns` by default. You can configure the tracking URI via environment variables if needed (e.g., for a remote server).

```bash
export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
```

## Integration with BasePipeline

The `BasePipeline` handles tracking automatically:

1.  **Initialization**: Sets up `self.mlflow` and gathers system context (git commit, config hash).
2.  **Execution**: Wraps `process()` in a `try...finally` block.
    -   **Success**: Logs `status="success"`.
    -   **Failure**: Logs `status="failed"` with error details.
3.  **Metrics**: Automatically logs headline metrics (`quality_pass_rate`, etc.) at the end of the run.

```python
class MyPipeline(BasePipeline):
    def process(self):
        # ... standard processing ...
        # BasePipeline handles start_run(), context logging, and end_run()
        pass
```

---

**Related Documentation:**
- [Data Pipeline Guide](data-pipeline.md) - Overview of data collection
- [Orchestration](../howto/orchestration.md) - Pipeline coordination
- [Configuration](../howto/configuration.md) - Environment setup

**Maintainers:** Somali NLP Contributors

---

## Related Documentation

- [Project Documentation](../index.md) - Main documentation index

**Maintainers**: Somali NLP Contributors
