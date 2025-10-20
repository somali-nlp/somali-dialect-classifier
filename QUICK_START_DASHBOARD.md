# Quick Start: Dashboard Setup

**Time required**: 5 minutes
**Cost**: $0

## Step 1: Enable GitHub Pages (30 seconds)

1. Go to your repo settings: `https://github.com/somali-nlp/somali-dialect-classifier/settings/pages`
2. Under **Source**, select: `GitHub Actions`
3. Click **Save**

## Step 2: Update URLs (30 seconds)

Replace `somali-nlp` with your actual GitHub username:

```bash
# Quick find/replace
sed -i '' 's/somali-nlp/your-actual-username/g' README.md dashboard/README.md dashboard/app.py

# Or manually edit 3 files:
# - README.md (lines 9, 13)
# - dashboard/README.md (line 5)
# - dashboard/app.py (line 464)
```

## Step 3: Deploy (1 minute)

```bash
# Add all dashboard files
git add .

# Commit
git commit -m "Add interactive data pipeline dashboard"

# Push
git push origin main
```

## Step 4: Watch Deployment (2 minutes)

1. Go to: `https://github.com/somali-nlp/somali-dialect-classifier/actions`
2. Watch "Deploy Dashboard to GitHub Pages" workflow
3. Wait for green checkmark ✅

## Step 5: Visit Your Dashboard! 🎉

```
https://somali-nlp.github.io/somali-dialect-classifier/
```

---

## Local Development

```bash
# Install dependencies
pip install -r dashboard/requirements.txt

# Run interactive dashboard
streamlit run dashboard/app.py

# Opens at: http://localhost:8501
```

---

## Ongoing Usage

Every time you run a pipeline:

```bash
# 1. Run pipeline
python -m somali_dialect_classifier.cli.download_bbcsom

# 2. Commit generated metrics
git add data/metrics/ data/reports/
git commit -m "Add pipeline run results"
git push

# 3. Dashboard auto-updates in ~2 minutes!
```

---

## Troubleshooting

**Dashboard not deploying?**
- Check GitHub Actions tab for errors
- Ensure GitHub Pages is enabled (Step 1)

**No data showing?**
- Run at least one pipeline to generate metrics
- Check `data/metrics/` has .json files

**404 error?**
- Wait 3-5 minutes after first deploy
- Check URL matches your GitHub username

---

## What You Get

✅ Live dashboard at: `https://somali-nlp.github.io/somali-dialect-classifier/`
✅ Auto-updates on every git push
✅ Interactive local dashboard with `streamlit run dashboard/app.py`
✅ Portfolio-ready project with professional visualizations
✅ $0 hosting cost forever

---

Need more details? See [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md) for comprehensive guide.
