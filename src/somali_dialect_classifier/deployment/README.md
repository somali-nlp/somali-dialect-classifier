# Dashboard Deployment Module

Automated deployment system for Somali NLP dashboard metrics.

## Overview

This module provides production-ready automation for deploying data pipeline metrics to GitHub Pages. It integrates seamlessly with the data collection orchestration system and follows DevOps best practices.

## Components

### 1. DashboardDeployer

Core deployment orchestrator that manages the entire deployment workflow.

**Features:**
- Environment validation
- Metrics file validation
- Git operations (stage, commit, push)
- Conventional Commits compliance
- Batch deployment mode
- Comprehensive error handling

### 2. MetricsValidator

Validates metrics files before deployment to ensure data quality.

**Validation Checks:**
- JSON structure validity
- Required fields presence
- Timestamp format correctness
- Data type validation

### 3. GitOperations

Handles all Git operations with proper error handling and safety checks.

**Operations:**
- Git availability check
- Repository detection
- Status retrieval
- File staging
- Committing changes
- Pushing to remote

### 4. DeploymentConfig

Configuration dataclass for deployment settings.

**Configurable Options:**
- Metrics directory path
- Git remote and branch
- Commit message prefix
- Auto-push behavior
- Validation settings
- Batch mode configuration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Pipelines                           │
│  (Wikipedia, BBC, HuggingFace, Språkbanken)                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Generate metrics
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              Metrics Files                                  │
│        data/metrics/*_processing.json                       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Trigger deployment
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              DashboardDeployer                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Validate Environment                              │  │
│  │    - Git available?                                  │  │
│  │    - In git repo?                                    │  │
│  │    - Remote configured?                              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 2. Validate Metrics                                  │  │
│  │    - JSON valid?                                     │  │
│  │    - Required fields present?                        │  │
│  │    - Timestamps correct?                             │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 3. Check Batch Requirements                          │  │
│  │    - Minimum sources met?                            │  │
│  │    - Ready to deploy?                                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 4. Generate Commit Message                           │  │
│  │    - Conventional Commits format                     │  │
│  │    - Include statistics                              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 5. Git Operations                                    │  │
│  │    - Stage metrics files                             │  │
│  │    - Commit with message                             │  │
│  │    - Push to remote                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Push triggers workflow
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Actions                                 │
│   (.github/workflows/deploy-dashboard-v2.yml)               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Rebuild dashboard
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Pages                                   │
│   https://somali-nlp.github.io/somali-dialect-classifier/  │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Programmatic Usage

```python
from pathlib import Path
from somali_dialect_classifier.deployment import (
    DashboardDeployer,
    DeploymentConfig,
    create_default_config,
)

# Use default configuration
config = create_default_config()

# Or create custom configuration
config = DeploymentConfig(
    metrics_dir=Path("data/metrics"),
    git_remote="origin",
    git_branch="main",
    commit_prefix="chore(metrics)",
    auto_push=True,
    validate_metrics=True,
    batch_mode=True,
    min_sources_for_deploy=2,
)

# Create deployer
deployer = DashboardDeployer(config)

# Execute deployment
success = deployer.deploy(dry_run=False)

if success:
    print("Deployment successful!")
else:
    print("Deployment failed or skipped")
```

### CLI Usage

```bash
# Basic deployment
somali-deploy-dashboard

# Dry run
somali-deploy-dashboard --dry-run

# Custom configuration
somali-deploy-dashboard \
    --metrics-dir ./custom/metrics \
    --git-branch develop \
    --min-sources 3 \
    --verbose
```

### Integration with Orchestration

```python
from somali_dialect_classifier.orchestration import run_all_pipelines

# Run pipelines with auto-deploy
result = run_all_pipelines(
    force=False,
    auto_deploy=True,
)
```

## Configuration

### Environment Variables

While the deployer auto-detects most settings, you can override them:

```bash
export SOMALI_METRICS_DIR="/path/to/metrics"
export SOMALI_GIT_REMOTE="origin"
export SOMALI_GIT_BRANCH="main"
```

### Batch Mode

Batch mode prevents premature deployments:

- **Enabled**: Waits until minimum source count is met
- **Disabled**: Deploys immediately after any pipeline

Example: Wait for at least 3 sources before deploying:

```python
config.batch_mode = True
config.min_sources_for_deploy = 3
```

## Error Handling

### Validation Errors

```python
from somali_dialect_classifier.deployment import MetricsValidator

# Validate all metrics
valid_files, invalid_files = MetricsValidator.validate_all_metrics(
    Path("data/metrics")
)

for file_path, error in invalid_files:
    print(f"{file_path.name}: {error}")
```

### Git Errors

```python
from somali_dialect_classifier.deployment import GitOperations

# Check git availability
if not GitOperations.check_git_available():
    print("Git not available!")

# Check repository status
status = GitOperations.get_repo_status(Path.cwd())
if not status["has_remote"]:
    print("No remote configured!")
```

### Deployment Errors

The deployer returns `False` on failure and logs detailed error information:

```python
deployer = DashboardDeployer(config)

success = deployer.deploy()
if not success:
    # Check logs for details
    # Deployment was skipped or failed
    pass
```

## Testing

Run the test suite:

```bash
pytest tests/test_dashboard_deployer.py -v
```

Test coverage includes:
- Metrics validation
- Git operations
- Configuration management
- Deployer functionality
- Commit message generation

## Best Practices

### 1. Always Validate First

```bash
somali-deploy-dashboard --dry-run --verbose
```

### 2. Use Batch Mode in Production

```python
config.batch_mode = True
config.min_sources_for_deploy = 4  # All sources
```

### 3. Enable Validation

```python
config.validate_metrics = True  # Always recommended
```

### 4. Monitor Deployment

```python
import logging

logging.basicConfig(level=logging.INFO)
deployer.deploy()
```

### 5. Handle Failures Gracefully

```python
try:
    success = deployer.deploy()
    if not success:
        # Send notification
        # Retry logic
        pass
except Exception as e:
    # Log error
    # Alert on-call
    pass
```

## Security Considerations

### Git Authentication

The deployer uses git's configured authentication:

- **SSH**: Recommended for automation
- **HTTPS**: Requires personal access token

Configure authentication outside this module:

```bash
# SSH
git remote set-url origin git@github.com:org/repo.git

# HTTPS with token
git remote set-url origin https://TOKEN@github.com/org/repo.git
```

### Secrets Management

- Never commit secrets in metrics files
- Metrics should contain only aggregated statistics
- Use environment variables for sensitive configuration

### Permissions

Required GitHub permissions:
- **Read**: Clone repository
- **Write**: Push commits
- **Actions**: Trigger workflows

## Performance

### Deployment Timing

- Validation: ~1-2 seconds (10 files)
- Git commit: ~2-5 seconds
- Git push: ~5-15 seconds (network dependent)
- Total: ~10-25 seconds

### Optimization

1. Use batch mode to reduce commit frequency
2. Run during off-peak hours
3. Keep metrics files compact
4. Use local commits during development (`auto_push=False`)

## Troubleshooting

### Common Issues

1. **"Git not available"**: Install git
2. **"Not in repo"**: Run from project root
3. **"No valid metrics"**: Run data pipelines first
4. **"Push failed"**: Check authentication and network
5. **"Batch waiting"**: Lower `min_sources_for_deploy`

### Debug Mode

Enable verbose logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Contributing

### Adding Features

1. Update `DashboardDeployer` class
2. Add tests to `test_dashboard_deployer.py`
3. Update documentation
4. Submit pull request

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings
- Include tests

### Testing

All changes must include tests:

```bash
pytest tests/test_dashboard_deployer.py -v --cov=deployment
```

## Version History

- **v1.0.0**: Initial release with full automation support

## License

MIT License - See project LICENSE file

## Support

- Documentation: `/docs/DASHBOARD_DEPLOYMENT.md`
- Issues: GitHub Issues
- Tests: `/tests/test_dashboard_deployer.py`
