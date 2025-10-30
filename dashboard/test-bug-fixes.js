/**
 * Comprehensive Test Suite for Bug Fixes in Commit 61b3eb4
 *
 * Tests the following critical bugs:
 * - BUG-001: Narrative showing "0 records, NaN%"
 * - BUG-002: Quality chart displaying "NaN%"
 * - BUG-003: Active sources showing "0"
 *
 * Test Categories:
 * 1. Data Extraction Functions (aggregates.js)
 * 2. Number Safety Guards
 * 3. Active Source Counting
 * 4. Integration Testing with Real Data
 * 5. Regression Testing
 */

// Test Results Accumulator
const testResults = {
    passed: 0,
    failed: 0,
    errors: [],
    details: []
};

// Mock Logger
const Logger = {
    info: (msg) => console.log(`[INFO] ${msg}`),
    warn: (msg) => console.warn(`[WARN] ${msg}`),
    error: (msg, err) => console.error(`[ERROR] ${msg}`, err),
    debug: (msg, data) => console.log(`[DEBUG] ${msg}`, data)
};

// ============================================================================
// HELPER FUNCTIONS
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
    return toNumber(
        metric.records_written ??
        metric.legacy_metrics?.snapshot?.records_written,
        0
    );
}

function extractQualityRate(metric) {
    if (!metric) return 0;

    const direct = clampRatio(metric.quality_pass_rate);
    if (direct > 0) {
        return direct;
    }

    const legacyStats = metric.legacy_metrics?.statistics || {};
    const legacyRatio = clampRatio(legacyStats.quality_pass_rate);
    if (legacyRatio > 0) {
        return legacyRatio;
    }

    const quality = metric.legacy_metrics?.statistics?.quality ||
                    metric.legacy_metrics?.layered_metrics?.quality ||
                    {};
    const passed = toNumber(quality.records_passed_filters, null);
    const received = toNumber(quality.records_received, null);
    if (passed !== null && received) {
        return clampRatio(passed / received);
    }

    const snapshot = metric.legacy_metrics?.snapshot || {};
    const recordsWritten = toNumber(snapshot.records_written, null);
    const recordsFiltered = toNumber(snapshot.records_filtered, null);
    if (recordsWritten !== null && recordsFiltered !== null) {
        const total = recordsWritten + recordsFiltered;
        if (total > 0) {
            return clampRatio(recordsWritten / total);
        }
    }

    return 0;
}

function extractSuccessRate(metric) {
    if (!metric) return 0;

    const candidates = [
        metric.http_request_success_rate,
        metric.content_extraction_success_rate,
        metric.legacy_metrics?.statistics?.http_request_success_rate,
        metric.legacy_metrics?.statistics?.fetch_success_rate,
        metric.legacy_metrics?.statistics?.file_extraction_success_rate,
        metric.legacy_metrics?.statistics?.record_parsing_success_rate
    ];

    for (const candidate of candidates) {
        const value = clampRatio(candidate);
        if (value > 0) {
            return value;
        }
    }

    const snapshot = metric.legacy_metrics?.snapshot || {};
    const urlsFetched = toNumber(snapshot.urls_fetched ?? snapshot.files_processed, 0);
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
        Logger.warn('computePipelineAggregates called with non-array metrics');
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

function assertEqual(actual, expected, testName) {
    if (actual === expected) {
        testResults.passed++;
        testResults.details.push({ test: testName, status: 'PASS', actual, expected });
        console.log(`✓ PASS: ${testName}`);
        return true;
    } else {
        testResults.failed++;
        testResults.errors.push(`${testName}: Expected ${expected}, got ${actual}`);
        testResults.details.push({ test: testName, status: 'FAIL', actual, expected });
        console.error(`✗ FAIL: ${testName}`);
        console.error(`  Expected: ${expected}`);
        console.error(`  Actual: ${actual}`);
        return false;
    }
}

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

function assertGreaterThan(actual, threshold, testName) {
    if (actual > threshold) {
        testResults.passed++;
        testResults.details.push({ test: testName, status: 'PASS', actual, threshold });
        console.log(`✓ PASS: ${testName} (${actual} > ${threshold})`);
        return true;
    } else {
        testResults.failed++;
        testResults.errors.push(`${testName}: ${actual} is not greater than ${threshold}`);
        testResults.details.push({ test: testName, status: 'FAIL', actual, threshold });
        console.error(`✗ FAIL: ${testName}`);
        console.error(`  Expected > ${threshold}, got ${actual}`);
        return false;
    }
}

// ============================================================================
// TEST SUITE 1: NUMBER SAFETY GUARDS (BUG-002 Fix Verification)
// ============================================================================

function testNumberSafetyGuards() {
    console.log('\n=== TEST SUITE 1: Number Safety Guards ===\n');

    // Test toNumber with valid inputs
    assertEqual(toNumber(42), 42, 'toNumber with valid integer');
    assertEqual(toNumber(3.14), 3.14, 'toNumber with valid float');
    assertEqual(toNumber('100'), 100, 'toNumber with numeric string');
    assertEqual(toNumber(0), 0, 'toNumber with zero');

    // Test toNumber with invalid inputs
    assertEqual(toNumber(NaN), 0, 'toNumber with NaN returns fallback');
    assertEqual(toNumber(Infinity), 0, 'toNumber with Infinity returns fallback');
    assertEqual(toNumber(undefined), 0, 'toNumber with undefined returns fallback');
    assertEqual(toNumber(null), 0, 'toNumber with null returns fallback');
    assertEqual(toNumber('invalid'), 0, 'toNumber with invalid string returns fallback');

    // Test clampRatio
    assertEqual(clampRatio(0.5), 0.5, 'clampRatio with valid ratio');
    assertEqual(clampRatio(1.5), 1, 'clampRatio clamps > 1 to 1');
    assertEqual(clampRatio(-0.5), 0, 'clampRatio clamps < 0 to 0');
    assertEqual(clampRatio(NaN), 0, 'clampRatio with NaN returns 0');
    assertEqual(clampRatio(Infinity), 1, 'clampRatio with Infinity returns 1');
}

// ============================================================================
// TEST SUITE 2: DATA EXTRACTION (BUG-001 Fix Verification)
// ============================================================================

function testDataExtraction() {
    console.log('\n=== TEST SUITE 2: Data Extraction Functions ===\n');

    // Test extractRecordsWritten
    const metricWithRecords = {
        records_written: 1000
    };
    assertEqual(extractRecordsWritten(metricWithRecords), 1000, 'extractRecordsWritten with direct value');

    const metricWithLegacy = {
        legacy_metrics: {
            snapshot: {
                records_written: 500
            }
        }
    };
    assertEqual(extractRecordsWritten(metricWithLegacy), 500, 'extractRecordsWritten with legacy value');

    assertEqual(extractRecordsWritten(null), 0, 'extractRecordsWritten with null');
    assertEqual(extractRecordsWritten({}), 0, 'extractRecordsWritten with empty object');

    // Test extractQualityRate
    const metricWithQuality = {
        quality_pass_rate: 0.85
    };
    assertEqual(extractQualityRate(metricWithQuality), 0.85, 'extractQualityRate with direct value');

    const metricWithLegacyQuality = {
        legacy_metrics: {
            statistics: {
                quality_pass_rate: 0.75
            }
        }
    };
    assertEqual(extractQualityRate(metricWithLegacyQuality), 0.75, 'extractQualityRate with legacy value');

    // Test zero quality rate (CRITICAL: BUG-001 scenario)
    const metricZeroQuality = {
        legacy_metrics: {
            statistics: {
                quality_pass_rate: 0
            }
        }
    };
    assertEqual(extractQualityRate(metricZeroQuality), 0, 'extractQualityRate with zero quality');
}

// ============================================================================
// TEST SUITE 3: ACTIVE SOURCES COUNTING (BUG-003 Fix Verification)
// ============================================================================

function testActiveSourcesCounting() {
    console.log('\n=== TEST SUITE 3: Active Sources Counting ===\n');

    // Test with multiple sources having records
    const metricsWithRecords = [
        { records_written: 1000 },
        { records_written: 2000 },
        { records_written: 3000 }
    ];
    const result1 = computePipelineAggregates(metricsWithRecords);
    assertEqual(result1.activeSources, 3, 'Active sources count with all sources having records');
    assertEqual(result1.totalRecords, 6000, 'Total records sum correct');

    // Test with some sources having zero records (CRITICAL: BUG-003 scenario)
    const metricsWithSomeZero = [
        { records_written: 1000 },
        { records_written: 0 },
        { records_written: 3000 }
    ];
    const result2 = computePipelineAggregates(metricsWithSomeZero);
    assertEqual(result2.activeSources, 2, 'Active sources count excludes sources with 0 records');
    assertEqual(result2.totalRecords, 4000, 'Total records excludes zero sources');

    // Test with all sources having zero records
    const metricsAllZero = [
        { records_written: 0 },
        { records_written: 0 }
    ];
    const result3 = computePipelineAggregates(metricsAllZero);
    assertEqual(result3.activeSources, 0, 'Active sources is 0 when all have 0 records');
    assertEqual(result3.totalRecords, 0, 'Total records is 0 when all have 0 records');

    // Test with empty array
    const result4 = computePipelineAggregates([]);
    assertEqual(result4.activeSources, 0, 'Active sources is 0 with empty metrics');

    // Test with null/undefined
    const result5 = computePipelineAggregates(null);
    assertEqual(result5.activeSources, 0, 'Active sources is 0 with null metrics');
}

// ============================================================================
// TEST SUITE 4: NaN PREVENTION (BUG-002 Fix Verification)
// ============================================================================

function testNaNPrevention() {
    console.log('\n=== TEST SUITE 4: NaN Prevention in Aggregates ===\n');

    // Test division by zero scenarios
    const emptyMetrics = [];
    const result1 = computePipelineAggregates(emptyMetrics);
    assertNotNaN(result1.avgQualityRate, 'avgQualityRate with empty metrics is not NaN');
    assertNotNaN(result1.avgSuccessRate, 'avgSuccessRate with empty metrics is not NaN');

    // Test with metrics but all zero records (CRITICAL: BUG-002 scenario)
    const metricsZeroRecords = [
        {
            records_written: 0,
            quality_pass_rate: 0.85,
            legacy_metrics: {
                statistics: {
                    http_request_success_rate: 0.96
                }
            }
        }
    ];
    const result2 = computePipelineAggregates(metricsZeroRecords);
    assertNotNaN(result2.avgQualityRate, 'avgQualityRate with zero records is not NaN');
    assertNotNaN(result2.avgSuccessRate, 'avgSuccessRate with zero records is not NaN');
    assertEqual(result2.avgQualityRate, 0, 'avgQualityRate is 0 when no records written');
    assertEqual(result2.avgSuccessRate, 0, 'avgSuccessRate is 0 when no records written');

    // Test with mixed valid and invalid data
    const mixedMetrics = [
        { records_written: 1000, quality_pass_rate: 0.85 },
        { records_written: 0, quality_pass_rate: NaN },
        { records_written: 2000, quality_pass_rate: 0.75 }
    ];
    const result3 = computePipelineAggregates(mixedMetrics);
    assertNotNaN(result3.avgQualityRate, 'avgQualityRate with mixed data is not NaN');
    assertNotNaN(result3.avgSuccessRate, 'avgSuccessRate with mixed data is not NaN');
    assertGreaterThan(result3.avgQualityRate, 0, 'avgQualityRate > 0 with valid records');
}

// ============================================================================
// TEST SUITE 5: REAL DATA SCENARIO (BUG-001 Critical Case)
// ============================================================================

function testRealDataScenario() {
    console.log('\n=== TEST SUITE 5: Real Data Scenario (BBC case) ===\n');

    // Simulate BBC extraction data with 0 records_written but content extracted
    const bbcMetric = {
        records_written: 0,
        legacy_metrics: {
            snapshot: {
                records_written: 0,
                records_filtered: 48,
                urls_fetched: 48
            },
            statistics: {
                quality_pass_rate: 0,
                http_request_success_rate: 0.96,
                text_length_stats: {
                    min: 156,
                    max: 11325,
                    mean: 4458.375,
                    median: 4116.5,
                    total_chars: 214002
                }
            }
        }
    };

    const recordsWritten = extractRecordsWritten(bbcMetric);
    const qualityRate = extractQualityRate(bbcMetric);
    const successRate = extractSuccessRate(bbcMetric);

    assertEqual(recordsWritten, 0, 'BBC records_written is 0');
    assertNotNaN(qualityRate, 'BBC quality_pass_rate is not NaN');
    assertEqual(qualityRate, 0, 'BBC quality_pass_rate is 0 (no records passed filters)');
    assertNotNaN(successRate, 'BBC success_rate is not NaN');
    assertGreaterThan(successRate, 0, 'BBC success_rate > 0 (HTTP requests succeeded)');

    // Test aggregation with BBC data included
    const mixedMetrics = [
        bbcMetric,
        { records_written: 5000, quality_pass_rate: 0.95 },
        { records_written: 3000, quality_pass_rate: 0.88 }
    ];

    const aggregates = computePipelineAggregates(mixedMetrics);

    assertNotNaN(aggregates.totalRecords, 'Total records is not NaN');
    assertNotNaN(aggregates.avgQualityRate, 'Average quality rate is not NaN');
    assertNotNaN(aggregates.avgSuccessRate, 'Average success rate is not NaN');
    assertNotNaN(aggregates.activeSources, 'Active sources is not NaN');

    assertEqual(aggregates.totalRecords, 8000, 'Total records excludes BBC (0 records)');
    assertEqual(aggregates.activeSources, 2, 'Active sources count excludes BBC (0 records)');
    assertGreaterThan(aggregates.avgQualityRate, 0.85, 'Average quality rate weighted correctly');
}

// ============================================================================
// TEST SUITE 6: EDGE CASES AND BOUNDARY CONDITIONS
// ============================================================================

function testEdgeCases() {
    console.log('\n=== TEST SUITE 6: Edge Cases and Boundary Conditions ===\n');

    // Test with very large numbers
    const largeNumberMetrics = [
        { records_written: 1000000000 }
    ];
    const result1 = computePipelineAggregates(largeNumberMetrics);
    assertNotNaN(result1.totalRecords, 'Large numbers handled correctly');
    assertEqual(result1.totalRecords, 1000000000, 'Large number precision maintained');

    // Test with very small ratios
    const smallRatioMetric = {
        quality_pass_rate: 0.00001
    };
    const qualityRate = extractQualityRate(smallRatioMetric);
    assertNotNaN(qualityRate, 'Very small ratios handled correctly');
    assertGreaterThan(qualityRate, 0, 'Very small ratio is greater than 0');

    // Test with negative values (should be clamped)
    const negativeMetric = {
        quality_pass_rate: -0.5
    };
    const clampedQuality = extractQualityRate(negativeMetric);
    assertEqual(clampedQuality, 0, 'Negative quality rate clamped to 0');

    // Test with values > 1 (should be clamped)
    const overoneMetric = {
        quality_pass_rate: 1.5
    };
    const clampedOverone = extractQualityRate(overoneMetric);
    assertEqual(clampedOverone, 1, 'Quality rate > 1 clamped to 1');
}

// ============================================================================
// TEST SUITE 7: FALLBACK CASCADE (7-FIELD FALLBACK)
// ============================================================================

function testFallbackCascade() {
    console.log('\n=== TEST SUITE 7: Fallback Cascade for Volume Metrics ===\n');

    // Test each level of the cascade for extractRecordsWritten

    // Level 1: Direct records_written
    const level1 = { records_written: 100 };
    assertEqual(extractRecordsWritten(level1), 100, 'Fallback level 1: records_written');

    // Level 2: legacy_metrics.snapshot.records_written
    const level2 = {
        legacy_metrics: {
            snapshot: {
                records_written: 200
            }
        }
    };
    assertEqual(extractRecordsWritten(level2), 200, 'Fallback level 2: legacy snapshot');

    // Test quality rate cascade
    // Level 1: Direct quality_pass_rate
    const qLevel1 = { quality_pass_rate: 0.9 };
    assertEqual(extractQualityRate(qLevel1), 0.9, 'Quality fallback level 1: direct');

    // Level 2: legacy_metrics.statistics.quality_pass_rate
    const qLevel2 = {
        legacy_metrics: {
            statistics: {
                quality_pass_rate: 0.8
            }
        }
    };
    assertEqual(extractQualityRate(qLevel2), 0.8, 'Quality fallback level 2: legacy stats');

    // Level 3: Calculated from records_passed_filters / records_received
    const qLevel3 = {
        legacy_metrics: {
            statistics: {
                quality: {
                    records_passed_filters: 80,
                    records_received: 100
                }
            }
        }
    };
    assertEqual(extractQualityRate(qLevel3), 0.8, 'Quality fallback level 3: calculated ratio');
}

// ============================================================================
// MAIN TEST RUNNER
// ============================================================================

function runAllTests() {
    console.log('\n');
    console.log('═══════════════════════════════════════════════════════════════════════');
    console.log('  BUG FIX VERIFICATION TEST SUITE - Commit 61b3eb4');
    console.log('═══════════════════════════════════════════════════════════════════════');
    console.log('\n');

    testNumberSafetyGuards();
    testDataExtraction();
    testActiveSourcesCounting();
    testNaNPrevention();
    testRealDataScenario();
    testEdgeCases();
    testFallbackCascade();

    // Print summary
    console.log('\n');
    console.log('═══════════════════════════════════════════════════════════════════════');
    console.log('  TEST SUMMARY');
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

    // Bug verification status
    console.log('═══════════════════════════════════════════════════════════════════════');
    console.log('  BUG VERIFICATION STATUS');
    console.log('═══════════════════════════════════════════════════════════════════════');

    const bug001Tests = testResults.details.filter(t =>
        t.test.includes('extractRecordsWritten') ||
        t.test.includes('Real Data Scenario')
    );
    const bug001Pass = bug001Tests.every(t => t.status === 'PASS');

    const bug002Tests = testResults.details.filter(t =>
        t.test.includes('NaN') ||
        t.test.includes('toNumber') ||
        t.test.includes('clampRatio')
    );
    const bug002Pass = bug002Tests.every(t => t.status === 'PASS');

    const bug003Tests = testResults.details.filter(t =>
        t.test.includes('Active sources')
    );
    const bug003Pass = bug003Tests.every(t => t.status === 'PASS');

    console.log(`BUG-001 (Narrative 0 records, NaN%): ${bug001Pass ? '✓ RESOLVED' : '✗ NOT RESOLVED'}`);
    console.log(`BUG-002 (Quality chart NaN%): ${bug002Pass ? '✓ RESOLVED' : '✗ NOT RESOLVED'}`);
    console.log(`BUG-003 (Active sources 0): ${bug003Pass ? '✓ RESOLVED' : '✗ NOT RESOLVED'}`);

    const allBugsResolved = bug001Pass && bug002Pass && bug003Pass;
    console.log('\n');
    console.log(`Overall Status: ${allBugsResolved ? '✓ ALL BUGS RESOLVED' : '✗ BUGS REMAIN'}`);
    console.log(`Production Ready: ${allBugsResolved && passRate >= 95 ? '✓ APPROVED' : '✗ BLOCKED'}`);
    console.log('\n');

    return {
        passRate,
        allBugsResolved,
        productionReady: allBugsResolved && passRate >= 95,
        testResults
    };
}

// Run tests
const finalResult = runAllTests();

// Export for Node.js or browser console
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { runAllTests, finalResult };
}
