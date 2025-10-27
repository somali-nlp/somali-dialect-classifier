# User Acceptance Testing (UAT) Session Guide

> Structured guide for conducting user acceptance testing sessions for the Somali Dialect Classifier Dashboard

**Version:** 1.0
**Last Updated:** 2025-10-27
**Session Duration:** 45 minutes

---

## Table of Contents

1. [Overview](#overview)
2. [User Personas](#user-personas)
3. [Pre-Session Preparation](#pre-session-preparation)
4. [Session Structure](#session-structure)
5. [Test Scenarios](#test-scenarios)
6. [Feedback Collection](#feedback-collection)
7. [Success Criteria](#success-criteria)
8. [Post-Session Analysis](#post-session-analysis)

---

## Overview

### Purpose
Validate that the dashboard meets the needs of both technical and non-technical users through structured testing sessions with representative users.

### Goals
- Verify dashboard is intuitive and easy to navigate
- Confirm all key metrics are accessible and understandable
- Identify usability issues and pain points
- Gather feature requests and improvement suggestions
- Validate accessibility and inclusive design

### Methodology
- Think-Aloud Protocol: Users verbalize their thought process
- Task-Based Testing: Users complete specific scenarios
- Semi-Structured Interviews: Open-ended feedback collection
- Quantitative Metrics: Task completion rate, time to insight

---

## User Personas

### Persona 1: Technical Contributor (Data Engineer)

**Profile:**
- **Name**: "Alex" (Data Engineer)
- **Experience**: 5+ years in data engineering
- **Technical Level**: High
- **Primary Goals**:
  - Monitor pipeline health and performance
  - Debug data quality issues
  - Optimize throughput and resource usage
  - Track error rates and types

**Usage Pattern:**
- Frequency: Daily
- Session Length: 10-30 minutes
- Depth: Deep dives into specific sources and metrics
- Actions: Download data, cross-reference with logs, investigate anomalies

**Key Questions They Ask:**
- "Why did the BBC source fail yesterday?"
- "Which source has the best quality-to-speed ratio?"
- "Are we hitting our throughput targets?"
- "What's causing the deduplication spike?"

---

### Persona 2: Non-Technical Sponsor (Project Manager)

**Profile:**
- **Name**: "Jordan" (Project Manager)
- **Experience**: Limited technical background, strong in project management
- **Technical Level**: Low-Medium
- **Primary Goals**:
  - Track overall project progress
  - Report status to stakeholders
  - Understand if project is "on track"
  - Communicate data quality to sponsors

**Usage Pattern:**
- Frequency: Weekly
- Session Length: 5-10 minutes
- Depth: High-level overview, summary statistics
- Actions: Screenshot metrics, copy key numbers for reports

**Key Questions They Ask:**
- "How many records have we collected?"
- "Is the data good quality?"
- "Are we making progress this week?"
- "What should I tell our sponsors?"

---

## Pre-Session Preparation

### 1. Environment Setup (30 minutes before)

**Dashboard Configuration:**
- [ ] Deploy dashboard with realistic test data
- [ ] Ensure all metrics are populated (not empty state)
- [ ] Verify all charts render correctly
- [ ] Test on target browser/device

**Test Data Requirements:**
- At least 4 data sources with metrics
- Mix of successful and failed runs
- Variety of quality rates (60%-100%)
- Different pipeline types represented
- Realistic timestamps (recent data)

**Equipment Checklist:**
- [ ] Computer with dashboard deployed
- [ ] Screen recording software running
- [ ] Audio recording setup (if separate)
- [ ] Notepad/device for facilitator notes
- [ ] Stopwatch/timer
- [ ] Printed scenario cards
- [ ] Feedback form (digital or paper)

### 2. Participant Briefing (5 minutes)

**Introduction Script:**
> "Thank you for participating in this usability test. We're testing our new data dashboard to make sure it works well for people like you. There are no right or wrong answers—we're testing the dashboard, not you.
>
> Please think aloud as you use the dashboard. Tell us what you're looking for, what you're thinking, and any reactions you have. If something is confusing, please tell us. Your honest feedback helps us improve.
>
> The session will take about 45 minutes. We'll record your screen and audio for analysis, but your information will remain confidential. Do you have any questions before we begin?"

**Consent:**
- [ ] Explain recording and how data will be used
- [ ] Obtain verbal or written consent
- [ ] Confirm participant understands they can stop anytime

---

## Session Structure

### Part 1: First Impressions (5 minutes)

**Objective:** Capture initial reactions and understand intuitiveness

**Instructions to Participant:**
> "I'm going to show you a dashboard. Don't click anything yet—just look at it for a moment and tell me what you think it shows."

**Facilitator Actions:**
- Open dashboard to homepage
- Start timer when page loads
- Observe participant's eye movement
- Note first words/reactions

**Questions to Ask:**
- "What is this dashboard for?"
- "Who do you think uses this?"
- "What are the most important numbers you see?"
- "Is there anything confusing or unclear?"

**What to Record:**
- Time to comprehend purpose (<30 seconds ideal)
- Elements mentioned first (hero stats, charts, etc.)
- Confusion points or questions
- Positive reactions ("Oh, I like...")

---

### Part 2: Guided Task Scenarios (20 minutes)

**Scenario Delivery:**
- Provide one scenario card at a time
- Read scenario aloud
- Allow participant to work independently
- Only intervene if completely stuck (after 3 minutes)

**For Each Scenario:**
- [ ] Start timer
- [ ] Record participant actions (clicks, scrolls, hovers)
- [ ] Note verbal comments
- [ ] Record completion time
- [ ] Ask follow-up questions

---

### Part 3: Exploratory Testing (10 minutes)

**Objective:** Discover unexpected behaviors and feature discovery

**Instructions:**
> "Now I'd like you to explore the dashboard freely. Imagine you're using this for the first time on your own. Click around, try different features, and tell me what you find."

**Facilitator Actions:**
- Step back and observe
- Note which features are discovered
- Record features that are ignored/missed
- Note any "aha!" moments

**Questions During Exploration:**
- "What are you curious about?"
- "Is this what you expected when you clicked that?"
- "Have you seen everything you wanted to see?"

---

### Part 4: Accessibility Check (5 minutes)

**Keyboard Navigation Test:**
> "Could you try navigating the dashboard using only the Tab key and Enter? Don't use your mouse."

**Observations:**
- Can user reach all interactive elements?
- Is focus indicator visible?
- Does tab order make sense?
- Can user activate tabs and buttons?

**Screen Reader Test (if applicable):**
- Enable screen reader (VoiceOver, NVDA, JAWS)
- Ask user to navigate one section
- Note announcements and clarity

---

### Part 5: Feedback Collection (10 minutes)

**Structured Questionnaire:** (See [Feedback Form](#feedback-form) below)

**Open-Ended Discussion:**
- "What did you like most?"
- "What frustrated you?"
- "What would you change?"
- "Would you use this regularly? Why or why not?"
- "Anything else you want to tell us?"

---

## Test Scenarios

### Scenarios for Technical Contributor (Alex)

#### Scenario 1: Investigating Pipeline Failure

**Context Card:**
```
SCENARIO: Investigating a Drop in Records

You noticed that yesterday's BBC Somali ingestion produced
fewer records than usual. Use the dashboard to investigate.

TASK:
1. Find the BBC Somali source metrics
2. Determine the success rate
3. Identify how many records were written
4. Check the quality metrics
5. Try to understand what might have gone wrong

Success: You can explain what happened with the BBC source.
```

**Expected Actions:**
- Navigate to Dashboard section
- Click "Overview" or "Data Sources" tab
- Locate BBC Somali card
- Read success rate and record count
- Possibly click Quality tab for more details
- May attempt to download metrics JSON

**Time Limit:** 3 minutes
**Success Criteria:**
- User finds BBC metrics within 90 seconds
- User can state success rate and record count
- User attempts to find error information

---

#### Scenario 2: Comparing Source Performance

**Context Card:**
```
SCENARIO: Optimizing Pipeline Performance

You want to optimize pipeline throughput. Compare all sources
to identify which one is slowest and could benefit from optimization.

TASK:
1. Find performance metrics for all sources
2. Compare URLs/second across sources
3. Identify the slowest performing source
4. Check if there's a trade-off between speed and quality

Success: You can recommend which source to optimize first.
```

**Expected Actions:**
- Navigate to "Pipeline Performance" tab
- Review performance cards for all 4 sources
- Compare URLs/second values
- Possibly cross-reference with Quality tab
- Make a recommendation

**Time Limit:** 4 minutes
**Success Criteria:**
- User finds performance tab within 60 seconds
- User compares at least 3 sources
- User identifies slowest source correctly

---

#### Scenario 3: Downloading Metrics for Analysis

**Context Card:**
```
SCENARIO: Offline Analysis

You need to perform deeper analysis in Python/Excel.
Download the metrics data for offline use.

TASK:
1. Find where to download metrics
2. Download the data
3. Verify what format it's in

Success: You have downloaded the metrics file.
```

**Expected Actions:**
- Navigate to "Technical Reports" tab
- Find "Metrics Report (JSON)" card
- Click download button
- Verify JSON file downloaded

**Time Limit:** 2 minutes
**Success Criteria:**
- User finds download within 90 seconds
- User successfully downloads file
- User recognizes JSON format

---

### Scenarios for Non-Technical Sponsor (Jordan)

#### Scenario 4: Weekly Progress Report

**Context Card:**
```
SCENARIO: Weekly Stakeholder Update

You need to report project progress to sponsors in your
weekly meeting (happening in 5 minutes!).

TASK:
1. Find the total number of records collected
2. Determine the overall data quality
3. Identify how many data sources are active
4. Prepare a simple summary (1-2 sentences)

Success: You can confidently report progress to stakeholders.
```

**Expected Actions:**
- Look at hero section statistics
- Note total records number
- Find quality percentage
- Count data sources
- Formulate summary statement

**Time Limit:** 2 minutes
**Success Criteria:**
- User finds key metrics without clicking (hero section)
- User can state numbers within 90 seconds
- User formulates coherent summary

---

#### Scenario 5: Understanding Data Quality

**Context Card:**
```
SCENARIO: Quality Assurance Question

Your sponsor asks: "Is the data good enough to use for
training machine learning models?"

TASK:
1. Find information about data quality
2. Determine what "quality" means in this context
3. Decide if you can answer the sponsor's question
4. Prepare a response

Success: You can confidently answer yes/no with a reason.
```

**Expected Actions:**
- Look for "Quality" information
- Possibly navigate to Quality Metrics tab
- Look for help text or explanations
- Read quality percentages
- Formulate answer

**Time Limit:** 3 minutes
**Success Criteria:**
- User finds quality information within 90 seconds
- User understands what quality metric represents
- User can form a yes/no answer

---

#### Scenario 6: Creating a Screenshot for Report

**Context Card:**
```
SCENARIO: Visual for Presentation

You're creating a slide deck and want to include a
visual showing the project's data sources and progress.

TASK:
1. Find the best view to screenshot
2. Identify what would look good in a presentation
3. Take a screenshot (pretend to)
4. Explain why you chose that view

Success: You select an appropriate, professional-looking view.
```

**Expected Actions:**
- Scroll through dashboard
- Evaluate different sections
- Possibly choose Overview tab or Data Sources
- Explain choice

**Time Limit:** 2 minutes
**Success Criteria:**
- User selects a visually clear section
- User can explain their choice
- Selection would work in presentation

---

## Feedback Collection

### Feedback Form

**Section 1: Usability (1-5 scale)**

Rate the following statements (1 = Strongly Disagree, 5 = Strongly Agree):

1. [ ] The dashboard is easy to navigate
2. [ ] I can find the information I need quickly
3. [ ] Charts and visualizations are clear and understandable
4. [ ] The layout is visually appealing
5. [ ] Text is readable and jargon-free (or well-explained)
6. [ ] The dashboard loads quickly
7. [ ] I feel confident using this dashboard
8. [ ] The dashboard meets my needs
9. [ ] I would use this dashboard regularly
10. [ ] I would recommend this dashboard to colleagues

**Section 2: Functionality**

1. Did all features work as expected? **[ ] Yes [ ] No**
   - If no, what didn't work? _______________________

2. Did you encounter any bugs or errors? **[ ] Yes [ ] No**
   - If yes, describe: _______________________

3. Was any information missing that you expected to see? **[ ] Yes [ ] No**
   - If yes, what? _______________________

**Section 3: Open Feedback**

1. What did you like MOST about the dashboard?
   ```
   _________________________________________________
   _________________________________________________
   ```

2. What FRUSTRATED you most?
   ```
   _________________________________________________
   _________________________________________________
   ```

3. If you could change ONE thing, what would it be?
   ```
   _________________________________________________
   _________________________________________________
   ```

4. What features did you NOT use or notice?
   ```
   _________________________________________________
   _________________________________________________
   ```

5. Any other comments, suggestions, or concerns?
   ```
   _________________________________________________
   _________________________________________________
   _________________________________________________
   ```

---

## Success Criteria

### Quantitative Metrics

**Task Completion:**
- [ ] >90% of scenarios completed successfully
- [ ] <2 hints required per participant
- [ ] Zero critical failures (unable to complete with help)

**Time to Insight:**
- [ ] Key metrics found within 60 seconds (Persona 2)
- [ ] Specific metrics found within 120 seconds (Persona 1)
- [ ] Download action completed within 90 seconds

**User Satisfaction:**
- [ ] Average rating >4.0/5 across usability questions
- [ ] >80% would use dashboard regularly
- [ ] >85% would recommend to colleagues

**Accessibility:**
- [ ] 100% of participants can navigate with keyboard
- [ ] All text readable without zooming (Persona 2)
- [ ] No complaints about color contrast

### Qualitative Indicators

**Positive Signals:**
- Unprompted positive comments ("Oh, this is nice!")
- Quick comprehension of purpose (<30 seconds)
- Smooth task completion without backtracking
- Feature discovery during exploration
- Confident answers to scenario questions

**Warning Signals:**
- Confusion about terminology or layout
- Multiple attempts to find information
- Frustration expressed (verbal or non-verbal)
- Unexpected use of features
- Giving up on tasks

---

## Post-Session Analysis

### Immediate Debrief (5 minutes after session)

**Facilitator Notes:**
- Overall impression of session
- Most significant issues observed
- Unexpected behaviors
- Feature requests mentioned
- Accessibility concerns

### Data Compilation

**For Each Participant:**
1. Demographic info (persona type, experience level)
2. Task completion rates and times
3. Usability ratings
4. Verbatim quotes (positive and negative)
5. Feature usage heatmap (what was clicked)
6. Video recording filename

### Cross-Participant Analysis

**Aggregate Metrics:**
- Average task completion rate by scenario
- Mean time to complete each scenario
- Average usability ratings
- Common themes in feedback

**Issue Prioritization:**
```
SEVERITY MATRIX:

Critical (P0):
- Prevents task completion
- Affects >50% of users
- Data accuracy issues
- Accessibility blockers

High (P1):
- Major usability issue
- Affects >30% of users
- Causes significant frustration
- Workaround exists but difficult

Medium (P2):
- Minor usability issue
- Affects <30% of users
- Has easy workaround
- Quality-of-life improvement

Low (P3):
- Cosmetic issue
- Nice-to-have feature
- Affects <10% of users
- No impact on core tasks
```

### Report Template

**Executive Summary:**
- Number of participants
- Overall success rate
- Key findings (3-5 bullets)
- Recommended next steps

**Detailed Findings:**
For each scenario:
- Completion rate
- Average time
- Common issues
- Participant quotes

**Recommendations:**
1. Critical fixes required before launch
2. High-priority improvements for v1.1
3. Medium-priority enhancements
4. Low-priority future considerations

**Appendix:**
- Individual session summaries
- Video recordings index
- Raw feedback forms
- Screenshots of issues

---

## Session Recording Template

**Participant ID:** ______ **Persona:** [ ] Technical [ ] Non-Technical
**Date:** __________ **Session Duration:** ______

### First Impressions
- Time to comprehend purpose: _____ seconds
- Initial reaction: _______________________
- Elements noticed first: _______________________

### Scenario Results

| Scenario | Completed? | Time | Issues | Notes |
|----------|-----------|------|--------|-------|
| 1        | Y / N     | __s  |        |       |
| 2        | Y / N     | __s  |        |       |
| 3        | Y / N     | __s  |        |       |

### Usability Ratings
Navigation: ___/5 | Speed: ___/5 | Clarity: ___/5 | Overall: ___/5

### Key Quotes
1. _______________________
2. _______________________
3. _______________________

### Top Issues Observed
1. _______________________
2. _______________________
3. _______________________

### Recommendations from This Session
- [ ] Critical: _______________________
- [ ] High: _______________________
- [ ] Medium: _______________________

---

## Appendix: Facilitator Tips

### Do's
- Remain neutral and non-defensive
- Encourage thinking aloud
- Take detailed notes
- Observe non-verbal cues
- Allow silence (don't rush to help)
- Thank participant genuinely

### Don'ts
- Don't defend design choices
- Don't lead the participant
- Don't explain how to use features (unless stuck >3 minutes)
- Don't interrupt their process
- Don't show disappointment in their struggles

### If Participant Gets Stuck
1. Wait 30 seconds silently
2. Ask: "What are you thinking right now?"
3. If still stuck after 2 minutes: "What would you expect to find this?"
4. If stuck after 3 minutes: Provide minimal hint
5. If still stuck: Mark as failed, move to next scenario

### Reading Body Language
- **Leaning forward** = engaged, interested
- **Leaning back** = confused, overwhelmed
- **Furrowed brow** = concentration or confusion
- **Smiling/nodding** = satisfaction, comprehension
- **Sighing** = frustration
- **Rapid clicking** = lost, searching

---

**End of UAT Session Guide**

For questions or support conducting UAT sessions, contact the UX Research team.
