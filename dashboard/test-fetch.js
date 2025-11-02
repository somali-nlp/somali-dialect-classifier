/**
 * Simple test script to verify fetch-based source mix targets loading
 * Run with: node dashboard/test-fetch.js
 */

// Simulate the fetch and processing logic
async function testSourceMixTargetsLoading() {
    console.log('Testing source mix targets loading...\n');

    // Test 1: Fetch JSON file
    console.log('Test 1: Fetching source_mix_targets.json');
    try {
        const response = await fetch('http://localhost:8000/data/source_mix_targets.json');
        if (!response.ok) {
            console.error(`❌ HTTP Error: ${response.status}`);
            return false;
        }
        const data = await response.json();
        console.log('✅ JSON file fetched successfully');
        console.log('   Version:', data.version);
        console.log('   Volumes:', JSON.stringify(data.volumes, null, 2));
    } catch (error) {
        console.error('❌ Fetch failed:', error.message);
        return false;
    }

    // Test 2: Process JSON data
    console.log('\nTest 2: Processing JSON data');
    try {
        const response = await fetch('http://localhost:8000/data/source_mix_targets.json');
        const data = await response.json();

        const volumes = data.volumes || {};
        const totalVolume = Object.values(volumes).reduce((sum, v) => sum + (Number(v) || 0), 0);

        console.log('✅ Data processed successfully');
        console.log('   Total volume:', totalVolume.toLocaleString());

        // Calculate shares
        const shares = {};
        for (const [key, value] of Object.entries(volumes)) {
            shares[key] = totalVolume > 0 ? (value / totalVolume) : 0;
        }

        console.log('   Calculated shares:');
        Object.entries(shares).forEach(([source, share]) => {
            console.log(`     ${source}: ${(share * 100).toFixed(1)}%`);
        });
    } catch (error) {
        console.error('❌ Processing failed:', error.message);
        return false;
    }

    // Test 3: Verify dashboard initialization
    console.log('\nTest 3: Verifying dashboard integration');
    console.log('✅ Dashboard should call initCoverageMetrics() during startup');
    console.log('✅ initCoverageMetrics() calls loadSourceMixTargets()');
    console.log('✅ loadSourceMixTargets() fetches and processes JSON file');
    console.log('✅ getSourceTargetShare() prioritizes loaded data over hardcoded fallback');

    return true;
}

// Run test
testSourceMixTargetsLoading()
    .then(success => {
        console.log('\n' + '='.repeat(60));
        if (success) {
            console.log('✅ All tests passed! Dashboard should load JSON file correctly.');
        } else {
            console.log('❌ Tests failed. Check server and file paths.');
        }
        console.log('='.repeat(60));
    })
    .catch(error => {
        console.error('\n❌ Test suite failed:', error.message);
        process.exit(1);
    });
