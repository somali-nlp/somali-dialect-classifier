# Dashboard Testing Suite

Comprehensive testing infrastructure for the Somali Dialect Classifier Dashboard, including visual regression, accessibility, integration, and unit tests.

## Quick Start

### Prerequisites

**Python 3.12+**
```bash
pip install -e ".[dev]"
```

**Node.js 18+**
```bash
npm install
npm run install:browsers
```

### Running Tests

**All Tests:**
```bash
# Python unit tests
pytest tests/unit/dashboard/ -v

# Playwright tests (visual + accessibility + integration)
npm test
```

**Specific Test Suites:**
```bash
# Visual regression tests
npm run test:visual

# Accessibility tests
npm run test:a11y

# Integration tests
npm run test:integration

# Interactive UI mode
npm run test:ui
```

---

## Test Suite Overview

### 1. Visual Regression Tests (`tests/visual/`)

**Purpose:** Catch unintended visual changes in dashboard UI

**Technology:** Playwright with screenshot comparison

**Coverage:**
- Full page snapshots at multiple breakpoints
- Component-level snapshots
- Interactive states (hover, focus, active)
- High-contrast theme
- Responsive layouts

**Running:**
```bash
npm run test:visual
```

**Updating Baselines:**
```bash
npm run update-snapshots
```

**Key Tests:**
- `dashboard-full-page.spec.js` - Full page snapshots and responsive breakpoints
- `dashboard-interactive-states.spec.js` - Hover, focus, tab navigation states

---

### 2. Accessibility Tests (`tests/accessibility/`)

**Purpose:** Ensure WCAG 2.1 AA compliance

**Technology:** Playwright + axe-core

**Coverage:**
- Color contrast ratios
- Keyboard navigation
- ARIA attributes
- Semantic HTML
- Screen reader compatibility
- Focus management

**Running:**
```bash
npm run test:a11y
```

**Key Tests:**
- `wcag-compliance.spec.js` - Automated WCAG 2.1 AA validation

**Zero Tolerance:** Accessibility tests must pass with zero violations.

---

### 3. Integration Tests (`tests/integration/`)

**Purpose:** Test end-to-end data flow from source to dashboard

**Technology:** pytest + Playwright

**Coverage:**
- Data pipeline processing
- Metrics generation
- Dashboard rendering
- Chart initialization
- Error handling

**Running:**
```bash
# Python integration tests
pytest tests/integration/ -v

# Playwright integration tests
npm run test:integration
```

**Key Tests:**
- `test_e2e_data_flow.py` - Complete pipeline to dashboard flow
- `test_ci_job.py` - GitHub Actions workflow simulation

---

### 4. Unit Tests (`tests/unit/dashboard/`)

**Purpose:** Test data pipeline logic in isolation

**Technology:** pytest

**Coverage:**
- Schema validation (v3.0, v2.0)
- Null/missing value handling
- Edge cases (zero records, large numbers, unicode)
- Metrics calculations
- Pipeline-specific metrics extraction

**Running:**
```bash
pytest tests/unit/dashboard/ -v --cov
```

**Coverage Goal:** >85%

**Key Tests:**
- `test_metrics_schema_validation.py` - Schema parsing and validation
- Additional tests match the comprehensive strategy

---

## Directory Structure

```
tests/
├── README.md                           # This file
├── conftest.py                         # Shared pytest fixtures
├── fixtures/
│   ├── metrics/                        # Sample metrics JSON files
│   │   └── create_sample_metrics.py    # Generate test data
│   └── html/                           # Sample HTML for testing
├── unit/
│   └── dashboard/
│       └── test_metrics_schema_validation.py
├── visual/
│   ├── playwright.config.js            # Playwright configuration
│   ├── dashboard-full-page.spec.js
│   └── dashboard-interactive-states.spec.js
├── accessibility/
│   └── wcag-compliance.spec.js
├── integration/
│   ├── playwright/                     # Playwright integration tests
│   ├── test_e2e_data_flow.py
│   └── test_ci_job.py
└── uat/
    └── UAT_SESSION_GUIDE.md            # User acceptance testing guide
```

---

## CI/CD Integration

### GitHub Actions Workflow

**File:** `.github/workflows/dashboard-tests.yml`

**Jobs:**
1. **Python Unit Tests** - Run unit tests with coverage
2. **Build Dashboard** - Build static site and generate metrics
3. **Visual Regression** - Screenshot comparison tests
4. **Accessibility** - WCAG compliance validation
5. **Integration Tests** - End-to-end pipeline tests
6. **Test Summary** - Aggregate results and report

**PR Checks:**
- All tests must pass before merge
- Coverage must be >85%
- Zero accessibility violations
- Visual regressions must be approved

**Viewing Results:**
```
GitHub PR → Checks tab → Dashboard Testing Suite
```

---

## Test Data Management

### Sample Metrics Generation

**Generate Test Data:**
```bash
python tests/fixtures/create_sample_metrics.py
```

**Output:** `data/metrics/*_processing.json`

This creates realistic v3.0 schema metrics for:
- Wikipedia-Somali (web_scraping)
- BBC-Somali (web_scraping)
- HuggingFace-Somali (stream_processing)
- Sprakbanken-Somali (file_processing)

### Fixtures

**Location:** `tests/fixtures/metrics/`

Fixtures include:
- Valid v3.0 schemas for all pipeline types
- Invalid/malformed JSON for error testing
- Edge cases (zero records, unicode, large numbers)

---

## Writing New Tests

### Visual Regression Test Template

```javascript
import { test, expect } from '@playwright/test';

test.describe('New Feature Visual Tests', () => {
  test('new feature renders correctly @visual', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const feature = page.locator('.new-feature');
    await expect(feature).toHaveScreenshot('new-feature.png');
  });
});
```

### Accessibility Test Template

```javascript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('new feature is accessible @a11y', async ({ page }) => {
  await page.goto('/');

  const results = await new AxeBuilder({ page })
    .include('.new-feature')
    .analyze();

  expect(results.violations).toEqual([]);
});
```

### Unit Test Template

```python
import pytest

class TestNewFeature:
    """Test new feature logic"""

    def test_feature_with_valid_input(self):
        """Should handle valid input correctly"""
        result = process_feature(valid_input)
        assert result == expected_output

    def test_feature_with_invalid_input(self):
        """Should handle invalid input gracefully"""
        result = process_feature(invalid_input)
        assert result == default_value
```

---

## Debugging Tests

### Visual Test Failures

**View HTML Report:**
```bash
npm run show-report
```

**Run in UI Mode:**
```bash
npm run test:ui
```

**Run with Browser Open:**
```bash
npm run test:headed
```

**Debug Specific Test:**
```bash
npm run test:debug tests/visual/dashboard-full-page.spec.js
```

### Python Test Failures

**Verbose Output:**
```bash
pytest tests/unit/dashboard/ -vv
```

**Stop on First Failure:**
```bash
pytest tests/unit/dashboard/ -x
```

**Run Specific Test:**
```bash
pytest tests/unit/dashboard/test_metrics_schema_validation.py::TestSchemaValidation::test_valid_v3_web_scraping_schema -v
```

**Debug with pdb:**
```bash
pytest tests/unit/dashboard/ --pdb
```

---

## Test Coverage

### Checking Coverage

**Python:**
```bash
pytest tests/unit/dashboard/ --cov=scripts --cov-report=html
open htmlcov/index.html
```

**JavaScript/Playwright:**
Coverage is tracked via Istanbul for JS code, but primarily we track:
- Functional coverage (features tested)
- Visual coverage (UI states captured)
- Accessibility coverage (WCAG checkpoints)

### Coverage Goals

| Category | Target | Current |
|----------|--------|---------|
| Python Code | 85% | TBD |
| Functional Features | 100% | TBD |
| WCAG 2.1 AA | 100% | TBD |
| Visual States | 90% | TBD |

---

## Performance Benchmarks

### Test Execution Times

**Target Times:**
- Unit Tests: <30 seconds
- Visual Regression: <5 minutes
- Accessibility: <2 minutes
- Integration: <3 minutes
- **Total CI Run:** <15 minutes

**Monitoring:**
Check GitHub Actions run times in CI logs.

---

## User Acceptance Testing (UAT)

**Guide:** `tests/uat/UAT_SESSION_GUIDE.md`

### UAT Process

1. **Recruit Participants**
   - 2 Technical Contributors (Data Engineers)
   - 2 Non-Technical Sponsors (Project Managers)

2. **Prepare Environment**
   - Deploy dashboard with test data
   - Set up screen recording
   - Print scenario cards

3. **Run Sessions** (45 minutes each)
   - First impressions (5 min)
   - Guided scenarios (20 min)
   - Exploratory testing (10 min)
   - Feedback collection (10 min)

4. **Analyze Results**
   - Calculate task completion rates
   - Identify common issues
   - Prioritize improvements

**See full guide for detailed instructions.**

---

## Troubleshooting

### Common Issues

**Issue: Playwright browsers not installed**
```bash
npm run install:browsers
```

**Issue: Visual tests failing with minor pixel differences**
- Check if intentional change
- Update baselines: `npm run update-snapshots`
- Adjust threshold in `playwright.config.js`

**Issue: Accessibility tests failing**
- Review axe-core violations in HTML report
- Fix WCAG issues (contrast, ARIA, etc.)
- Zero tolerance - must fix before merge

**Issue: Tests passing locally but failing in CI**
- Ensure deterministic data (no random values)
- Check for timing issues (add proper waits)
- Verify environment consistency

**Issue: Sample metrics not generating**
```bash
chmod +x tests/fixtures/create_sample_metrics.py
python tests/fixtures/create_sample_metrics.py
```

---

## Best Practices

### Test Design

1. **Isolation:** Each test should be independent
2. **Determinism:** Tests should produce same results every time
3. **Speed:** Keep tests fast (<30s per test)
4. **Clarity:** Use descriptive test names and comments
5. **Maintainability:** Avoid duplication, use fixtures

### Test Naming

**Format:** `test_<what>_<scenario>_<expected>`

**Good:**
- `test_dashboard_renders_correctly_on_mobile`
- `test_metrics_schema_validates_v3_web_scraping`
- `test_tab_navigation_works_with_keyboard`

**Bad:**
- `test_dashboard` (too vague)
- `test1`, `test2` (no context)
- `test_everything` (not focused)

### Tags

Use tags to categorize tests:

**Playwright:**
- `@visual` - Visual regression tests
- `@a11y` - Accessibility tests
- `@responsive` - Responsive layout tests
- `@chart` - Chart rendering tests
- `@keyboard` - Keyboard navigation tests

**pytest:**
- `@integration` - Integration tests
- `@slow` - Tests >5 seconds
- `@requires_network` - Needs internet access

---

## Contributing

### Adding New Tests

1. **Create Test File**
   - Place in appropriate directory
   - Follow naming convention
   - Add descriptive docstring

2. **Write Test**
   - Use provided templates
   - Follow best practices
   - Add appropriate tags

3. **Run Locally**
   - Verify test passes
   - Check doesn't break existing tests
   - Ensure meets coverage goals

4. **Update Documentation**
   - Add to test coverage list
   - Update README if needed
   - Document any new fixtures

5. **Submit PR**
   - Include test rationale in PR description
   - Link to related issue/feature
   - Wait for CI checks

---

## Resources

### Documentation

- [DASHBOARD_TESTING_STRATEGY.md](../DASHBOARD_TESTING_STRATEGY.md) - Comprehensive strategy
- [UAT_SESSION_GUIDE.md](uat/UAT_SESSION_GUIDE.md) - User acceptance testing guide
- [Playwright Docs](https://playwright.dev) - Playwright documentation
- [pytest Docs](https://docs.pytest.org) - pytest documentation
- [axe-core](https://github.com/dequelabs/axe-core) - Accessibility testing

### Tools

- **Playwright Inspector:** `npm run test:debug`
- **Playwright UI Mode:** `npm run test:ui`
- **HTML Report:** `npm run show-report`
- **Coverage Report:** `pytest --cov-report=html`

---

## Support

For questions or issues with the testing suite:

1. Check this README and the testing strategy doc
2. Review existing test examples
3. Search GitHub issues
4. Ask in project discussions
5. Contact the QA team

---

**Last Updated:** 2025-10-27
**Maintained by:** Somali NLP Initiative - QA Team
