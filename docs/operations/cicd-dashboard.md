# CI/CD Dashboard Automation

**Comprehensive guide for automated dashboard build, validation, testing, and deployment pipeline.**

**Last Updated:** 2025-11-21

Comprehensive guide for the automated dashboard build, validation, testing, and deployment pipeline.

## Table of Contents

- [Overview](#overview)
- [Workflows](#workflows)
- [Setup Instructions](#setup-instructions)
- [Manual Operations](#manual-operations)
- [Troubleshooting](#troubleshooting)
- [Monitoring and Alerts](#monitoring-and-alerts)

## Overview

The dashboard CI/CD pipeline automates the complete lifecycle of metrics data generation, validation, testing, and deployment. It ensures data quality, visual consistency, and deployment reliability.

### Architecture

```
┌─────────────────┐
│ Metrics Files   │
│ (data/metrics/) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Dashboard Metrics       │
│ Regeneration Workflow   │
│ • Parse processing.json │
│ • Generate aggregated   │
│ • Commit & push         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Validation Pipeline     │
│ • Schema validation     │
│ • Quality checks        │
│ • Freshness checks      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ CI Testing              │
│ • Unit tests (pytest)   │
│ • Visual tests          │
│   (Playwright)          │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Deploy to GitHub Pages  │
│ • Build _site/          │
│ • Deploy artifact       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Health Check            │
│ • Accessibility         │
│ • Performance           │
│ • Data freshness        │
└─────────────────────────┘
```

## Workflows

### 1. Dashboard Metrics Regeneration

**File**: `.github/workflows/dashboard-metrics.yml`

**Trigger**:
- On push to `main` when `data/metrics/**/*_processing.json` changes
- Manual trigger via `workflow_dispatch`

**Purpose**: Automatically regenerates `_site/data/all_metrics.json` and `_site/data/summary.json` when new metrics are added.

**Steps**:
1. Parse all `*_processing.json` files from `data/metrics/`
2. Extract pipeline-specific metrics based on pipeline type
3. Aggregate data into `all_metrics.json`
4. Generate summary statistics in `summary.json`
5. Commit and push changes if data has changed

**Caching**: Uses pip cache for faster dependency installation

**Outputs**:
- `metrics_generated`: true/false
- `total_runs`: Number of pipeline runs
- `total_records`: Total records processed

### 2. Dashboard Validation Pipeline

**File**: `.github/workflows/dashboard-validation.yml`

**Trigger**:
- On pull requests affecting metrics or dashboard files
- On push to `main` affecting metrics
- Manual trigger

**Purpose**: Validates metrics data quality and schema compliance

**Validation Checks**:

#### Schema Validation
- Validates JSON structure against `schemas/metrics_schema.json`
- Ensures all required fields are present
- Checks data types and value ranges

#### Quality Checks
- **Success Rates**: Flags runs with low success rates
  - Web scraping: HTTP success rate < 50%
  - File processing: Extraction rate < 50%
  - Stream processing: Retrieval rate < 50%
- **Text Quality**: Warns if mean text length < 50 characters
- **Zero Records**: Flags runs that wrote no records

#### Freshness Checks
- Warns if metrics are older than 30 days
- Reports age of newest and oldest metrics

#### Test Generation
- Dry-run test of metrics generation
- Validates all processing files can be parsed

**Outputs**: Validation report posted as PR comment

### 3. CI Testing with Dashboard Tests

**File**: `.github/workflows/ci.yml` (enhanced)

**Trigger**: On all pushes and pull requests

**Purpose**: Runs comprehensive test suite including visual regression tests

**Test Jobs**:

#### Lint and Type Check
- Runs ruff linter
- Runs ruff formatter check
- Runs mypy type checker

#### Unit Tests
- Matrix testing across Python 3.9, 3.10, 3.11
- Cross-platform (Ubuntu, macOS)
- Coverage reporting to Codecov

#### Dashboard Visual Tests (NEW)
- Builds dashboard from current code
- Generates test metrics data
- Runs Playwright visual regression tests
- Tests across multiple browsers (Chromium, Firefox, WebKit)
- Tests responsive design (mobile, tablet, desktop)

**Visual Test Coverage**:
- Dashboard loading and error handling
- Metrics card display and content
- Chart rendering (Plotly)
- Tab navigation functionality
- Responsive layouts (mobile/tablet/desktop)
- Empty state handling
- Error state handling
- Accessibility features
- Performance benchmarks

**Artifacts**:
- Test results (JSON, JUnit)
- HTML test reports
- Screenshots on failure
- Video recordings on failure

### 4. Deploy Dashboard to GitHub Pages

**File**: `.github/workflows/deploy-dashboard-v2.yml`

**Trigger**:
- On push to `main` affecting dashboard, metrics, or workflow files
- Manual trigger

**Purpose**: Builds and deploys dashboard to GitHub Pages

**Build Process**:
1. Run `src/dashboard/build-site.sh` (creates structure, copies assets)
2. Generate `all_metrics.json` from processing files
3. Verify build (check all required files exist)
4. Upload artifact to GitHub Pages
5. Deploy to production

**Deployment Safety**:
- Build verification before deployment
- Artifact staging
- Atomic deployment via GitHub Pages action

### 5. Deployment Health Check

**File**: `.github/workflows/deployment-health-check.yml`

**Trigger**:
- On deployment status change
- Every 6 hours (scheduled)
- Manual trigger

**Purpose**: Continuously monitors dashboard health and creates alerts on issues

**Health Checks**:

#### Accessibility Check
- Verifies dashboard returns HTTP 200
- Measures response time
- Alerts if response time > 10s

#### Metrics Data Check
- Verifies `all_metrics.json` is accessible
- Validates JSON structure
- Reports metrics count, records, and sources

#### Freshness Check
- Calculates age of most recent metrics
- Warns if data > 30 days old

#### Performance Check
- Measures main page load time
- Measures metrics data load time
- Alerts if slow (> 5s for page, > 3s for data)

**Incident Response**:
- Generates health report
- Creates GitHub issue on failure (with deduplication)
- Provides rollback instructions
- Checks rollback capability

**Outputs**: Health report with all check results

## Setup Instructions

### Prerequisites

1. **Repository Permissions**: Ensure workflows have necessary permissions
   ```yaml
   permissions:
     contents: write
     pages: write
     id-token: write
     issues: write
   ```

2. **GitHub Pages**: Enable GitHub Pages in repository settings
   - Settings → Pages → Source: GitHub Actions

3. **Node.js and npm**: For Playwright tests
   ```bash
   node --version  # Should be >= 18.0.0
   npm --version
   ```

4. **Python 3.9+**: For metrics processing
   ```bash
   python --version  # Should be >= 3.9
   ```

### Initial Setup

1. **Install Dependencies**

   Python:
   ```bash
   pip install -e ".[dev]"
   pip install pandas plotly numpy jsonschema
   ```

   Node.js:
   ```bash
   npm install
   npx playwright install --with-deps
   ```

2. **Verify Workflows**
   ```bash
   # Validate workflow syntax
   yamllint .github/workflows/*.yml
   ```

3. **Test Locally**

   Validate metrics:
   ```bash
   python scripts/validate_metrics.py
   ```

   Build dashboard:
   ```bash
   ./src/dashboard/build-site.sh
   ```

   Run visual tests:
   ```bash
   npm test
   ```

### Configuration

#### Validation Thresholds

Edit `scripts/validate_metrics.py`:
```python
validator = MetricsValidator(
    max_age_days=30,        # Data freshness threshold
    min_success_rate=0.5,   # Minimum success rate
)
```

#### Health Check Schedule

Edit `.github/workflows/deployment-health-check.yml`:
```yaml
schedule:
  - cron: '0 */6 * * *'  # Change frequency
```

#### Visual Test Configuration

Edit `playwright.config.js`:
```javascript
{
  timeout: 60000,           // Test timeout
  retries: 2,               // Retry failed tests
  workers: 1,               // Parallel workers
}
```

## Manual Operations

### Manually Regenerate Metrics

```bash
# Using the workflow
gh workflow run dashboard-metrics.yml \
  --field force_rebuild=true

# Or locally
mkdir -p _site/data
python << 'EOF'
import json
from pathlib import Path

# ... (see workflow for full script)
EOF
```

### Manually Validate Metrics

```bash
# Using the validation script
python scripts/validate_metrics.py

# Using the workflow
gh workflow run dashboard-validation.yml
```

### Manually Run Visual Tests

```bash
# Run all tests
npm test

# Run specific browser
npx playwright test --project=chromium

# Run in headed mode (see browser)
npm run test:headed

# Update snapshots
npm run test:update-snapshots

# View test report
npm run test:report
```

### Manually Check Dashboard Health

```bash
# Using the workflow
gh workflow run deployment-health-check.yml \
  --field dashboard_url="https://somali-nlp.github.io/somali-dialect-classifier/"

# Or using curl
curl -I https://somali-nlp.github.io/somali-dialect-classifier/
curl -s https://somali-nlp.github.io/somali-dialect-classifier/data/all_metrics.json | jq .
```

### Trigger Deployment

```bash
# Trigger deployment workflow
gh workflow run deploy-dashboard-v2.yml

# Or commit/push to main
git add _site/data/all_metrics.json
git commit -m "chore(dashboard): update metrics"
git push origin main
```

## Troubleshooting

### Common Issues

#### 1. Metrics Generation Fails

**Symptoms**: Workflow fails at "Regenerate all_metrics.json" step

**Causes**:
- Invalid JSON in processing files
- Missing required fields in metrics
- Python script errors

**Solutions**:
```bash
# Validate individual metrics files
for file in data/metrics/*_processing.json; do
  echo "Checking $file"
  jq empty "$file" || echo "Invalid JSON: $file"
done

# Test locally
python scripts/validate_metrics.py

# Check for schema version mismatch
jq '._schema_version' data/metrics/*_processing.json
```

#### 2. Validation Fails

**Symptoms**: Validation workflow reports errors or warnings

**Causes**:
- Schema violations
- Low success rates
- Stale data
- Missing required fields

**Solutions**:
```bash
# Review validation errors
cat validation_report.md

# Check specific metrics
python << 'EOF'
import json
with open('_site/data/all_metrics.json') as f:
    data = json.load(f)
    for m in data['metrics']:
        if m['records_written'] == 0:
            print(f"Zero records: {m['source']}")
EOF

# Update stale data by re-running pipelines
bbcsom-download
wikisom-download
```

#### 3. Visual Tests Fail

**Symptoms**: Playwright tests fail in CI

**Causes**:
- Visual regressions (intentional changes)
- Timing issues
- Missing data
- Browser compatibility

**Solutions**:
```bash
# Run locally to reproduce
npm test

# Update snapshots if changes are intentional
npm run test:update-snapshots

# View failure screenshots
open test-results/

# Check specific failure
npx playwright test --debug

# Run only failed tests
npx playwright test --last-failed
```

#### 4. Deployment Fails

**Symptoms**: Deploy workflow fails

**Causes**:
- Build verification fails
- Missing files
- GitHub Pages configuration
- Permissions issues

**Solutions**:
```bash
# Verify build locally
./src/dashboard/build-site.sh
ls -la _site/
ls -la _site/data/

# Check GitHub Pages settings
gh api repos/:owner/:repo/pages

# Check permissions
cat .github/workflows/deploy-dashboard-v2.yml | grep permissions

# Review deployment logs
gh run list --workflow=deploy-dashboard-v2.yml
gh run view <run-id>
```

#### 5. Health Check Fails

**Symptoms**: Health check workflow fails, creates issues

**Causes**:
- Dashboard not accessible
- Slow response times
- Invalid metrics data
- Stale data

**Solutions**:
```bash
# Check dashboard manually
curl -I https://somali-nlp.github.io/somali-dialect-classifier/

# Check metrics data
curl -s https://somali-nlp.github.io/somali-dialect-classifier/data/all_metrics.json | jq .count

# Check GitHub Pages status
gh api repos/:owner/:repo/pages

# Force rebuild
gh workflow run deploy-dashboard-v2.yml
```

### Debugging Workflows

#### View Workflow Runs
```bash
# List recent runs
gh run list

# View specific workflow
gh run list --workflow=ci.yml

# View run details
gh run view <run-id>

# View logs
gh run view <run-id> --log
```

#### Download Artifacts
```bash
# List artifacts
gh run view <run-id> --log-artifacts

# Download specific artifact
gh run download <run-id> -n playwright-report
```

#### Re-run Failed Workflows
```bash
# Re-run failed jobs
gh run rerun <run-id> --failed

# Re-run entire workflow
gh run rerun <run-id>
```

### Performance Issues

#### Slow Metrics Generation
- **Cause**: Many metrics files to process
- **Solution**: Optimize processing script, add parallel processing
- **Monitoring**: Check workflow duration trends

#### Slow Visual Tests
- **Cause**: Many screenshots, slow rendering
- **Solution**: Run fewer projects in CI (only chromium)
- **Configuration**: Update `playwright.config.js` to reduce projects

#### Slow Deployments
- **Cause**: Large site artifacts
- **Solution**: Optimize asset sizes, enable compression
- **Monitoring**: Check artifact sizes

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Workflow Success Rate**
   - Target: > 95%
   - Alert: < 90%

2. **Dashboard Response Time**
   - Target: < 2s
   - Alert: > 5s

3. **Data Freshness**
   - Target: < 7 days
   - Alert: > 30 days

4. **Test Coverage**
   - Target: > 80%
   - Alert: Significant drops

5. **Deployment Frequency**
   - Target: Daily or as needed
   - Alert: No deploys in 7 days (if active development)

### Alert Channels

1. **GitHub Issues**
   - Created automatically by health check workflow
   - Labels: `dashboard`, `health-check`, `bug`

2. **Workflow Notifications**
   - Configure in GitHub settings
   - Email or third-party integrations (Slack, Teams, etc.)

3. **Custom Webhooks**
   - Add to workflows for custom alerting
   - Example: Slack webhook for failures

### Monitoring Dashboard Health

Regular checks:
```bash
# Run health check
gh workflow run deployment-health-check.yml

# Check recent deployments
gh run list --workflow=deploy-dashboard-v2.yml --limit 10

# Check metrics data age
curl -s https://somali-nlp.github.io/somali-dialect-classifier/data/all_metrics.json | \
  jq -r '[.metrics[].timestamp] | max'
```

### Setting Up Custom Monitoring

Example: Add Slack notification on failure

```yaml
- name: Notify on failure
  if: failure()
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
      -H 'Content-Type: application/json' \
      -d '{
        "text": "Dashboard health check failed",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Dashboard Health Check Failed*\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Run>"
            }
          }
        ]
      }'
```

## Best Practices

### For Developers

1. **Test Locally First**
   - Run validation before pushing
   - Test visual changes with Playwright
   - Verify build completes

2. **Keep Metrics Fresh**
   - Re-run pipelines regularly
   - Update data sources when content changes

3. **Monitor Workflow Runs**
   - Check CI results on PRs
   - Investigate failures promptly

4. **Update Snapshots Intentionally**
   - Only update when changes are desired
   - Review visual diffs carefully

### For Operators

1. **Monitor Dashboard Health**
   - Check health check results regularly
   - Respond to issues promptly

2. **Review Metrics Quality**
   - Check validation reports
   - Investigate quality warnings

3. **Maintain Workflows**
   - Update dependencies regularly
   - Review and optimize performance

4. **Document Changes**
   - Update this guide when workflows change
   - Document troubleshooting solutions

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Playwright Documentation](https://playwright.dev/)
- [JSON Schema Documentation](https://json-schema.org/)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [CI/CD Quick Reference](cicd-quick-reference.md) - Quick commands and common operations

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review workflow logs
3. Search existing GitHub issues
4. Create new issue with `dashboard` and `cicd` labels

---

**Maintainers**: Somali NLP Contributors
