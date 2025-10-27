# Dashboard Developer Onboarding

**Quick start guide for developers contributing to the dashboard system.**

**Last Updated**: 2025-10-27

---

## Prerequisites

- Python 3.11+
- Git
- Node.js (optional, for local development server)
- GitHub account with repository access

---

## Setup Instructions

### 1. Clone Repository

```bash
git clone https://github.com/YOUR-USERNAME/somali-dialect-classifier.git
cd somali-dialect-classifier
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package in development mode
pip install -e .

# Install additional dependencies
pip install -r requirements.txt
```

### 3. Generate Sample Data

```bash
# Run a small pipeline to generate metrics
python -m somali_dialect_classifier.cli.download_wikisom --max-articles 50

# Verify metrics were generated
ls -l data/metrics/
ls -l data/reports/
```

### 4. Build Dashboard Locally

```bash
# Generate dashboard data
python scripts/export_dashboard_data.py

# Build static site
cd dashboard
bash build-site.sh
cd ..

# Serve locally
python -m http.server 8000 --directory _site

# Visit: http://localhost:8000
```

---

## Code Structure

### Directory Layout

```
somali-dialect-classifier/
├── dashboard/
│   ├── templates/
│   │   └── index.html          # Main dashboard HTML
│   ├── build-site.sh           # Build script
│   └── README.md               # Dashboard README
├── scripts/
│   ├── export_dashboard_data.py # Metrics aggregation
│   └── generate_dashboard_html.py # HTML generation (deprecated)
├── src/somali_dialect_classifier/
│   ├── deployment/
│   │   └── dashboard_deployer.py # Auto-deployment logic
│   └── utils/
│       └── metrics.py          # Metrics collection
├── data/
│   ├── metrics/                # JSON metrics files
│   └── reports/                # Quality reports
└── _site/                      # Generated static site
    ├── index.html
    └── data/
        ├── all_metrics.json
        ├── summary.json
        └── reports.json
```

### Key Files

| File | Purpose | When to Modify |
|------|---------|---------------|
| `dashboard/templates/index.html` | Dashboard UI | Adding visualizations, changing design |
| `scripts/export_dashboard_data.py` | Data aggregation | Adding new aggregations, changing data format |
| `src/.../metrics.py` | Metrics collection | Adding new metrics, changing collection logic |
| `src/.../dashboard_deployer.py` | Auto-deployment | Changing deployment behavior |
| `.github/workflows/deploy-dashboard-v2.yml` | CI/CD | Changing deployment pipeline |

---

## Adding New Visualizations

### Step 1: Add Chart Container

In `dashboard/templates/index.html`:

```html
<!-- Add canvas element -->
<section class="card">
    <h3>My New Chart</h3>
    <canvas id="myNewChart"></canvas>
</section>
```

### Step 2: Implement Rendering Function

```javascript
function renderMyNewChart(data) {
    const ctx = document.getElementById('myNewChart').getContext('2d');

    // Prepare data
    const chartData = {
        labels: data.metrics.map(m => m.source),
        datasets: [{
            label: 'My Metric',
            data: data.metrics.map(m => m.my_metric),
            backgroundColor: '#0176D3'
        }]
    };

    // Create chart
    new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Metric Value'
                    }
                }
            }
        }
    });
}
```

### Step 3: Call in Initialization

```javascript
document.addEventListener('DOMContentLoaded', async () => {
    const data = await loadData();

    // Render existing charts
    renderHeroMetrics(data);
    renderRecordsOverTime(data);

    // Add your new chart
    renderMyNewChart(data);
});
```

### Step 4: Test Locally

```bash
python -m http.server 8000 --directory _site
# Open http://localhost:8000
```

---

## Running Tests

### Unit Tests

```bash
# Run all tests
pytest

# Run dashboard-specific tests
pytest tests/test_dashboard_*.py

# Run with coverage
pytest --cov=src/somali_dialect_classifier/deployment
pytest --cov=src/somali_dialect_classifier/utils/metrics.py
```

### Integration Tests

```bash
# Test full pipeline + dashboard generation
python tests/test_cli_e2e.py

# Test dashboard deployment
python tests/test_dashboard_deployer.py
```

### Manual Testing Checklist

- [ ] Dashboard loads without errors
- [ ] All charts render correctly
- [ ] Metrics show non-zero values
- [ ] Filters work (if interactive)
- [ ] Mobile responsive design works
- [ ] No console errors in browser
- [ ] Data fetches successfully
- [ ] Quality reports link works

---

## Development Workflow

### Making Changes

```bash
# 1. Create feature branch
git checkout -b feature/my-dashboard-improvement

# 2. Make changes to code

# 3. Test locally
python scripts/export_dashboard_data.py
bash dashboard/build-site.sh
python -m http.server 8000 --directory _site

# 4. Run tests
pytest tests/test_dashboard_*.py

# 5. Commit changes
git add .
git commit -m "feat(dashboard): add new visualization for XYZ"

# 6. Push and create PR
git push origin feature/my-dashboard-improvement
gh pr create --title "Add XYZ visualization" --body "Description..."
```

### Code Review Process

1. Create PR with clear description
2. Ensure CI/CD passes
3. Request review from maintainers
4. Address feedback
5. Merge to main
6. Deployment happens automatically

---

## Common Tasks

### Task 1: Update Color Scheme

```css
/* In dashboard/templates/index.html <style> section */
:root {
    --tableau-blue: #0176D3;  /* Change primary color */
    --brand-accent: #00A651;  /* Change accent color */
}
```

### Task 2: Add New Metric to Export

```python
# In scripts/export_dashboard_data.py

metric_entry = {
    "run_id": snapshot.get("run_id", ""),
    "source": snapshot.get("source", ""),
    # ... existing fields ...
    "my_new_field": snapshot.get("my_new_field", 0)  # Add this
}
```

### Task 3: Change Chart Type

```javascript
// Change from bar to line chart
new Chart(ctx, {
    type: 'line',  // Was: 'bar'
    data: chartData,
    options: {
        // ... options ...
        tension: 0.4  // Add smooth curves
    }
});
```

### Task 4: Add Interactivity

```javascript
// Add click handler
options: {
    onClick: (event, elements) => {
        if (elements.length > 0) {
            const index = elements[0].index;
            const metric = data.metrics[index];
            alert(`Selected: ${metric.source}`);
        }
    }
}
```

---

## Debugging Tips

### Issue: Chart Not Rendering

```javascript
// Check data in console
console.log('Data:', data);
console.log('Chart data:', data.metrics.map(m => m.my_metric));

// Verify element exists
console.log('Canvas:', document.getElementById('myChart'));

// Check for errors
window.addEventListener('error', (e) => {
    console.error('Error:', e);
});
```

### Issue: Data Not Loading

```javascript
// Test data fetch
fetch('/somali-dialect-classifier/data/all_metrics.json')
    .then(r => {
        console.log('Status:', r.status);
        return r.json();
    })
    .then(data => console.log('Data:', data))
    .catch(e => console.error('Error:', e));
```

### Issue: Build Fails

```bash
# Check build script output
bash dashboard/build-site.sh 2>&1 | tee build.log

# Verify dependencies
pip install -e . --no-cache-dir

# Check Python version
python --version  # Should be 3.11+
```

---

## Resources

### Documentation

- [Dashboard User Guide](dashboard-user-guide.md)
- [Dashboard Technical Guide](dashboard-technical.md)
- [Metrics Reference](../reference/metrics.md)
- [Filter Reference](../reference/filters.md)

### External Resources

- [Chart.js Documentation](https://www.chartjs.org/docs/)
- [GitHub Pages Docs](https://docs.github.com/pages)
- [GitHub Actions Docs](https://docs.github.com/actions)

### Getting Help

- **Questions**: Open discussion in GitHub Discussions
- **Bugs**: Open issue with `bug` label
- **Features**: Open issue with `enhancement` label
- **Chat**: Join project Discord/Slack (if available)

---

**Welcome to the team!**
