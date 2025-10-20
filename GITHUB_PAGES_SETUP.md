# GitHub Pages Setup Instructions

**Issue:** Dashboard link not working yet
**Reason:** GitHub Pages needs to be enabled in repository settings

---

## ⚡ Quick Fix (2 minutes)

### Step 1: Enable GitHub Pages

1. Go to your repository: https://github.com/somali-nlp/somali-dialect-classifier

2. Click the **Settings** tab (top right, looks like a gear icon)

3. In the left sidebar, scroll down and click **Pages**

4. Under "Build and deployment", you'll see:
   - **Source**: Select **GitHub Actions** from the dropdown

   ![GitHub Pages Source Setting](https://docs.github.com/assets/cb-47267/mw-1440/images/help/pages/publishing-source-drop-down.webp)

5. Click **Save** (if there's a save button)

6. You should see a message:
   > "Your site is ready to be published at https://somali-nlp.github.io/somali-dialect-classifier/"

---

### Step 2: Wait for Deployment

After enabling GitHub Pages:

1. Go to the **Actions** tab: https://github.com/somali-nlp/somali-dialect-classifier/actions

2. Look for the workflow run called **"Deploy Dashboard to GitHub Pages"**

3. It should show:
   - ⏳ Yellow circle = Running (wait 2-3 minutes)
   - ✅ Green check = Success! Dashboard is live
   - ❌ Red X = Failed (check logs)

4. Once you see the green checkmark ✅, your dashboard is live!

---

### Step 3: Access Your Dashboard

Visit: **https://somali-nlp.github.io/somali-dialect-classifier/**

If you still see 404:
- Wait 1-2 more minutes for DNS propagation
- Clear your browser cache (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
- Try in an incognito/private browser window

---

## 🔍 Troubleshooting

### Issue 1: "Pages" not visible in Settings

**Solution:** You need admin access to the repository.
- If this is an organization repo, ask an org admin to enable Pages
- Or, they can give you admin permissions

### Issue 2: Workflow hasn't run yet

**Solution:** Trigger it manually:

1. Go to **Actions** tab
2. Click "Deploy Dashboard to GitHub Pages" workflow (left sidebar)
3. Click "Run workflow" button (top right)
4. Select branch: **main**
5. Click green "Run workflow" button

### Issue 3: Workflow is failing

**Solution:** Check the logs:

1. Go to **Actions** tab
2. Click on the failed workflow run (red X)
3. Click on the job name to see logs
4. Look for error messages

Common errors:
- **"Permission denied"** → Need to enable GitHub Pages first (Step 1)
- **"No metrics found"** → This is okay, the static HTML will still deploy
- **"No such file"** → Check if `_site/` directory exists in your repo

### Issue 4: 404 Error on dashboard URL

**Possible causes:**

1. **GitHub Pages not enabled** → Follow Step 1 above
2. **Workflow hasn't completed** → Wait for green checkmark in Actions
3. **Wrong URL** → Make sure it's exactly: `https://somali-nlp.github.io/somali-dialect-classifier/`
4. **DNS propagation delay** → Wait 5-10 minutes, then try again

---

## 🎯 Quick Verification Script

Run this to check your setup:

```bash
# Check if workflow file exists
ls -la .github/workflows/deploy-dashboard.yml && echo "✅ Workflow file exists" || echo "❌ Workflow file missing"

# Check if _site data exists
ls -la _site/data/ && echo "✅ Site data exists" || echo "❌ Site data missing"

# Check remote URL
git remote get-url origin
```

Expected output:
```
✅ Workflow file exists
✅ Site data exists
git@github.com:somali-nlp/somali-dialect-classifier
```

---

## 📋 Enabling GitHub Pages - Visual Guide

### If you need more detailed instructions:

1. **Navigate to Settings**
   ```
   GitHub Repo → Settings tab → Pages (in left sidebar)
   ```

2. **Configure Source**
   ```
   Source: GitHub Actions (NOT "Deploy from a branch")
   ```

3. **No custom domain needed** (leave blank)

4. **Click Save**

### Screenshot of what you should see:

```
┌─────────────────────────────────────────────────┐
│ GitHub Pages                                    │
├─────────────────────────────────────────────────┤
│                                                 │
│ Build and deployment                            │
│                                                 │
│ Source                                          │
│ ┌──────────────────────┐                       │
│ │ GitHub Actions    ▼  │                       │
│ └──────────────────────┘                       │
│                                                 │
│ Your site is ready to be published at          │
│ https://somali-nlp.github.io/somali-dialect... │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## ✅ Success Indicators

Once everything is working, you should see:

1. **In Settings → Pages:**
   > ✅ Your site is live at https://somali-nlp.github.io/somali-dialect-classifier/

2. **In Actions tab:**
   > ✅ Green checkmark on "Deploy Dashboard to GitHub Pages" workflow

3. **When visiting the URL:**
   > ✅ Dashboard loads with metrics and visualizations

---

## 🚀 Alternative: Trigger Deployment Now

If GitHub Pages is enabled but the workflow hasn't run, you can trigger it:

### Option 1: Manual Trigger (via GitHub UI)

1. Go to: https://github.com/somali-nlp/somali-dialect-classifier/actions
2. Click "Deploy Dashboard to GitHub Pages" in left sidebar
3. Click "Run workflow" button
4. Select branch: main
5. Click "Run workflow"

### Option 2: Push a Small Change

```bash
# Make a small change to trigger the workflow
git commit --allow-empty -m "Trigger dashboard deployment"
git push origin main
```

This will trigger the workflow because it watches the `main` branch.

---

## 🔗 Important Links

- **Repository:** https://github.com/somali-nlp/somali-dialect-classifier
- **Settings:** https://github.com/somali-nlp/somali-dialect-classifier/settings/pages
- **Actions:** https://github.com/somali-nlp/somali-dialect-classifier/actions
- **Expected Dashboard URL:** https://somali-nlp.github.io/somali-dialect-classifier/

---

## 💡 Quick Summary

**The problem:** GitHub Pages isn't enabled yet in your repository settings.

**The solution:**
1. Go to repo Settings → Pages
2. Set Source to "GitHub Actions"
3. Save
4. Wait 2-3 minutes
5. Visit https://somali-nlp.github.io/somali-dialect-classifier/

**Time required:** 2-3 minutes

---

## 📞 Still Not Working?

If you've enabled GitHub Pages and waited 5+ minutes but still see 404:

1. **Check workflow status:**
   ```bash
   # See if workflow ran successfully
   # Visit: https://github.com/somali-nlp/somali-dialect-classifier/actions
   ```

2. **Check workflow logs:**
   - Look for errors in the deployment step
   - Common issue: permissions not set correctly

3. **Verify workflow permissions:**
   - Go to Settings → Actions → General
   - Under "Workflow permissions", ensure "Read and write permissions" is selected
   - Save

4. **Re-run the workflow:**
   - Go to Actions tab
   - Click latest workflow run
   - Click "Re-run all jobs"

---

## ✨ Next Steps After Enabling

Once your dashboard is live:

1. ✅ Bookmark the URL
2. ✅ Add to your resume/LinkedIn
3. ✅ Share with collaborators
4. ��� Run more pipelines to populate with data

Your dashboard will automatically update whenever you push new metrics files!

---

*Last updated: 2025-10-20*
