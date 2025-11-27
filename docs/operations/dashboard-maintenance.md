# Dashboard Maintenance Guide

**Operational guide for maintaining and troubleshooting the dashboard system.**

**Last Updated:** 2025-11-21

**Last Updated**: 2025-10-27
**Audience**: DevOps engineers, maintainers, system administrators

---

## Table of Contents

- [Regenerating Dashboard Data](#regenerating-dashboard-data)
- [Running Validation Jobs](#running-validation-jobs)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [CI/CD Workflow](#cicd-workflow)
- [Monitoring and Alerts](#monitoring-and-alerts)
- [Backup and Recovery](#backup-and-recovery)

---

## Regenerating Dashboard Data

### Manual Regeneration

```bash
# Navigate to project root
cd /path/to/somali-dialect-classifier

# Option 1: Regenerate for GitHub Pages
python scripts/export_dashboard_data.py --github-pages

# Option 2: Regenerate for local development
python scripts/export_dashboard_data.py --local

# Option 3: Regenerate both
python scripts/export_dashboard_data.py
```

**Output**:
```
[INFO] Exporting dashboard data...

[INFO] GitHub Pages Export:
[SUCCESS] Exported summary to _site/data/summary.json
   - Total records: 130,456
   - Total runs: 42
   - Sources: BBC-Somali, HuggingFace-Somali_c4-so, Sprakbanken-Somali, Wikipedia-Somali
[SUCCESS] Exported all metrics to _site/data/all_metrics.json
[SUCCESS] Exported 42 reports to _site/data/reports.json

[SUCCESS] Dashboard data export complete!
```

### Automated Regeneration

The dashboard automatically regenerates on:
1. Push to `main` branch (via GitHub Actions)
2. Manual workflow dispatch
3. Scheduled runs (if configured)

**Trigger manual regeneration**:
```bash
# Via GitHub CLI
gh workflow run deploy-dashboard-v2.yml

# Via GitHub web interface
# Navigate to: Actions → Deploy Dashboard → Run workflow
```

---

## Running Validation Jobs

### Metrics Validation

```bash
# Validate all metrics files
python -c "
from src.somali_dialect_classifier.deployment.dashboard_deployer import MetricsValidator
from pathlib import Path

validator = MetricsValidator()
valid, invalid = validator.validate_all_metrics(Path('data/metrics'))

print(f'Valid files: {len(valid)}')
print(f'Invalid files: {len(invalid)}')

for file_path, error in invalid:
    print(f'  ❌ {file_path.name}: {error}')
"
```

**Expected output**:
```
Valid files: 42
Invalid files: 0
```

### Data Integrity Checks

```bash
# Check for missing required fields
python -c "
import json
from pathlib import Path

required_fields = ['run_id', 'source', 'timestamp']
metrics_dir = Path('data/metrics')

for file in metrics_dir.glob('*_processing.json'):
    with open(file) as f:
        data = json.load(f)
        snapshot = data.get('legacy_metrics', {}).get('snapshot', {})

        missing = [f for f in required_fields if f not in snapshot]
        if missing:
            print(f'{file.name}: Missing {missing}')
"
```

### Dashboard Build Validation

```bash
# Build dashboard locally
cd dashboard
bash build-site.sh

# Verify outputs
ls -lh _site/
ls -lh _site/data/

# Expected files:
#   _site/index.html
#   _site/data/all_metrics.json
#   _site/data/summary.json
#   _site/data/reports.json
```

---

## Troubleshooting Common Issues

### Issue 1: Dashboard Shows No Data

**Symptoms**:
- Dashboard loads but charts are empty
- "No data available" message

**Diagnosis**:
```bash
# Check if metrics exist
ls -l data/metrics/*.json | wc -l
# Should show > 0

# Check if data was exported
ls -l _site/data/*.json 2>/dev/null
# Should show all_metrics.json, summary.json

# Check GitHub Pages deployment
curl -I https://YOUR-USERNAME.github.io/somali-dialect-classifier/data/all_metrics.json
# Should return 200 OK
```

**Solutions**:

1. **No metrics files**:
   ```bash
   # Run a pipeline to generate metrics
   python -m somali_dialect_classifier.cli.download_wikisom --max-articles 100
   ```

2. **Metrics not committed**:
   ```bash
   git add data/metrics/
   git commit -m "chore(metrics): add missing metrics files"
   git push origin main
   ```

3. **Export script failed**:
   ```bash
   # Run export manually
   python scripts/export_dashboard_data.py
   # Check for errors in output
   ```

4. **GitHub Actions failed**:
   ```bash
   # Check workflow status
   gh run list --workflow=deploy-dashboard-v2.yml --limit 5

   # View failed run logs
   gh run view <run-id> --log-failed
   ```

### Issue 2: Metrics Showing Zero Values

**Symptoms**:
- Metrics exist but show 0 for quality_pass_rate or other fields

**Diagnosis**:
```bash
# Inspect a metrics file
cat data/metrics/latest_processing.json | jq '.legacy_metrics.statistics.quality_pass_rate'
# If shows 0 or null, there's an issue

# Check calculation logic
cat data/metrics/latest_processing.json | jq '.legacy_metrics.snapshot | {records_written, records_filtered}'
```

**Common Causes**:

1. **Formula error**: `records_written` and `records_filtered` both 0
   - **Fix**: Check pipeline filter application

2. **Schema mismatch**: Using old schema version
   - **Fix**: Update MetricsCollector to v3.0 schema

3. **Validation clamping**: Metrics out of range, clamped to 0
   - **Fix**: Check logs for validation warnings

### Issue 3: GitHub Actions Deployment Fails

**Symptoms**:
- Workflow shows red X
- Dashboard not updating after push

**Diagnosis**:
```bash
# View recent workflow runs
gh run list --workflow=deploy-dashboard-v2.yml --limit 10

# Get details of failed run
gh run view <run-id>

# Download logs
gh run download <run-id>
```

**Common Errors**:

**Error**: `No module named 'somali_dialect_classifier'`
```yaml
# Solution: Verify setup.py and package installation in workflow
- name: Install dependencies
  run: |
    pip install -e .
    pip install -r requirements.txt
```

**Error**: `Permission denied` when pushing to Pages
```yaml
# Solution: Check repository permissions
# Settings → Actions → General → Workflow permissions
# Set to: "Read and write permissions"
```

**Error**: `No such file or directory: data/metrics`
```bash
# Solution: Ensure metrics are committed
git status
git add data/metrics/ data/reports/
git commit -m "chore(metrics): add metrics files"
git push
```

### Issue 4: Dashboard Rendering Slow

**Symptoms**:
- Initial load takes > 5 seconds
- Charts take long to render

**Diagnosis**:
```javascript
// In browser console
console.time('Data Load');
fetch('/somali-dialect-classifier/data/all_metrics.json')
    .then(r => r.json())
    .then(data => {
        console.timeEnd('Data Load');
        console.log('Data size:', JSON.stringify(data).length, 'bytes');
        console.log('Metrics count:', data.length);
    });
```

**Solutions**:

1. **Large data file** (> 1 MB):
   ```python
   # In export_dashboard_data.py
   # Limit to last 90 days
   from datetime import datetime, timedelta

   cutoff = datetime.now() - timedelta(days=90)
   recent_metrics = [m for m in all_metrics if datetime.fromisoformat(m['timestamp']) > cutoff]
   ```

2. **Too many data points**:
   ```javascript
   // In index.html
   // Sample data for charts
   const sampledData = data.filter((_, i) => i % 5 === 0); // Every 5th point
   ```

3. **Inefficient rendering**:
   ```javascript
   // Use Chart.js decimation plugin
   options: {
       plugins: {
           decimation: {
               enabled: true,
               algorithm: 'lttb', // Largest-Triangle-Three-Buckets
               samples: 200
           }
       }
   }
   ```

---

## CI/CD Workflow

### GitHub Actions Pipeline

**Workflow file**: `.github/workflows/deploy-dashboard-v2.yml`

**Trigger events**:
- `push` to `main` branch
- `workflow_dispatch` (manual trigger)

**Steps**:

1. **Checkout repository**
   ```yaml
   - uses: actions/checkout@v4
   ```

2. **Setup Python**
   ```yaml
   - uses: actions/setup-python@v5
     with:
       python-version: '3.11'
   ```

3. **Install dependencies**
   ```yaml
   - run: |
       pip install -e .
       pip install -r requirements.txt
   ```

4. **Generate dashboard data**
   ```yaml
   - run: python scripts/export_dashboard_data.py --github-pages
   ```

5. **Build static site**
   ```yaml
   - run: bash dashboard/build-site.sh
   ```

6. **Deploy to GitHub Pages**
   ```yaml
   - uses: peaceiris/actions-gh-pages@v3
     with:
       github_token: ${{ secrets.GITHUB_TOKEN }}
       publish_dir: ./_site
   ```

### Manual Deployment

```bash
# Full deployment workflow (local)

# 1. Ensure metrics are up to date
python -m somali_dialect_classifier.cli.download_wikisom

# 2. Generate dashboard data
python scripts/export_dashboard_data.py

# 3. Build site
cd dashboard && bash build-site.sh && cd ..

# 4. Test locally
python -m http.server 8000 --directory _site

# 5. Commit and push (triggers auto-deployment)
git add data/metrics/ data/reports/ _site/
git commit -m "chore(dashboard): update dashboard data"
git push origin main
```

### Rollback Procedure

If deployment introduces issues:

```bash
# Option 1: Revert last commit
git revert HEAD
git push origin main

# Option 2: Reset to previous commit
git reset --hard HEAD~1
git push --force origin main

# Option 3: Deploy specific commit
git checkout <commit-hash>
bash dashboard/build-site.sh
git checkout main
# Manually copy _site/ to gh-pages branch
```

---

## Monitoring and Alerts

### Health Checks

Create a monitoring script:

```python
# scripts/check_dashboard_health.py
import requests
import sys
from datetime import datetime, timedelta

DASHBOARD_URL = "https://YOUR-USERNAME.github.io/somali-dialect-classifier/data/summary.json"

def check_dashboard_health():
    try:
        response = requests.get(DASHBOARD_URL, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Check 1: Data freshness
        last_update = datetime.fromisoformat(data['last_update'])
        age = datetime.now() - last_update

        if age > timedelta(days=7):
            print(f"⚠️  WARNING: Dashboard data is {age.days} days old")
            return False

        # Check 2: Minimum sources
        if len(data['sources']) < 4:
            print(f"⚠️  WARNING: Only {len(data['sources'])} sources active")
            return False

        # Check 3: Reasonable record count
        if data['total_records'] < 50000:
            print(f"⚠️  WARNING: Low record count: {data['total_records']}")
            return False

        print("✅ Dashboard health check passed")
        return True

    except Exception as e:
        print(f"❌ Dashboard health check failed: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if check_dashboard_health() else 1)
```

**Schedule with cron**:
```cron
# Check dashboard health daily at 9 AM
0 9 * * * /usr/bin/python /path/to/check_dashboard_health.py && echo "Dashboard healthy" || echo "Dashboard needs attention" | mail -s "Dashboard Alert" admin@example.com
```

### GitHub Actions Monitoring

**Setup notifications**:
1. Go to repository Settings → Notifications
2. Enable workflow failure notifications
3. Add Slack/Email integration

**Slack webhook integration**:
```yaml
# In workflow file
- name: Notify on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    payload: |
      {
        "text": "Dashboard deployment failed",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "Dashboard deployment failed for commit: ${{ github.sha }}"
            }
          }
        ]
      }
```

---

## Backup and Recovery

### Backing Up Metrics

```bash
# Create backup script
# scripts/backup_metrics.sh

#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="backups/metrics-$DATE"

mkdir -p "$BACKUP_DIR"

# Copy metrics and reports
cp -r data/metrics "$BACKUP_DIR/"
cp -r data/reports "$BACKUP_DIR/"

# Create archive
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

# Upload to cloud storage (example: AWS S3)
# aws s3 cp "$BACKUP_DIR.tar.gz" s3://your-bucket/metrics-backups/

# Keep only last 30 days
find backups/ -name "metrics-*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR.tar.gz"
```

**Schedule backups**:
```cron
# Daily backup at 2 AM
0 2 * * * /path/to/backup_metrics.sh
```

### Recovery Procedures

**Scenario 1: Accidental deletion of metrics**

```bash
# Restore from backup
tar -xzf backups/metrics-20251027.tar.gz
cp -r metrics-20251027/data/metrics/* data/metrics/
cp -r metrics-20251027/data/reports/* data/reports/

# Regenerate dashboard
python scripts/export_dashboard_data.py
bash dashboard/build-site.sh
```

**Scenario 2: Corrupted dashboard data**

```bash
# Clear corrupted data
rm -rf _site/data/*

# Regenerate from source metrics
python scripts/export_dashboard_data.py

# Rebuild and redeploy
bash dashboard/build-site.sh
git add _site/
git commit -m "fix(dashboard): regenerate corrupted data"
git push origin main
```

**Scenario 3: GitHub Pages outage**

```bash
# Deploy to alternative hosting (Netlify/Vercel)

# 1. Build site
bash dashboard/build-site.sh

# 2. Deploy to Netlify
netlify deploy --prod --dir=_site

# 3. Update DNS/links temporarily
```

---

## Related Documentation

- [Dashboard Guide](../guides/dashboard.md)
- [Troubleshooting Guide](../howto/troubleshooting.md)
- [Deployment Operations](../operations/deployment.md)

---

**Questions?**
Contact the maintainers or open an issue with the `dashboard` or `operations` label.

---

**Maintainers**: Somali NLP Contributors
