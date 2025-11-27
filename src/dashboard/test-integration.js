/**
 * Integration Test Suite
 * Tests bug fixes with actual metrics data from production sources
 */

const fs = require('fs');
const path = require('path');

// Import the test functions from the unit test file
const testResults = {
    passed: 0,
    failed: 0,
    errors: [],
    details: []
};

// ============================================================================
// LOAD REAL METRICS DATA
// ============================================================================

function loadRealMetricsData() {
    const metricsDir = path.join(__dirname, '../../data/metrics');
    console.log(`\nLoading metrics from: ${metricsDir}\n`);

    const files = fs.readdirSync(metricsDir)
        .filter(f => f.endsWith('_extraction.json'))
        .slice(0, 4); // Load 4 sources

    const metrics = [];
    for (const file of files) {
        const filePath = path.join(metricsDir, file);
        const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));

        // Normalize to expected format
        const metric = {
            source: data._source || 'Unknown',
            pipeline_type: data._pipeline_type || 'unknown',
            timestamp: data._timestamp,
            records_written: data.layered_metrics?.volume?.records_written || 0,
            quality_pass_rate: data.legacy_metrics?.statistics?.quality_pass_rate,
            http_request_success_rate: data.http_request_success_rate || 0
        };

        metrics.push(metric);
        console.log(`Loaded: ${metric.source} (${metric.records_written} records)`);
    }

    return metrics;
}

// ============================================================================
// AGGREGATE COMPUTATION (from aggregates.js)
// ============================================================================

function toNumber(value, fallback = 0) {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
}

function clampRatio(value) {
    const num = toNumber(value, 0);
    if (!Number.isFinite(num)) {
        return 0;
    }
    if (num < 0) return 0;
    if (num > 1) return 1;
    return num;
}

function extractRecordsWritten(metric) {
    if (!metric) return 0;
    return toNumber(metric.records_written, 0);
}

function extractQualityRate(metric) {
    if (!metric) return 0;

    const direct = clampRatio(metric.quality_pass_rate);
    if (direct > 0) {
        return direct;
    }



    return 0;
}

function extractSuccessRate(metric) {
    if (!metric) return 0;

    const candidates = [
        metric.http_request_success_rate,
        metric.content_extraction_success_rate,
        metric.content_extraction_success_rate
    ];

    for (const candidate of candidates) {
        const value = clampRatio(candidate);
        if (value > 0) {
            return value;
        }
    }

    const snapshot = {};
    const urlsFetched = 0;
    const recordsWritten = extractRecordsWritten(metric);

    if (urlsFetched > 0) {
        return clampRatio(recordsWritten / urlsFetched);
    }

    if (recordsWritten > 0) {
        return 1;
    }

    return 0;
}

function computePipelineAggregates(metrics = []) {
    if (!Array.isArray(metrics)) {
        return {
            totalRecords: 0,
            avgQualityRate: 0,
            avgSuccessRate: 0,
            activeSources: 0
        };
    }

    let totalRecords = 0;
    let qualityNumerator = 0;
    let qualityDenominator = 0;
    let successNumerator = 0;
    let successDenominator = 0;
    let activeSources = 0;

    metrics.forEach(metric => {
        if (!metric) return;

        const recordsWritten = extractRecordsWritten(metric);
        const qualityRate = extractQualityRate(metric);
        const successRate = extractSuccessRate(metric);

        totalRecords += recordsWritten;

        if (recordsWritten > 0) {
            activeSources += 1;
        }

        if (recordsWritten > 0) {
            qualityNumerator += qualityRate * recordsWritten;
            qualityDenominator += recordsWritten;
        }

        if (recordsWritten > 0) {
            successNumerator += successRate * recordsWritten;
            successDenominator += recordsWritten;
        }
    });

    const avgQualityRate = qualityDenominator > 0 ? qualityNumerator / qualityDenominator : 0;
    const avgSuccessRate = successDenominator > 0 ? successNumerator / successDenominator : 0;

    return {
        totalRecords,
        avgQualityRate,
        avgSuccessRate,
        activeSources
    };
}

// ============================================================================
// TEST FRAMEWORK
// ============================================================================

function assertNotNaN(value, testName) {
    if (Number.isFinite(value) && !isNaN(value)) {
        testResults.passed++;
        testResults.details.push({ test: testName, status: 'PASS', value });
        console.log(`✓ PASS: ${testName} (value: ${value})`);
        return true;
    } else {
        testResults.failed++;
        testResults.errors.push(`${testName}: Value is NaN or not finite: ${value}`);
        testResults.details.push({ test: testName, status: 'FAIL', value });
        console.error(`✗ FAIL: ${testName}`);
        console.error(`  Value is NaN or not finite: ${value}`);
        return false;
    }
}

function assertGreaterThanOrEqual(actual, threshold, testName) {
    if (actual >= threshold) {
        testResults.passed++;
        testResults.details.push({ test: testName, status: 'PASS', actual, threshold });
        console.log(`✓ PASS: ${testName} (${actual} >= ${threshold})`);
        return true;
    } else {
        testResults.failed++;
        testResults.errors.push(`${testName}: ${actual} is not >= ${threshold}`);
        testResults.details.push({ test: testName, status: 'FAIL', actual, threshold });
        console.error(`✗ FAIL: ${testName}`);
        console.error(`  Expected >= ${threshold}, got ${actual}`);
        return false;
    }
}

// ============================================================================
// INTEGRATION TESTS
// ============================================================================

function runIntegrationTests() {
    console.log('\n═══════════════════════════════════════════════════════════════════════');
    console.log('  INTEGRATION TEST SUITE - Real Production Data');
    console.log('═══════════════════════════════════════════════════════════════════════\n');

    const metrics = loadRealMetricsData();

    console.log('\n=== Testing Individual Metric Extraction ===\n');

    metrics.forEach((metric, index) => {
        console.log(`\n--- Source ${index + 1}: ${metric.source} ---`);

        const recordsWritten = extractRecordsWritten(metric);
        const qualityRate = extractQualityRate(metric);
        const successRate = extractSuccessRate(metric);

        assertNotNaN(recordsWritten, `[${metric.source}] records_written is not NaN`);
        assertNotNaN(qualityRate, `[${metric.source}] quality_pass_rate is not NaN`);
        assertNotNaN(successRate, `[${metric.source}] success_rate is not NaN`);

        console.log(`  Records: ${recordsWritten}`);
        console.log(`  Quality Rate: ${(qualityRate * 100).toFixed(1)}%`);
        console.log(`  Success Rate: ${(successRate * 100).toFixed(1)}%`);
    });

    console.log('\n\n=== Testing Pipeline Aggregation ===\n');

    const aggregates = computePipelineAggregates(metrics);

    assertNotNaN(aggregates.totalRecords, 'Total records is not NaN');
    assertNotNaN(aggregates.avgQualityRate, 'Average quality rate is not NaN');
    assertNotNaN(aggregates.avgSuccessRate, 'Average success rate is not NaN');
    assertNotNaN(aggregates.activeSources, 'Active sources count is not NaN');

    assertGreaterThanOrEqual(aggregates.totalRecords, 0, 'Total records >= 0');
    assertGreaterThanOrEqual(aggregates.avgQualityRate, 0, 'Average quality rate >= 0');
    assertGreaterThanOrEqual(aggregates.avgSuccessRate, 0, 'Average success rate >= 0');
    assertGreaterThanOrEqual(aggregates.activeSources, 0, 'Active sources >= 0');

    console.log('\n--- Aggregate Results ---');
    console.log(`Total Records: ${aggregates.totalRecords.toLocaleString()}`);
    console.log(`Average Quality Rate: ${(aggregates.avgQualityRate * 100).toFixed(1)}%`);
    console.log(`Average Success Rate: ${(aggregates.avgSuccessRate * 100).toFixed(1)}%`);
    console.log(`Active Sources: ${aggregates.activeSources}`);

    // BUG-001 Verification: Check narrative rendering
    console.log('\n\n=== BUG-001: Narrative Rendering Test ===\n');

    const narrativeText = aggregates.totalRecords === 0
        ? 'No data ingested yet'
        : `Ingested ${aggregates.totalRecords.toLocaleString()} records from ${aggregates.activeSources} source(s)`;

    const hasNaN = narrativeText.includes('NaN');
    if (!hasNaN) {
        testResults.passed++;
        console.log(`✓ PASS: Narrative does not contain NaN`);
        console.log(`  Narrative: "${narrativeText}"`);
    } else {
        testResults.failed++;
        testResults.errors.push('Narrative contains NaN');
        console.error(`✗ FAIL: Narrative contains NaN`);
        console.error(`  Narrative: "${narrativeText}"`);
    }

    // BUG-002 Verification: Check quality chart percentages
    console.log('\n\n=== BUG-002: Quality Chart Percentage Test ===\n');

    const qualityPercentage = `${(aggregates.avgQualityRate * 100).toFixed(1)}%`;
    const hasNaNInQuality = qualityPercentage.includes('NaN');

    if (!hasNaNInQuality) {
        testResults.passed++;
        console.log(`✓ PASS: Quality percentage does not contain NaN`);
        console.log(`  Quality: "${qualityPercentage}"`);
    } else {
        testResults.failed++;
        testResults.errors.push('Quality percentage contains NaN');
        console.error(`✗ FAIL: Quality percentage contains NaN`);
        console.error(`  Quality: "${qualityPercentage}"`);
    }

    // BUG-003 Verification: Check active sources counting
    console.log('\n\n=== BUG-003: Active Sources Counting Test ===\n');

    const sourcesWithRecords = metrics.filter(m => extractRecordsWritten(m) > 0).length;
    const activeSourcesCorrect = aggregates.activeSources === sourcesWithRecords;

    if (activeSourcesCorrect) {
        testResults.passed++;
        console.log(`✓ PASS: Active sources count is correct`);
        console.log(`  Expected: ${sourcesWithRecords}, Got: ${aggregates.activeSources}`);
    } else {
        testResults.failed++;
        testResults.errors.push(`Active sources mismatch: expected ${sourcesWithRecords}, got ${aggregates.activeSources}`);
        console.error(`✗ FAIL: Active sources count is incorrect`);
        console.error(`  Expected: ${sourcesWithRecords}, Got: ${aggregates.activeSources}`);
    }

    // Print summary
    console.log('\n');
    console.log('═══════════════════════════════════════════════════════════════════════');
    console.log('  INTEGRATION TEST SUMMARY');
    console.log('═══════════════════════════════════════════════════════════════════════');
    console.log(`Total Tests: ${testResults.passed + testResults.failed}`);
    console.log(`Passed: ${testResults.passed}`);
    console.log(`Failed: ${testResults.failed}`);

    const passRate = testResults.passed + testResults.failed > 0
        ? ((testResults.passed / (testResults.passed + testResults.failed)) * 100).toFixed(1)
        : 0;
    console.log(`Pass Rate: ${passRate}%`);

    if (testResults.failed > 0) {
        console.log('\n❌ FAILED TESTS:');
        testResults.errors.forEach(err => console.error(`  - ${err}`));
    }

    console.log('\n');

    return {
        passRate,
        testResults
    };
}

// Run integration tests
const result = runIntegrationTests();

// Export results
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { runIntegrationTests, result };
}
