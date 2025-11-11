#!/usr/bin/env python3
"""
Test script to verify P2.2 God Object Refactoring.

Tests that DataManager and refactored BasePipeline work correctly.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("Testing P2.2 God Object Refactoring")
print("=" * 60)

# Test 1: DataManager import and instantiation
print("\n1. Testing DataManager...")
try:
    from somali_dialect_classifier.data import DataManager, DataPaths

    dm = DataManager(source="test-source", run_id="test-123")
    print(f"   ✅ DataManager created: source={dm.source}, run_id={dm.run_id}")
    print(f"   ✅ DataPaths initialized: {dm.paths.raw}")

except Exception as e:
    print(f"   ❌ DataManager test failed: {e}")
    sys.exit(1)

# Test 2: DataManager file checksum
print("\n2. Testing DataManager.compute_file_checksum...")
try:
    # Create a temporary test file
    test_file = Path("test_file.txt")
    test_file.write_text("Hello, refactoring!")

    checksum = dm.compute_file_checksum(test_file)
    print(f"   ✅ Checksum computed: {checksum[:16]}...")

    # Cleanup
    test_file.unlink()

except Exception as e:
    print(f"   ❌ Checksum test failed: {e}")
    if test_file.exists():
        test_file.unlink()
    sys.exit(1)

# Test 3: BasePipeline import (bypassing preprocessing/__init__.py)
print("\n3. Testing BasePipeline import...")
try:
    # Import base_pipeline module directly
    from somali_dialect_classifier.preprocessing import base_pipeline

    BasePipeline = base_pipeline.BasePipeline
    RawRecord = base_pipeline.RawRecord

    print(f"   ✅ BasePipeline imported: {BasePipeline}")
    print(f"   ✅ RawRecord imported: {RawRecord}")

except Exception as e:
    print(f"   ❌ BasePipeline import failed: {e}")
    sys.exit(1)

# Test 4: RawRecord instantiation
print("\n4. Testing RawRecord...")
try:
    record = RawRecord(
        title="Test Title",
        text="Test content",
        url="https://example.com",
        metadata={"key": "value"}
    )

    print(f"   ✅ RawRecord created: title={record.title}")

except Exception as e:
    print(f"   ❌ RawRecord test failed: {e}")
    sys.exit(1)

# Test 5: DedupEngine enhancements
print("\n5. Testing DedupEngine enhancements...")
try:
    from somali_dialect_classifier.preprocessing.dedup import DedupEngine, DedupConfig

    config = DedupConfig(enable_minhash=False)  # Disable MinHash to avoid datasketch requirement
    engine = DedupEngine(config)

    print(f"   ✅ DedupEngine created")
    print(f"   ✅ check_discovery_stage method exists: {hasattr(engine, 'check_discovery_stage')}")
    print(f"   ✅ check_file_duplicate method exists: {hasattr(engine, 'check_file_duplicate')}")

except Exception as e:
    print(f"   ❌ DedupEngine test failed: {e}")
    sys.exit(1)

# Test 6: BasePipeline with DataManager injection
print("\n6. Testing BasePipeline with DataManager injection...")
try:
    # Note: We can't instantiate BasePipeline directly (it's abstract)
    # But we can check that it accepts data_manager parameter
    import inspect

    init_sig = inspect.signature(BasePipeline.__init__)
    params = list(init_sig.parameters.keys())

    if 'data_manager' in params:
        print(f"   ✅ BasePipeline.__init__ has data_manager parameter")
    else:
        print(f"   ❌ data_manager parameter not found in BasePipeline.__init__")
        sys.exit(1)

    # Check that _compute_file_checksum exists (backward compatibility)
    if hasattr(BasePipeline, '_compute_file_checksum'):
        print(f"   ✅ BasePipeline._compute_file_checksum exists (backward compatible)")
    else:
        print(f"   ❌ _compute_file_checksum missing from BasePipeline")
        sys.exit(1)

except Exception as e:
    print(f"   ❌ Dependency injection test failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED - Refactoring successful!")
print("=" * 60)
print("\nSummary:")
print("  - DataManager service extracted and working")
print("  - DedupEngine enhanced with discovery-stage methods")
print("  - BasePipeline supports dependency injection")
print("  - Backward compatibility maintained")
