# How to Set Up Secret Scanning with Gitleaks

**Setting up automated secret scanning to prevent credential leaks in version control.**

**Last Updated:** 2025-11-21

---

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
  - [Required](#required)
  - [Optional](#optional)
  - [Assumptions](#assumptions)
- [Quick Start](#quick-start)
- [Step-by-Step Guide](#step-by-step-guide)
  - [Step 1: Install the Pre-Commit Hook](#step-1-install-the-pre-commit-hook)
  - [Step 2: Test the Hook](#step-2-test-the-hook)
  - [Step 3: Manual Scanning](#step-3-manual-scanning)
- [Complete Example](#complete-example)
- [Configuration](#configuration)
  - [Gitleaks Configuration File](#gitleaks-configuration-file)
  - [Supported Secret Types](#supported-secret-types)
  - [Excluding Directories](#excluding-directories)
- [Advanced Usage](#advanced-usage)
  - [Option 1: Bypassing the Hook (Emergency Only)](#option-1-bypassing-the-hook-emergency-only)
  - [Option 2: Creating a Baseline](#option-2-creating-a-baseline)
  - [Option 3: Scanning Specific Commits](#option-3-scanning-specific-commits)
  - [Option 4: Custom Rules](#option-4-custom-rules)
- [Troubleshooting](#troubleshooting)
  - [Issue: False Positives](#issue-false-positives)
  - [Issue: Hook Not Running](#issue-hook-not-running)
  - [Issue: Slow Scans](#issue-slow-scans)
  - [Issue: CI/CD Failing on Secrets](#issue-cicd-failing-on-secrets)
- [Performance Tips](#performance-tips)
  - [Benchmarks](#benchmarks)
- [Next Steps](#next-steps)
  - [Related How-To Guides](#related-how-to-guides)
  - [Reference Documentation](#reference-documentation)
  - [External Resources](#external-resources)
- [Feedback](#feedback)

---

## Overview

This guide shows you how to set up Gitleaks secret scanning to prevent accidental commits of sensitive information like API keys, passwords, and tokens. Once configured, Gitleaks will automatically scan your code before every commit, blocking commits that contain secrets.

**What You'll Learn**:
- How to install and configure the pre-commit hook for automatic scanning
- How to run manual secret scans locally
- How to interpret scan results and fix false positives
- How to use CI/CD integration for additional security

---

## Prerequisites

### Required

- **Gitleaks installed**:
  ```bash
  # macOS
  brew install gitleaks

  # Linux (using binary)
  wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
  tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
  sudo mv gitleaks /usr/local/bin/
  ```

- **Git repository initialized** (already configured in this project)

### Optional

- **GitHub repository** - For CI/CD integration (already configured)

### Assumptions

- You have basic familiarity with git and command line
- You understand the importance of not committing secrets to version control

---

## Quick Start

For experienced users, here's the minimal setup:

```bash
# Install pre-commit hook
make secrets-install

# Verify it's working
make secrets-check
```

**Expected Output**:
```
✅ Pre-commit hook installed successfully!
...
🔍 Scanning staged files for secrets...
✓ No secrets detected. Proceeding with commit...
```

For detailed walkthrough, continue to [Step-by-Step Guide](#step-by-step-guide).

---

## Step-by-Step Guide

### Step 1: Install the Pre-Commit Hook

**Purpose**: The pre-commit hook automatically scans staged files before every commit, preventing secrets from entering the git history.

**Instructions**:

Run the installation command:

```bash
make secrets-install
```

**Expected Output**:
```
==================================
Gitleaks Pre-Commit Hook Setup
==================================

✓ Gitleaks found: 8.29.0
✓ Configuration file found: .gitleaks.toml

✅ Pre-commit hook installed successfully!

Location: .git/hooks/pre-commit

────────────────────────────────────────────────
How it works:
────────────────────────────────────────────────
• Runs automatically before every git commit
• Scans ONLY staged files (super fast!)
• Blocks commit if secrets are detected
• Uses configuration from .gitleaks.toml
```

**Verification**: Check that the hook exists:

```bash
ls -la .git/hooks/pre-commit
```

**Expected Output**:
```
-rwxr-xr-x  1 user  staff  627 Nov 13 19:24 .git/hooks/pre-commit
```

**Common Issues**:
- **"gitleaks: command not found"**: Install gitleaks using the [Prerequisites](#prerequisites) instructions
- **Permission denied**: The script will automatically make the hook executable; if not, run `chmod +x .git/hooks/pre-commit`

---

### Step 2: Test the Hook

**Purpose**: Verify the pre-commit hook is working correctly before making real commits.

**Instructions**:

Make a small change to test the hook:

```bash
# Make a safe change (e.g., edit a comment in any file)
echo "# Test comment" >> README.md

# Stage the file
git add README.md

# Try to commit
git commit -m "test: verify secret scanning hook"
```

**Expected Output**:
```
🔍 Scanning staged files for secrets...

    ○
    │╲
    │ ○
    ○ ░
    ░    gitleaks

7:24PM INF 0 commits scanned.
7:24PM INF scanned ~245 bytes (245 B) in 28.5ms
7:24PM INF no leaks found
✓ No secrets detected. Proceeding with commit...

[main a1b2c3d] test: verify secret scanning hook
 1 file changed, 1 insertion(+)
```

Notice the scan completed in milliseconds (e.g., 28.5ms) - this is because it only scans staged files.

**Verification**: The commit should succeed with no secrets detected.

---

### Step 3: Manual Scanning

**Purpose**: Sometimes you want to manually check for secrets before staging files, or run a full repository scan.

**Instructions**:

For quick checks on staged files:

```bash
make secrets-check
```

For comprehensive scans of the entire repository:

```bash
make secrets-scan
```

**Expected Output (secrets-check)**:
```
Scanning staged files for secrets...
7:24PM INF 0 commits scanned.
7:24PM INF scanned ~0 bytes (0) in 25.4ms
7:24PM INF no leaks found
```

**Expected Output (secrets-scan)**:
```
Running full repository secret scan (this may take a while)...
7:24PM INF 127 commits scanned.
7:24PM INF scanned ~2.5 MB in 2.1s
7:24PM INF no leaks found
```

**Common Issues**:
- **High CPU usage during full scan**: This is normal for `make secrets-scan` on first run. Use `make secrets-check` for daily work (it's much faster).
- **"No staged files"**: The quick check only scans staged files. Stage some changes with `git add` first.

---

## Complete Example

Here's a complete workflow showing how secret scanning integrates into your daily development:

```bash
#!/bin/bash
# Example workflow: Making changes with secret scanning protection

# 1. Make some code changes
echo "API_KEY=test_value_here" >> .env.example  # Safe - example file

# 2. Stage your changes
git add .env.example

# 3. (Optional) Manual check before committing
make secrets-check

# 4. Commit - the hook runs automatically
git commit -m "docs: update .env.example with new variables"

# Output:
# 🔍 Scanning staged files for secrets...
# ✓ No secrets detected. Proceeding with commit...
# [main 1a2b3c4] docs: update .env.example with new variables

# 5. Push to remote
git push origin main
```

**What happens if a secret is detected**:

```bash
# Accidentally try to commit a real API key
echo "API_KEY=apify_api_1234567890abcdef" >> config.py
git add config.py
git commit -m "feat: add API configuration"

# Output:
# 🔍 Scanning staged files for secrets...
# ❌ COMMIT REJECTED: Secrets detected in staged files!
#
# Finding:     Apify API token
# Secret:      apify_api_1234567890abcdef
# RuleID:      apify-api-token
# File:        config.py:42
#
# What to do:
#   1. Remove the detected secrets from your files
#   2. Use environment variables or .env files (not committed)
#   3. Re-stage your files: git add <file>
#   4. Try committing again
```

**To fix**:

```bash
# Remove the secret and use environment variable instead
# In config.py:
# API_KEY = os.getenv("APIFY_API_TOKEN")

# In .env (gitignored):
# APIFY_API_TOKEN=apify_api_1234567890abcdef

# Re-stage and commit
git add config.py
git commit -m "feat: add API configuration"
# ✓ No secrets detected. Proceeding with commit...
```

---

## Configuration

### Gitleaks Configuration File

The project uses `.gitleaks.toml` for configuration:

```toml
# Excerpt from .gitleaks.toml

[extend]
useDefault = true  # Use built-in gitleaks rules

# Custom rules for project-specific secrets
[[rules]]
id = "apify-api-token"
description = "Detected Apify API token"
regex = '''(apify_api_[A-Za-z0-9]{40})'''
keywords = ["apify_api_"]

# Exclude false positives
[allowlist]
paths = [
  '''.env\.example$''',      # Template files
  '''^data/''',               # Data directories (gitignored)
  '''^\.archive/''',          # Archived files (gitignored)
]

regexes = [
  '''placeholder''',          # Placeholder values
  '''your_.*_here''',         # Template patterns
  '''test_.*_token''',        # Test tokens
]
```

### Supported Secret Types

Gitleaks detects:

- **Apify API tokens**: `apify_api_*`
- **PostgreSQL passwords**: `POSTGRES_PASSWORD=*`
- **AWS access keys**: `AKIA*`, `ASIA*`
- **GitHub tokens**: `ghp_*`
- **HuggingFace tokens**: `hf_*`
- **Private keys**: `BEGIN PRIVATE KEY`
- **JWT tokens**: `eyJ*`
- **Generic API keys**: `api_key=*`
- And many more via default gitleaks rules

### Excluding Directories

The configuration already excludes gitignored directories:

```toml
paths = [
  '''^data/''',              # Data directories
  '''^logs/''',              # Log files
  '''^models/''',            # Model files
  '''^venv.*''',             # Virtual environments
  '''^node_modules/''',      # Dependencies
  '''\.db$''',               # Database files
]
```

This prevents scanning large datasets and keeps scans fast.

---

## Advanced Usage

### Option 1: Bypassing the Hook (Emergency Only)

If you absolutely need to commit without the secret scan (not recommended):

```bash
git commit --no-verify -m "emergency: hotfix for production issue"
```

**Warning**: Only use this in genuine emergencies. You're responsible for ensuring no secrets are in the commit.

### Option 2: Creating a Baseline

If you have known secrets in your history that you can't remove (e.g., revoked tokens), create a baseline:

```bash
# Generate baseline (one-time)
gitleaks detect --config .gitleaks.toml --report-path .gitleaks-baseline.json

# Add to .gitignore
echo ".gitleaks-baseline.json" >> .gitignore

# Future scans skip baseline findings
gitleaks detect --config .gitleaks.toml --baseline-path .gitleaks-baseline.json
```

### Option 3: Scanning Specific Commits

To scan a range of commits:

```bash
# Scan last 10 commits
gitleaks detect --config .gitleaks.toml --log-opts="-10"

# Scan specific branch
gitleaks detect --config .gitleaks.toml --log-opts="origin/feature-branch"

# Scan between commits
gitleaks detect --config .gitleaks.toml --log-opts="abc123..def456"
```

### Option 4: Custom Rules

Add custom secret patterns to `.gitleaks.toml`:

```toml
[[rules]]
id = "custom-api-key"
description = "Your custom API key pattern"
regex = '''your_custom_regex_here'''
keywords = ["custom_keyword"]
entropy = 3.5
```

---

## Troubleshooting

### Issue: False Positives

**Symptoms**:
- Gitleaks detects a secret that isn't actually sensitive
- Test data or placeholder values are flagged

**Error Message**:
```
Finding:     Generic API key pattern
Secret:      test_api_key_placeholder
RuleID:      generic-api-key
File:        tests/fixtures/example.json:10
```

**Cause**: The pattern matches a rule, but it's a test value or placeholder.

**Solution**:

Add to `.gitleaks.toml` allowlist:

```toml
[allowlist]
# Exclude by file path
paths = [
  '''tests/fixtures/.*''',  # All test fixtures
]

# Or exclude by pattern
regexes = [
  '''test_api_key_placeholder''',  # Specific value
]
```

**Prevention**: Use obviously fake patterns in test data: `test_token_12345`, `fake_api_key`, etc.

---

### Issue: Hook Not Running

**Symptoms**:
- Commits succeed without seeing the "Scanning staged files..." message
- The hook doesn't execute

**Cause**: The hook file doesn't exist, isn't executable, or was overwritten.

**Solution**:

Reinstall the hook:

```bash
make secrets-install
```

Verify it's executable:

```bash
ls -la .git/hooks/pre-commit
```

Should show: `-rwxr-xr-x` (executable flag)

**Prevention**: Don't manually edit `.git/hooks/` unless necessary. Use `make secrets-install` to reinstall.

---

### Issue: Slow Scans

**Symptoms**:
- Commits take 30+ seconds
- High CPU usage during commits

**Cause**: You're scanning the wrong files (e.g., running `gitleaks detect --source .` instead of using the hook).

**Solution**:

Use the Makefile commands:

```bash
# Fast - staged files only (milliseconds)
make secrets-check

# Slow - full history (seconds)
make secrets-scan  # Only when needed
```

Make sure the pre-commit hook uses `gitleaks protect --staged` (already configured).

**Prevention**: Never run `gitleaks detect --source .` manually - it scans all files including gitignored ones.

---

### Issue: CI/CD Failing on Secrets

**Symptoms**:
- GitHub Actions workflow fails with secret detection
- CI blocks the PR merge

**Error Message**:
```
gitleaks detected secrets in your commit
```

**Cause**: A secret was committed and pushed to the remote repository.

**Solution**:

1. **Remove the secret** from the file
2. **Add to `.env` file** (gitignored)
3. **Commit the fix**:
   ```bash
   git add .
   git commit -m "fix: remove hardcoded secret, use environment variable"
   git push
   ```

4. **If the secret is in history**, you need to rewrite history:
   ```bash
   # WARNING: This rewrites git history
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/file" \
     --prune-empty --tag-name-filter cat -- --all

   # Force push (coordinate with team!)
   git push origin --force --all
   ```

5. **Rotate the exposed secret** - Change the password/token immediately, as it's now in git history.

**Prevention**: Always use the pre-commit hook and never bypass it without good reason.

---

## Performance Tips

- **Use `make secrets-check` for daily work**: Scans staged files only (~25-50ms)
- **Use `make secrets-scan` sparingly**: Full history scans are slower (~2-10s depending on repo size)
- **Let the hook do its job**: The automatic pre-commit hook is the fastest and most convenient
- **Exclude gitignored directories**: Already configured in `.gitleaks.toml` to skip `data/`, `logs/`, etc.

### Benchmarks

| Operation | Time | What It Scans |
|-----------|------|---------------|
| Pre-commit hook | 25-50ms | Staged files only |
| `make secrets-check` | 25-50ms | Staged files only |
| `make secrets-scan` | 2-10s | Full git history |
| CI/CD scan | 20-40s | Full repo + history |

---

## Next Steps

After setting up secret scanning, you might want to:

1. **Set up environment variables**: See [Configuration Guide](configuration.md) for `.env` file management
2. **Configure branch protection**: Require secret scanning to pass before PR merges
3. **Review testing practices**: See [Testing Guide](../operations/testing.md) for secure test fixtures

---

## Related Documentation

### Related How-To Guides

- [Configuration](configuration.md) - Managing environment variables and secrets
- [Troubleshooting](troubleshooting.md) - Common development issues

### Reference Documentation

- [CI/CD Quick Reference](../operations/cicd-quick-reference.md) - GitHub Actions workflows

### External Resources

- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks) - Official gitleaks docs
- [Gitleaks Configuration](https://github.com/gitleaks/gitleaks#configuration) - Writing custom rules
- [Pre-commit Hooks](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) - Git hooks documentation

---

## Feedback

Found an issue with this guide? Please:

- Open an issue: [GitHub Issues](https://github.com/yourusername/somali-dialect-classifier/issues)
- Suggest improvements: Submit a PR
- Ask questions: Use GitHub Discussions

---

**Maintainers**: Somali NLP Contributors
