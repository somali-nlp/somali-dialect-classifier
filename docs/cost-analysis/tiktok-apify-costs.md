# TikTok Apify Cost Analysis

**Comprehensive cost analysis for TikTok comment scraping via Apify, including linguistic yield realities and budget optimization strategies.**

**Last Updated:** 2025-11-21

---

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Apify Pricing (Verified)](#apify-pricing-verified)
- [The Linguistic Comment Reality](#the-linguistic-comment-reality)
  - [Key Discovery: 67% Emoji-Only Loss](#key-discovery-67-emoji-only-loss)
  - [What Counts as "Linguistic"?](#what-counts-as-linguistic)
  - [Why This Matters](#why-this-matters)
- [Why You Can't Avoid Emoji-Only Comments](#why-you-cant-avoid-emoji-only-comments)
- [Budget Scenarios](#budget-scenarios)
  - [Scenario 1: Test Run (1,000 comments)](#scenario-1-test-run-1000-comments)
  - [Scenario 2: Medium Test (5,000 comments)](#scenario-2-medium-test-5000-comments)
  - [Scenario 3: Starter Plan Budget ($49)](#scenario-3-starter-plan-budget-49)
  - [Scenario 4: Full 30k Linguistic Target](#scenario-4-full-30k-linguistic-target)
- [Cost Optimization Strategies](#cost-optimization-strategies)
  - [1. Smart Video Selection](#1-smart-video-selection)
  - [2. Avoid Re-scraping](#2-avoid-re-scraping)
  - [3. Batch Video Lists](#3-batch-video-lists)
  - [4. Set Realistic Expectations](#4-set-realistic-expectations)
- [Cost Monitoring](#cost-monitoring)
  - [Real-Time Monitoring](#real-time-monitoring)
  - [Post-Run Analysis](#post-run-analysis)
- [Budget Planning Timeline](#budget-planning-timeline)
  - [Phase 1: Testing (Week 1) - $5](#phase-1-testing-week-1-5)
  - [Phase 2: Production (Week 2) - $44](#phase-2-production-week-2-44)
  - [Phase 3: Validation (Week 2-3)](#phase-3-validation-week-2-3)
- [Cost-Saving Checklist](#cost-saving-checklist)
- [ROI Analysis](#roi-analysis)
  - [Value Comparison](#value-comparison)
  - [Time Savings](#time-savings)
  - [Research Value](#research-value)
- [Recommendations](#recommendations)
  - [For Testing Phase](#for-testing-phase)
  - [For Production Phase](#for-production-phase)
  - [Budget Discipline](#budget-discipline)
- [Conclusion](#conclusion)

---

## Executive Summary

**Verified pricing:** $1 USD per 1,000 comments scraped

**Critical reality:** 67% of TikTok comments are emoji-only (no linguistic value)

**Effective cost:** $3.03 per 1,000 linguistic comments

**Budget options:**
- **Option A (Starter Plan - $39):** ~12,870 linguistic comments from 39,000 scraped
- **Option B (Full Target - $91):** ~30,030 linguistic comments from 91,000 scraped

---

## Apify Pricing (Verified)

**Confirmed pricing:** **$1 USD per 1,000 results**

This pricing was verified through:
- Test run: 1,111 comments = $1.11 charge
- Apify documentation confirmation
- Direct account billing verification

**Plan Details:**

| Plan | Monthly Cost | Results Included | Cost/1k Results |
|------|--------------|------------------|-----------------|
| **Free tier** | $0 | 5,000 | $1.00 (credit) |
| **Starter** | $49 | 49,000 | $1.00 |
| **Team** | $499 | 499,000 | $1.00 |

**Important:** Pricing is per **result returned**, not compute units (CU). TikTok Comments Scraper charges based on comments scraped, regardless of runtime.

---

## The Linguistic Comment Reality

### Key Discovery: 67% Emoji-Only Loss

**Verified with 1,111 comment dataset:**

```
Apify Scrapes: 1,000 comments → $1.00 charged
     ↓
Raw JSONL: 1,000 items saved (100% - audit trail)
     ↓
Linguistic Filter (removes emoji-only, <3 chars text)
     ↓
Staging JSONL: ~330 linguistic comments (33%)
     ↓
Processing (minimal whitespace cleaning)
     ↓
Silver Parquet: ~271 comments (82% of linguistic)
```

**Real-World Test Results:**

| Stage | Count | Percentage |
|-------|-------|------------|
| Scraped (charged) | 1,111 | 100% |
| Linguistic | 368 | 33.1% |
| Final silver | 303 | 27.3% (82.3% of linguistic) |
| **Cost** | **$1.11** | **Effective: $3.67/1k linguistic** |

### What Counts as "Linguistic"?

Comments filtered at transform stage:

```python
# Filtered:
- Empty text → skip
- Emoji-only (no alphanumeric after removing symbols) → skip
- Too short (<3 characters of actual text) → skip

# Kept:
- Any comment with ≥3 characters of Somali/English text
- Mixed emoji + text (text extracted)
- Code-switching (Somali + English/Arabic)
```

### Why This Matters

- **Budget calculations** must account for 67% emoji-only loss
- **30k linguistic comments** require 91k total scraped
- **Original estimates** assumed 100% usable → now only 33% usable
- **Effective cost** is 3x higher than raw scraping cost

---

## Why You Can't Avoid Emoji-Only Comments

**Q: Can I configure Apify to skip emoji-only comments?**

**A: No - This is impossible with current technology.**

The Apify TikTok Comments Scraper has only **3 input parameters**:

```python
actor_input = {
    "postURLs": [list_of_video_urls],        # Which videos to scrape
    "commentsPerPost": 100000,                # Max number per video
    "proxy": {"useApifyProxy": True}          # Proxy settings
}
```

**NO content filtering options exist:**
- ❌ No emoji detection/filtering
- ❌ No text length filters
- ❌ No language detection
- ❌ No quality filters
- ❌ No content-based filtering of any kind

**Why this limitation exists:**

1. **TikTok API design** - Comment text is not exposed before downloading
2. **Apify billing model** - You're charged when a comment is scraped, not when you keep it
3. **Platform constraints** - No way to "peek" at comment content without downloading it fully

**This means:**
- You MUST pay for all comments Apify scrapes (including 67% emoji-only)
- Content filtering happens AFTER downloading (in your local code)
- This is a **fundamental platform limitation**, not a configuration issue

**Your options:**

1. ✅ **Accept the reality** (Recommended)
   - Budget for $3.03 per 1,000 linguistic comments
   - Filter locally after download
   - Keep all raw data for audit trail

2. ✅ **Strategic video selection**
   - Choose news/educational content (40-45% linguistic yield)
   - Avoid music/entertainment videos (20-30% linguistic yield)
   - Slightly improves ratio but doesn't eliminate cost

3. ❌ **Build custom scraper**
   - Violates TikTok Terms of Service
   - High development and maintenance cost
   - Legal risks and IP bans
   - NOT recommended

---

## Budget Scenarios

### Scenario 1: Test Run (1,000 comments)

**Purpose:** Initial testing, validation

| Component | Scraped | Linguistic | Cost |
|-----------|---------|------------|------|
| Comments scraped | 1,000 | ~330 (33%) | $1.00 |
| Final silver | - | ~271 (82% of linguistic) | - |
| **Total** | **1,000** | **~271 usable** | **$1.00** |

**Recommended for:**
- Initial testing
- Validation of data quality
- Pipeline integration testing

### Scenario 2: Medium Test (5,000 comments)

**Purpose:** Quality validation, filter tuning

| Component | Scraped | Linguistic | Cost |
|-----------|---------|------------|------|
| Comments scraped | 5,000 | ~1,650 (33%) | $5.00 |
| Final silver | - | ~1,353 (82% of linguistic) | - |
| **Total** | **5,000** | **~1,353 usable** | **$5.00** |

**Recommended for:**
- Quality validation
- Filter tuning
- Dialect distribution analysis

### Scenario 3: Starter Plan Budget ($49)

**Purpose:** Maximum dataset within Starter plan

| Component | Scraped | Linguistic | Cost |
|-----------|---------|------------|------|
| Comments scraped | 49,000 | ~16,170 (33%) | $49.00 |
| Final silver | - | ~13,259 (82% of linguistic) | - |
| **Total** | **49,000** | **~13,259 usable** | **$49.00** |

**Videos needed:** ~221 videos (at 222 avg comments/video)

**Recommended for:**
- Maximum dataset within Starter plan budget
- Sufficient for dialect classification

### Scenario 4: Full 30k Linguistic Target

**Purpose:** Target 30,000 linguistic comments

| Component | Scraped | Linguistic | Cost |
|-----------|---------|------------|------|
| Comments scraped | 91,000 | ~30,037 (33%) | $91.00 |
| Final silver | - | ~24,630 (82% of linguistic) | - |
| **Total** | **91,000** | **~24,630 usable** | **$91.00** |

**Videos needed:** ~410 videos (at 222 avg comments/video)

**Recommended for:**
- Full 30k linguistic target
- Requires Team plan ($499) or one-time $91 budget

---

## Cost Optimization Strategies

### 1. Smart Video Selection

**Maximize linguistic yield through strategic video selection:**

**High-yield videos (40-45% linguistic):**
- News and current events
- Educational content
- Political discussions
- Cultural topics

**Low-yield videos (20-30% linguistic):**
- Music and dance videos
- Comedy/memes
- Entertainment content
- Viral trends

**Pre-filtering checklist:**
- ✅ Check visible comment count (150+ minimum)
- ✅ Verify Somali language in visible comments
- ✅ Prioritize 150-400 comment range (good ROI)
- ✅ Include some viral videos (500+) for diversity
- ✅ Mix topics and creators for dialect diversity

**Impact:**
- Potentially improve to 40% linguistic yield
- Better quality per dollar
- More diverse Somali usage patterns

### 2. Avoid Re-scraping

**Implement proper deduplication:**

```bash
# Check ledger before scraping
python -c "
from somali_dialect_classifier.preprocessing.tiktok_somali_processor import TikTokSomaliProcessor
processor = TikTokSomaliProcessor(...)
# Processor automatically checks ledger for duplicates
"
```

**Impact:**
- Prevent duplicate charges
- Maximize dataset diversity
- Critical for staying within budget

### 3. Batch Video Lists

**Combine videos into single runs:**

```python
# Instead of multiple small runs
# 5 runs × 27 videos = overhead + complexity

# Do one large batch
# 1 run × 135 videos = efficient + simple
processor.run(video_urls=all_135_videos)
```

**Impact:**
- Reduced API calls
- Simpler tracking
- Potentially lower overhead

### 4. Set Realistic Expectations

**Use verified averages:**
- Actual average: **222 comments/video** (verified by test)
- Plan for 150-300 comment range
- Don't expect viral levels from every video

**Impact:**
- Accurate budget planning
- No surprises in final cost
- Realistic dataset targets

---

## Cost Monitoring

### Real-Time Monitoring

**1. Apify Console Dashboard:**
- URL: https://console.apify.com/account/usage
- Track: Results scraped, cost accrued
- Alerts: Set at 80% of budget

**2. Ledger Tracking:**
```bash
# Count unique URLs fetched
grep -c "^" data/ledger/tiktok-*.ledger

# Estimate cost from ledger
python -c "
import glob
count = sum(1 for f in glob.glob('data/ledger/tiktok-*.ledger') for _ in open(f))
print(f'Comments: {count}, Cost: \${count/1000:.2f}')
"
```

**3. Pre-Run Validation:**
```python
# Before running large batch
estimated_comments = len(video_urls) * 222  # avg per video
estimated_cost = estimated_comments / 1000
print(f"Estimated cost: ${estimated_cost:.2f}")

# Confirm budget
if estimated_cost > remaining_budget:
    print("WARNING: Exceeds budget!")
```

### Post-Run Analysis

**Check metrics:**

```bash
# View extraction metrics
cat data/metrics/*tiktok*extraction.json | jq '.layered_metrics.extraction'

# Calculate actual cost
python -c "
import json
with open('data/metrics/tiktok_extraction.json') as f:
    metrics = json.load(f)
    comments = metrics['layered_metrics']['extraction']['urls_fetched']
    cost = comments / 1000
    print(f'Actual: {comments} comments = \${cost:.2f}')
"
```

---

## Budget Planning Timeline

### Phase 1: Testing (Week 1) - $5

**Goal:** Validate integration and data quality

**Plan:**
- Small test (1k comments): $1
- Review quality, fix issues: $0
- Medium test (4k comments): $4

**Total:** $5 from testing reserve

**Deliverable:** Confirmed working pipeline, quality data

### Phase 2: Production (Week 2) - $44

**Goal:** Collect production comments

**Plan:**
- Collect ~200 video URLs: $0 (manual, 60-90 min)
- Submit to Apify: $44 (~44k comments)
- Monitor scraping: $0 (2-3 hours runtime)
- Quality validation: $0

**Total:** $44 production budget

**Deliverable:** ~44,000 scraped comments → ~14,520 linguistic comments

### Phase 3: Validation (Week 2-3)

**Goal:** Verify dataset quality

**Plan:**
- Dialect distribution analysis
- Quality spot-checks
- Additional samples if needed (from remaining budget)

**Deliverable:** Validated, high-quality linguistic dataset

---

## Cost-Saving Checklist

Before running production scrape:

- [ ] **Test completed**: 1k+ comment test run successful
- [ ] **Video list optimized**: 150+ comments each verified
- [ ] **Duplicates removed**: Checked against ledger
- [ ] **Budget confirmed**: Videos × 222 avg = cost estimate
- [ ] **Quality filters enabled**: Length, deduplication active
- [ ] **Monitoring setup**: Apify alerts configured
- [ ] **Somali verification**: Spot-checked comment language quality
- [ ] **Backup plan**: Know which videos to skip if over budget

---

## ROI Analysis

### Value Comparison

**Market comparison (informal estimates):**
- Social media text data: $0.05-0.20 per comment
- Dialect-labeled data: $0.50-2.00 per comment
- 30k comments market value: $1,500-60,000

**Our cost:** $91 for 30k linguistic comments

**ROI:** 16x to 660x value vs cost

### Time Savings

**Equivalent manual collection:**
- Time per comment: ~30 seconds (find, copy, clean)
- Total time: 30k × 30 sec = 250 hours
- At $15/hour volunteer time: $3,750

**Our cost:** $91 (automated scraping)

**Time savings:** 97.6% reduction ($3,659 saved)

### Research Value

**For nonprofit/academic research:**
- High-quality colloquial Somali text
- Diverse dialect representation
- Modern social media register
- Enables dialect classification research
- Supports Somali NLP advancement

---

## Recommendations

### For Testing Phase

**Budget:** $5

**Plan:**
1. Small test (1k comments): $1
2. Validate quality and integration
3. Medium test (4k comments): $4
4. Confirm pipeline works correctly

**Total:** $5, preserves remaining budget for production

### For Production Phase

**Option A: Starter Plan Budget ($49)**
- Scrape: 49,000 comments
- Linguistic yield: ~16,170 comments
- Videos needed: ~221
- Recommended if budget-constrained

**Option B: Full Target ($91)**
- Scrape: 91,000 comments
- Linguistic yield: ~30,030 comments
- Videos needed: ~410
- Recommended for comprehensive dataset

### Budget Discipline

**Critical rules:**

1. **Track spend continuously**
   - Monitor Apify console
   - Check ledger comment counts
   - Stop if approaching limit

2. **Reserve budget for testing**
   - Catch bugs before production
   - Validate data quality
   - Avoid wasting production budget

3. **Prioritize quality over quantity**
   - Curated video selection critical
   - 13k quality comments > 50k low-quality
   - Don't scrape marginal videos to hit quota

---

## Conclusion

**Key Takeaways:**

1. **Verified pricing:** $1 per 1,000 comments scraped
2. **Linguistic reality:** 67% emoji-only, 33% linguistic yield
3. **Effective cost:** $3.03 per 1,000 linguistic comments
4. **Budget options:** $49 (13k linguistic) or $91 (30k linguistic)
5. **Quality focus:** Curated videos maximize value per dollar

**Realistic Budget Options:**

| Budget | Scraped | Linguistic | Videos | Best For |
|--------|---------|------------|--------|----------|
| $5 | 5,000 | ~1,650 | 23 | Testing |
| $49 | 49,000 | ~16,170 | 221 | Starter plan max |
| $91 | 91,000 | ~30,030 | 410 | Full 30k target |

**Bottom Line:**

The 67% emoji-only loss is **unavoidable** - it's a characteristic of TikTok social media data, not a bug. Budget accordingly:
- For **testing**: Start with $5 (5k comments → 1.6k linguistic)
- For **Starter plan**: Use full $49 (49k → 16k linguistic)
- For **30k target**: Budget $91 (91k → 30k linguistic)

**ROI remains excellent:** High-quality colloquial Somali text with diverse dialects at a fraction of manual collection cost.

---

## Related Documentation

- [TikTok Integration Guide](../howto/tiktok-integration.md) - Complete TikTok scraping setup and usage
- [Data Pipeline Architecture](../overview/data-pipeline-architecture.md) - Overall pipeline design
- [Budget Planning](../roadmap/future-work.md) - Project budget and resource allocation

**Maintainers**: Somali NLP Contributors
