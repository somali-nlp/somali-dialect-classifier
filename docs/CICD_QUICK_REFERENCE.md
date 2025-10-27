# CI/CD Quick Reference Guide

Quick commands and workflows for common dashboard operations.

## Table of Contents
- [Workflows](#workflows)
- [Common Commands](#common-commands)
- [Troubleshooting Quick Fixes](#troubleshooting-quick-fixes)
- [Emergency Procedures](#emergency-procedures)

## Workflows

### Trigger Workflows

```bash
# Regenerate metrics
gh workflow run dashboard-metrics.yml

# Force regenerate (even if no changes)
gh workflow run dashboard-metrics.yml --field force_rebuild=true

# Run validation
gh workflow run dashboard-validation.yml

# Deploy dashboard
gh workflow run deploy-dashboard-v2.yml

# Run health check
gh workflow run deployment-health-check.yml

# Run health check on custom URL
gh workflow run deployment-health-check.yml \
  --field dashboard_url="https://example.com"
```

### View Workflow Status

```bash
# List all recent runs
gh run list --limit 10

# List runs for specific workflow
gh run list --workflow=ci.yml

# View specific run
gh run view <run-id>

# View logs
gh run view <run-id> --log

# Download artifacts
gh run download <run-id>
```

## Common Commands

### Metrics Operations

```bash
# Validate metrics locally
python scripts/validate_metrics.py

# Generate metrics manually
python << 'EOF'
import json
from pathlib import Path

metrics_dir = Path("data/metrics")
all_metrics = []

for f in metrics_dir.glob("*_processing.json"):
    with open(f) as file:
        data = json.load(file)
        # Process data...
        all_metrics.append(data)

with open("_site/data/all_metrics.json", "w") as out:
    json.dump({"metrics": all_metrics}, out, indent=2)
EOF

# Check metrics structure
jq '.count, .records, .sources' _site/data/all_metrics.json

# Find stale metrics (> 30 days)
jq '.metrics[] | select(.timestamp < (now - 2592000 | todate))' \
  _site/data/all_metrics.json
```

### Testing

```bash
# Run all Playwright tests
npm test

# Run specific browser
npx playwright test --project=chromium

# Run single test file
npx playwright test tests/visual/dashboard.spec.js

# Run in headed mode
npm run test:headed

# Update snapshots
npm run test:update-snapshots

# View test report
npm run test:report

# Run specific test
npx playwright test -g "should load dashboard"

# Debug test
npx playwright test --debug
```

### Dashboard Build

```bash
# Build dashboard locally
./dashboard/build-site.sh

# Serve locally
python -m http.server 8000 --directory _site

# Open in browser
open http://localhost:8000

# Verify build
ls -la _site/
ls -la _site/data/
```

### Validation

```bash
# Validate JSON files
jq empty _site/data/all_metrics.json

# Validate schema
python << 'EOF'
import json
from pathlib import Path

with open('_site/data/all_metrics.json') as f:
    data = json.load(f)
    required = ['count', 'records', 'sources', 'metrics']
    missing = [f for f in required if f not in data]
    if missing:
        print(f"Missing: {missing}")
    else:
        print("Schema valid")
EOF

# Check data quality
python << 'EOF'
import json
with open('_site/data/all_metrics.json') as f:
    data = json.load(f)
    for m in data['metrics']:
        if m['records_written'] == 0:
            print(f"Zero records: {m['source']}")
        if m.get('pipeline_metrics', {}).get('http_success_rate', 1) < 0.5:
            print(f"Low success: {m['source']}")
EOF
```

### Health Checks

```bash
# Check dashboard accessibility
curl -I https://somali-nlp.github.io/somali-dialect-classifier/

# Check metrics data
curl -s https://somali-nlp.github.io/somali-dialect-classifier/data/all_metrics.json | jq .

# Check response time
curl -w "Time: %{time_total}s\n" -o /dev/null -s \
  https://somali-nlp.github.io/somali-dialect-classifier/

# Check all resources
for url in \
  "https://somali-nlp.github.io/somali-dialect-classifier/" \
  "https://somali-nlp.github.io/somali-dialect-classifier/data/all_metrics.json" \
  "https://somali-nlp.github.io/somali-dialect-classifier/data/summary.json"; do
  echo "Checking $url"
  curl -I -s "$url" | head -1
done
```

## Troubleshooting Quick Fixes

### Metrics Generation Failed

```bash
# Check for invalid JSON
for f in data/metrics/*_processing.json; do
  jq empty "$f" 2>&1 || echo "Invalid: $f"
done

# Fix: Remove or fix invalid files
# Then regenerate
gh workflow run dashboard-metrics.yml --field force_rebuild=true
```

### Validation Errors

```bash
# Check what's failing
python scripts/validate_metrics.py

# Common fixes:
# 1. Stale data - Re-run pipelines
bbcsom-download
wikisom-download

# 2. Low success rates - Investigate source
# Check logs for specific pipeline run

# 3. Missing fields - Update metrics schema or fix processing
```

### Visual Tests Failed

```bash
# View failures
npm run test:report

# If intentional changes, update snapshots
npm run test:update-snapshots
git add tests/visual/*.spec.js-snapshots/
git commit -m "test(dashboard): update visual snapshots"

# If unintentional, fix and re-test
npm test
```

### Deployment Failed

```bash
# Check what failed
gh run list --workflow=deploy-dashboard-v2.yml --limit 1
gh run view <run-id> --log

# Common fixes:
# 1. Build failed - Check build logs, fix errors
# 2. Missing files - Run build-site.sh locally first
# 3. Permissions - Check workflow permissions in .github/workflows/

# Force rebuild
gh workflow run deploy-dashboard-v2.yml
```

### Dashboard Not Accessible

```bash
# 1. Check GitHub Pages status
gh api repos/:owner/:repo/pages

# 2. Check recent deployments
gh run list --workflow=deploy-dashboard-v2.yml

# 3. Force redeploy
gh workflow run deploy-dashboard-v2.yml

# 4. Check DNS/CDN (may take a few minutes)
curl -I https://somali-nlp.github.io/somali-dialect-classifier/
```

## Emergency Procedures

### Dashboard is Down

```bash
# 1. Check status
curl -I https://somali-nlp.github.io/somali-dialect-classifier/

# 2. Check recent deploys
gh run list --workflow=deploy-dashboard-v2.yml --limit 5

# 3. Check for issues
gh issue list --label dashboard

# 4. Rollback to previous version
git log --oneline -5
git revert HEAD  # If last commit caused issue
git push origin main

# 5. Monitor deployment
gh run watch
```

### Broken Metrics Data

```bash
# 1. Verify issue
curl -s https://somali-nlp.github.io/somali-dialect-classifier/data/all_metrics.json | jq .

# 2. Rollback metrics data
git log --oneline -- _site/data/all_metrics.json
git checkout <commit-hash> -- _site/data/all_metrics.json
git commit -m "fix(dashboard): revert broken metrics data"
git push origin main

# 3. Regenerate from source
gh workflow run dashboard-metrics.yml --field force_rebuild=true
```

### Pipeline Health Check Failing

```bash
# 1. Run manual health check
gh workflow run deployment-health-check.yml

# 2. Check specific issues
# - Accessibility: curl -I <url>
# - Performance: curl -w "Time: %{time_total}s\n" <url>
# - Data: curl -s <url>/data/all_metrics.json | jq .

# 3. If persistent, check GitHub Status
open https://www.githubstatus.com/

# 4. Create incident issue if needed
gh issue create \
  --title "Dashboard Health Check Failing" \
  --body "Health check has been failing. See run: <url>" \
  --label dashboard,incident
```

### Critical: Complete System Failure

```bash
# 1. Assess scope
gh run list --limit 20

# 2. Check GitHub Status
open https://www.githubstatus.com/

# 3. Rollback to last known good state
git log --oneline -10
git reset --hard <last-good-commit>
git push --force origin main

# 4. Notify team
gh issue create \
  --title "CRITICAL: Dashboard System Failure" \
  --body "Complete system rollback initiated. Investigating root cause." \
  --label dashboard,critical,incident

# 5. Investigate root cause
# - Review logs
# - Check recent changes
# - Test locally

# 6. Implement fix
# - Fix issue
# - Test thoroughly
# - Deploy carefully
```

## Quick Status Check

Run this one-liner to check overall system health:

```bash
echo "=== Dashboard Health ===" && \
curl -I https://somali-nlp.github.io/somali-dialect-classifier/ 2>&1 | head -1 && \
echo "=== Recent Workflows ===" && \
gh run list --limit 5 && \
echo "=== Open Issues ===" && \
gh issue list --label dashboard && \
echo "=== Recent Commits ===" && \
git log --oneline -5
```

## Useful Aliases

Add these to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
# Dashboard aliases
alias dash-status='gh run list --workflow=deploy-dashboard-v2.yml --limit 5'
alias dash-deploy='gh workflow run deploy-dashboard-v2.yml'
alias dash-test='npm test'
alias dash-build='./dashboard/build-site.sh'
alias dash-serve='python -m http.server 8000 --directory _site'
alias dash-health='gh workflow run deployment-health-check.yml'
alias dash-validate='python scripts/validate_metrics.py'
alias dash-metrics='gh workflow run dashboard-metrics.yml'

# Quick checks
alias dash-check='curl -I https://somali-nlp.github.io/somali-dialect-classifier/'
alias dash-logs='gh run list --workflow=deploy-dashboard-v2.yml --limit 1 | tail -1 | cut -f 7 | xargs gh run view --log'
```

## Cheat Sheet

| Task | Command |
|------|---------|
| Regenerate metrics | `gh workflow run dashboard-metrics.yml` |
| Deploy dashboard | `gh workflow run deploy-dashboard-v2.yml` |
| Run tests | `npm test` |
| Validate metrics | `python scripts/validate_metrics.py` |
| Build locally | `./dashboard/build-site.sh` |
| Serve locally | `python -m http.server 8000 --directory _site` |
| Check health | `curl -I <dashboard-url>` |
| View logs | `gh run view <run-id> --log` |
| Update snapshots | `npm run test:update-snapshots` |
| Rollback | `git revert HEAD && git push` |

## Additional Resources

- Full documentation: `docs/CICD_DASHBOARD.md`
- GitHub Actions: https://docs.github.com/en/actions
- Playwright: https://playwright.dev/
- Repository issues: `gh issue list`
